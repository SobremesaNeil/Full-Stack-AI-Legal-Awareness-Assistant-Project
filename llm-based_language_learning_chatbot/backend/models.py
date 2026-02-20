from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone
import uuid

# 【修复重点】：Python 3.12+ 建议使用 datetime.now(timezone.utc) 代替 datetime.utcnow()
def get_utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") 
    created_at = Column(DateTime, default=get_utc_now)
    sessions = relationship("Session", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, index=True) 
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    role = Column(String)  
    content = Column(Text) 
    message_type = Column(String, default="text") 
    media_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    citations = Column(Text, nullable=True) 
    feedback_score = Column(Integer, nullable=True) 
    admin_correction = Column(Text, nullable=True) 
    is_corrected = Column(Boolean, default=False)   

    session = relationship("Session", back_populates="messages")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(Text)
    status = Column(String, default="pending") 
    is_paid = Column(Boolean, default=False)
    
    expert_reply = Column(Text, nullable=True)
    expert_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    user = relationship("User", foreign_keys=[user_id], back_populates="tickets")

class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, index=True)
    patterns = Column(Text) 
    answer = Column(Text)   
    source = Column(String) 
    active = Column(Boolean, default=True) 
    created_at = Column(DateTime, default=get_utc_now)