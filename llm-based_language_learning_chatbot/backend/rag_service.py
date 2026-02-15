import chromadb
from chromadb.utils import embedding_functions
import os
import uuid

# 初始化 ChromaDB (本地持久化)
CHROMA_DATA_PATH = "./chroma_db"
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# 使用 OpenAI 的 Embedding 模型 (效果最好，且你已有 Key)
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

# 获取或创建集合
collection = client.get_or_create_collection(
    name="legal_knowledge",
    embedding_function=openai_ef
)

def add_legal_document(content: str, source: str):
    """
    向知识库添加一条法律条文或案例
    """
    doc_id = str(uuid.uuid4())
    collection.add(
        documents=[content],
        metadatas=[{"source": source}],
        ids=[doc_id]
    )
    return doc_id

def search_knowledge(query: str, n_results: int = 3):
    """
    检索相关法律知识
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    # 格式化返回结果
    knowledge_list = []
    if results['documents']:
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i]
            knowledge_list.append(f"【来源：{meta['source']}】\n内容：{doc}")
            
    return knowledge_list

# --- 初始化脚本 (第一次运行时调用) ---
def init_knowledge_base():
    """
    这里模拟灌入一些基础法律数据，实际生产中应从 PDF/Word 解析
    """
    if collection.count() == 0:
        print("正在初始化法律知识库...")
        laws = [
            ("《中华人民共和国民法典》第六百七十五条：借款人应当按照约定的期限返还借款。对借款期限没有约定或者约定不明确，依据本法第五百一十条的规定仍不能确定的，借款人可以随时返还；贷款人可以催告借款人在合理期限内返还。", "民法典"),
            ("《中华人民共和国刑法》第二百六十六条：诈骗公私财物，数额较大的，处三年以下有期徒刑、拘役或者管制，并处或者单处罚金。", "刑法"),
            ("最高人民法院关于审理民间借贷案件适用法律若干问题的规定：出借人向人民法院提起民间借贷诉讼时，应当提供借据、收据、欠条等债权凭证以及其他能够证明借贷法律关系存在的证据。", "司法解释"),
            ("《劳动合同法》第三十七条：劳动者提前三十日以书面形式通知用人单位，可以解除劳动合同。劳动者在试用期内提前三日通知用人单位，可以解除劳动合同。", "劳动合同法")
        ]
        for content, source in laws:
            add_legal_document(content, source)
        print("法律知识库初始化完成！")