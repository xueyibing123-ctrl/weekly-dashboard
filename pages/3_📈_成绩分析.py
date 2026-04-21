import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from database import (
    get_all_classes, get_exams_by_class, get_scores_for_exam,
    get_top_students, get_class_history, get_students_by_class,
    get_student_history
)
from io import BytesIO

st.set_page_config(page_title="成绩分析", page_icon="📈", layout="wide")
st.title("📈 成绩分析")

classes = get_all_classes()
if not classes:
    st.warning("请先在「学生管理」页创建班级和学生")
    st.stop()

selected_class = st.selectbox(
    "选择班级",
    classes,
    format_func=lambda c: f"{c['grade']} {c['name']}"
)
class_id = selected_class["id"]
exams = get_exams_by_class(class_id)

if not exams:
    st.info("该班级暂无考试记录，请先在「成绩录入」页录入成绩")
    st.stop()

tab1, tab2, tab3 = st.tabs(["🏆 排名 & 前五", "📊 班级趋势", "👤 学生个人趋势"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — 排名 & 前五
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    selected_exam = st.selectbox(
        "选择考试",
        exams,
        format_func=lambda e: f"{e['title']} ({e['exam_date']})"
    )
    exam_id = selected_exam["id"]
    scores = get_scores_for_exam(exam_id)

    if not scores:
        st.info("该次考试暂未录入成绩")
    else:
        df = pd.DataFrame(scores)

        # ── 前五名展示 ────────────────────────────────────────────────────────
        st.subheader("🏆 本次前五名")
        top5 = [s for s in scores if s["rank"] <= 5]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

        if top5:
            cols = st.columns(min(len(top5), 5))
            for i, (col, s) in enumerate(zip(cols, top5)):
                medal = medals[s["rank"] - 1] if s["rank"] <= 3 else f"No.{s['rank']}"
                col.markdown(f"""
                <div style="background:linear-gradient(135deg,#fff9e6,#fff3cd);
                            border:2px solid #f6c90e;border-radius:12px;
                            padding:1rem;text-align:center;">
                    <div style="font-size:2rem">{medal}</div>
                    <div style="font-weight:700;font-size:1.1rem">{s['name']}</div>
                    <div style="color:#666;font-size:0.85rem;margin-top:0.3rem">
                        总分 <strong style="color:#e67e22;font-size:1.2rem">{int(s['total'])}</strong>
                    </div>
                    <div style="color:#888;font-size:0.8rem">
                        语{int(s['chinese'])} 数{int(s['math'])} 英{int(s['english'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # ── 完整排名表 ────────────────────────────────────────────────────────
        col_table, col_chart = st.columns([1, 1])

        with col_table:
            st.subheader("📋 完整排名")
            display_df = df[["rank", "name", "chinese", "math", "english", "total"]].copy()
            display_df.columns = ["名次", "姓名", "语文", "数学", "英语", "总分"]
            display_df["总分"] = display_df["总分"].astype(int)
            for col in ["语文", "数学", "英语","总分"]:
                display_df[col] = display_df[col].round(1)

            def highlight_top(row):
                if row["名次"] == 1:
                    return ["background-color:#fff3cd"] * len(row)
                elif row["名次"] <= 3:
                    return ["background-color:#f8f9fa"] * len(row)
                return [""] * len(row)

            st.dataframe(
                display_df.style.apply(highlight_top, axis=1),
                use_container_width=True,
                hide_index=True
            )

            # 导出
            buf = BytesIO()
            display_df.to_excel(buf, index=False)
            st.download_button(
                "⬇️ 导出排名 Excel",
                buf.getvalue(),
                f"{selected_exam['title']}_排名.xlsx"
            )

        with col_chart:
            st.subheader("📊 各科平均分")
            avg_chinese = df["chinese"].mean()
            avg_math = df["math"].mean()
            avg_english = df["english"].mean()

            fig = go.Figure(go.Bar(
                x=["语文", "数学", "英语"],
                y=[round(avg_chinese, 1), round(avg_math, 1), round(avg_english, 1)],
                marker_color=["#667eea", "#f5576c", "#43e97b"],
                text=[round(avg_chinese, 1), round(avg_math, 1), round(avg_english, 1)],
                textposition="outside"
            ))
            fig.update_layout(
                height=300,
                margin=dict(t=20, b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis_range=[0, 150]
            )
            st.plotly_chart(fig, use_container_width=True)

            # 分数段分布
            st.subheader("📊 总分分布")
            bins = [0, 150, 180, 210, 240, 270, 300]
            labels = ["<150", "150-180", "180-210", "210-240", "240-270", "270-300"]
            df["分段"] = pd.cut(df["total"], bins=bins, labels=labels, right=True)
            dist = df["分段"].value_counts().sort_index()
            fig2 = px.bar(x=dist.index.astype(str), y=dist.values,
                          labels={"x": "总分段", "y": "人数"},
                          color_discrete_sequence=["#764ba2"])
            fig2.update_layout(height=250, margin=dict(t=10, b=10),
                               plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — 班级趋势
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    history = get_class_history(class_id)
    if len(history) < 2:
        st.info("至少需要 2 次考试记录才能显示趋势图")
    else:
        df_hist = pd.DataFrame(history)

        st.subheader("📈 班级各科均分趋势")
        fig = go.Figure()
        colors = {"avg_chinese": "#667eea", "avg_math": "#f5576c", "avg_english": "#43e97b"}
        names = {"avg_chinese": "语文", "avg_math": "数学", "avg_english": "英语"}
        for col, color in colors.items():
            fig.add_trace(go.Scatter(
                x=df_hist["title"],
                y=df_hist[col].round(1),
                name=names[col],
                line=dict(color=color, width=2.5),
                mode="lines+markers+text",
                text=df_hist[col].round(1),
                textposition="top center"
            ))
        fig.update_layout(
            height=380,
            margin=dict(t=20, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📈 班级总分均分趋势")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=df_hist["title"],
            y=df_hist["avg_total"].round(1),
            name="总分均分",
            line=dict(color="#764ba2", width=3),
            mode="lines+markers+text",
            text=df_hist["avg_total"].round(1),
            textposition="top center",
            fill="tozeroy",
            fillcolor="rgba(118,75,162,0.1)"
        ))
        fig2.add_trace(go.Scatter(
            x=df_hist["title"],
            y=df_hist["max_total"],
            name="最高分",
            line=dict(color="#f6c90e", dash="dash"),
            mode="lines+markers"
        ))
        fig2.add_trace(go.Scatter(
            x=df_hist["title"],
            y=df_hist["min_total"],
            name="最低分",
            line=dict(color="#ccc", dash="dot"),
            mode="lines+markers"
        ))
        fig2.update_layout(
            height=350,
            margin=dict(t=20, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig2, use_container_width=True)

        # 进步/退步分析
        st.subheader("📊 本班各科数据汇总")
        summary = df_hist[["title", "avg_chinese", "avg_math", "avg_english", "avg_total", "max_total", "min_total"]].copy()
        summary.columns = ["考试名称", "语文均分", "数学均分", "英语均分", "总分均分", "最高分", "最低分"]
        for col in summary.columns[1:]:
            summary[col] = summary[col].round(1)
        st.dataframe(summary, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — 学生个人趋势
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    students = get_students_by_class(class_id)
    if not students:
        st.info("暂无学生数据")
    else:
        selected_student = st.selectbox(
            "选择学生",
            students,
            format_func=lambda s: s["name"]
        )
        history = get_student_history(selected_student["id"])

        if len(history) < 1:
            st.info("该学生暂无成绩记录")
        else:
            df_s = pd.DataFrame(history)

            col1, col2, col3 = st.columns(3)
            col1.metric("最新排名", f"第 {df_s.iloc[-1]['rank']} 名")
            col2.metric("最新总分", int(df_s.iloc[-1]["total"]))
            if len(df_s) >= 2:
                delta = int(df_s.iloc[-1]["total"]) - int(df_s.iloc[-2]["total"])
                col3.metric("与上次对比", f"{'+' if delta >= 0 else ''}{delta} 分")
            else:
                col3.metric("参测次数", len(df_s))

            # 个人趋势图
            fig = go.Figure()
            for subj, color in [("chinese", "#667eea"), ("math", "#f5576c"), ("english", "#43e97b")]:
                name_map = {"chinese": "语文", "math": "数学", "english": "英语"}
                fig.add_trace(go.Scatter(
                    x=df_s["title"],
                    y=df_s[subj],
                    name=name_map[subj],
                    line=dict(color=color, width=2),
                    mode="lines+markers"
                ))
            fig.add_trace(go.Scatter(
                x=df_s["title"],
                y=df_s["total"],
                name="总分",
                line=dict(color="#764ba2", width=3, dash="dash"),
                mode="lines+markers+text",
                text=df_s["total"].astype(int),
                textposition="top center",
                yaxis="y2"
            ))
            fig.update_layout(
                height=380,
                margin=dict(t=20, b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                yaxis=dict(title="单科成绩"),
                yaxis2=dict(title="总分", overlaying="y", side="right")
            )
            st.plotly_chart(fig, use_container_width=True)

            # 名次变化
            if len(df_s) >= 2:
                st.subheader("📊 名次变化趋势")
                fig_rank = go.Figure(go.Scatter(
                    x=df_s["title"],
                    y=df_s["rank"],
                    mode="lines+markers+text",
                    text=df_s["rank"].apply(lambda r: f"第{r}名"),
                    textposition="top center",
                    line=dict(color="#f6c90e", width=2.5),
                    marker=dict(size=8)
                ))
                fig_rank.update_yaxes(autorange="reversed", title="名次")
                fig_rank.update_layout(
                    height=250,
                    margin=dict(t=20, b=10),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_rank, use_container_width=True)

            st.dataframe(
                df_s[["title", "exam_date", "chinese", "math", "english", "total", "rank"]].rename(
                    columns={"title": "考试", "exam_date": "日期",
                             "chinese": "语文", "math": "数学",
                             "english": "英语", "total": "总分", "rank": "名次"}
                ),
                use_container_width=True,
                hide_index=True
            )
