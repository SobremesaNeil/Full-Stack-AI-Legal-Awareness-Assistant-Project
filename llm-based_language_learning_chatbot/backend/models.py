from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid

# --- 用户体系 ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") # "user" 或 "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
    sessions = relationship("Session", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")

# --- 聊天会话 (关联到用户) ---
class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, index=True) # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # 允许游客模式，但建议登录
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

# --- 消息记录 (增强反馈和纠偏) ---
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    role = Column(String)  # user, assistant, system
    content = Column(Text) 
    message_type = Column(String, default="text") # text, image, audio, mindmap
    media_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    citations = Column(Text, nullable=True) 
    feedback_score = Column(Integer, nullable=True) # 1=赞, -1=踩
    admin_correction = Column(Text, nullable=True) # 专家纠偏后的正确答案
    is_corrected = Column(Boolean, default=False)   # 是否已被专家处理

    session = relationship("Session", back_populates="messages")

# --- 专家工单系统 (付费咨询) ---
class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(Text)
    status = Column(String, default="pending") # pending, answered, closed
    is_paid = Column(Boolean, default=False)
    
    expert_reply = Column(Text, nullable=True)
    expert_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="tickets")

class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, index=True)
    patterns = Column(Text) # 存储 JSON 字符串，例如 '["关键词1", "正则2"]'
    answer = Column(Text)   # 标准回答
    source = Column(String) # 法律依据来源
    active = Column(Boolean, default=True) # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)