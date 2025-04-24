from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey, Text, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from .config import get_settings

Base = declarative_base()
settings = get_settings()

# Create SQLAlchemy engine using Supabase URL
engine = create_engine(settings.supabase_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Market(Base):
    __tablename__ = "markets"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    raw_data = Column(Text, nullable=False)  # JSON string of bids/asks
    mid_price = Column(Float, nullable=False)

class TruePrice(Base):
    __tablename__ = "true_prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    value = Column(Float, nullable=False)
    mid_price = Column(Float, nullable=False)
    
class Trader(Base):
    __tablename__ = "traders"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TraderScore(Base):
    __tablename__ = "trader_scores"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_id = Column(String, ForeignKey("traders.id"), nullable=False)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    score = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
class AlertRule(Base):
    __tablename__ = "alert_rules"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    email = Column(String, nullable=False)
    threshold = Column(Float, nullable=False)
    condition = Column(String, nullable=False)  # "above" or "below"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class AlertNotification(Base):
    __tablename__ = "alert_notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_rule_id = Column(String, ForeignKey("alert_rules.id"), nullable=False)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    true_price = Column(Float, nullable=False)
    mid_price = Column(Float, nullable=False)
    difference = Column(Float, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

def init_db(use_create_all=False):
    """Initialize the database with tables.
    
    Args:
        use_create_all (bool): If True, use Base.metadata.create_all to create tables.
                               For production, this should be False and you should rely on
                               Alembic migrations (alembic upgrade head) instead.
    """
    if use_create_all:
        # Use create_all only in development or when explicitly needed
        # For production, rely on Alembic migrations instead
        Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()