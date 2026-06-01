from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.i18n import get_translator
from src.knowledge_base.uploader import Uploader
from src.knowledge_base.validator import detect_mapping
from src.knowledge_base.stats import StatsAggregator
from src.knowledge_base.query import KnowledgeBase
from src.storage.mongodb import JobDatabase

st.set_page_config(page_title="知识库管理", page_icon="📂", layout="wide")

st.title("📂 知识库管理")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📤 上传数据", "📊 数据概览", "⚙️ 数据管理"])

with tab1:
    st.header("上传招聘数据")

    uploaded_file = st.file_uploader(
        "选择 CSV/JSON/Excel 文件",
        type=["csv", "json", "xlsx"],
        help="支持 UTF-8 CSV、JSON（数组或逐行）、Excel 格式",
    )

    col1, col2 = st.columns(2)
    with col1:
        source_tag = st.text_input("数据来源标签", value="user_upload", help="用于标识数据来源")
    with col2:
        pass

    with st.expander("高级选项"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            run_cleaning = st.checkbox("执行清洗", value=True)
        with col_b:
            run_extraction = st.checkbox("执行技能提取", value=True)
        with col_c:
            detect_duplicates = st.checkbox("检测去重", value=True)

    if uploaded_file is not None:
        st.info(f"文件: {uploaded_file.name} | 大小: {len(uploaded_file.getvalue()) / 1024:.1f} KB")

        preview_df = None
        if uploaded_file.name.endswith(".csv"):
            preview_df = pd.read_csv(uploaded_file, nrows=5)
        elif uploaded_file.name.endswith(".json"):
            raw = json.loads(uploaded_file.getvalue().decode("utf-8"))
            preview_df = pd.DataFrame(raw if isinstance(raw, list) else [raw])
        elif uploaded_file.name.endswith(".xlsx"):
            preview_df = pd.read_excel(uploaded_file, nrows=5)

        if preview_df is not None:
            st.subheader("数据预览")
            st.dataframe(preview_df, width="stretch")

            mapping = detect_mapping(list(preview_df.columns))
            st.subheader("字段映射")
            mapping_rows = []
            for orig_col, std_col in mapping.items():
                icon = "✅" if std_col else "⚠️"
                mapping_rows.append({"原始字段": orig_col, "映射到": std_col or "❌ 未匹配（将保留原字段名）", "状态": icon})
            st.dataframe(pd.DataFrame(mapping_rows), width="stretch")

        if st.button("开始处理", type="primary"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            try:
                progress_bar = st.progress(0, text="初始化...")
                status_placeholder = st.empty()

                status_placeholder.info("📄 文件解析中...")
                progress_bar.progress(10)

                uploader = Uploader(
                    file_path=tmp_path,
                    source_tag=source_tag,
                    detect_duplicates=detect_duplicates,
                    run_cleaning=run_cleaning,
                    run_extraction=run_extraction,
                )

                status_placeholder.info("🔍 格式校验中...")
                progress_bar.progress(20)

                if not uploader.validate_format():
                    st.error("文件格式校验失败")
                    Path(tmp_path).unlink(missing_ok=True)
                    st.stop()

                status_placeholder.info("🧹 数据清洗中...")
                progress_bar.progress(40)

                result = uploader.process()

                status_placeholder.info("📦 入库中...")
                progress_bar.progress(80)

                time.sleep(0.3)
                progress_bar.progress(100)
                status_placeholder.success("处理完成!")

                st.markdown("---")
                st.subheader("处理摘要")
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                col_r1.metric("总记录数", result.total)
                col_r2.metric("成功入库", result.success)
                col_r3.metric("跳过", result.skipped)
                col_r4.metric("耗时", f"{result.duration_ms:.0f} ms")

                if result.errors:
                    st.subheader("错误信息")
                    for e in result.errors:
                        st.error(e)

            except Exception as e:
                st.error(f"处理失败: {e}")
            finally:
                Path(tmp_path).unlink(missing_ok=True)

with tab2:
    st.header("知识库统计")

    db = JobDatabase()
    if db.is_connected:
        stats = StatsAggregator(db)

        total = stats.total_records()
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("总记录数", total)
        salary = stats.salary_range()
        if salary:
            col_s2.metric("平均月薪 (HKD)", f"{salary.get('avg', 0):,.0f}")
            col_s3.metric("薪资范围", f"{salary.get('min', 0):,.0f} - {salary.get('max', 0):,.0f} HKD")

        src_df = stats.source_distribution()
        if not src_df.empty:
            st.subheader("数据来源分布")
            fig = px.pie(src_df, values="count", names="source", title="数据来源占比")
            st.plotly_chart(fig, width="stretch")

        loc_df = stats.location_distribution()
        if not loc_df.empty:
            st.subheader("地点分布 Top 10")
            fig = px.bar(
                loc_df.head(10), x="count", y="location",
                orientation="h", title="岗位数量 (按地点)",
                color="count", color_continuous_scale="Blues",
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("MongoDB 未连接，统计功能不可用。当前使用 CSV 模式。")

        csv_path = Path("data/cleaned/jobs.csv")
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            st.metric("CSV 记录数", len(df))
            translator = get_translator()
            df = translator.translate_df(df)
            if "location" in df.columns:
                loc_counts = df["location"].value_counts().head(10).reset_index()
                loc_counts.columns = ["location", "count"]
                fig = px.bar(
                    loc_counts, x="count", y="location",
                    orientation="h", title="岗位数量 (按地点)",
                    color="count", color_continuous_scale="Blues",
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, width="stretch")

with tab3:
    st.header("数据管理")

    db_mgmt = JobDatabase()
    if db_mgmt.is_connected:
        search_keyword = st.text_input("关键词搜索 JD 内容", placeholder="例如: Python, React, AWS...")
        if search_keyword:
            kb = KnowledgeBase(db_mgmt)
            results = kb.search_by_keyword(search_keyword, limit=50)
            if results:
                st.success(f"找到 {len(results)} 条结果")
                st.dataframe(pd.DataFrame(results).drop(columns=["_id"], errors="ignore").head(100), width="stretch")
            else:
                st.info("无匹配结果")

        st.markdown("---")
        st.subheader("批量操作")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if st.button("清空所有数据", type="secondary"):
                count = db_mgmt.delete_many({})
                st.success(f"已删除 {count} 条记录" if count else "数据库为空")
        with col_d2:
            csv_path = Path("data/cleaned/jobs.csv")
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                st.download_button(
                    "导出全部数据 (CSV)",
                    data=df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="hk_jobs_export.csv",
                    mime="text/csv",
                )
    else:
        st.info("MongoDB 未连接，数据管理功能不可用。当前使用 CSV 模式。")

        csv_path = Path("data/cleaned/jobs.csv")
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            st.dataframe(df.head(100), width="stretch")
            st.download_button(
                "导出 CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name="hk_jobs_export.csv",
                mime="text/csv",
            )

st.markdown("---")
st.caption("HK-JobMarket-Analyzer v1.2 | 数据仅供学术研究参考")
