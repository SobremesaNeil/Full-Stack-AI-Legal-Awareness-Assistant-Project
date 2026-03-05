import json
import os
import shutil
import uuid
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, APIRouter, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# 本地模块导入
import models
import schemas
import auth_utils
import rule_service
from database import engine, get_db, AsyncSessionLocal
from ai_service import get_legal_response, synthesize_dialect_audio
from rag_service import init_knowledge_base

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SECURITY: Validate required environment variables at startup
def validate_environment():
    """Validate required environment variables are set"""
    # DATABASE_URL has a SQLite default in database.py; only warn if not set
    if not os.getenv("DATABASE_URL"):
        logger.warning("DATABASE_URL not set; using SQLite default (not suitable for production)")
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set; AI responses will be unavailable")

    # Log environment for debugging (be careful with secrets)
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info("Environment validation passed")

# --- 生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0. 验证环境变量
    validate_environment()

    # 1. 数据库初始化
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    
    # 2. 初始化 RAG 知识库
    init_knowledge_base()
    
    # 3. 初始化默认管理员和种子规则 (修复点：使用 AsyncSessionLocal)
    async with AsyncSessionLocal() as db:
        await init_admin_user(db)
        await init_rules(db)
        
    logger.info("系统启动完成")
    yield
    logger.info("系统正在关闭")

async def init_admin_user(db: AsyncSession):
    """初始化管理员账户"""
    res = await db.execute(select(models.User).filter(models.User.username == "admin"))
    if not res.scalars().first():
        default_pwd = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")
        hp = auth_utils.get_password_hash(default_pwd)
        db.add(models.User(username="admin", hashed_password=hp, role="admin"))
        await db.commit()
        logger.info("👤 管理员已创建 (admin)")

async def init_rules(db: AsyncSession):
    """初始化规则"""
    rule_check = await db.execute(select(models.Rule))
    if not rule_check.scalars().first():
        seed_rules = rule_service.get_default_seed_rules()
        for patterns, answer, source in seed_rules:
            db.add(models.Rule(
                patterns=json.dumps(patterns, ensure_ascii=False),
                answer=answer,
                source=source
            ))
        await db.commit()
        logger.info("注入了默认种子规则")
    
    # 初始化完成后，统一加载到内存缓存中
    await rule_service.load_rules_from_db(db)

# --- App 初始化 ---
app = FastAPI(title="AI Legal Assistant", lifespan=lifespan)

# SECURITY: Configure CORS with specific allowed origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- 依赖项 ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = auth_utils.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的认证凭证")
    username = payload.get("sub")
    result = await db.execute(select(models.User).filter(models.User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

async def get_current_admin(user: models.User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="权限不足：需要管理员权限")
    return user

# ============================
# API 路由分组
# ============================

# 1. 认证模块
auth_router = APIRouter(tags=["Auth"])

@auth_router.post("/register", response_model=schemas.Token)
async def register(user_data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(models.User).filter(models.User.username == user_data.username))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="用户名已被注册")
    
    hashed_pw = auth_utils.get_password_hash(user_data.password)
    new_user = models.User(username=user_data.username, hashed_password=hashed_pw)
    db.add(new_user)
    await db.commit()
    
    access_token = auth_utils.create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.post("/token", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).filter(models.User.username == form_data.username))
    user = result.scalars().first()
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    access_token = auth_utils.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# 2. 规则管理模块 (Admin)
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

@admin_router.get("/rules", response_model=List[schemas.Rule])
async def get_rules(admin: models.User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Rule).order_by(models.Rule.id.desc()))
    rules = result.scalars().all()
    for r in rules:
        try:
            r.patterns = json.loads(r.patterns)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse rule patterns: {e}")
            r.patterns = [] 
    return rules

@admin_router.post("/rules", response_model=schemas.Rule)
async def create_rule(rule: schemas.RuleCreate, admin: models.User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    db_rule = models.Rule(
        patterns=json.dumps(rule.patterns, ensure_ascii=False),
        answer=rule.answer,
        source=rule.source,
        active=rule.active
    )
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)
    await rule_service.load_rules_from_db(db)
    db_rule.patterns = json.loads(db_rule.patterns)
    return db_rule

@admin_router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, admin: models.User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Rule).filter(models.Rule.id == rule_id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    db.delete(rule)
    await db.commit()
    await rule_service.load_rules_from_db(db)
    return {"status": "deleted"}

# 3. 聊天与会话模块
chat_router = APIRouter(tags=["Chat"])

@chat_router.post("/sessions/", response_model=schemas.Session)
async def create_session(db: AsyncSession = Depends(get_db)):
    session_id = str(uuid.uuid4())
    db_session = models.Session(id=session_id)
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session

@chat_router.get("/sessions/", response_model=List[schemas.Session])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Session)
        .options(selectinload(models.Session.messages))
        .order_by(models.Session.created_at.desc())
    )
    sessions = result.scalars().all()
    return sessions

