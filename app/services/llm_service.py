# 文件名: app/services/llm_service.py
import logging
import time
import numpy as np
import dashscope
from dashscope import Generation, TextEmbedding
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import DASHSCOPE_API_KEY, EMBEDDING_MODEL
from app.utils.helpers import log_time

logger = logging.getLogger(__name__)

# 初始化 Dashscope API Key
dashscope.api_key = DASHSCOPE_API_KEY
if not dashscope.api_key:
    logger.error("错误：未能从 .env 文件或环境变量中加载 DASHSCOPE_API_KEY！")
    exit()

def get_embeddings(texts: list[str], model: str = EMBEDDING_MODEL, batch_size: int = 25) -> list[list[float]]:
    """为文本列表生成向量嵌入"""
    # ... (此处代码与原文件中的 get_embeddings 完全相同) ...
    if len(texts) == 1 and len(texts[0]) > 2048:
        logger.info("检测到单个长文本，将采用分块平均策略生成向量...")
        long_text = texts[0]
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_text(long_text)
        chunk_embeddings = get_embeddings(chunks, model, batch_size)
        if not chunk_embeddings:
            logger.error("长文本的分块向量生成失败。")
            return []
        avg_embedding = np.mean(np.array(chunk_embeddings), axis=0).tolist()
        return [avg_embedding]

    logger.info(f"正在为 {len(texts)} 个文本块生成向量（分批处理，每批 {batch_size} 个）...")
    all_embeddings = []
    start_time = time.time()
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        logger.info(f"处理批次 {i // batch_size + 1}/{len(texts) // batch_size + 1}...")
        try:
            for text_item in batch_texts:
                if len(text_item) > 2048:
                     logger.warning(f"一个文本块长度超过2048字符，可能导致API错误: {text_item[:100]}...")
            response = TextEmbedding.call(model=model, input=batch_texts)
            if response.status_code == 200:
                batch_embeddings = [record['embedding'] for record in response.output['embeddings']]
                all_embeddings.extend(batch_embeddings)
            else:
                logger.error(f"批次处理失败: Code: {response.status_code}, Message: {response.message}")
                continue
        except Exception as e:
            logger.error(f"批次处理异常: {e}", exc_info=True)
    log_time(start_time, f"向量生成（共 {len(all_embeddings)} 个）")
    if len(all_embeddings) != len(texts):
        logger.warning(f"向量生成不完整：预期 {len(texts)} 个，实际生成 {len(all_embeddings)} 个。")
    return all_embeddings


def call_qwen_model(prompt: str, model: str = "qwen-turbo", temperature: float = 0.1) -> str:
    """调用通义千问模型"""
    # ... (此处代码与原文件中的 call_qwen_model 完全相同) ...
    logger.info(f"调用Qwen模型({model})，温度系数: {temperature}")
    start_time = time.time()
    try:
        response = Generation.call(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的AI法律助手，精通中国法律，特别是合同法和民法典。你的回答必须严格遵循用户的指令，尤其是格式要求。"},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            result_format='message'
        )
        if response.status_code == 200:
            content = response.output.choices[0]['message']['content']
            log_time(start_time, f"Qwen({model})模型调用")
            return content
        else:
            logger.error(f"模型调用失败: Code: {response.status_code}, Message: {response.message}")
            return ""
    except Exception as e:
        logger.error(f"模型调用异常: {str(e)}", exc_info=True)
        return ""