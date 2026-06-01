from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
pio.json.config.default_engine = "json"

from src.i18n import get_translator
from src.llm_config_manager import LLMConfigManager

st.set_page_config(
    page_title="HK Job Market Analyzer",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("香港 IT 招聘市场数据分析看板")
st.markdown("---")

st.markdown(
    """
    <div style="text-align: center; padding: 1rem;">
        <a href="/" target="_self" style="margin: 0 1rem; font-size: 1.1rem;">📊 分析看板</a>
        <a href="/01_%E7%9F%A5%E8%AF%86%E5%BA%93%E7%AE%A1%E7%90%86" target="_self" style="margin: 0 1rem; font-size: 1.1rem;">📂 知识库管理</a>
        <a href="/02_%E6%A8%A1%E5%9E%8B%E9%85%8D%E7%BD%AE" target="_self" style="margin: 0 1rem; font-size: 1.1rem;">⚙️ 模型配置</a>
    </div>
    <hr style="margin: 0.5rem 0;">
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    translator = get_translator()
    df = translator.translate_df(df)
    return df


@st.cache_data
def flatten_skills(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.dropna(subset=["skills"]).iterrows():
        skills = row["skills"]
        if isinstance(skills, str):
            try:
                import json
                skills = json.loads(skills.replace("'", '"'))
            except Exception:
                continue
        if isinstance(skills, dict):
            translator = get_translator()
            translated = translator.translate_skills(skills)
            for category, skill_list in translated.items():
                if isinstance(skill_list, list):
                    for skill in skill_list:
                        records.append({"skill": skill, "category": category})
    return pd.DataFrame(records)


data_path = "data/cleaned/jobs.csv"
try:
    df = load_data(data_path)
except FileNotFoundError:
    st.warning("数据文件未找到，请先运行爬虫或上传数据。\n执行: `python scripts/run_pipeline.py`")
    st.stop()

with st.sidebar:
    st.header("筛选条件")

    if "location" in df.columns:
        locations = df["location"].dropna().unique().tolist()
        selected_locations = st.multiselect("工作地点", sorted(locations), default=[])

    if "source" in df.columns:
        sources = df["source"].dropna().unique().tolist()
        selected_sources = st.multiselect("数据来源", sorted(sources), default=sources)

    st.markdown("---")
    st.caption(f"总数据量: {len(df)} 条岗位")

    st.markdown("---")
    _llm_config = LLMConfigManager()
    if _llm_config.configured:
        st.success(f"🤖 LLM: {_llm_config.load().get('model', '-')}")
    else:
        st.warning("⚙️ LLM 未配置")
        if st.button("前往配置 ➔", key="goto_llm_config"):
            st.switch_page("pages/02_模型配置.py")

filtered_df = df.copy()
if selected_locations:
    filtered_df = filtered_df[filtered_df["location"].isin(selected_locations)]
if selected_sources:
    filtered_df = filtered_df[filtered_df["source"].isin(selected_sources)]

tab1, tab2, tab3, tab4 = st.tabs(["技术热度", "薪资分析", "区域分布", "原始数据"])

with tab1:
    st.header("技术栈热度排行")

    skill_df = flatten_skills(filtered_df)
    if not skill_df.empty:
        top_n = st.slider("显示前 N 个技能", 5, 30, 15, key="skill_top_n")
        top_skills = skill_df["skill"].value_counts().head(top_n).reset_index()
        top_skills.columns = ["skill", "count"]

        fig = px.bar(
            top_skills,
            x="count",
            y="skill",
            orientation="h",
            title=f"香港 IT 技术栈需求排行 Top {top_n}",
            color="count",
            color_continuous_scale="Blues",
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            height=600,
            xaxis_title="岗位数量",
            yaxis_title="技术栈",
        )
        st.plotly_chart(fig, width="stretch")

        st.subheader("技能类别分布")
        cat_counts = skill_df["category"].value_counts().reset_index()
        cat_counts.columns = ["category", "count"]
        fig2 = px.pie(cat_counts, values="count", names="category", title="技能类别占比")
        st.plotly_chart(fig2, width="stretch")
    else:
        st.info("暂无技能数据")

with tab2:
    st.header("薪资分布概览")

    salary_df = filtered_df.dropna(subset=["salary_min"])
    if not salary_df.empty:
        salary_df["avg_salary"] = (salary_df["salary_min"] + salary_df["salary_max"].fillna(salary_df["salary_min"])) / 2

        col1, col2, col3 = st.columns(3)
        col1.metric("平均月薪 (HKD)", f"{salary_df['avg_salary'].mean():,.0f}")
        col2.metric("最低月薪 (HKD)", f"{salary_df['salary_min'].min():,.0f}")
        col3.metric("最高月薪 (HKD)", f"{salary_df['salary_max'].max():,.0f}")

        if "location" in salary_df.columns:
            fig = px.box(
                salary_df,
                x="salary_min",
                y="location",
                title="各区域薪资分布",
                color="location",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(
                height=500,
                showlegend=False,
                xaxis_title="月薪 (HKD)",
                yaxis_title="工作地点",
            )
            st.plotly_chart(fig, width="stretch")

        if "title" in salary_df.columns:
            top_titles = salary_df.groupby("title")["avg_salary"].agg(["mean", "count"]).query("count >= 1").sort_values("mean", ascending=False).head(15)
            fig3 = px.bar(
                top_titles.reset_index(),
                x="mean",
                y="title",
                orientation="h",
                title="高薪职位 Top 15",
                color="mean",
                color_continuous_scale="Viridis",
            )
            fig3.update_layout(
                yaxis={"categoryorder": "total ascending"},
                height=500,
                xaxis_title="平均月薪 (HKD)",
                yaxis_title="职位",
            )
            st.plotly_chart(fig3, width="stretch")
    else:
        st.info("暂无薪资数据")

with tab3:
    st.header("岗位区域分布")

    if "location" in filtered_df.columns:
        loc_counts = filtered_df["location"].value_counts().reset_index()
        loc_counts.columns = ["location", "count"]

        fig = px.bar(
            loc_counts.head(20),
            x="count",
            y="location",
            orientation="h",
            title="香港各区域岗位数量分布",
            color="count",
            color_continuous_scale="Reds",
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            height=600,
            xaxis_title="岗位数量",
            yaxis_title="工作地点",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("暂无地点数据")

with tab4:
    st.header("原始数据预览")
    st.dataframe(filtered_df.head(100), width="stretch")

    csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="下载 CSV",
        data=csv,
        file_name="hk_jobs_filtered.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption("HK-JobMarket-Analyzer v1.2 | 数据仅供学术研究参考")
