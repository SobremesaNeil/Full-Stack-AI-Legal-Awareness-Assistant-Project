from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import httpx
from openai import OpenAI

proxies = "http://127.0.0.1:7890"

load_dotenv()

transport = httpx.AsyncHTTPTransport(proxy=proxies)

client = OpenAI(api_key="your-api-key-here")

class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=os.getenv("API_URL"),
            api_key=os.getenv("API_KEY"),
            timeout=60.0,  # 设置超时时间为60秒
            http_client=httpx.AsyncClient(transport=transport) #proxies
        )
        self.model = "deepseek-chat"
        self.system_prompt = """你是一个专业的语言学习助手，专注于帮助用户学习和提高他们的语言技能。你应该：

1. 提供准确的语言知识和解释
2. 根据用户的语言水平调整回答的难度
3. 在合适的时候提供例句和练习
4. 鼓励用户多练习和使用目标语言
5. 纠正用户的语言错误，并解释原因
6. 提供实用的学习建议和方法
7. 保持友好和耐心的态度

请记住，你的目标是帮助用户有效地学习和掌握语言。"""

    async def get_chat_response(self, messages):
        """
        调用 DeepSeek API 获取聊天响应
        
        Args:
            messages (list): 消息历史列表，格式为 [{"role": "user", "content": "..."}, ...]
            
        Returns:
            dict: 包含 AI 响应的字典
        """
        try:
            # 确保消息格式正确
            formatted_messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            for msg in messages:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=2000,
                stream=False  # 确保不使用流式响应
            )
            
            # 处理响应
            if hasattr(response, 'choices') and len(response.choices) > 0:
                return {
                    "role": "assistant",
                    "content": response.choices[0].message.content
                }
            else:
                raise Exception("Invalid response format from DeepSeek API")
                
        except Exception as e:
            print(f"Error calling DeepSeek API: {str(e)}")
            return {
                "role": "assistant",
                "content": "抱歉，我现在无法正常响应。请稍后再试。"
            }


    def generate_image(prompt: str):
        try:
            response = client.images.generate(
                model="dall-e-3",  # 推荐最新模型
                prompt=prompt,
                n=1,  # 仅支持生成1张
                size="1024x1024",  # 可选尺寸：1024x1024/1792x1024/1024x1792
                quality="hd",  # 高清模式（细节更丰富）
                style="vivid",  # 风格：vivid(超现实)/natural(自然)
                response_format="url"  # 或 b64_json 本地存储
            )
            return response.data[0].url
        except Exception as e:
            print(f"API 调用失败: {str(e)}")
            return None