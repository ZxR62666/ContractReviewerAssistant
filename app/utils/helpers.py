# 文件名: app/utils/helpers.py
import os
import time
import logging
from PyPDF2 import PdfReader
from config import Config

logger = logging.getLogger(__name__)

def log_time(start_time, operation_name):
    """记录操作耗时"""
    elapsed_time = time.time() - start_time
    logger.info(f"{operation_name} 耗时: {elapsed_time:.2f} 秒")

def extract_text_from_pdf(pdf_path: str) -> str:
    """从 PDF 文件中提取文本"""
    if not os.path.exists(pdf_path):
        logger.error(f"PDF文件未找到: {pdf_path}")
        return ""
    try:
        logger.info(f"正在从 {pdf_path} 提取文本...")
        reader = PdfReader(pdf_path)
        text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        logger.info(f"文本提取成功，共 {len(text)} 字符。")
        return text
    except Exception as e:
        logger.error(f"提取PDF文本失败: {e}", exc_info=True)
        return ""

def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否被允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS