import asyncio
import logging
import uuid
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from backend.common.config import get_settings
from backend.common.utils import get_db, get_from_redis
from backend.common.db import AlertRule, AlertNotification, Market, init_db
from backend.common.models import AlertRule as AlertRuleModel, AlertNotification as AlertNotificationModel

# Initialize settings and logging
settings = get_settings()
settings.service_name = "alerts"
settings.service_port = 8004

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Market Alerts Service")

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
    """
    while True:
        try:
            # Get all active alert rules
            # In a real implementation, this would query the database
            # For demo purposes, we'll use mock data
            alert_rules = await get_mock_alert_rules()
            
            for rule in alert_rules:
                await check_alert_rule(rule)
            
            # Wait before the next check
            await asyncio.sleep(5)  # Check every 5 seconds
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            await asyncio.sleep(10)  # Wait longer on error

async def get_mock_alert_rules():
    """Get mock alert rules for demonstration purposes."""
    # This would be a database query in a real implementation
    return [
        AlertRuleModel(
            id="rule1",
            name="BTC price deviation",
            market_id="1",
            email="user@example.com",
            threshold=0.05,
            condition="above"
        ),
        AlertRuleModel(
            id="rule2",
            name="ETH price deviation",
            market_id="2",
            email="user@example.com",
            threshold=0.03,
            condition="below"
        )
    ]

async def check_alert_rule(rule: AlertRuleModel):
    """
    Check if an alert rule's conditions are met and send a notification if needed.
    """
    try:
        # Get the latest true price from Redis
        redis_key = f"market:{rule.market_id}:true_price"
        true_price_data = get_from_redis(redis_key)
        
        if not true_price_data:
            logger.warning(f"No true price data found for market {rule.market_id}")
            return
        
        # Extract values
        true_price = true_price_data.get("value", 0.0)
        mid_price = true_price_data.get("mid_price", 0.0)
        
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
            # Create notification
            notification = AlertNotificationModel(
                alert_rule_id=rule.id,
                market_id=rule.market_id,
                true_price=true_price,
                mid_price=mid_price,
                difference=difference
            )
            
            # Send email notification
            await send_alert_email(rule, notification)
            
            # Store notification in database
            # In a real implementation, this would save to the database
            logger.info(f"Alert triggered: {rule.name} - Difference: {difference:.4f}")
    except Exception as e:
        logger.error(f"Error checking alert rule {rule.id}: {e}")

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
        # In a real implementation, this would actually send an email
        # For demo purposes, we'll just log it
        logger.info(f"Email notification sent to {rule.email} for alert {rule.name}")
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")

@app.post("/api/alerts")
async def create_alert(
    alert: AlertRuleModel,
    background_tasks: BackgroundTasks,
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
    
    # Immediately check the alert
    background_tasks.add_task(check_alert_rule, alert)
    
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