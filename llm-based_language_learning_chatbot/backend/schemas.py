from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class MessageBase(BaseModel):
    role: str
    content: str
    message_type: str = "text"
    media_url: Optional[str] = None

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    session_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class SessionBase(BaseModel):
    pass

class Session(SessionBase):
    id: str
    created_at: datetime
    messages: List[Message] = []

    class Config:
        from_attributes = True