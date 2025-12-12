from sqlalchemy import Column, Integer, String, DateTime, PickleType, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    qr_code_data = Column(String(100), unique=True, nullable=False)
    face_encoding = Column(PickleType, nullable=False)
    photo_path = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)

class AccessLog(Base):
    __tablename__ = 'access_logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    user_name = Column(String(100))
    status = Column(String(20))
    snapshot_path = Column(String(200), nullable=True)