@chat_router.get("/sessions/{session_id}", response_model=schemas.Session)
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

@chat_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Session).filter(models.Session.id == session_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return {"status": "deleted"}

@chat_router.post("/feedback/")
async def submit_feedback(feedback: schemas.FeedbackCreate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(models.Message).filter(models.Message.id == feedback.message_id))
        msg = result.scalars().first()
        if not msg:
            raise HTTPException(404, "Message not found")
        msg.feedback_score = feedback.score
        await db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        await db.rollback()
        raise HTTPException(500, "Failed to submit feedback")
    finally:
        await db.close()

# 4. 工单系统与文件上传
misc_router = APIRouter(tags=["Misc"])

@misc_router.post("/upload/")
async def upload_file(request: Request, file: UploadFile = File(...)):
    # Configuration
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "wav"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

    filename = file.filename or "unknown"

    # Validate file extension
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: .{ext}")

    # Validate file size (read file to check size)
    file_size = 0
    file_content = b""
    chunk_size = 8192

    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(413, f"文件不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB")
            file_content += chunk
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件读取失败: {e}")
        raise HTTPException(500, "文件读取失败")

    new_filename = f"{uuid.uuid4()}.{ext}"
    file_path = f"static/uploads/{new_filename}"

    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(500, "文件保存失败")

    base_url = str(request.base_url).rstrip("/")
    # Use proper URL joining instead of f-string
    return {"url": f"{base_url}/static/uploads/{new_filename}", "filename": new_filename}

@misc_router.post("/tickets/", response_model=schemas.Ticket)
async def create_ticket(ticket: schemas.TicketCreate, user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
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

@misc_router.get("/admin/tickets", response_model=List[schemas.Ticket])
async def get_all_tickets(admin: models.User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Ticket).order_by(models.Ticket.created_at.desc()))
    return result.scalars().all()

@misc_router.put("/admin/tickets/{ticket_id}", response_model=schemas.Ticket)
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

@misc_router.post("/tts/")
async def tts_endpoint(text: str = Form(...), dialect: str = Form(...)):
    v_map = {
        "cantonese": "zh-HK-HiuGaaiNeural", 
        "sichuan": "zh-CN-Sichuan-YunxiNeural", 
        "mandarin": "zh-CN-XiaoxiaoNeural"
    }
    url = await synthesize_dialect_audio(text, v_map.get(dialect, "zh-CN-XiaoxiaoNeural"))
    if not url: 
        raise HTTPException(500, "TTS 生成失败")
    return {"audio_url": url}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                user_input = json.loads(data)
                # 新增防御：确保传入的是 JSON 字典
                if not isinstance(user_input, dict):
                    raise ValueError("Payload is not a dictionary")
            except Exception:
                await websocket.send_json({"role": "system", "content": "错误：消息格式必须为 JSON 对象", "type": "error"})
                continue
            
            # 作用域内临时申请 DB Session
            async with AsyncSessionLocal() as db:
                user_msg = models.Message(
                    session_id=session_id, 
                    role="user", 
                    content=user_input.get("content", ""), 
                    message_type=user_input.get("type", "text"), 
                    media_url=user_input.get("url")
                )
                db.add(user_msg)
                await db.commit()

                hist_res = await db.execute(
                    select(models.Message)
                    .filter(models.Message.session_id == session_id)
                    .order_by(models.Message.created_at)
                )
                history = hist_res.scalars().all()

                try:
                    ai_res = await get_legal_response(history, user_input)
                except Exception as e:
                    logger.error(f"AI Service Error: {e}")
                    ai_res = {"content": "系统繁忙，请稍后再试。", "message_type": "text", "media_url": None}

                ai_msg = models.Message(
                    session_id=session_id, 
                    role="assistant", 
                    content=ai_res["content"], 
                    message_type=ai_res["message_type"], 
                    media_url=ai_res["media_url"], 
                    citations=ai_res.get("citations")
                )
                db.add(ai_msg)
                await db.commit()

            # 发送给前端
            await websocket.send_json({
                "role": "assistant", 
                "content": ai_res["content"], 
                "type": ai_res["message_type"], 
                "mediaUrl": ai_res["media_url"],
                "citations": ai_res.get("citations"),
                "messageId": ai_msg.id
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        try:
            await websocket.close(code=1011)
        except RuntimeError as close_error:
            logger.warning(f"Failed to close WebSocket: {close_error}")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(misc_router)