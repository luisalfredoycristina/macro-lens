from sqlalchemy import Column, String, Numeric, Date, DateTime, Boolean, Integer, JSON, Text
from sqlalchemy.sql import func
from .database import Base

class MacroSeries(Base):
    __tablename__ = "macro_series"

    series_id = Column(String(80), primary_key=True)
    country_code = Column(String(3), primary_key=True, default="USA")
    observation_date = Column(Date, primary_key=True)
    value = Column(Numeric(20, 6), nullable=True)
    source = Column(String(10), nullable=False)  # 'FRED' or 'WORLDBANK'
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_revised = Column(Boolean, default=False)


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_name = Column(String(100), nullable=False)
    fired_at = Column(DateTime(timezone=True), server_default=func.now())
    direction = Column(String(20))       # BULLISH, BEARISH, NEUTRAL
    conviction = Column(Integer)         # 1-3
    trade_implication = Column(Text)
    data_snapshot = Column(JSON)
    alert_sent = Column(Boolean, default=False)


class AlertConfig(Base):
    __tablename__ = "alert_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), nullable=True)
    webhook_url = Column(String(500), nullable=True)
    cooldown_hours = Column(Integer, default=24)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
