import chromadb
from chromadb.utils import embedding_functions
import os
import uuid
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 ChromaDB (本地持久化)
CHROMA_DATA_PATH = "./chroma_db"
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("无 OpenAI Key，RAG 服务将不可用")
    logger.warning("未检测到 OPENAI_API_KEY，RAG 功能将无法正常工作。")
    openai_ef = None
else:
    # 【修复重点】：这里必须要有缩进！
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key or "sk-placeholder", 
        model_name="text-embedding-3-small"
    )

# 获取或创建集合
collection = client.get_or_create_collection(
    name="legal_knowledge",
    embedding_function=openai_ef if openai_ef else None
)

def add_legal_document(content: str, source: str):
    try:
        doc_id = str(uuid.uuid4())
        collection.add(
            documents=[content],
            metadatas=[{"source": source}],
            ids=[doc_id]
        )
        return doc_id
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        return None

def search_knowledge(query: str, n_results: int = 3):
    try:
        if not openai_ef: return []
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        knowledge_list = []
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i]
                knowledge_list.append(f"【来源：{meta['source']}】\n内容：{doc}")
                
        return knowledge_list
    except Exception as e:
        logger.error(f"检索失败: {e}")
        return []

def load_initial_data_from_file(file_path: str = "legal_data.json"):
    if not os.path.exists(file_path):
        logger.warning(f"数据文件 {file_path} 不存在，跳过初始化。")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        count = 0
        for item in data:
            add_legal_document(item["content"], item["source"])
            count += 1
        logger.info(f"成功从文件加载了 {count} 条法律条文。")
    except json.JSONDecodeError:
        logger.error("数据文件格式错误，请检查 JSON 格式。")
    except Exception as e:
        logger.error(f"加载初始数据时发生未知错误: {e}")

def init_knowledge_base():
    if collection.count() == 0:
        logger.info("正在初始化法律知识库...")
        load_initial_data_from_file()
        
        # 【修复重点】：安全的导入，避免循环引用
        try:
            from rule_service import get_default_seed_rules
            for patterns, answer, source in get_default_seed_rules():
                content = f"问题关键词：{patterns[0]}。标准答案：{answer}"
                add_legal_document(content, f"规则库-{source}")
        except ImportError:
            logger.warning("未能导入 rule_service 初始化默认规则到向量库。")
            
        logger.info("法律知识库初始化完成！")
    else:
        logger.info(f"法律知识库已就绪，当前文档数: {collection.count()}")