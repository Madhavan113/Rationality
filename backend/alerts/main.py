import asyncio
import logging
import uuid
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

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
    Fetches data from the database.
    """
    while True:
        try:
            # Get DB session
            db: Session = next(get_db())
            try:
                # Get all active alert rules from the database
                alert_rules = db.query(AlertRule).filter(AlertRule.is_active == True).all()

                for rule_orm in alert_rules:
                    rule_model = AlertRuleModel.from_orm(rule_orm)
                    await check_alert_rule(rule_model, db)
            finally:
                db.close()

            # Wait before the next check
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            await asyncio.sleep(10)

async def check_alert_rule(rule: AlertRuleModel, db: Session):
    """
    Check if an alert rule's conditions are met using data from the DB session.
    """
    try:
        # Get the latest true price from the database
        latest_true_price = db.query(TruePrice)\
            .filter(TruePrice.market_id == rule.market_id)\
            .order_by(desc(TruePrice.timestamp))\
            .first()

        if not latest_true_price:
            logger.warning(f"No true price data found for market {rule.market_id} in DB")
            return

        # Extract values
        true_price = latest_true_price.value
        mid_price = latest_true_price.mid_price

        # Calculate difference as a percentage
        if mid_price == 0:
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

            # Send email notification
            await send_alert_email(rule, notification_model)

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

            logger.info(f"Alert triggered and stored: {rule.name} - Difference: {difference:.4f}")
    except Exception as e:
        logger.error(f"Error checking alert rule {rule.id}: {e}")
        db.rollback()

async def send_alert_email(rule: AlertRuleModel, notification: AlertNotificationModel):
    """
    Send an email notification for an alert.
    """
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
            <p>Your alert rule "{rule.name}" has been triggered.</p>
            <p>Details:</p>
            <ul>
                <li>Market ID: {notification.market_id}</li>
                <li>True Price: {notification.true_price:.4f}</li>
                <li>Mid Price: {notification.mid_price:.4f}</li>
                <li>Difference: {notification.difference:.4f} ({notification.difference * 100:.2f}%)</li>
                <li>Timestamp: {notification.timestamp}</li>
            </ul>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email
        logger.info(f"Email notification sent to {rule.email} for alert {rule.name}")
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")

@app.post("/api/alerts")
async def create_alert(
    alert: AlertRuleModel,
    db: Session = Depends(get_db)
):
    """Create a new alert rule."""
    # Check if market exists
    market = db.query(Market).filter(Market.id == alert.market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # Generate ID if not provided
    if not alert.id:
        alert.id = str(uuid.uuid4())

    # Store in database
    db_alert = AlertRule(
        id=alert.id,
        name=alert.name,
        market_id=alert.market_id,
        email=alert.email,
        threshold=alert.threshold,
        condition=alert.condition
    )

    db.add(db_alert)
    db.commit()

    return {
        "id": alert.id,
        "message": "Alert rule created successfully"
    }

@app.get("/api/alerts")
async def get_alerts(db: Session = Depends(get_db)):
    """Get all alert rules."""
    alerts = db.query(AlertRule).all()
    return [
        {
            "id": alert.id,
            "name": alert.name,
            "market_id": alert.market_id,
            "email": alert.email,
            "threshold": alert.threshold,
            "condition": alert.condition,
            "is_active": alert.is_active,
            "created_at": alert.created_at
        }
        for alert in alerts
    ]

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: str, db: Session = Depends(get_db)):
    """Delete an alert rule."""
    alert = db.query(AlertRule).filter(AlertRule.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    db.delete(alert)
    db.commit()

    return {"message": "Alert rule deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )