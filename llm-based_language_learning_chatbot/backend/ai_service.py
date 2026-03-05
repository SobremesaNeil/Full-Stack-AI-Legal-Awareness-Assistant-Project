import os
import asyncio
import base64
import logging
from openai import AsyncOpenAI
from fastapi.concurrency import run_in_threadpool
from rag_service import search_knowledge
from rule_service import check_rules

# Configure logger
logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

LAWYER_AGENT_PROMPT = """你是一位经验丰富、立场积极进取的中国执业律师。
你的职责是：从当事人利益最大化的角度出发，分析案件事实，援引相关法律条文，提出最有力的法律主张和诉讼策略。
要求：
1. 援引具体法律条文（如《民法典》第X条、《劳动合同法》第X条等）
2. 指出对方可能存在的违法点或过错
3. 提出具体的维权途径（协商、调解、仲裁、诉讼）
4. 评估当事人胜诉的可能性
回答请简洁专业，使用中文。"""

JUDGE_AGENT_PROMPT = """你是一位公正严谨、立场中立保守的中国法官。
你的职责是：从司法实践和法律规范的角度，客观评估案件，指出法律风险与不确定性，提出稳妥的处理建议。
要求：
1. 严格依据现行法律法规分析（不超越法律条文做推断）
2. 客观指出案件的争议焦点和举证困难
3. 提示当事人可能面临的法律风险
4. 建议优先通过非诉讼途径（调解、和解）解决争议
5. 如证据不足，应提示当事人谨慎维权
回答请简洁严谨，使用中文。"""

SYNTHESIS_AGENT_PROMPT = """你是一位全面专业的AI法律顾问，名叫"普法小助手"。
你综合了律师的积极主张和法官的审慎判断，为用户提供平衡、实用的法律建议。

你的能力包括：
1. 解答各类法律问题（民法、刑法、劳动法、合同法等）
2. 分析案件事实，援引具体法律条文
3. 针对复杂案情，生成案情思维导图（使用 <mindmap>...</mindmap> 标签包裹 Markdown 内容）
4. 针对用户需要，生成法律文书草稿（使用 <document title="文书名称">...</document> 标签包裹 Markdown 内容）

回答原则：
- 语言清晰、通俗易懂，避免过度使用法律术语
- 援引具体法律依据，确保建议有据可查
- 区分法律意见和实际建议，注明"仅供参考"
- 对于无法确定的问题，建议咨询专业律师
- 始终使用中文回答

重要提示：你的回答仅供参考，不构成正式法律意见，如涉及重大法律事务，请务必咨询执业律师。"""

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