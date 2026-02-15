import os
import asyncio
from openai import AsyncOpenAI
import azure.cognitiveservices.speech as speechsdk
from fastapi.concurrency import run_in_threadpool

# 系统提示词保持不变
SYSTEM_PROMPT = """
你是一名资深的中国法律顾问“普法小助手”。
1. 请依据《中华人民共和国民法典》、《刑法》等现行法律回答。
2. 回答要严谨但通俗，适合普通大众，尽量结合案例。
3. 如果用户要求“生成思维导图”或“总结结构”，请输出标准的 Markdown 格式（以 # 开头）。
4. 如果用户上传图片，请从法律角度分析图片中的风险或证据价值。
"""

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_speech_config():
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    service_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not service_region:
        return None
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    return speech_config

# --- 核心修改：将同步的 SDK 调用封装为异步任务 ---
def _synthesize_sync(text: str, dialect_voice: str, output_path: str):
    """
    这是内部同步函数，不要直接从 async 函数调用它，
    除非通过 run_in_threadpool 或 asyncio.to_thread
    """
    speech_config = get_speech_config()
    if not speech_config:
        return None
    
    speech_config.speech_synthesis_voice_name = dialect_voice
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    # 这里 .get() 会阻塞线程，所以必须放在线程池里运行
    result = synthesizer.speak_text_async(text).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    return False

async def synthesize_dialect_audio(text: str, dialect_voice: str = "zh-CN-Sichuan-YunxiNeural"):
    filename = f"tts_{os.urandom(4).hex()}.wav"
    # 确保存储路径存在
    upload_dir = os.path.join("static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    output_path = os.path.join(upload_dir, filename)
    
    # 关键：使用 run_in_threadpool 将同步IO操作变为非阻塞
    success = await run_in_threadpool(_synthesize_sync, text, dialect_voice, output_path)
    
    if success:
        return f"http://localhost:8000/static/uploads/{filename}"
    return None

async def get_legal_response(history: list, latest_input: dict):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 填充历史 (注意：传入的 history 对象现在是 ORM 对象，直接访问属性即可)
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    text_content = latest_input.get("content", "")
    user_content = []

    if latest_input.get("type") == "image":
        user_content = [
            {"type": "text", "text": text_content if text_content else "请分析这张图片。"},
            {"type": "image_url", "image_url": {"url": latest_input.get("url")}}
        ]
    else:
        user_content = text_content

    messages.append({"role": "user", "content": user_content})

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        ai_text = response.choices[0].message.content
        
        result = {
            "content": ai_text,
            "message_type": "text",
            "media_url": None
        }

        # 判断思维导图
        if ai_text.strip().startswith("#"):
            result["message_type"] = "mindmap"

        # 判断是否需要画图
        if "画" in text_content and ("图片" in text_content or "场景" in text_content):
            try:
                img_response = await client.images.generate(
                    model="dall-e-3",
                    prompt=f"法律科普插画: {text_content}",
                    size="1024x1024", 
                    quality="standard",
                    n=1,
                )
                result["message_type"] = "image"
                result["media_url"] = img_response.data[0].url
            except Exception as e:
                print(f"DALL-E Error: {e}")

        return result
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return {"content": "抱歉，AI服务暂时不可用，请稍后再试。", "message_type": "text", "media_url": None}