# 文件名: app/db/milvus_kb.py
import logging
from pymilvus import (
    connections, utility, FieldSchema, CollectionSchema, DataType, Collection
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import MILVUS_HOST, MILVUS_PORT, EMBEDDING_DIM
from app.utils.helpers import extract_text_from_pdf
from app.services.llm_service import get_embeddings

logger = logging.getLogger(__name__)

class MilvusKnowledgeBase:
    def __init__(self):
        # ... (此处代码与原文件中的 MilvusKnowledgeBase 类完全相同) ...
        # 注意：需要修改一些函数的参数，使其不再依赖全局变量
        # 比如 create_collection, build_and_store 等
        self.connect()

    def connect(self):
        try:
            if "default" in connections.list_connections():
                connections.disconnect("default")
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            logger.info(f"成功连接到 Milvus ({MILVUS_HOST}:{MILVUS_PORT})")
        except Exception as e:
            logger.error(f"连接 Milvus 失败: {e}")
            raise

    def create_collection(self, collection_name: str):
        if utility.has_collection(collection_name):
            logger.info(f"集合 '{collection_name}' 已存在，正在删除旧集合...")
            utility.drop_collection(collection_name)
        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192)
        ]
        schema = CollectionSchema(fields, f"{collection_name}知识库")
        collection = Collection(collection_name, schema)
        index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
        collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"集合 '{collection_name}' 创建成功并已创建索引。")
        return collection
    
    def build_and_store(self, pdf_path: str, collection_name: str):
        collection = self.create_collection(collection_name)
        logger.info(f"开始为集合 '{collection_name}' 构建并存储知识库...")
        text = extract_text_from_pdf(pdf_path)
        if not text: return 0
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        chunks = text_splitter.split_text(text)
        logger.info(f"文本被切分为 {len(chunks)} 个块。")
        embeddings = get_embeddings(chunks)
        if not embeddings: return 0
        entities = [embeddings, chunks]
        insert_result = collection.insert(entities)
        collection.flush()
        logger.info(f"成功插入 {insert_result.insert_count} 条数据到 Milvus 集合 '{collection_name}'。")
        logger.info("知识库构建并存储完成！")
        return insert_result.insert_count

    def retrieve(self, query: str, collection_name: str, k: int = 5) -> str:
        if not utility.has_collection(collection_name):
            return f"知识库 '{collection_name}' 不存在。"
        
        collection = Collection(collection_name)
        collection.load()
        
        logger.info(f"正在从 Milvus 集合 '{collection_name}' 检索上下文...")
        query_embedding = get_embeddings([query])
        if not query_embedding:
            return "无法为查询生成向量。"
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=query_embedding,
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=["text"]
        )
        collection.release()
        retrieved_docs = [hit.entity.get('text') for hit in results[0]]
        context = "\n---\n".join(retrieved_docs)
        logger.info(f"成功从 Milvus 集合 '{collection_name}' 检索到 {len(retrieved_docs)} 条相关信息。")
        return context

    def is_ready(self, collection_name: str) -> bool:
        if not utility.has_collection(collection_name):
            return False
        try:
            collection = Collection(collection_name)
            return collection.num_entities > 0
        except Exception as e:
            logger.warning(f"检查集合 '{collection_name}' 状态失败: {e}")
            return False

    def delete_collection(self, collection_name: str):
        if utility.has_collection(collection_name):
            logger.info(f"正在删除集合 '{collection_name}'...")
            try:
                utility.drop_collection(collection_name)
                logger.info(f"集合 '{collection_name}' 已成功删除。")
                return True, f"知识库 '{collection_name}' 已成功删除。"
            except Exception as e:
                logger.error(f"删除集合 '{collection_name}' 失败: {e}", exc_info=True)
                return False, f"删除知识库 '{collection_name}' 失败: {str(e)}"
        else:
            logger.warning(f"集合 '{collection_name}' 不存在，无需删除。")
            return True, f"知识库 '{collection_name}' 本身不存在，无需操作。"

    def list_all_collections(self):
        logger.info("正在获取所有知识库列表...")
        try:
            collections = utility.list_collections()
            logger.info(f"成功获取到 {len(collections)} 个知识库: {collections}")
            return True, collections
        except Exception as e:
            logger.error(f"获取知识库列表失败: {e}", exc_info=True)
            return False, f"获取知识库列表失败: {str(e)}"