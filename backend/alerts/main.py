import asyncio
import logging
import uuid
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from backend.common.config import get_settings
from backend.common.db import AlertRule, AlertNotification, Market, TruePrice, init_db, get_db
from backend.common.models import AlertRule as AlertRuleModel, AlertNotification as AlertNotificationModel

# Initialize settings and logging
settings = get_settings()
settings.service_name = "alerts"
settings.service_port = 8004

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Market Alerts Service")

# Define allowed origins for CORS
allowed_origins = [
    "http://localhost:3000",  # Allow local development frontend
    "https://app.yourdomain.com"  # Production frontend URL
]

# Add CORS middleware with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize database
init_db()

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.service_name}

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    asyncio.create_task(check_alerts())

async def check_alerts():
    """
    Background task to check for alert conditions and send notifications.
    Fetches data from the database using a single session per cycle.
    """
    while True:
        db: Session = next(get_db())
        try:
            # Get all active alert rules from the database
            alert_rules = db.query(AlertRule).filter(AlertRule.is_active == True).all()
            if not alert_rules:
                pass # No rules to check
            else:
                logger.info(f"Checking {len(alert_rules)} active alert rules...")
                tasks = [check_alert_rule(AlertRuleModel.from_orm(rule_orm), db) for rule_orm in alert_rules]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Error checking alert rule ID {alert_rules[i].id}: {result}")

        except SQLAlchemyError as e:
            logger.error(f"Database error fetching alert rules: {e}")
        except Exception as e:
            logger.error(f"Error during alert checking cycle: {e}", exc_info=True)
        finally:
            db.close()

        await asyncio.sleep(5)

async def check_alert_rule(rule: AlertRuleModel, db: Session):
    """
    Check if an alert rule's conditions are met using data from the DB session.
    Handles potential errors during the check.
    """
    try:
        # Get the latest true price from the database
        latest_true_price = db.query(TruePrice)\
            .filter(TruePrice.market_id == rule.market_id)\
            .order_by(desc(TruePrice.timestamp))\
            .first()

        if not latest_true_price:
            return

        # Extract values
        true_price = latest_true_price.value
        mid_price = latest_true_price.mid_price

        # Avoid division by zero or invalid calculations
        if mid_price is None or mid_price == 0 or true_price is None:
            return

        difference = abs(true_price - mid_price) / mid_price

        # Check if the threshold is exceeded
        threshold_exceeded = False
        if rule.condition == "above" and difference > rule.threshold:
            threshold_exceeded = True
        elif rule.condition == "below" and difference < rule.threshold:
            threshold_exceeded = True

        if threshold_exceeded:
            # Create notification model
            notification_model = AlertNotificationModel(
                alert_rule_id=rule.id,
                market_id=rule.market_id,
                true_price=true_price,
                mid_price=mid_price,
                difference=difference,
                timestamp=datetime.utcnow()
            )

            # Send email notification (non-blocking)
            asyncio.create_task(send_alert_email(rule, notification_model))

            # Store notification in database
            db_notification = AlertNotification(
                alert_rule_id=notification_model.alert_rule_id,
                market_id=notification_model.market_id,
                true_price=notification_model.true_price,
                mid_price=notification_model.mid_price,
                difference=notification_model.difference,
                sent_at=notification_model.timestamp
            )
            db.add(db_notification)
            db.commit()

            logger.info(f"Alert triggered and stored: {rule.name} (Rule ID: {rule.id}) - Difference: {difference:.4f}")

    except SQLAlchemyError as e:
        logger.error(f"Database error checking/storing notification for alert rule {rule.id}: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error checking alert rule {rule.id}: {e}", exc_info=True)
        db.rollback()
        raise

