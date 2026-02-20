import os
import asyncio
from openai import AsyncOpenAI
from fastapi.concurrency import run_in_threadpool
from rag_service import search_knowledge
from rule_service import check_rules

# 支持国产化适配：只需在 .env 中配置 OPENAI_BASE_URL (如通义千问/DeepSeek的API地址)
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1") 
)

# ================= 智能体 Prompt 定义 =================
LAWYER_AGENT_PROMPT = """
你是一名“激进型”原告律师。你的目标是：
1. 站在用户的角度，最大化用户的合法权益。
2. 挖掘对方可能存在的过错和违约点。
3. 提出最具攻击性和索赔效益的法律方案。
基于以下案情和法律依据，给出你的激进策略（限300字）。
"""

JUDGE_AGENT_PROMPT = """
你是一名“保守型”法官/合规专家。你的目标是：
1. 提示用户方案中存在的法律风险、证据获取难度及败诉可能性。
2. 指出激进策略中可能越界或不切实际的地方。
3. 提供最稳妥、合规、低成本的纠纷解决建议。
基于以下案情和法律依据，给出你的保守建议（限300字）。
"""

SYNTHESIS_AGENT_PROMPT = """
你是一名资深首席法律顾问。请综合“激进律师”和“保守法官”的观点，给用户一个最终平衡、可操作的答复。
你必须遵守以下【格式规范】：
1. 正常回复用户的文字建议。
2. 如果案情包含多方责任或复杂逻辑，请在文本末尾使用 <mindmap> 标签包裹 Markdown 列表格式的思维导图数据（必须是规范的无序或有序列表，用 # 代表根节点）。
3. 如果用户明确要求“起诉”、“写文书”、“写合同”，请使用 <document title="文书标题"> 标签包裹生成的文书正文。

示例输出：
您的案件分析如下...
【激进策略】... 【保守建议】... 【最终方案】...

<mindmap>
# 案情分析
## 责任方
### 房东 (违约)
### 租客 (维权)
## 证据链
### 聊天记录
### 转账凭证
</mindmap>

<document title="民事起诉状">
**原告**：XXX...
**被告**：XXX...
**诉讼请求**：1. 请求判令...
</document>
"""

async def agent_inference(prompt: str, context: str, user_query: str) -> str:
    """独立的 Agent 推理函数"""
    try:
        response = await client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o"), # 适配国产模型时可改为 qwen-max 等
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

    # 判断是否需要启动复杂的多智能体推理 (简单问题直接回答，复杂问题启动辩论)
    is_complex = len(text_content) > 15 or "起诉" in text_content or "怎么办" in text_content or "合同" in text_content
    
    if latest_input.get("type") == "image":
        # 图片处理逻辑保持不变
        messages = [{"role": "system", "content": SYNTHESIS_AGENT_PROMPT}]
        messages.append({
            "role": "user", 
            "content": [
                {"type": "text", "text": "请分析这张图片中的法律风险，并提供防范建议。"},
                {"type": "image_url", "image_url": {"url": latest_input.get("url")}}
            ]
        })
        ai_text = await agent_inference(SYNTHESIS_AGENT_PROMPT, "", str(messages[-1]["content"]))
    
    elif is_complex:
        # === Level 3: Multi-Agent 协作辩论 ===
        print("⚡ 启动 Multi-Agent 辩论模式")
        lawyer_reply, judge_reply = await asyncio.gather(
            agent_inference(LAWYER_AGENT_PROMPT, rag_context, text_content),
            agent_inference(JUDGE_AGENT_PROMPT, rag_context, text_content)
        )
        
        synthesis_context = f"【RAG检索依据】:\n{rag_context}\n\n【激进律师观点】:\n{lawyer_reply}\n\n【保守法官观点】:\n{judge_reply}"
        
        # 组装最终历史上下文
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
        # 简单问题单模型直出
        ai_text = await agent_inference(SYNTHESIS_AGENT_PROMPT, rag_context, text_content)

    return {
        "content": ai_text,
        "message_type": "text",
        "media_url": None,
        "citations": "\n".join(citations) if citations else None
    }

async def synthesize_dialect_audio(text, voice):
    # 占位符，保持原样
    return None