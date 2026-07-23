"""扫地机器人智能客服的 Streamlit 前端。"""

import importlib
from uuid import uuid4

import streamlit as st

from utils.auth_service import authenticate_user, init_user_db, register_user


AGENT_CACHE_VERSION = "report-user-check-v3"


st.set_page_config(
    page_title="扫地机器人智能客服",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 900px;
            padding-top: 2.2rem;
            padding-bottom: 6rem;
        }
        [data-testid="stChatMessage"] {
            border: 1px solid rgba(128, 128, 128, 0.16);
            border-radius: 16px;
            padding: 0.35rem 0.65rem;
            margin-bottom: 0.65rem;
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button {
            text-align: left;
            justify-content: flex-start;
        }
        .subtitle {
            color: #6b7280;
            margin-top: -0.65rem;
            margin-bottom: 1.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

init_user_db()


def show_auth_page() -> None:
    """显示登录和注册页面，认证成功后进入聊天页面。"""
    st.title("🤖 扫地机器人智能客服")
    st.markdown(
        '<p class="subtitle">登录后开始咨询设备使用、维护和故障问题</p>',
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(["登录", "注册"])

    with login_tab:
        with st.form("login_form"):
            login_username = st.text_input("用户名", key="login_username")
            login_password = st.text_input(
                "密码", type="password", key="login_password"
            )
            login_submitted = st.form_submit_button(
                "登录", type="primary", use_container_width=True
            )

        if login_submitted:
            user = authenticate_user(login_username, login_password)
            if user is None:
                st.error("用户名或密码错误。")
            else:
                st.session_state.user = user
                st.session_state.messages = []
                st.session_state.thread_id = str(uuid4())
                st.rerun()

    with register_tab:
        with st.form("register_form"):
            register_username = st.text_input("用户名", key="register_username")
            register_password = st.text_input(
                "密码", type="password", key="register_password"
            )
            register_submitted = st.form_submit_button(
                "注册并登录", type="primary", use_container_width=True
            )

        if register_submitted:
            success, message, user = register_user(
                register_username, register_password
            )
            if not success:
                st.error(message)
            else:
                st.session_state.user = user
                st.session_state.messages = []
                st.session_state.thread_id = str(uuid4())
                st.rerun()


if "user" not in st.session_state:
    show_auth_page()
    st.stop()


@st.cache_resource(show_spinner=False)
def get_agent(cache_version: str):
    """创建并缓存 Agent，避免页面每次刷新都重新加载模型与向量库。"""
    # Agent 会加载模型和本地向量库，延迟导入可避免阻塞页面首屏渲染。
    import agent.react_agent as react_agent_module

    # Streamlit 热更新可能保留旧类对象，显式重载可避免方法签名仍是旧版本。
    react_agent_module = importlib.reload(react_agent_module)

    return react_agent_module.ReactAgent()


if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid4())


with st.sidebar:
    st.success(f"已登录：{st.session_state.user['username']}")
    if st.button("退出登录", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.header("使用指南")
    st.caption("可以咨询使用技巧、故障排查、选购保养，也可以生成个人使用报告。")

    st.subheader("试着问我")
    examples = (
        "扫地机器人清扫时总是漏扫怎么办？",
        "拖布有异味，应该如何清洁保养？",
        "潮湿天气适合使用扫拖机器人吗？",
        "帮我生成本月的使用报告",
    )
    selected_example = None
    for index, example in enumerate(examples):
        if st.button(example, key=f"example_{index}", use_container_width=True):
            selected_example = example

    st.divider()
    if st.button("🗑️ 清空对话", use_container_width=True):
        # 新 thread_id 会开启一段完全独立的 Agent 上下文。
        st.session_state.thread_id = str(uuid4())
        st.session_state.messages = []
        st.rerun()


st.title("🤖 扫地机器人智能客服")
st.markdown(
    '<p class="subtitle">你的使用、维护、故障排查与设备报告助手</p>',
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.info("你好！请在下方输入问题，或从左侧选择一个常用问题开始。")

for message in st.session_state.messages:
    avatar = "🧑" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])


typed_prompt = st.chat_input("请输入你想咨询的问题……")
prompt = selected_example or typed_prompt

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        try:
            with st.spinner("正在查找资料并思考……"):
                response = st.write_stream(
                    get_agent(AGENT_CACHE_VERSION).execute_stream(
                        prompt,
                        thread_id=st.session_state.thread_id,
                        user_id=st.session_state.user["username"],
                    )
                )
        except Exception as exc:
            response = "抱歉，服务暂时不可用，请稍后重试。"
            st.error(response)
            st.exception(exc)

    st.session_state.messages.append(
        {"role": "assistant", "content": response or "抱歉，我暂时没有找到合适的答案。"}
    )
