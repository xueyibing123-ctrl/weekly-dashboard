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
        report_style      = st.radio("报告风格", ["简洁版（发家长群）", "详细版（教学分析）"], index=0)
        include_trend     = st.checkbox("包含历史趋势分析", value=True)
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
                def arrow(v):
                    return f"↑{abs(v):.1f}分" if v > 0 else (f"↓{abs(v):.1f}分" if v < 0 else "持平")
                trend_text = (
                    f"总分均分：{prev['avg_total']:.1f} → {curr['avg_total']:.1f}，{arrow(curr['avg_total']-prev['avg_total'])}；"
                    f"语文{arrow(curr['avg_chinese']-prev['avg_chinese'])}，"
                    f"数学{arrow(curr['avg_math']-prev['avg_math'])}，"
                    f"英语{arrow(curr['avg_english']-prev['avg_english'])}"
                )
                if show_science:
                    delta_sci = (curr.get("avg_science") or 0) - (prev.get("avg_science") or 0)
                    trend_text += f"，科学{arrow(delta_sci)}"

            top5_names  = "、".join([s["name"] for s in top5])
            science_line = f"\n科学均分：{avg_science:.1f}" if show_science else ""

            # ── Prompt 根据风格区分 ──────────────────────────────────────────
            if "简洁" in report_style:
                style_instruction = """请生成一份简洁的家长群通知（150字以内）。
要求：语气温暖亲切，重点报告均分和前五名，给出1条家庭配合建议，直接输出文字，不用标题格式。"""
            else:
                style_instruction = """请生成一份详细的教学分析报告（500字左右），依次包含以下四个部分：

1.【成绩概览】客观呈现各科均分、最高分、最低分、参测人数等核心数据，概括整体表现水平。

2.【学情诊断】深入分析各科强弱对比，指出薄弱科目及可能原因；关注分数跨度大小，分析是否存在两极分化；结合历史趋势判断班级整体走势。

3.【教学建议】针对薄弱科目给出3条具体可操作的教学调整建议，包括：课堂节奏调整、练习题型设计、分层教学策略、课后辅导重点等，建议要落地可执行。

4.【下次周测备考重点】基于本次数据，明确提出下次周测前需要重点强化的知识点方向和教学准备事项。

语气专业客观，面向教师，直接输出文字，不要使用markdown标题符号（#、**等）。"""

            prompt = f"""你是一位有丰富经验的小学教学研究专家。

班级：{selected_class['grade']}{selected_class['name']}
考试：{selected_exam['title']}（{selected_exam['exam_date']}）
参测人数：{class_size}人
总分均分：{avg_total:.1f}  最高分：{int(max_score)}  最低分：{int(min_score)}
语文均分：{avg_chinese:.1f}  数学均分：{avg_math:.1f}  英语均分：{avg_english:.1f}{science_line}
前五名：{top5_names}
{('历史趋势：' + trend_text) if trend_text else '（本次为首次考试，暂无历史对比数据）'}

{style_instruction}"""

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
                                    "temperature": 0.4,
                                    "messages": [
                                        {"role": "system", "content": "你是一位有丰富经验的小学教学研究专家，擅长用专业、清晰的语言解读成绩数据并给出教学指导建议。"},
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
                if "简洁" in report_style:
                    report_lines = [
                        f"📊 **{selected_class['grade']}{selected_class['name']} · {selected_exam['title']}**",
                        f"📅 {selected_exam['exam_date']}　参测：{class_size} 人",
                        "",
                        f"总分均分 **{avg_total:.1f}**，最高 {int(max_score)}，最低 {int(min_score)}",
                        f"语文 {avg_chinese:.1f}　数学 {avg_math:.1f}　英语 {avg_english:.1f}" +
                        (f"　科学 {avg_science:.1f}" if show_science else ""),
                        "",
                        f"🏆 本次前五名：{top5_names}，恭喜！",
                        "",
                        "建议家长每天陪孩子复习薄弱科目，保持良好学习节奏。",
                    ]
                else:
                    subjects = {"语文": avg_chinese, "数学": avg_math, "英语": avg_english}
                    if show_science: subjects["科学"] = avg_science
                    weakest  = min(subjects, key=subjects.get)
                    strongest = max(subjects, key=subjects.get)
                    report_lines = [
                        f"📊 **{selected_class['grade']}{selected_class['name']} · {selected_exam['title']} 教学分析报告**",
                        f"📅 考试日期：{selected_exam['exam_date']}　参测学生：{class_size} 人",
                        "",
                        "**【成绩概览】**",
                        f"总分均分 {avg_total:.1f}，最高分 {int(max_score)}，最低分 {int(min_score)}，分差 {int(max_score-min_score)}。",
                        f"各科均分：语文 {avg_chinese:.1f}，数学 {avg_math:.1f}，英语 {avg_english:.1f}" +
                        (f"，科学 {avg_science:.1f}" if show_science else "") + "。",
                        "",
                        "**【学情诊断】**",
                        f"{strongest} 为本次最强科目（均分 {subjects[strongest]:.1f}），{weakest} 为相对薄弱科目（均分 {subjects[weakest]:.1f}）。" +
                        (f"班级分数跨度达 {int(max_score-min_score)} 分，需关注两极分化。" if max_score-min_score > 80 else "班级整体分布较均衡。"),
                    ]
                    if trend_text:
                        report_lines += ["", "**【历史趋势】**", trend_text]
                    report_lines += [
                        "",
                        "**【教学建议】**",
                        f"① 针对{weakest}薄弱问题，建议增加专项练习，课堂留出5-10分钟查漏补缺。",
                        "② 对中下层学生实施分层辅导，课后重点跟进，避免差距进一步扩大。",
                        "③ 总结本次共性错误，下节课集中讲评，强化易错知识点。",
                        "",
                        "**【下次周测备考重点】**",
                        f"重点强化{weakest}基础知识，关注中下层学生进步情况，确保下次均分有所提升。",
                        "",
                        f"_报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}_"
                    ]

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
                   "语文": int(s["chinese"]), "数学": int(s["math"]),
                   "英语": int(s["english"]), "奖项": award_title}
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
