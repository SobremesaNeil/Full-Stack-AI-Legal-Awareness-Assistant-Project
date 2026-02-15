from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import models, schemas
from database import engine, get_db
from ai_service import get_legal_response, synthesize_dialect_audio
import json
import os
import shutil
import uuid
from contextlib import asynccontextmanager

# 生命周期管理：启动时创建数据库表
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # 在异步模式下执行同步的建表操作
        await conn.run_sync(models.Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 异步 Session API ---
@app.post("/sessions/", response_model=schemas.Session)
async def create_session(db: AsyncSession = Depends(get_db)):
    session_id = str(uuid.uuid4())
    db_session = models.Session(id=session_id)
    db.add(db_session)
    await db.commit()       # 异步提交
    await db.refresh(db_session) # 异步刷新
    return db_session

@app.get("/sessions/{session_id}", response_model=schemas.Session)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    # 异步查询语法：select(...)
    result = await db.execute(select(models.Session).filter(models.Session.id == session_id))
    session = result.scalars().first()
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 由于是异步加载，relationship 默认是 lazy load，需要小心。
    # 为了简单起见，我们手动加载 messages 或者在 models 里配置 eager load。
    # 这里为了演示，我们单独查一下消息 (更稳妥的做法)
    msg_result = await db.execute(
        select(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
    )
    session.messages = msg_result.scalars().all()
    
    return session

# --- 文件上传 (已经是 async，无需大改，但建议用 aiofiles) ---
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = f"static/uploads/{file_name}"
    
    # 简单写法，如果文件很大，建议用 aiofiles
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"http://localhost:8000/{file_path}", "filename": file_name}

@app.post("/tts/")
async def text_to_speech(text: str = Form(...), dialect: str = Form(...)):
    voice_map = {
        "cantonese": "zh-HK-HiuGaaiNeural",
        "sichuan": "zh-CN-Sichuan-YunxiNeural",
        "mandarin": "zh-CN-XiaoxiaoNeural"
    }
    voice = voice_map.get(dialect, "zh-CN-XiaoxiaoNeural")
    # 现在调用的是异步非阻塞版本
    audio_url = await synthesize_dialect_audio(text, voice)
    if not audio_url:
         raise HTTPException(status_code=500, detail="TTS Generation Failed")
    return {"audio_url": audio_url}

# --- 核心：WebSocket 异步改造 ---
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            user_input = json.loads(data) 

            # 1. 保存用户消息
            user_msg = models.Message(
                session_id=session_id,
                role="user",
                content=user_input.get("content", ""),
                message_type=user_input.get("type", "text"),
                media_url=user_input.get("url")
            )
            db.add(user_msg)
            await db.commit() # 异步提交

            # 2. 获取历史记录 (异步查询)
            result = await db.execute(
                select(models.Message)
                .filter(models.Message.session_id == session_id)
                .order_by(models.Message.created_at)
            )
            history = result.scalars().all()

            # 3. 获取 AI 回复 (传入历史对象列表)
            ai_result = await get_legal_response(history, user_input)

            # 4. 保存 AI 消息
            ai_msg = models.Message(
                session_id=session_id,
                role="assistant",
                content=ai_result["content"],
                message_type=ai_result["message_type"],
                media_url=ai_result["media_url"]
            )
            db.add(ai_msg)
            await db.commit() 

            # 5. 发送回前端
            await websocket.send_json({
                "role": "assistant",
                "content": ai_result["content"],
                "type": ai_result["message_type"],
                "mediaUrl": ai_result["media_url"]
            })

    except WebSocketDisconnect:
        print(f"Session {session_id} disconnected")
    except Exception as e:
        print(f"Error in websocket: {e}")
        # 发送错误提示给前端，而不是直接断开
        try:
            await websocket.send_json({
                "role": "system",
                "content": "服务器遇到错误，请稍后重试。",
                "type": "error"
            })
        except:
            pass