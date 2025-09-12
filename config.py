# 文件名: config.py
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# --- Dashscope API 配置 ---
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY')

# --- Flask 应用配置 ---
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'guess_it_hahahaha'
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf'}

# --- Milvus 配置 ---
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"

# --- 模型常量 ---
EMBEDDING_MODEL = "text-embedding-v2"
EMBEDDING_DIM = 1536
