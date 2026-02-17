from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any

# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

# --- Chat ---
class MessageBase(BaseModel):
    role: str
    content: str
    message_type: str = "text"
    media_url: Optional[str] = None
    citations: Optional[str] = None

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    session_id: str
    created_at: datetime
    feedback_score: Optional[int] = None
    admin_correction: Optional[str] = None

    class Config:
        from_attributes = True

class Session(BaseModel):
    id: str
    created_at: datetime
    messages: List[Message] = []

    class Config:
        from_attributes = True

# --- Ticket ---
class TicketCreate(BaseModel):
    title: str
    description: str

class TicketUpdate(BaseModel):
    expert_reply: str
    status: str

class Ticket(BaseModel):
    id: int
    title: str
    description: str
    status: str
    expert_reply: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Feedback ---
class FeedbackCreate(BaseModel):
    message_id: int
    score: int # 1 or -1

class CorrectionCreate(BaseModel):
    message_id: int
    correction_content: str

class RuleBase(BaseModel):
    patterns: List[str] # 前端传数组，后端存 JSON
    answer: str
    source: str
    active: bool = True

class RuleCreate(RuleBase):
    pass

class RuleUpdate(RuleBase):
    pass

class Rule(RuleBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True