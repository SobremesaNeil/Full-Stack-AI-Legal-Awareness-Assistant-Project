import os
import asyncio
import base64
import logging
import itertools
from openai import AsyncOpenAI
from fastapi.concurrency import run_in_threadpool
from rag_service import search_knowledge
from rule_service import check_rules

# Configure logger
logger = logging.getLogger(__name__)

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

MOCK_RESPONSES = [
    "根据《中华人民共和国合同法》第八条，依法成立的合同，对当事人具有法律约束力。建议您保留好合同原件及相关证据。",
    "您好！根据您的问题，建议您咨询专业律师以获取针对性法律意见。如需了解更多，请提供详细情况。",
    "【模拟回复】这是一个测试回复，用于演示系统功能。在实际使用中，本系统将调用 AI 模型提供专业法律建议。",
    "根据《劳动合同法》相关规定，劳动者依法享有相应权益保障。建议您收集并保存相关证据，必要时可申请劳动仲裁。",
    "根据您描述的情况，建议您：1. 保留相关证据；2. 尝试协商解决；3. 如协商失败，可通过法律途径维权。",
]

# Use itertools.cycle so index advancement is stateless and naturally
# round-robins without needing a mutable global counter.
_mock_cycle = itertools.cycle(MOCK_RESPONSES)

async def get_mock_legal_response(latest_input: dict) -> dict:
    """Return a pre-defined mock response without calling any external API."""
    text = latest_input.get("content", "")
    input_type = latest_input.get("type", "text")

    if input_type == "image":
        content = "【模拟图片分析】系统已收到您上传的图片。在 Mock 模式下，图片内容分析功能不可用。请配置真实的 AI 服务后使用此功能。"
    else:
        base_response = next(_mock_cycle)
        content = (
            f"【模拟回复 - 针对您的问题「{text[:30]}{'...' if len(text) > 30 else ''}」】\n\n{base_response}"
            if text
            else base_response
        )

    return {
        "content": content,
        "message_type": "text",
        "media_url": None,
        "citations": "【Mock 模式 - 仅供测试使用，非真实法律建议】",
    }

LAWYER_AGENT_PROMPT = """...（同原代码）..."""
JUDGE_AGENT_PROMPT = """...（同原代码）..."""
SYNTHESIS_AGENT_PROMPT = """...（同原代码）..."""

def encode_image_to_base64(image_path: str) -> str:
    """将本地图片文件转换为 Base64 字符串"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"读取图片失败: {e}")
        return None

async def agent_inference(prompt: str, context: str, user_query: str) -> str:
    try:
        response = await client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o"), 
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"【案件背景与法律依据】\n{context}\n\n【用户问题】\n{user_query}"}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Agent Error: {e}")
        return ""

async def get_legal_response(history: list, latest_input: dict):
    # === Mock mode: skip all external calls ===
    if USE_MOCK:
        return await get_mock_legal_response(latest_input)

    text_content = latest_input.get("content", "")
    
    # === Level 1: 规则引擎极速拦截 ===
    if text_content and latest_input.get("type") == "text":
        rule_ans, rule_src = check_rules(text_content)
        if rule_ans:
            return {
                "content": rule_ans,
                "message_type": "text",
                "media_url": None,
                "citations": f"【系统速查 - {rule_src}】\n(注：此回复基于专家规则库自动匹配)"
            }

    # === Level 2: 真·RAG 向量检索 ===
    citations = []
    rag_context = ""
    if text_content and latest_input.get("type") == "text":
        try:
            knowledge_docs = await run_in_threadpool(search_knowledge, text_content)
            if knowledge_docs:
                rag_context = "\n".join(knowledge_docs)
                citations = knowledge_docs
        except Exception as e:
            logger.error(f"RAG Error: {e}")

    is_complex = len(text_content) > 15 or "起诉" in text_content or "怎么办" in text_content or "合同" in text_content
    
    if latest_input.get("type") == "image":
        # 【核心修复】：拦截本地图片路径，转为 Base64，否则 OpenAI 会报下载失败
        raw_url = latest_input.get("url", "")
        openai_image_url = raw_url
        
        if "/static/uploads/" in raw_url:
            filename = raw_url.split("/static/uploads/")[-1]
            local_path = f"static/uploads/{filename}"
            
            if os.path.exists(local_path):
                base64_data = encode_image_to_base64(local_path)
                if base64_data:
                    ext = filename.split('.')[-1].lower()
                    mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
                    openai_image_url = f"data:{mime_type};base64,{base64_data}"
        
        messages = [{"role": "system", "content": SYNTHESIS_AGENT_PROMPT}]
        messages.append({
            "role": "user", 
            "content": [
                {"type": "text", "text": "请分析这张图片中的法律风险，并提供防范建议。"},
                {"type": "image_url", "image_url": {"url": openai_image_url}}
            ]
        })
        try:
            response = await client.chat.completions.create(
                model=os.getenv("VISION_MODEL", "gpt-4o"), # 保证使用视觉模型
                messages=messages,
                temperature=0.3
            )
            ai_text = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Vision Agent Error: {e}")
            ai_text = "图片分析失败，请检查模型配置是否支持视觉处理。"
    
    elif is_complex:
        # === Level 3: Multi-Agent 协作辩论 ===
        print("⚡ 启动 Multi-Agent 辩论模式")
        lawyer_reply, judge_reply = await asyncio.gather(
            agent_inference(LAWYER_AGENT_PROMPT, rag_context, text_content),
            agent_inference(JUDGE_AGENT_PROMPT, rag_context, text_content)
        )
        
        synthesis_context = f"【RAG检索依据】:\n{rag_context}\n\n【激进律师观点】:\n{lawyer_reply}\n\n【保守法官观点】:\n{judge_reply}"
        
        messages = [{"role": "system", "content": SYNTHESIS_AGENT_PROMPT}]
        effective_history = history[:-1] if history and history[-1].content == text_content else history
        for msg in effective_history[-6:]:
            messages.append({"role": msg.role, "content": msg.content})
            
        messages.append({"role": "user", "content": f"上下文参考：\n{synthesis_context}\n\n当前用户问题：{text_content}"})
        
        try:
            response = await client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o"),
                messages=messages,
                temperature=0.3
            )
            ai_text = response.choices[0].message.content
        except Exception as e:
            ai_text = "系统思考超时，请检查服务配置。"
    else:
        ai_text = await agent_inference(SYNTHESIS_AGENT_PROMPT, rag_context, text_content)

    return {
        "content": ai_text,
        "message_type": "text",
        "media_url": None,
        "citations": "\n".join(citations) if citations else None
    }

async def synthesize_dialect_audio(text, voice):
    return None