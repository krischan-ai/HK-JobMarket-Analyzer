from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from src.llm_config_manager import LLMConfigManager
from src.logger import get_logger

st.set_page_config(
    page_title="模型配置",
    page_icon="⚙️",
    layout="centered",
)

st.title("⚙️ 大模型配置")
st.markdown("在此页面配置大语言模型 API，启用后即可使用 LLM 引擎进行智能技能提取。")
st.markdown("---")

config_mgr = LLMConfigManager()
current_config = config_mgr.load()

col_status, col_model = st.columns([1, 2])

with col_status:
    if config_mgr.configured:
        st.success("✅ **LLM 已配置**")
    else:
        st.warning("⚠️ **LLM 未配置**")

with col_model:
    st.caption(f"当前模型: {current_config.get('model', 'deepseek-chat')}")
    st.caption(f"API Base: {current_config.get('base_url', 'https://api.deepseek.com/v1')}")

st.markdown("---")

with st.form("llm_config_form", clear_on_submit=False):
    st.subheader("API 配置")

    api_key = st.text_input(
        "API Key",
        value=current_config.get("api_key", ""),
        type="password",
        help="输入你的 API Key，例如 DeepSeek、OpenAI、Groq 等兼容 API 的 Key。存储在本地 config/llm_config.json",
    )

    base_url = st.text_input(
        "API Base URL",
        value=current_config.get("base_url", "https://api.deepseek.com/v1"),
        help="OpenAI 兼容 API 的基础地址。例如：DeepSeek: https://api.deepseek.com/v1, OpenAI: https://api.openai.com/v1",
    )

    model = st.text_input(
        "模型名称",
        value=current_config.get("model", "deepseek-chat"),
        help="模型名称。例如：deepseek-chat, gpt-4o-mini, gemini-2.0-flash",
    )

    timeout = st.slider("请求超时（秒）", 10, 120, current_config.get("timeout", 30), help="API 请求超时时间")

    st.markdown("---")
    col_save, col_test, col_clear = st.columns([1, 1, 1])

    with col_save:
        saved = st.form_submit_button("💾 保存配置", use_container_width=True, type="primary")

    with col_test:
        tested = st.form_submit_button("🔌 测试连接", use_container_width=True)

    with col_clear:
        cleared = st.form_submit_button("🗑️ 清除配置", use_container_width=True)

if saved:
    ok = config_mgr.save(api_key=api_key, base_url=base_url, model=model, timeout=timeout)
    if ok:
        st.success("✅ 配置已保存！LLM 引擎将在下次使用时自动加载配置。")
        st.rerun()
    else:
        st.error("❌ 配置保存失败，请检查文件权限。")

if tested:
    ok = config_mgr.save(api_key=api_key, base_url=base_url, model=model, timeout=timeout)
    if ok:
        with st.spinner("正在测试连接..."):
            success, msg = config_mgr.test_connection()
            if success:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")
    else:
        st.error("❌ 配置保存失败，请检查后重试。")

if cleared:
    config_mgr.clear()
    st.success("✅ 配置已清除，LLM 引擎将回退至规则引擎模式。")
    st.rerun()

st.markdown("---")
st.subheader("🔍 LLM 引擎状态")

col_a, col_b, col_c = st.columns(3)
col_a.metric("API Key 已配置", "✅ 是" if config_mgr.configured else "❌ 否")
col_b.metric("Base URL", current_config.get("base_url", "-"))
col_c.metric("模型", current_config.get("model", "-"))

st.markdown("")
st.info(
    "💡 **启用 LLM 后的工作流程**：\n\n"
    "1. 规则引擎首先提取常见技能关键词（< 5ms/条）\n"
    "2. 如果规则引擎提取结果不足，自动调用 LLM 进行深度提取\n"
    "3. LLM 发现的**新词**可通过 `scripts/update_dict.py` 增量更新到词表\n"
    "4. 重复使用后，词表逐渐完善，对 LLM 的依赖逐渐降低\n\n"
    "**支持的 API 提供商**：DeepSeek、OpenAI、Groq、Google Gemini（OpenAI 兼容模式）"
)

st.markdown("---")
st.subheader("📋 快速上手")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**DeepSeek**")
    st.code(
        "API Base:\nhttps://api.deepseek.com/v1\n\nModel:\ndeepseek-chat",
        language="text",
    )
    st.markdown("[获取 Key](https://platform.deepseek.com/api_keys)")

with col2:
    st.markdown("**OpenAI**")
    st.code(
        "API Base:\nhttps://api.openai.com/v1\n\nModel:\ngpt-4o-mini",
        language="text",
    )
    st.markdown("[获取 Key](https://platform.openai.com/api-keys)")

with col3:
    st.markdown("**Groq (免费)**")
    st.code(
        "API Base:\nhttps://api.groq.com/openai/v1\n\nModel:\nllama-3.3-70b-versatile",
        language="text",
    )
    st.markdown("[获取 Key](https://console.groq.com/keys)")

st.caption("API Key 仅存储在本地 config/llm_config.json 文件中，不会上传到任何远程服务器。")
