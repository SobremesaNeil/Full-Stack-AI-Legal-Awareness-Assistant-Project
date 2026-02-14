from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class MessageBase(BaseModel):
    role: str
    content: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    chat_session_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, json_encoders={datetime: lambda dt: dt.isoformat()})

class ChatSessionBase(BaseModel):
    session_id: str

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSession(ChatSessionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    context: List[dict]
    messages: List[Message] = []

    model_config = ConfigDict(from_attributes=True, json_encoders={datetime: lambda dt: dt.isoformat()}) 