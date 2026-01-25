from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, LargeBinary
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    qr_code_data = Column(String, unique=True, nullable=False)
    
    # Tutaj przechowujemy wektor twarzy (dane binarne z pickle)
    face_encoding = Column(LargeBinary, nullable=False) 
    
    photo_path = Column(String)
    is_active = Column(Boolean, default=True)

class AccessLog(Base):
    __tablename__ = 'access_logs'

    id = Column(Integer, primary_key=True)
    user_name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    status = Column(String) # np. "SUCCESS", "DENIED_QR", "DENIED_FACE"
    snapshot_path = Column(String) # Ścieżka do zdjęcia z incydentu