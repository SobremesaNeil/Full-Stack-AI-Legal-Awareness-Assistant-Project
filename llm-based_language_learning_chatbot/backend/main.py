from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import models, schemas, auth_utils
from database import engine, get_db
from ai_service import get_legal_response, synthesize_dialect_audio
from rag_service import init_knowledge_base
import json, os, shutil, uuid
from contextlib import asynccontextmanager

# 生命周期：初始化数据库 + 向量库 + 默认管理员
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 数据库建表
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    
    # 2. 初始化 RAG 知识库
    init_knowledge_base()
    
    # 3. 创建默认管理员 (admin/admin123) - 仅作演示，生产环境请删除
    async with AsyncSession(engine) as db:
        result = await db.execute(select(models.User).filter(models.User.username == "admin"))
        if not result.scalars().first():
            hashed_pw = auth_utils.get_password_hash("admin123")
            admin_user = models.User(username="admin", hashed_password=hashed_pw, role="admin")
            db.add(admin_user)
            await db.commit()
            print("默认管理员已创建: admin / admin123")
    yield

app = FastAPI(lifespan=lifespan)

# CORS & Static
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- 依赖项：获取当前用户 ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = auth_utils.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    username = payload.get("sub")
    result = await db.execute(select(models.User).filter(models.User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_current_admin(user: models.User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user

# --- API: Auth ---
@app.post("/register", response_model=schemas.Token)
async def register(user_data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # 检查重名
    existing = await db.execute(select(models.User).filter(models.User.username == user_data.username))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pw = auth_utils.get_password_hash(user_data.password)
    new_user = models.User(username=user_data.username, hashed_password=hashed_pw)
    db.add(new_user)
    await db.commit()
    
    access_token = auth_utils.create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).filter(models.User.username == form_data.username))
    user = result.scalars().first()
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = auth_utils.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- API: Chat Sessions (支持匿名 + 登录) ---
@app.post("/sessions/", response_model=schemas.Session)
async def create_session(db: AsyncSession = Depends(get_db)):
    # 简化：允许匿名创建，暂不强制绑定 user_id
    session_id = str(uuid.uuid4())
    db_session = models.Session(id=session_id)
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session

@app.get("/sessions/{session_id}", response_model=schemas.Session)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Session).filter(models.Session.id == session_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    msg_result = await db.execute(
        select(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
    )
    session.messages = msg_result.scalars().all()
    return session

# --- API: Feedback & Correction (闭环核心) ---
@app.post("/feedback/")
async def submit_feedback(feedback: schemas.FeedbackCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Message).filter(models.Message.id == feedback.message_id))
    msg = result.scalars().first()
    if not msg:
        raise HTTPException(404, "Message not found")
    
    msg.feedback_score = feedback.score
    await db.commit()
    return {"status": "success"}

@app.post("/admin/correct")
async def admin_correct_answer(correction: schemas.CorrectionCreate, admin: models.User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Message).filter(models.Message.id == correction.message_id))
    msg = result.scalars().first()
    if not msg:
        raise HTTPException(404, "Message not found")
    
    msg.admin_correction = correction.correction_content
    msg.is_corrected = True
    await db.commit()
    # TODO: 这里可以触发一个后台任务，把 <msg.content(User), correction.correction_content> 加入微调数据集
    return {"status": "corrected"}

# --- API: Expert Tickets (付费咨询) ---
@app.post("/tickets/", response_model=schemas.Ticket)
async def create_ticket(ticket: schemas.TicketCreate, user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 实际项目中这里应接支付网关，支付成功后才创建
    new_ticket = models.Ticket(
        user_id=user.id,
        title=ticket.title,
        description=ticket.description,
        is_paid=True
    )
    db.add(new_ticket)
    await db.commit()
    await db.refresh(new_ticket)
    return new_ticket

@app.get("/admin/tickets", response_model=list[schemas.Ticket])
async def get_all_tickets(admin: models.User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Ticket).order_by(models.Ticket.created_at.desc()))
    return result.scalars().all()

@app.put("/admin/tickets/{ticket_id}", response_model=schemas.Ticket)
async def reply_ticket(ticket_id: int, update: schemas.TicketUpdate, admin: models.User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Ticket).filter(models.Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    
    ticket.expert_reply = update.expert_reply
    ticket.status = update.status
    ticket.expert_id = admin.id
    await db.commit()
    await db.refresh(ticket)
    return ticket

# --- 辅助接口 ---
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    ALLOWED = {"png", "jpg", "jpeg", "wav"}
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED:
        raise HTTPException(400, "File type not allowed")
    
    fname = f"{uuid.uuid4()}.{ext}"
    fpath = f"static/uploads/{fname}"
    with open(fpath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"http://localhost:8000/{fpath}", "filename": fname}

@app.post("/tts/")
async def tts_endpoint(text: str = Form(...), dialect: str = Form(...)):
    # 简化的 Voice Map
    v_map = {"cantonese": "zh-HK-HiuGaaiNeural", "sichuan": "zh-CN-Sichuan-YunxiNeural", "mandarin": "zh-CN-XiaoxiaoNeural"}
    url = await synthesize_dialect_audio(text, v_map.get(dialect, "zh-CN-XiaoxiaoNeural"))
    if not url: raise HTTPException(500, "TTS Failed")
    return {"audio_url": url}

# --- WebSocket (保持原逻辑，但加上异常处理) ---
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                user_input = json.loads(data)
            except:
                continue

            # 存用户消息
            user_msg = models.Message(session_id=session_id, role="user", content=user_input.get("content"), message_type=user_input.get("type"), media_url=user_input.get("url"))
            db.add(user_msg)
            await db.commit()

            # 查历史
            hist_res = await db.execute(select(models.Message).filter(models.Message.session_id == session_id).order_by(models.Message.created_at))
            history = hist_res.scalars().all()

            # AI 回答 (带 RAG)
            ai_res = await get_legal_response(history, user_input)

            # 存 AI 消息 (含 Citation)
            ai_msg = models.Message(
                session_id=session_id, role="assistant", 
                content=ai_res["content"], message_type=ai_res["message_type"], 
                media_url=ai_res["media_url"], citations=ai_res.get("citations")
            )
            db.add(ai_msg)
            await db.commit()

            # 推送
            await websocket.send_json({
                "role": "assistant", "content": ai_res["content"], 
                "type": ai_res["message_type"], "mediaUrl": ai_res["media_url"],
                "citations": ai_res.get("citations"),
                "messageId": ai_msg.id # 返回 ID 供前端点踩使用
            })
    except WebSocketDisconnect:
        pass