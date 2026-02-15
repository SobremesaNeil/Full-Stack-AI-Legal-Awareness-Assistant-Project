import os
import asyncio
from openai import AsyncOpenAI
import azure.cognitiveservices.speech as speechsdk
from fastapi.concurrency import run_in_threadpool
from rag_service import search_knowledge

# 系统提示词升级：强制要求引用
SYSTEM_PROMPT = """
你是一名资深的中国法律顾问“普法小助手”。
请基于用户提供的问题和【相关法律依据】进行回答。
1. 必须优先引用【相关法律依据】中的条款。
2. 如果知识库中没有相关内容，请运用你的通用法律知识回答，但需声明“根据一般法律原则”。
3. 回答要严谨、结构清晰。
4. 如果用户上传图片，请分析法律风险。
"""

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ... (TTS 相关代码保持不变，此处省略以节省篇幅，请保留原来的 get_speech_config 等函数) ...
def get_speech_config():
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    service_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not service_region:
        return None
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    return speech_config

def _synthesize_sync(text: str, dialect_voice: str, output_path: str):
    speech_config = get_speech_config()
    if not speech_config:
        return None
    speech_config.speech_synthesis_voice_name = dialect_voice
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    return False

async def synthesize_dialect_audio(text: str, dialect_voice: str = "zh-CN-Sichuan-YunxiNeural"):
    filename = f"tts_{os.urandom(4).hex()}.wav"
    upload_dir = os.path.join("static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    output_path = os.path.join(upload_dir, filename)
    success = await run_in_threadpool(_synthesize_sync, text, dialect_voice, output_path)
    if success:
        return f"http://localhost:8000/static/uploads/{filename}"
    return None
# ... (TTS 结束) ...

async def get_legal_response(history: list, latest_input: dict):
    text_content = latest_input.get("content", "")
    
    # 1. RAG 检索
    citations = []
    rag_context = ""
    if text_content and latest_input.get("type") == "text":
        knowledge_docs = await run_in_threadpool(search_knowledge, text_content)
        if knowledge_docs:
            rag_context = "\n\n【相关法律依据】:\n" + "\n".join(knowledge_docs)
            citations = knowledge_docs

    # 2. 构建 Prompt
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 限制历史记录 + 注入 RAG 上下文
    recent_history = history[-10:] 
    for msg in recent_history:
        messages.append({"role": msg.role, "content": msg.content})

    # 将 RAG 检索到的知识拼接到用户的最后一条消息前
    full_user_content = text_content
    if rag_context:
        full_user_content += rag_context
        
    user_payload = []
    if latest_input.get("type") == "image":
        user_payload = [
            {"type": "text", "text": "请分析这张图片中的法律风险。"},
            {"type": "image_url", "image_url": {"url": latest_input.get("url")}}
        ]
    else:
        user_payload = full_user_content

    messages.append({"role": "user", "content": user_payload})

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        ai_text = response.choices[0].message.content
        
        result = {
            "content": ai_text,
            "message_type": "text",
            "media_url": None,
            "citations": "\n".join(citations) if citations else None
        }

        # DALL-E 画图逻辑 (保持不变)
        if "画" in text_content and ("图片" in text_content or "场景" in text_content):
            try:
                img_response = await client.images.generate(
                    model="dall-e-3",
                    prompt=f"法律科普插画: {text_content}",
                    size="1024x1024", 
                    n=1,
                )
                result["message_type"] = "image"
                result["media_url"] = img_response.data[0].url
            except Exception:
                pass

        return result
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return {"content": "服务暂时繁忙，请稍后再试。", "message_type": "text", "media_url": None}