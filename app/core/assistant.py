# 文件名: app/core/assistant.py
import logging
import json
import re
from app.db.milvus_kb import MilvusKnowledgeBase
from app.services.llm_service import call_qwen_model

logger = logging.getLogger(__name__)

class ContractReviewAssistant:
    def __init__(self, knowledge_base: MilvusKnowledgeBase):
        self.knowledge_base = knowledge_base
        
    def get_contract_summary(self, contract_text: str) -> str:
        logger.info("开始生成合同摘要...")
        prompt = f"""
        ### 角色 ###
        你是一位专业的法律助理，擅长将复杂的法律文件提炼成清晰、简洁的摘要。

        ### 任务 ###
        请仔细阅读以下合同全文，并生成一份核心要点摘要。摘要应涵盖以下关键信息：
        1.  **合同双方**: 明确指出甲方和乙方是谁。
        2.  **核心目的**: 一句话概括这份合同是关于什么的（例如：软件开发、房屋租赁等）。
        3.  **主要权利与义务**: 分别列出甲乙双方的核心责任。
        4.  **关键条款**: 简要提及关于费用、交付、知识产权、违约责任等核心条款。
        5.  **合同期限与争议解决**: 如果合同中有明确的期限或争议解决方式，请指出。

        ### 输出要求 ###
        - 使用清晰的标题和要点格式。
        - 语言力求简洁明了，避免不必要的法律术语。
        - 摘要内容必须严格基于所提供的合同文本，不得添加外部信息或进行推测。

        ### 待摘要的合同文本 ###
        ---
        {contract_text}
        ---
        """
        summary = call_qwen_model(prompt, model="qwen-turbo", temperature=0.0)
        logger.info("合同摘要生成完毕。")
        return summary or "未能生成合同摘要。"

    def review_party_profile(self, contract_text: str, party_profile: str, party_name_to_review: str, perspective: str) -> dict:
        """
        根据用户提供的公司简介，审查合同另一方的潜在风险和履约能力。
        """
        logger.info(f"开始对 {party_name_to_review} 进行主体资格与履约能力审查...")
        prompt = f"""
        ### 角色 ###
        你是一位经验丰富的商业尽职调查专家，特别擅长从公司简介和合同文本中识别潜在的商业风险。

        ### 背景 ###
        我方是 **{perspective}**，正在审查合作方 **“{party_name_to_review}”** 的可靠性。我将为你提供该公司的简介以及相关的合同内容。

        ### 任务 ###
        请结合下方提供的“合作方公司简介”和“合同相关内容”，进行综合分析，并生成一份主体审查报告。报告需要关注以下几点：
        1.  **风险评估**: 根据公司简介，分析该公司是否存在潜在的商业风险（例如：描述含糊、过度承诺、业务范围与合同不符等）。
        2.  **履约能力匹配度分析**: 比较公司简介中描述的能力、资质、经验，与合同中约定的义务和责任是否匹配。判断是否存在夸大宣传或能力不足以履行合同的风险。
        3.  **提出建议**: 基于你的分析，给我方（{perspective}）提出一些具体的、可操作的尽职调查建议（例如：建议核实某项资质、要求提供过往案例证明等）。

        ### 输出要求 ###
        1. 以一个严格的JSON对象的格式返回你的审查报告。
        2. JSON对象必须包含以下三个键：
           - `risk_summary`: (string) 对合作方潜在风险的总体概括。
           - `capability_analysis`: (string) 详细分析其简介与合同义务的匹配度，明确指出任何不一致或夸大的地方。
           - `due_diligence_suggestions`: (list of strings) 一个包含多条具体核查建议的列表。
        3. 如果分析后未发现明显风险，请在对应字段中客观说明。
        4. 请不要在JSON格式之外添加任何解释性文字。

        ### 待分析的资料 ###

        #### 1. 合作方公司简介 ####
        ---
        {party_profile}
        ---

        #### 2. 合同相关内容 ####
        ---
        {contract_text}
        ---
        """
        
        response_str = call_qwen_model(prompt, model="qwen-plus", temperature=0.1)
        
        if not response_str:
            logger.error("模型未能返回主体审查结果。")
            return {}

        try:
            if response_str.strip().startswith("```json"):
                response_str = response_str.strip()[7:-3].strip()
            
            review_report = json.loads(response_str)
            logger.info(f"主体审查完成。")
            return review_report
        except json.JSONDecodeError as e:
            logger.error(f"解析主体审查报告JSON失败: {e}")
            logger.error(f"模型返回的原始文本: \n{response_str}")
            return {}

    def extract_party_names(self, contract_text: str) -> dict:
        logger.info("开始提取合同方信息...")
        prompt = f"""
        请从以下合同文本中，提取并识别出“甲方”和“乙方”分别对应的公司全称。

        合同文本：
        ---
        {contract_text[:1000]}
        ---

        请以严格的JSON格式返回，不要包含任何额外的解释。格式如下：
        {{"party_a": "甲方公司全称", "party_b": "乙方公司全称"}}
        如果找不到，请将对应的值留空字符串 ""。
        """
        response_str = call_qwen_model(prompt)
        try:
            parties = json.loads(response_str)
            logger.info(f"成功提取合同方: 甲方 - {parties.get('party_a')}, 乙方 - {parties.get('party_b')}")
            return parties
        except (json.JSONDecodeError, TypeError):
            logger.warning("模型返回非JSON，尝试正则提取...")
            party_a = re.search(r"甲\s*方：\s*([^\n\r]+)", contract_text)
            party_b = re.search(r"乙\s*方：\s*([^\n\r]+)", contract_text)
            parties = {
                "party_a": party_a.group(1).strip() if party_a else "未知",
                "party_b": party_b.group(1).strip() if party_b else "未知"
            }
            logger.info(f"正则提取结果: 甲方 - {parties['party_a']}, 乙方 - {parties['party_b']}")
            return parties

    def review_contract(self, contract_text: str, perspective: str, party_names: dict, collection_name: str) -> list:
        if perspective.upper() not in ["甲方", "乙方"]:
            raise ValueError("立场必须是 '甲方' 或 '乙方'")
            
        party_name = party_names.get('party_a' if perspective == '甲方' else 'party_b', perspective)
        logger.info(f"开始合同条款风险审查（使用知识库 '{collection_name}'），当前立场: {perspective} ({party_name})")
        
        retrieved_context = self.knowledge_base.retrieve(contract_text, collection_name=collection_name)
        
        prompt = f"""
        ### 角色 ###
        你是一位专注于《中华人民共和国民法典》的法务专家。你的所有知识和分析都必须严格基于我提供给你的《民法典》条款。

        ### 背景 ###
        我现在的立场是 **{perspective}** ({party_name})。请你站在我的立场上，以保护我方利益为首要目标。

        ### 法律依据参考 (唯一知识来源) ###
        以下是从《中华人民共和国民法典》知识库中检索到的相关法律条文。这是你进行本次审查时可以使用的 **唯一** 法律依据。
        ---
        {retrieved_context}
        ---

        ### 核心约束 ###
        你的所有分析、风险判断和修改建议，都必须严格且唯一地基于上方“法律依据参考”中提供的《民法典》条文。**绝对禁止**引用、参考或依赖任何未在上方明确提供的其他法律法规（例如《公司法》、《劳动合同法》等）。你的知识范围被严格限定在所提供的文本内。

        ### 任务 ###
        请你根据上述提供的《民法典》条文，逐条审查以下合同文本。对于任何可能对我方（{perspective}）不利、存在法律风险、或与上方提供的民法典条款相冲突的条款，请识别出来并生成一份审查报告。

        ### 输出要求 ###
        1. 以一个JSON列表（List of JSON objects）的格式返回你的审查报告。
        2. 列表中的每一个JSON对象代表一个风险条款，并必须包含以下六个键：
            - `original_clause`: (string) 风险条款的原文。
            - `clause_category`: (string) 对该条款内容的分类，例如：“解除权”、“违约责任”、“知识产权”、“保密义务”等。
            - `risk_level`: (string) 风险等级，必须是 "高风险", "中风险", "低风险" 中的一个。
            - `compliance_analysis`: (string) **严格引用**上方“法律依据参考”中的具体条款进行合规性分析。**禁止**引用任何未被提供的法律条文。
            - `risk_reason`: (string) 详细解释该条款依据所提供的民法典条款对我方（{perspective}）造成的具体风险点。
            - `modification_suggestion`: (string) 基于所提供的民法典条款，提出具体的、可操作的修改建议。
        3. 如果根据所提供的民法典条款，合同没有发现任何对我方不利的风险，请返回一个空的JSON列表 `[]`。
        4. 请不要在JSON格式之外添加任何解释性文字或注释。

        ### 待审查的合同文本 ###
        ---
        {contract_text}
        ---
        """
        
        response_str = call_qwen_model(prompt, model="qwen-long", temperature=0.1)
        
        if not response_str:
            logger.error("模型未能返回审查结果。")
            return []
            
        try:
            if response_str.strip().startswith("```json"):
                response_str = response_str.strip()[7:-3].strip()
            
            review_results = json.loads(response_str)
            review_results = json.loads(json.dumps(review_results, ensure_ascii=False))

            logger.info(f"条款审查完成，发现 {len(review_results)} 个风险点。")
            return review_results
        except json.JSONDecodeError as e:
            logger.error(f"解析条款审查报告JSON失败: {e}")
            logger.error(f"模型返回的原始文本: \n{response_str}")
            return []