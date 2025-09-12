# 文件名: app/services/qichacha_service.py

import requests
import time
import hashlib
import json
import os
import logging

logger = logging.getLogger(__name__)

# --- 配置 ---
# 强烈建议使用环境变量来配置 AppKey 和 SecretKey，而不是硬编码在代码中
# 在您的服务器环境中设置:
# export QICHACHA_APP_KEY="your_app_key"
# export QICHACHA_SECRET_KEY="your_secret_key"
APP_KEY = os.environ.get("QICHACHA_APP_KEY", "appKey")      # 替换为你的 AppKey
SECRET_KEY = os.environ.get("QICHACHA_SECRET_KEY", "secretKey") # 替换为你的 SecretKey
BASE_URL = "http://api.qichacha.com/ECIV4/GetBasicDetailsByName"  # 企业工商信息查询接口

def get_company_info(company_name: str) -> dict:
    """
    调用企查查API，根据公司名称获取工商信息。
    :param company_name: 公司全称
    :return: 包含公司信息的字典，如果失败则返回包含 'error' 键的字典。
    """
    if APP_KEY == "appKey" or SECRET_KEY == "secretKey":
        logger.error("企查查 API Key 或 Secret Key 未配置。请将其设置为环境变量。")
        return {"error": "Qichacha API service is not configured on the server."}

    timespan = str(int(time.time()))
    token = APP_KEY + timespan + SECRET_KEY
    
    hl = hashlib.md5()
    hl.update(token.encode(encoding='utf-8'))
    token_md5 = hl.hexdigest().upper()
    
    headers = {'Token': token_md5, 'Timespan': timespan}
    params = {'key': APP_KEY, 'keyword': company_name}
    
    try:
        logger.info(f"正在向企查查查询公司信息: {company_name}")
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # 如果状态码不是 2xx，则抛出异常
        
        result_data = response.json()
        
        if result_data.get("Status") == "200":
            logger.info(f"成功获取到 '{company_name}' 的信息。")
            return result_data.get("Result", {})
        else:
            error_message = result_data.get("Message", "未知错误")
            logger.error(f"企查查 API 返回错误: {error_message} (公司: {company_name})")
            return {"error": f"Qichacha API error: {error_message}"}

    except requests.exceptions.RequestException as e:
        logger.error(f"请求企查查 API 时发生网络错误: {e}", exc_info=True)
        return {"error": f"Network error when calling Qichacha API: {str(e)}"}
    except json.JSONDecodeError:
        logger.error(f"解析企查查 API 响应失败。响应内容: {response.text}", exc_info=True)
        return {"error": "Failed to parse response from Qichacha API."}

def format_company_info_for_llm(info: dict) -> str:
    """
    将从企查查获取的JSON信息格式化为一段适合LLM分析的文本。
    """
    if not info or "error" in info:
        return "未能获取到有效的公司工商信息。"

    # 精选关键字段进行格式化
    profile_parts = [
        f"公司名称: {info.get('Name', '未知')}",
        f"企业状态: {info.get('Status', '未知')}",
        f"法定代表人: {info.get('OperName', '未知')}",
        f"注册资本: {info.get('RegistCapi', '未提供')}",
        f"成立日期: {info.get('StartDate', '未知')[:10] if info.get('StartDate') else '未知'}",
        f"企业类型: {info.get('EconKind', '未知')}",
        f"经营范围: {info.get('Scope', '未提供')}",
    ]
    # 添加注销/吊销信息（如果存在）
    revoke_info = info.get('RevokeInfo')
    if revoke_info and (revoke_info.get('CancelDate') or revoke_info.get('RevokeDate')):
        profile_parts.append(f"注销/吊销信息: {json.dumps(revoke_info, ensure_ascii=False)}")
        
    return "\n".join(profile_parts)