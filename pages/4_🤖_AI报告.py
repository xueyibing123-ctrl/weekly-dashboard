import streamlit as st
import pandas as pd
import httpx
from datetime import datetime
from io import BytesIO
from database import (
    get_all_classes, get_exams_by_class, get_scores_for_exam,
    get_top_students, get_class_history, has_science
)

st.set_page_config(page_title="AI报告", page_icon="🤖", layout="wide")
st.title("🤖 AI 成绩分析报告")
st.caption("一键生成班级成绩简报，可直接复制发群或打印存档")

classes = get_all_classes()
if not classes:
    st.warning("请先在「学生管理」页创建班级和学生")
    st.stop()

selected_class = st.selectbox(
    "选择班级", classes,
    format_func=lambda c: f"{c['grade']} {c['name']}"
)
class_id = selected_class["id"]
grade = selected_class["grade"]
show_science = has_science(grade)

exams = get_exams_by_class(class_id)
if not exams:
    st.info("该班级暂无考试记录")
    st.stop()

selected_exam = st.selectbox(
    "选择考试", exams,
    format_func=lambda e: f"{e['title']} ({e['exam_date']})"
)
exam_id = selected_exam["id"]
scores  = get_scores_for_exam(exam_id)

if not scores:
    st.info("该次考试暂未录入成绩")
    st.stop()

tab1, tab2 = st.tabs(["🤖 AI 智能简报", "📄 奖励名单"])

# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_settings, col_result = st.columns([1, 2])

    with col_settings:
        st.subheader("⚙️ 报告设置")
        report_style      = st.radio("报告风格", ["简洁版（发家长群）", "详细版（存档/汇报）"], index=0)
        include_trend     = st.checkbox("包含历史趋势分析", value=True)
        include_suggestions = st.checkbox("包含教学建议", value=True)
        generate_btn      = st.button("🚀 生成分析报告", use_container_width=True, type="primary")

    with col_result:
        st.subheader("📋 分析报告")

        if generate_btn:
            df = pd.DataFrame(scores)
            history = get_class_history(class_id)
            top5    = [s for s in scores if s["rank"] <= 5]

            avg_total   = df["total"].mean()
            avg_chinese = df["chinese"].mean()
            avg_math    = df["math"].mean()
            avg_english = df["english"].mean()
            avg_science = df["science"].mean() if show_science else 0
            max_score   = df["total"].max()
            min_score   = df["total"].min()
            class_size  = len(df)

            # 趋势对比
            trend_text = ""
            if include_trend and len(history) >= 2:
                prev  = history[-2]
                curr  = history[-1]
                delta_total   = curr["avg_total"]   - prev["avg_total"]
                delta_chinese = curr["avg_chinese"] - prev["avg_chinese"]
                delta_math    = curr["avg_math"]    - prev["avg_math"]
                delta_english = curr["avg_english"] - prev["avg_english"]

                def arrow(v):
                    return f"↑{abs(v):.1f}分" if v > 0 else (f"↓{abs(v):.1f}分" if v < 0 else "持平")

                trend_text = (f"总分均分：{prev['avg_total']:.1f} → {curr['avg_total']:.1f}，{arrow(delta_total)}；"
                              f"语文{arrow(delta_chinese)}，数学{arrow(delta_math)}，英语{arrow(delta_english)}")
                if show_science:
                    delta_science = curr.get("avg_science", 0) - prev.get("avg_science", 0)
                    trend_text += f"，科学{arrow(delta_science)}"

            # 教学建议
            suggestions = []
            if include_suggestions:
                subjects = {"语文": avg_chinese, "数学": avg_math, "英语": avg_english}
                if show_science:
                    subjects["科学"] = avg_science
                weakest  = min(subjects, key=subjects.get)
                strongest = max(subjects, key=subjects.get)
                suggestions.append(f"· 本次 **{weakest}** 为相对薄弱科目（均分 {subjects[weakest]:.1f}），建议加强专项练习")
                suggestions.append(f"· **{strongest}** 表现突出（均分 {subjects[strongest]:.1f}），可作为优势继续保持")
                if max_score - min_score > 80:
                    suggestions.append("· 班级分数跨度较大，建议关注中下层学生的巩固训练")
                if avg_total < (240 if show_science else 180):
                    suggestions.append("· 整体均分偏低，建议排查共性知识盲点，加强课堂反馈")
                elif avg_total > (320 if show_science else 240):
                    suggestions.append("· 整体表现良好，可适当提升题目难度，挑战优秀学生上限")

            top5_names = "、".join([s["name"] for s in top5])
            science_line = f"  科学均分：{avg_science:.1f}" if show_science else ""

            prompt = f"""
你是一位专业的小学教育数据分析师，请根据以下周测数据生成一份{'简洁的家长群通知（150字以内）' if '简洁' in report_style else '详细的成绩分析报告（300字左右）'}。

班级：{selected_class['grade']}{selected_class['name']}
考试：{selected_exam['title']}（{selected_exam['exam_date']}）
参测人数：{class_size}人
总分均分：{avg_total:.1f}  最高分：{int(max_score)}  最低分：{int(min_score)}
语文均分：{avg_chinese:.1f}  数学均分：{avg_math:.1f}  英语均分：{avg_english:.1f}{science_line}
前五名：{top5_names}
{('历史趋势：' + trend_text) if trend_text else '（本次为首次考试）'}

要求：语气正面鼓励，客观呈现数据，给出1-2条实用建议，不要使用 markdown 标题格式，直接输出文字。
"""

            api_key = st.secrets.get("DASHSCOPE_API_KEY", "")

            if api_key:
                with st.spinner("AI 正在分析数据，请稍候..."):
                    try:
                        with httpx.Client(timeout=60) as client:
                            resp = client.post(
                                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                json={
                                    "model": "qwen-plus",
                                    "temperature": 0.3,
                                    "messages": [
                                        {"role": "system", "content": "你是一位专业的小学教育数据分析师，擅长用简洁友好的语言解读成绩数据。"},
                                        {"role": "user", "content": prompt}
                                    ],
                                }
                            )
                        resp.raise_for_status()
                        ai_report = resp.json()["choices"][0]["message"]["content"]
                        st.success("✅ AI 报告生成成功")
                        st.markdown("---")
                        st.markdown(ai_report)
                        st.download_button("⬇️ 导出报告文本", ai_report.encode("utf-8"),
                                           f"{selected_exam['title']}_AI分析报告.txt", use_container_width=True)
                    except Exception as e:
                        st.error(f"AI 调用失败：{e}，已切换为模板报告")
                        api_key = ""

            if not api_key:
                report_lines = [
                    f"📊 **{selected_class['grade']}{selected_class['name']} · {selected_exam['title']} 成绩报告**",
                    f"📅 考试日期：{selected_exam['exam_date']}　　参测学生：{class_size} 人",
                    "",
                    "**【成绩概览】**",
                    f"- 总分均分：**{avg_total:.1f}**　最高分：{int(max_score)}　最低分：{int(min_score)}",
                    f"- 语文均分：{avg_chinese:.1f}　数学均分：{avg_math:.1f}　英语均分：{avg_english:.1f}" +
                    (f"　科学均分：{avg_science:.1f}" if show_science else ""),
                ]
                if trend_text:
                    report_lines += ["", "**【与上次对比】**", trend_text]
                report_lines += ["", "**【本次前五名】**", f"🏆 {top5_names}", "恭喜以上同学本次取得优异成绩！"]
                if suggestions:
                    report_lines += ["", "**【教学建议】**"] + suggestions
                report_lines += ["", f"_报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}_"]

                full_report = "\n".join(report_lines)
                st.markdown(full_report)
                st.download_button("⬇️ 导出报告文本", full_report.encode("utf-8"),
                                   f"{selected_exam['title']}_成绩报告.txt", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🏆 前五名表彰名单")
    top_n       = st.slider("显示前几名", 3, 10, 5)
    award_title = st.text_input("奖项名称", value="学习之星")
    school_name = st.text_input("学校名称", value="XX小学")
    top_students = [s for s in scores if s["rank"] <= top_n]

    if top_students:
        st.markdown(f"""
        <div style="border:2px solid #f6c90e;border-radius:12px;padding:2rem;
                    background:linear-gradient(135deg,#fff9e6,#fff3cd);">
            <div style="text-align:center;margin-bottom:1.5rem">
                <div style="font-size:1.8rem;font-weight:700;color:#1a1a2e">{school_name}</div>
                <div style="font-size:1.3rem;color:#666;margin-top:0.3rem">
                    {selected_class['grade']}{selected_class['name']} · {selected_exam['title']} · {award_title}名单
                </div>
                <div style="color:#999;font-size:0.9rem">{selected_exam['exam_date']}</div>
            </div>
        """, unsafe_allow_html=True)

        medals = ["🥇", "🥈", "🥉"]
        for s in top_students:
            medal = medals[s["rank"] - 1] if s["rank"] <= 3 else "⭐"
            st.markdown(f"""
            <div style="display:flex;align-items:center;padding:0.7rem 1rem;
                        background:white;border-radius:8px;margin-bottom:0.5rem;
                        box-shadow:0 1px 3px rgba(0,0,0,0.1)">
                <span style="font-size:1.5rem;margin-right:1rem">{medal}</span>
                <span style="font-size:1.1rem;font-weight:600;flex:1">第 {s['rank']} 名　{s['name']}</span>
                <span style="color:#666">总分 <strong style="color:#e67e22">{int(s['total'])}</strong> 分</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        award_data = []
        for s in top_students:
            row = {"名次": s["rank"], "姓名": s["name"], "总分": int(s["total"]),
                   "语文": int(s["chinese"]), "数学": int(s["math"]), "英语": int(s["english"]), "奖项": award_title}
            if show_science:
                row["科学"] = int(s["science"])
            award_data.append(row)

        award_df = pd.DataFrame(award_data)
        buf = BytesIO()
        award_df.to_excel(buf, index=False)
        st.download_button("⬇️ 导出表彰名单 Excel", buf.getvalue(),
                           f"{selected_exam['title']}_{award_title}名单.xlsx", use_container_width=True)
    else:
        st.info("暂无成绩数据")
