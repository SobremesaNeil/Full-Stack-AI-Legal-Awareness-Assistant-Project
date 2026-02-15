import os
import json
from openai import AsyncOpenAI
import azure.cognitiveservices.speech as speechsdk

# 系统提示词：赋予AI律师人设
SYSTEM_PROMPT = """
你是一名资深的中国法律顾问“普法小助手”。
1. 请依据《中华人民共和国民法典》、《刑法》等现行法律回答。
2. 回答要严谨但通俗，适合普通大众，尽量结合案例。
3. 如果用户要求“生成思维导图”或“总结结构”，请输出标准的 Markdown 格式（以 # 开头），不要包含其他寒暄。
4. 如果用户上传图片，请从法律角度分析图片中的风险或证据价值。
"""

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 配置 Azure 语音 (支持方言)
def get_speech_config():
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    service_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not service_region:
        return None
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    return speech_config

async def get_legal_response(history: list, latest_input: dict):
    """
    latest_input 格式: { "type": "text/image/audio", "content": "...", "url": "..." }
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 1. 填充历史记录
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # 2. 处理当前多模态输入
    user_content = []
    
    # A. 如果是语音，先转文字 (这里简化为后端接收到的是已转好的文字，或者在这里调用STT)
    # 为简单起见，假设前端已经传来了文字，或者在这里处理
    text_content = latest_input.get("content", "")
    
    if latest_input.get("type") == "image":
        # GPT-4o 视觉输入
        user_content.append({"type": "text", "text": text_content if text_content else "请从法律角度分析这张图片。"})
        user_content.append({
            "type": "image_url",
            "image_url": {"url": latest_input.get("url")}
        })
    else:
        # 纯文本
        user_content = text_content

    messages.append({"role": "user", "content": user_content})

    # 3. 调用 GPT-4o
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

    # 4. 后处理：判断是否生成思维导图
    if ai_text.strip().startswith("#"):
        result["message_type"] = "mindmap"

    # 5. 后处理：判断是否生成图片 (用户明确要求"生成图片"或"画")
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
            result["content"] = "这是为您生成的普法插画："
        except Exception as e:
            print(f"Image generation failed: {e}")

    return result

# 方言合成 (Text-to-Speech)
def synthesize_dialect_audio(text: str, dialect_voice: str = "zh-CN-Sichuan-YunxiNeural"):
    """
    dialect_voice 示例:
    普通话: zh-CN-XiaoxiaoNeural
    粤语: zh-HK-HiuGaaiNeural
    四川话: zh-CN-Sichuan-YunxiNeural
    """
    speech_config = get_speech_config()
    if not speech_config:
        return None
    
    speech_config.speech_synthesis_voice_name = dialect_voice
    # 保存到静态目录
    filename = f"tts_{os.urandom(4).hex()}.wav"
    output_path = os.path.join("static", "uploads", filename)
    
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    result = synthesizer.speak_text_async(text).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return f"http://localhost:8000/static/uploads/{filename}"
    return None