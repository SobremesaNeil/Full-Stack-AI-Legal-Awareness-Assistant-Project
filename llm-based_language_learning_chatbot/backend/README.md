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

## 运行（Mock 模式 – 无需数据库或 AI 密钥）

Mock 模式使用 **SQLite**（自动创建本地文件）代替 PostgreSQL，并返回预设的法律问答，无需任何外部服务或 API 密钥。

```bash
# 1. 将 Mock 环境文件复制为 .env
cp .env.mock .env

# 2. 安装依赖（aiosqlite 已包含在 requirements.txt 中）
pip install -r requirements.txt

# 3. 启动开发服务器
uvicorn main:app --reload
```

服务器将在 http://localhost:8000 运行，返回预设的 AI 回复，无需真实的 OpenAI 密钥。

### Mock 模式环境变量说明

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./chatbot_mock.db` – 使用本地 SQLite 文件 |
| `MOCK_AI` | `true` – 跳过 OpenAI 调用，返回预置法律回复 |
| `ADMIN_DEFAULT_PASSWORD` | 管理员初始密码（需含大写+小写+数字） |

## 运行（正式模式）

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