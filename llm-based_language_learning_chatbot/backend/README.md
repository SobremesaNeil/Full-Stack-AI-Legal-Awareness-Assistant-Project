# AI Chat Backend

基于 FastAPI 的 AI 聊天后端服务，支持 WebSocket 实时通信和聊天上下文管理。

## 功能特性

- WebSocket 实时聊天
- 聊天上下文管理
- PostgreSQL 数据存储
- RESTful API 接口

## 技术栈

- FastAPI
- SQLAlchemy
- PostgreSQL
- WebSocket
- OpenAI GPT-4

## 安装

1. 克隆项目并进入项目目录：
```bash
git clone <repository_url>
cd backend
```

2. 创建并激活虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置信息
```

5. 创建数据库：
```bash
createdb chatbot
```

## 运行

启动开发服务器：
```bash
uvicorn main:app --reload
```

服务器将在 http://localhost:8000 运行

## API 文档

启动服务器后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### WebSocket
- `ws://localhost:8000/ws/{session_id}` - WebSocket 聊天连接

### REST API
- `POST /sessions/` - 创建新的聊天会话
- `GET /sessions/{session_id}` - 获取特定会话信息
- `GET /sessions/` - 获取所有会话列表

## 开发

1. 确保已安装所有依赖
2. 配置正确的环境变量
3. 运行数据库迁移（如果需要）
4. 启动开发服务器

## 许可证

MIT 