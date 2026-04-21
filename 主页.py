import streamlit as st
from database import init_db, get_all_classes, get_latest_exam_per_class, get_top_students, get_all_exams
import pandas as pd

st.set_page_config(
    page_title="校园周测数据看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化数据库
init_db()

# ── 样式 ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        color: white;
        text-align: center;
    }
    .metric-card h2 { font-size: 2.2rem; margin: 0; }
    .metric-card p  { margin: 0; opacity: 0.85; font-size: 0.9rem; }

    .top5-card {
        background: #fff9e6;
        border-left: 4px solid #f6c90e;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
    }
    .class-card {
        background: #f0f4ff;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
    }
    div[data-testid="stSidebarNav"] { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ── 标题 ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">📊 校园周测数据看板</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">统一管理周测成绩 · 自动排名评优 · 数据趋势一目了然</div>', unsafe_allow_html=True)

# ── 顶部统计卡片 ──────────────────────────────────────────────────────────────
classes = get_all_classes()
all_exams = get_all_exams()

total_classes = len(classes)
# 按考试名称+日期去重，统计实际举办的周测次数
total_exams = len(set((e["title"], e["exam_date"]) for e in all_exams))
latest_exams = get_latest_exam_per_class()
total_students = sum(e.get("student_count", 0) for e in latest_exams)

col1, col2, col3, col4 = st.columns(4)

def metric_card(col, icon, value, label, color):
    col.markdown(f"""
    <div style="background:linear-gradient(135deg,{color});border-radius:12px;
                padding:1.2rem 1.5rem;color:white;text-align:center;">
        <div style="font-size:1.8rem">{icon}</div>
        <div style="font-size:2rem;font-weight:700;margin:0.2rem 0">{value}</div>
        <div style="opacity:0.85;font-size:0.9rem">{label}</div>
    </div>
    """, unsafe_allow_html=True)

metric_card(col1, "🏫", total_classes, "参与班级", "#667eea,#764ba2")
metric_card(col2, "📝", total_exams, "累计周测场次", "#f093fb,#f5576c")
metric_card(col3, "👥", total_students, "本期参测学生", "#4facfe,#00f2fe")
metric_card(col4, "📅", all_exams[0]["exam_date"] if all_exams else "暂无", "最近一次考试", "#43e97b,#38f9d7")

st.markdown("---")

# ── 各班最新周测概览 ──────────────────────────────────────────────────────────
if not latest_exams:
    st.info("📭 暂无数据。请先在「学生管理」页添加班级和学生，再录入成绩。")
else:
    st.subheader("📋 各班最新周测概览")

    for exam in latest_exams:
        with st.expander(
            f"**{exam['grade']} {exam['class_name']}** ｜ {exam['title']} · {exam['exam_date']} ｜ "
            f"参测 {exam['student_count']} 人 ｜ 班级均分 {round(exam['avg_total'], 1) if exam['avg_total'] else '--'}",
            expanded=False
        ):
            top5 = get_top_students(exam["id"], 5)
            if top5:
                st.markdown("**🏆 本次前五名**")
                medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                cols = st.columns(len(top5))
                for i, (col, s) in enumerate(zip(cols, top5)):
                    # 修复：用名次直接取勋章，避免IndexError
                    rank = s["rank"]
                    medal = medals[rank - 1] if rank <= len(medals) else f"No.{rank}"
                    col.markdown(f"""
                    <div style="background:#fff9e6;border-left:4px solid #f6c90e;
                                border-radius:8px;padding:0.7rem 0.8rem;text-align:center;">
                        <div style="font-size:1.5rem">{medal}</div>
                        <div style="font-weight:600">{s['name']}</div>
                        <div style="color:#666;font-size:0.85rem">总分 <strong>{int(s['total'])}</strong></div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("该次考试暂未录入成绩")

    # ── 各班均分横向对比 ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 各班最新均分横向对比")

    chart_data = [e for e in latest_exams if e["avg_total"]]
    if chart_data:
        import plotly.graph_objects as go

        labels = [f"{e['grade']}{e['class_name']}" for e in chart_data]
        values = [round(e["avg_total"], 1) for e in chart_data]

        fig = go.Figure(go.Bar(
            x=labels,
            y=values,
            marker_color=["#667eea", "#764ba2", "#f093fb", "#f5576c",
                          "#4facfe", "#43e97b", "#f6c90e", "#fa8231"][:len(labels)],
            text=values,
            textposition="outside"
        ))
        fig.update_layout(
            height=350,
            margin=dict(t=20, b=20),
            yaxis_title="班级均分",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("录入成绩后将在此显示各班对比图")
