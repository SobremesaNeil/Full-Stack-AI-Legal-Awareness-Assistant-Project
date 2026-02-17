import os
from openai import AsyncOpenAI
# import azure.cognitiveservices.speech as speechsdk # 暂时注释，避免无环境报错
from fastapi.concurrency import run_in_threadpool
from rag_service import search_knowledge
# 引入规则引擎
from rule_service import check_rules

SYSTEM_PROMPT = """
你是一名资深的中国法律顾问“普法小助手”。
你的回答机制遵循“规则优先 + 语义分析”原则。
请基于用户提供的问题和【相关法律依据】进行回答。
1. 严禁自我编造具体的刑期、罚款数额等硬性数据。
2. 如果用户问题模糊，请进行追问。
3. 如果用户上传图片，请分析法律风险。
"""

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 注意：这里假设你原来的 TTS 代码依然存在于文件中，为保持完整性请不要删除

async def get_legal_response(history: list, latest_input: dict):
    text_content = latest_input.get("content", "")
    
    # === 1. Level 1: 规则引擎极速拦截 ===
    if text_content and latest_input.get("type") == "text":
        # 直接查内存，无需 await
        rule_ans, rule_src = check_rules(text_content)
        if rule_ans:
            print(f"⚡ 规则引擎命中: {rule_src}")
            return {
                "content": rule_ans,
                "message_type": "text",
                "media_url": None,
                "citations": f"【系统速查 - {rule_src}】\n(注：此回复基于专家规则库自动匹配)"
            }

    # === 2. Level 2: AI + RAG 兜底 ===
    citations = []
    rag_context = ""
    if text_content and latest_input.get("type") == "text":
        try:
            knowledge_docs = await run_in_threadpool(search_knowledge, text_content)
            if knowledge_docs:
                rag_context = "\n\n【相关法律依据 (RAG检索)】:\n" + "\n".join(knowledge_docs)
                citations = knowledge_docs
        except Exception as e:
            print(f"RAG Error: {e}")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # --- 核心修复逻辑开始 ---
    # 1. 过滤重复消息：如果数据库历史记录的最后一条与当前输入相同，则切片排除最后一条
    effective_history = history
    if history and history[-1].content == text_content:
        effective_history = history[:-1]
    
    # 2. 取最近 10 条上下文
    recent_history = effective_history[-10:]
    
    # 3. 构造消息列表
    for msg in recent_history:
        messages.append({"role": msg.role, "content": msg.content})
    # --- 核心修复逻辑结束 ---

    full_user_content = text_content
    if rag_context:
        full_user_content += rag_context
        
    user_payload = full_user_content
    if latest_input.get("type") == "image":
        user_payload = [
            {"type": "text", "text": "请分析这张图片中的法律风险。"},
            {"type": "image_url", "image_url": {"url": latest_input.get("url")}}
        ]

    messages.append({"role": "user", "content": user_payload})

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3
        )
        ai_text = response.choices[0].message.content
        
        return {
            "content": ai_text,
            "message_type": "text",
            "media_url": None,
            "citations": "\n".join(citations) if citations else None
        }
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return {
            "content": "系统思考超时，请检查 API Key 或网络连接。", 
            "message_type": "text", 
            "media_url": None
        }

# 请保留原有的 TTS 相关函数（synthesize_dialect_audio 等）
async def synthesize_dialect_audio(text, voice):
    # 占位符，防止 main.py 导入报错
    return None