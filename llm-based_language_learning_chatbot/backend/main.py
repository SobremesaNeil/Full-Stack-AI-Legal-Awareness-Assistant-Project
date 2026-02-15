from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas, database
from database import engine, get_db
from ai_service import get_legal_response, synthesize_dialect_audio
import json
import os
import shutil
import uuid

# 初始化数据库
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录 (用于访问上传的图片/生成的语音)
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# REST API: 会话管理
@app.post("/sessions/", response_model=schemas.Session)
def create_session(db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())
    db_session = models.Session(id=session_id)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@app.get("/sessions/{session_id}", response_model=schemas.Session)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

# REST API: 文件上传接口 (图片/语音)
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = f"static/uploads/{file_name}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"http://localhost:8000/{file_path}", "filename": file_name}

# REST API: 方言语音合成请求
@app.post("/tts/")
async def text_to_speech(text: str = Form(...), dialect: str = Form(...)):
    # 映射前端方言选项到 Azure Voice Name
    voice_map = {
        "cantonese": "zh-HK-HiuGaaiNeural",
        "sichuan": "zh-CN-Sichuan-YunxiNeural",
        "mandarin": "zh-CN-XiaoxiaoNeural"
    }
    voice = voice_map.get(dialect, "zh-CN-XiaoxiaoNeural")
    audio_url = synthesize_dialect_audio(text, voice)
    return {"audio_url": audio_url}

# WebSocket: 实时聊天
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            # 接收前端的 JSON 数据
            data = await websocket.receive_text()
            user_input = json.loads(data) 
            # 格式: { "content": "...", "type": "text/image", "url": "..." }

            # 1. 保存用户消息
            user_msg = models.Message(
                session_id=session_id,
                role="user",
                content=user_input.get("content", ""),
                message_type=user_input.get("type", "text"),
                media_url=user_input.get("url")
            )
            db.add(user_msg)
            db.commit()

            # 2. 获取 AI 回复
            history = db.query(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at).all()
            ai_result = await get_legal_response(history, user_input)

            # 3. 保存 AI 消息
            ai_msg = models.Message(
                session_id=session_id,
                role="assistant",
                content=ai_result["content"],
                message_type=ai_result["message_type"],
                media_url=ai_result["media_url"]
            )
            db.add(ai_msg)
            db.commit()

            # 4. 发送回前端
            # 4. 发送回前端 (注意这里把 media_url 改为 mediaUrl 以匹配前端)
            await websocket.send_json({
                "role": "assistant",
                "content": ai_result["content"],
                "type": ai_result["message_type"],
                "mediaUrl": ai_result["media_url"]  # <--- 修改这里: media_url -> mediaUrl
            })

    except WebSocketDisconnect:
        print(f"Session {session_id} disconnected")