async def send_alert_email(rule: AlertRuleModel, notification: AlertNotificationModel, max_retries=3, initial_delay=1):
    """
    Send an email notification for an alert with retry logic.
    
    Args:
        rule: The alert rule that was triggered
        notification: The notification details
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds between retries, doubles on each retry (default: 1)
    """
    retries = 0
    delay = initial_delay
    
    while retries <= max_retries:
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.email_from
            msg['To'] = rule.email
            msg['Subject'] = f"Market Alert: {rule.name}"

            # Create message body
            body = f"""
            <html>
            <body>
                <h2>Market Alert Notification</h2>
                <p>Your alert rule "{rule.name}" (ID: {rule.id}) has been triggered.</p>
                <p>Details:</p>
                <ul>
                    <li>Market ID: {notification.market_id}</li>
                    <li>True Price: {notification.true_price:.4f}</li>
                    <li>Mid Price: {notification.mid_price:.4f}</li>
                    <li>Difference: {notification.difference:.4f} ({notification.difference * 100:.2f}%)</li>
                    <li>Threshold: {rule.threshold} ({rule.condition})</li>
                    <li>Timestamp: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
                </ul>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))

            # Send email using configured SMTP settings
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_user and settings.smtp_password:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.email_from, rule.email, msg.as_string())
                logger.info(f"Email notification sent to {rule.email} for alert {rule.name} (Rule ID: {rule.id})")
                
                # Success, so exit the retry loop
                return True

        except smtplib.SMTPServerDisconnected as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Failed to connect to SMTP server after {max_retries} attempts for alert {rule.id}: {e}")
                return False
                
            logger.warning(f"SMTP server disconnected, retrying ({retries}/{max_retries}) in {delay}s: {e}")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
            
        except smtplib.SMTPException as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"SMTP error sending email for alert {rule.id} after {max_retries} attempts: {e}")
                return False
                
            logger.warning(f"SMTP error, retrying ({retries}/{max_retries}) in {delay}s: {e}")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
            
        except Exception as e:
            logger.error(f"Unexpected error sending email for alert {rule.id}: {e}", exc_info=True)
            # For unexpected errors, don't retry as they're likely to fail again
            return False
            
    return False  # If we get here, all retries failed

@app.post("/api/alerts", response_model=AlertRuleModel)
async def create_alert(
    alert: AlertRuleModel,
    db: Session = Depends(get_db)
):
    """Create a new alert rule."""
    try:
        # Check if market exists
        market = db.query(Market).filter(Market.id == alert.market_id).first()
        if not market:
            raise HTTPException(status_code=404, detail=f"Market with ID '{alert.market_id}' not found")

        # Generate ID if not provided
        if not alert.id:
            alert.id = str(uuid.uuid4())

        # Validate condition
        if alert.condition not in ["above", "below"]:
            raise HTTPException(status_code=400, detail="Condition must be 'above' or 'below'")

        # Validate threshold
        if not (0 < alert.threshold < 1):
             raise HTTPException(status_code=400, detail="Threshold must be between 0 and 1 (exclusive)")

        # Store in database
        db_alert = AlertRule(
            id=alert.id,
            name=alert.name,
            market_id=alert.market_id,
            email=alert.email,
            threshold=alert.threshold,
            condition=alert.condition,
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        logger.info(f"Created alert rule {db_alert.id}: {db_alert.name}")
        return AlertRuleModel.from_orm(db_alert)

    except SQLAlchemyError as e:
        logger.error(f"Database error creating alert rule: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create alert rule in database")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error creating alert rule: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        pass

@app.get("/api/alerts", response_model=List[AlertRuleModel])
async def get_alerts(db: Session = Depends(get_db)):
    """Get all alert rules."""
    try:
        alerts_orm = db.query(AlertRule).all()
        return [AlertRuleModel.from_orm(alert) for alert in alerts_orm]
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving alert rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alert rules")
    except Exception as e:
        logger.error(f"Unexpected error retrieving alert rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        pass

@app.delete("/api/alerts/{alert_id}", status_code=204)
async def delete_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete an alert rule."""
    try:
        alert = db.query(AlertRule).filter(AlertRule.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        db.delete(alert)
        db.commit()
        logger.info(f"Deleted alert rule {alert_id}")
        return

    except SQLAlchemyError as e:
        logger.error(f"Database error deleting alert rule {alert_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete alert rule")
    except Exception as e:
        logger.error(f"Unexpected error deleting alert rule {alert_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
    finally:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )