# 文件名: ui.py
import streamlit as st
import requests
import json
import time
import base64

# --- 配置 ---
# 确保这里的地址和端口与你的 Flask 应用 (run.py) 匹配
API_BASE_URL = "http://127.0.0.1:6045"


# --- 页面美化辅助函数 ---

def load_custom_css():
    """加载自定义CSS样式来美化界面"""
    st.markdown("""
        <style>
        /* --- 全局背景 --- */
        .stApp {
            background-image: linear-gradient(to right top, #d16ba5, #c777b9, #ba83ca, #aa8fd8, #9a9ae1, #8aa7ec, #79b3f4, #69bff8, #52cffe, #41dfff, #46eefa, #5ffbf1);
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }

        /* --- 主内容区样式 --- */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 3rem;
            padding-right: 3rem;
            background-color: rgba(255, 255, 255, 0.85); /* 半透明背景 */
            backdrop-filter: blur(10px); /* 模糊效果 */
            border-radius: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }

        /* --- Streamlit 组件美化 --- */
        .stButton>button {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.2s ease-in-out;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.15);
        }
        
        /* --- 卡片容器样式 --- */
        [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] {
            border: 1px solid rgba(0,0,0,0.1);
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            background-color: rgba(255, 255, 255, 0.9);
        }

        /* --- Expander 样式 --- */
        .st-expander {
            border: none !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            border-radius: 10px !important;
        }

        /* --- 文件上传框样式 --- */
        [data-testid="stFileUploader"] {
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 1.5rem;
            background-color: #fafafa;
        }
        
        /* --- 侧边栏样式 --- */
        [data-testid="stSidebar"] {
            background-color: rgba(240, 242, 246, 0.7);
             backdrop-filter: blur(5px);
        }

        </style>
    """, unsafe_allow_html=True)

# --- API 调用辅助函数 ---

