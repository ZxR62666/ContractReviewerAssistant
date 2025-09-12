# 文件名: app/api/routes.py
import os
import re
import logging
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.db.milvus_kb import MilvusKnowledgeBase
from app.core.assistant import ContractReviewAssistant
from app.utils.helpers import allowed_file, extract_text_from_pdf

logger = logging.getLogger(__name__)

# 创建蓝图
api_bp = Blueprint('api', __name__)

# --- 全局实例化核心组件 ---
# 在应用启动时就初始化，避免每次请求都重新连接
try:
    kb = MilvusKnowledgeBase()
    assistant = ContractReviewAssistant(kb)
except Exception as e:
    logger.error(f"启动时初始化核心组件失败: {e}", exc_info=True)
    kb = None
    assistant = None

# --- Flask 路由定义 ---

@api_bp.route('/build_kb', methods=['POST'])
def build_kb_endpoint():
    # ... (此处代码与原文件中的 build_kb_endpoint 函数完全相同) ...
    # 注意：将 `@app.route` 改为 `@api_bp.route`
    # 并将 `app.config['UPLOAD_FOLDER']` 改为 `current_app.config['UPLOAD_FOLDER']`
    if not kb:
        return jsonify({"status": "error", "message": "服务初始化失败，请检查 Milvus 连接。"}), 500
        
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "请求中未找到文件部分"}), 400
    
    collection_name = request.form.get('collection_name')
    if not collection_name or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,254}$", collection_name):
        return jsonify({"status": "error", "message": "必须提供有效的知识库名称 (collection_name)，只能包含字母、数字和下划线，且不能以数字开头。"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            logger.info(f"开始为 {filename} 构建知识库 '{collection_name}'...")
            inserted_count = kb.build_and_store(filepath, collection_name)
            os.remove(filepath)
            return jsonify({
                "status": "success", 
                "message": f"知识库 '{collection_name}' 构建成功，共存入 {inserted_count} 个条目。"
            })
        except Exception as e:
            logger.error(f"构建知识库时发生错误: {e}", exc_info=True)
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"status": "error", "message": f"服务器内部错误: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "文件类型不允许，仅支持 PDF"}), 400



@api_bp.route('/review_contract', methods=['POST'])
def review_contract_endpoint():
    if not assistant or not kb:
        return jsonify({"status": "error", "message": "服务初始化失败。"}), 500

    collection_name = request.form.get('collection_name')
    if not collection_name:
        return jsonify({"status": "error", "message": "必须提供要使用的知识库名称 (collection_name)"}), 400
    if not kb.is_ready(collection_name):
         return jsonify({"status": "error", "message": f"知识库 '{collection_name}' 不存在或为空。"}), 400

    if 'contract_file' not in request.files:
        return jsonify({"status": "error", "message": "请求中未找到合同文件"}), 400
    
    perspective = request.form.get('perspective')
    if perspective not in ['甲方', '乙方']:
        return jsonify({"status": "error", "message": "立场 (perspective) 必须是 '甲方' 或 '乙方'"}), 400
        
    file = request.files['contract_file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择合同文件"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            contract_content = extract_text_from_pdf(filepath)
            if not contract_content:
                os.remove(filepath)
                return jsonify({"status": "error", "message": "无法从PDF中提取文本内容"}), 500

            summary = assistant.get_contract_summary(contract_content)
            party_info = assistant.extract_party_names(contract_content)
            risk_report = assistant.review_contract(contract_content, perspective, party_info, collection_name)
            
            os.remove(filepath)
            
            response_data = {
                "contract_summary": summary,
                "risk_review_report": risk_report
            }
            return jsonify(response_data)
        except Exception as e:
            logger.error(f"合同审查时发生错误: {e}", exc_info=True)
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"status": "error", "message": f"服务器内部错误: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "文件类型不允许，仅支持 PDF"}), 400

@api_bp.route('/review_party', methods=['POST'])
def review_party_endpoint():
    # --- 此函数已更新 ---
    if not assistant:
        return jsonify({"status": "error", "message": "服务初始化失败。"}), 500

    if 'contract_file' not in request.files:
        return jsonify({"status": "error", "message": "请求中未找到合同文件"}), 400
    
    # 不再需要用户手动提供 party_profile
    perspective = request.form.get('perspective')
    
    if perspective not in ['甲方', '乙方']:
        return jsonify({"status": "error", "message": "我方立场 (perspective) 必须是 '甲方' 或 '乙方'"}), 400

    file = request.files['contract_file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择合同文件"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            contract_content = extract_text_from_pdf(filepath)
            if not contract_content:
                os.remove(filepath)
                return jsonify({"status": "error", "message": "无法从PDF中提取文本内容"}), 500

            party_info = assistant.extract_party_names(contract_content)
            party_to_review_str = "乙方" if perspective == "甲方" else "甲方"
            party_name_key = 'party_b' if party_to_review_str == "乙方" else 'party_a'
            party_name_to_review = party_info.get(party_name_key)

            if not party_name_to_review or party_name_to_review == "未知":
                 os.remove(filepath)
                 return jsonify({"status": "error", "message": f"无法从合同中自动识别出{party_to_review_str}的公司名称。"}), 400

            party_review_report = assistant.review_party_profile(
                contract_text=contract_content,
                party_name_to_review=party_name_to_review,
                perspective=perspective
            )

            # 检查 assistant 是否返回了 API 错误
            if isinstance(party_review_report, dict) and "error" in party_review_report:
                # 503 Service Unavailable 表示上游服务（企查查）暂时不可用
                return jsonify({"status": "error", "message": party_review_report["error"]}), 503
            
            os.remove(filepath)
            return jsonify(party_review_report)
        except Exception as e:
            logger.error(f"主体审查时发生错误: {e}", exc_info=True)
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"status": "error", "message": f"服务器内部错误: {str(e)}"}), 500
    else:
        return jsonify({"status": "error", "message": "文件类型不允许，仅支持 PDF"}), 400

@api_bp.route('/delete_kb', methods=['POST'])
def delete_kb_endpoint():
    if not kb:
        return jsonify({"status": "error", "message": "服务初始化失败。"}), 500
    
    collection_name = request.form.get('collection_name')
    if not collection_name:
        return jsonify({"status": "error", "message": "必须提供要删除的知识库名称 (collection_name)"}), 400

    try:
        success, message = kb.delete_collection(collection_name)
        if success:
            return jsonify({"status": "success", "message": message})
        else:
            return jsonify({"status": "error", "message": message}), 500
    except Exception as e:
        logger.error(f"删除知识库接口发生未知错误: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"服务器内部错误: {str(e)}"}), 500

@api_bp.route('/list_kbs', methods=['GET'])
def list_kbs_endpoint():
    if not kb:
        return jsonify({"status": "error", "message": "服务初始化失败。"}), 500
    
    try:
        success, data = kb.list_all_collections()
        if success:
            return jsonify({
                "status": "success",
                "knowledge_bases": data
            })
        else:
            return jsonify({"status": "error", "message": data}), 500
    except Exception as e:
        logger.error(f"列出知识库接口发生未知错误: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"服务器内部错误: {str(e)}"}), 500