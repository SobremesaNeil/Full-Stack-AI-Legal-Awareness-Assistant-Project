from fastapi import FastAPI, WebSocket, Depends, HTTPException, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import json
import uuid
import os
from datetime import datetime
import requests
from PIL import Image
from io import BytesIO
import models
import schemas
from database import engine, get_db
from models import Base
from ai_service import AIService
from pathlib import Path

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Chat API",
    description="WebSocket API for AI chat with context management",
    version="1.0.0"
)

# 存储活跃的 WebSocket 连接
active_connections: dict = {}

# 初始化 AI 服务
ai_service = AIService()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    try:
        await websocket.accept()
        active_connections[session_id] = websocket
        
        # 获取或创建聊天会话
        chat_session = db.query(models.ChatSession).filter(
            models.ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            chat_session = models.ChatSession(
                session_id=session_id,
                context=[]
            )
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)
        
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                if "content" not in message_data:
                    await websocket.send_json({
                        "role": "assistant",
                        "content": "消息格式错误，请确保包含 'content' 字段"
                    })
                    continue
                
                # 保存用户消息
                user_message = models.Message(
                    chat_session_id=chat_session.id,
                    role="user",
                    content=message_data["content"],
                    created_at=datetime.utcnow()
                )
                db.add(user_message)
                
                # 使用前端发送的上下文或数据库中的上下文
                context = message_data.get("context", chat_session.context)
                chat_session.context = context
                
                # 调用 DeepSeek API 获取响应
                assistant_response = await ai_service.get_chat_response(context)
                
                # 保存助手响应
                created_at = datetime.utcnow()
                assistant_message = models.Message(
                    chat_session_id=chat_session.id,
                    role="assistant",
                    content=assistant_response["content"],
                    created_at=created_at
                )
                db.add(assistant_message)
                
                # 更新上下文
                chat_session.context.append(assistant_response)
                
                db.commit()
                
                # 发送响应
                await websocket.send_json({
                    "role": "assistant",
                    "content": assistant_response["content"],
                    "created_at": created_at.isoformat()
                })
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "role": "assistant",
                    "content": "无效的 JSON 格式"
                })
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                await websocket.send_json({
                    "role": "assistant",
                    "content": "处理消息时发生错误，请重试"
                })
    
    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        if session_id in active_connections:
            del active_connections[session_id]
        # 不在这里显式调用 websocket.close()，让 FastAPI 处理连接关闭



# 创建保存图片的目录
IMAGE_DIR = Path("generated_images")
IMAGE_DIR.mkdir(exist_ok=True)

@app.websocket("/blankImage")
async def websocket_endpoint(websocket: WebSocket):
    # 接受 WebSocket 连接
    await websocket.accept()

    try:
        # 接收客户端参数（可选）
        params = await websocket.receive_json()

        # 解析参数或使用默认值
        width = params.get("width", 800)
        height = params.get("height", 600)
        color = params.get("color", "white")  # 支持颜色名称或十六进制
        file_format = params.get("format", "png")

        # 生成唯一文件名
        filename = f"{uuid.uuid4().hex}.{file_format}"
        save_path = IMAGE_DIR / filename
        img = Image.new(mode='RGB', size=(width, height), color=color)
        # 保存图片
        img.save(save_path)
        await websocket.send_json({
            "status": "success",
            "message": "图片生成成功",
            "path": str(save_path.absolute()),
            "size": os.path.getsize(save_path)
        })

    except Exception as e:
        await websocket.send_json({
            "status": "error",
            "message": f"生成失败: {str(e)}"
        })
    finally:
        await websocket.close()


# 运行命令：uvicorn main:app --reload

@app.websocket("/wsImage/{session_id}")
async def websocket_endpointofimage(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    try:
        await websocket.accept()
        active_connections[session_id] = websocket

        # 获取或创建聊天会话
        chat_session = db.query(models.ChatSession).filter(
            models.ChatSession.session_id == session_id
        ).first()

        if not chat_session:
            chat_session = models.ChatSession(
                session_id=session_id,
                context=[]
            )
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)

        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                if "content" not in message_data:
                    await websocket.send_json({
                        "role": "assistant",
                        "content": "消息格式错误，请确保包含 'content' 字段"
                    })
                    continue

                # 保存用户消息
                user_message = models.Message(
                    chat_session_id=chat_session.id,
                    role="user",
                    content=message_data["content"],
                    created_at=datetime.utcnow()
                )
                db.add(user_message)

                # 使用前端发送的上下文或数据库中的上下文
                context = message_data.get("context", chat_session.context)
                chat_session.context = context

                # 调用 DeepSeek API 获取响应
                image_url = await ai_service.generate_image(context)
                if image_url:
                    # 下载图片
                    response = requests.get(image_url)
                    image = Image.open(BytesIO(response.content))

                    # 保存到本地
                    image.save("image.png")
                    image.show()
                else:
                    print("生成失败，请检查提示词或API配置")


            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "role": "assistant",
                    "content": "无效的 JSON 格式"
                })
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                await websocket.send_json({
                    "role": "assistant",
                    "content": "处理消息时发生错误，请重试"
                })

    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        if session_id in active_connections:
            del active_connections[session_id]
        # 不在这里显式调用 websocket.close()，让 FastAPI 处理连接关闭
@app.post("/sessions/", response_model=schemas.ChatSession)
def create_chat_session(db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())
    chat_session = models.ChatSession(session_id=session_id)
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session

@app.get("/sessions/{session_id}", response_model=schemas.ChatSession)
def get_chat_session(session_id: str, db: Session = Depends(get_db)):
    chat_session = db.query(models.ChatSession).filter(
        models.ChatSession.session_id == session_id
    ).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_session

@app.get("/sessions/", response_model=List[schemas.ChatSession])
def list_chat_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    chat_sessions = db.query(models.ChatSession).offset(skip).limit(limit).all()
    return chat_sessions

@app.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str, db: Session = Depends(get_db)):
    chat_session = db.query(models.ChatSession).filter(
        models.ChatSession.session_id == session_id
    ).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # 删除相关的消息
    db.query(models.Message).filter(
        models.Message.chat_session_id == chat_session.id
    ).delete()
    
    # 删除会话
    db.delete(chat_session)
    db.commit()
    return {"status": "success"} 