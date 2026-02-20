import os
import asyncio
import base64
from openai import AsyncOpenAI
from fastapi.concurrency import run_in_threadpool
from rag_service import search_knowledge
from rule_service import check_rules

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1") 
)

LAWYER_AGENT_PROMPT = """...（同原代码）..."""
JUDGE_AGENT_PROMPT = """...（同原代码）..."""
SYNTHESIS_AGENT_PROMPT = """...（同原代码）..."""

def encode_image_to_base64(image_path: str) -> str:
    """将本地图片文件转换为 Base64 字符串"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"读取图片失败: {e}")
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
        print(f"Agent Error: {e}")
        return ""

async def get_legal_response(history: list, latest_input: dict):
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
            print(f"RAG Error: {e}")

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
            print(f"Vision Agent Error: {e}")
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