def api_request(method, endpoint, data=None, files=None):
    """一个通用的函数来处理对 Flask 后端的 API 请求"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, data=data, files=files, timeout=300) # 增加超时时间
        response.raise_for_status()  # 如果响应状态码是 4xx 或 5xx，则抛出异常
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"请求 API 失败: {e}")
        try:
            # 尝试解析错误响应体
            error_details = e.response.json()
            st.error(f"服务器返回错误: {error_details.get('message', '未知错误')}")
        except:
            st.error(f"无法解析服务器错误响应。")
        return None

# --- 状态管理函数 ---

def refresh_kb_list():
    """刷新知识库列表并存储在 session state 中"""
    st.session_state.kb_list_ts = time.time() # 记录刷新时间
    response = api_request('GET', '/list_kbs')
    if response and response.get('status') == 'success':
        st.session_state.kb_list = response.get('knowledge_bases', [])
    else:
        st.session_state.kb_list = []

# --- 界面渲染函数 ---

def page_kb_management():
    """渲染知识库管理页面"""
    st.header("📚 知识库管理中心")
    st.markdown("在这里，您可以创建、查看和删除用于合同审查的专业知识库。")

    # 列出现有知识库
    with st.container(border=True):
        st.subheader("🗂️ 现有知识库")
        col1, col2 = st.columns([4, 1])
        with col1:
            if 'kb_list' in st.session_state and st.session_state.kb_list:
                st.dataframe(st.session_state.kb_list, use_container_width=True)
            else:
                st.info("当前没有知识库。请在下方构建一个新的知识库。", icon="ℹ️")
        with col2:
            if st.button("🔄 刷新列表", use_container_width=True):
                refresh_kb_list()
                st.rerun()

    # 构建新知识库
    with st.container(border=True):
        st.subheader("➕ 构建新知识库")
        kb_name = st.text_input(
            "**知识库名称 (collection_name)**", 
            placeholder="例如: civil_code_2021",
            help="只能包含字母、数字和下划线，不能以数字开头。"
        )
        uploaded_kb_file = st.file_uploader(
            "**上传知识库文件 (PDF)**",
            type="pdf",
            key="kb_uploader"
        )
        if st.button("🚀 开始构建", type="primary"):
            if not kb_name:
                st.warning("请输入知识库名称。", icon="⚠️")
            elif not uploaded_kb_file:
                st.warning("请上传知识库文件。", icon="⚠️")
            else:
                with st.spinner(f"正在构建知识库 '{kb_name}'..."):
                    files = {'file': (uploaded_kb_file.name, uploaded_kb_file.getvalue(), 'application/pdf')}
                    data = {'collection_name': kb_name}
                    response = api_request('POST', '/build_kb', data=data, files=files)
                if response:
                    if response.get('status') == 'success':
                        st.success(response.get('message'), icon="✅")
                        refresh_kb_list() # 成功后刷新列表
                        st.rerun()
                    else:
                        st.error(f"构建失败: {response.get('message')}", icon="❌")
    
    # 删除知识库
    with st.container(border=True):
        st.subheader("🗑️ 删除知识库")
        if st.session_state.kb_list:
            kb_to_delete = st.selectbox(
                "**选择要删除的知识库**",
                options=st.session_state.kb_list,
                index=None,
                placeholder="请选择..."
            )
            if kb_to_delete:
                confirm_delete = st.checkbox(f"我确认要永久删除知识库 '{kb_to_delete}'", key="delete_confirm")
                if st.button("❌ 确认删除", disabled=(not confirm_delete)):
                    with st.spinner(f"正在删除知识库 '{kb_to_delete}'..."):
                        data = {'collection_name': kb_to_delete}
                        response = api_request('POST', '/delete_kb', data=data)
                    if response:
                        if response.get('status') == 'success':
                            st.success(response.get('message'), icon="✅")
                            refresh_kb_list()
                            st.rerun()
                        else:
                            st.error(f"删除失败: {response.get('message')}", icon="❌")
        else:
            st.info("没有可删除的知识库。", icon="ℹ️")


def page_contract_review():
    """渲染合同条款审查页面"""
    st.header("🔍 智能合同条款审查")
    st.markdown("基于您选择的知识库，对合同文本进行逐条分析，识别潜在风险。")

    if not st.session_state.get('kb_list'):
        st.warning("系统中没有可用的知识库。请先在“知识库管理”页面创建一个。", icon="⚠️")
        return

    # 输入区域
    with st.container(border=True):
        st.subheader("📝 审查设置")
        selected_kb = st.selectbox(
            "**1. 选择审查依据的知识库** 📚",
            options=st.session_state.kb_list,
            index=None,
            placeholder="请选择一个知识库..."
        )
        perspective = st.radio(
            "**2. 选择你的立场** 👤",
            options=['甲方', '乙方'],
            horizontal=True
        )
        uploaded_contract_file = st.file_uploader(
            "**3. 上传需要审查的合同文件 (PDF)** 📄",
            type="pdf",
            key="contract_uploader"
        )

        if st.button("🚀 开始审查", type="primary", use_container_width=True):
            if not selected_kb or not perspective or not uploaded_contract_file:
                st.warning("请确保已选择知识库、立场并上传了合同文件。", icon="⚠️")
            else:
                with st.spinner("正在进行深度合同审查，请稍候..."):
                    files = {'contract_file': (uploaded_contract_file.name, uploaded_contract_file.getvalue(), 'application/pdf')}
                    data = {
                        'collection_name': selected_kb,
                        'perspective': perspective
                    }
                    # 将响应存储在 session_state 中，避免 rerun 后丢失
                    st.session_state.review_response = api_request('POST', '/review_contract', data=data, files=files)
    
    # 显示结果
    if 'review_response' in st.session_state and st.session_state.review_response:
        response = st.session_state.review_response
        st.markdown("---")
        st.subheader("📊 审查结果报告")

        with st.container(border=True):
            st.markdown("#### 📄 合同摘要")
            st.markdown(response.get('contract_summary', "未能生成合同摘要。"))
        
        with st.container(border=True):
            st.markdown("#### 🚨 风险审查详情")
            risk_report = response.get('risk_review_report', [])
            if not risk_report:
                st.success("🎉 恭喜！根据所选知识库，未在合同中发现对您不利的风险条款。", icon="✅")
            else:
                st.info(f"共发现 {len(risk_report)} 个潜在风险点：", icon="💡")
                for i, risk in enumerate(risk_report):
                    risk_level = risk.get('risk_level', '未知')
                    if '高' in risk_level:
                        icon = "🔴"
                        delta_color = "inverse"
                    elif '中' in risk_level:
                        icon = "🟠"
                        delta_color = "normal"
                    else:
                        icon = "🟡"
                        delta_color = "off"
                    
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**风险点 {i+1}:** {risk.get('clause_category', '未知类别')}")
                        with col2:
                            st.metric(label="风险等级", value=risk_level, delta=icon, delta_color=delta_color)

                        tab1, tab2, tab3 = st.tabs(["风险条款原文", "合规性与风险分析", "修改建议"])

                        with tab1:
                            st.code(risk.get('original_clause', 'N/A'), language=None)
                        with tab2:
                            st.markdown("**合规性分析 (基于知识库):**")
                            st.info(risk.get('compliance_analysis', 'N/A'), icon="⚖️")
                            st.markdown("**具体风险说明:**")
                            st.warning(risk.get('risk_reason', 'N/A'), icon="⚠️")
                        with tab3:
                            st.markdown("**修改建议:**")
                            st.success(risk.get('modification_suggestion', 'N/A'), icon="✍️")


def page_party_review():
    """渲染交易对手审查页面"""
    st.header("🤝 交易对手审查")
    st.markdown("根据您提供的对方简介和合同文本，分析其履约能力和潜在风险。")

    # 输入区域
    with st.container(border=True):
        st.subheader("📝 审查信息输入")
        perspective = st.radio(
            "**1. 选择我方立场** 👤",
            options=['甲方', '乙方'],
            horizontal=True
        )
        party_profile = st.text_area(
            "**2. 粘贴对方公司简介或相关背景资料** 🏢",
            height=200,
            placeholder="例如，从对方官网、宣传册、或工商信息中获取的公司介绍..."
        )
        uploaded_contract_file_party = st.file_uploader(
            "**3. 上传相关的合同文件 (PDF)** 📄",
            type="pdf",
            key="party_contract_uploader"
        )

        if st.button("🔍 开始审查对方", type="primary", use_container_width=True):
            if not party_profile or not uploaded_contract_file_party:
                st.warning("请确保已粘贴对方简介并上传了合同文件。", icon="⚠️")
            else:
                with st.spinner("正在分析交易对手，请稍候..."):
                    files = {'contract_file': (uploaded_contract_file_party.name, uploaded_contract_file_party.getvalue(), 'application/pdf')}
                    data = {
                        'perspective': perspective,
                        'party_profile': party_profile
                    }
                    st.session_state.party_response = api_request('POST', '/review_party', data=data, files=files)
            
    # 显示结果
    if 'party_response' in st.session_state and st.session_state.party_response:
        response = st.session_state.party_response
        st.markdown("---")
        st.subheader("📊 主体审查报告")
        
        with st.container(border=True):
            st.markdown("#### ⚠️ 风险总结")
            st.warning(response.get('risk_summary', "未能生成风险总结。"))
            
            st.markdown("#### 📈 履约能力匹配度分析")
            st.info(response.get('capability_analysis', "未能生成履约能力分析。"))

            st.markdown("#### 🕵️ 尽职调查建议")
            suggestions = response.get('due_diligence_suggestions', [])
            if suggestions:
                suggestion_text = ""
                for suggestion in suggestions:
                    suggestion_text += f"- {suggestion}\n"
                st.markdown(suggestion_text)
            else:
                st.success("无特别的尽职调查建议。", icon="✅")

# --- 主程序 ---
def main():
    st.set_page_config(page_title="智能合同审查助手", layout="wide", initial_sidebar_state="expanded")
    
    # 应用自定义CSS
    load_custom_css()

    # 标题部分
    st.title("🤖 智能合同审查助手")
    st.caption("AI-Powered Legal Tech Assistant")
    
    # 初始化 session state
    if 'kb_list' not in st.session_state or time.time() - st.session_state.get('kb_list_ts', 0) > 300:
        refresh_kb_list()
    
    # 初始化响应存储
    if 'review_response' not in st.session_state:
        st.session_state.review_response = None
    if 'party_response' not in st.session_state:
        st.session_state.party_response = None

    # 侧边栏导航
    with st.sidebar:
        st.header("导航菜单")
        page = st.radio(
            "选择功能",
            ["合同条款审查", "交易对手审查", "知识库管理"],
            captions=["基于知识库的风险分析", "分析交易对手履约能力", "管理您的知识库"]
        )
        st.markdown("---")
        st.info("💡 **提示**: 请先在“知识库管理”中创建或确认已有知识库，然后再进行合同审查。")
        st.markdown("---")
        st.success("Powered by Streamlit & AI")


    # 根据选择渲染不同页面
    if page == "知识库管理":
        page_kb_management()
    elif page == "合同条款审查":
        page_contract_review()
    elif page == "交易对手审查":
        page_party_review()

if __name__ == "__main__":
    main()