import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO
from database import (
    get_all_classes, get_students_by_class,
    add_exam, get_exams_by_class, delete_exam,
    upsert_score, bulk_upsert_scores, get_scores_for_exam,
    has_science
)

st.set_page_config(page_title="成绩录入", page_icon="📝", layout="wide")
st.title("📝 成绩录入")

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
grade = selected_class["grade"]
students = get_students_by_class(class_id)
show_science = has_science(grade)

if not students:
    st.warning("该班级暂无学生，请先在「学生管理」页添加学生")
    st.stop()

tab1, tab2, tab3 = st.tabs(["➕ 新建考试 + 录入成绩", "📥 Excel 批量导入", "📋 历史考试管理"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — 手动录入
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.subheader("📅 考试信息")
        exam_title = st.text_input("考试名称", placeholder="例如：第5次周测")
        exam_date = st.date_input("考试日期", value=date.today())
        default_subjects = ["语文", "数学", "英语", "科学"] if show_science else ["语文", "数学"]
        subjects = st.multiselect(
            "考试科目",
            ["语文", "数学", "英语", "科学", "道德与法治"],
            default=default_subjects
        )

    with col_r:
        st.subheader(f"✏️ 录入成绩（共 {len(students)} 名学生）")
        if not exam_title.strip():
            st.info("请先填写考试名称")
        elif not subjects:
            st.info("请先选择考试科目")
        else:
            score_data = {}
            with st.form("score_form"):
                header_cols = st.columns([2] + [1] * len(subjects))
                header_cols[0].markdown("**学生姓名**")
                for i, sub in enumerate(subjects):
                    header_cols[i + 1].markdown(f"**{sub}**")
                for s in students:
                    row_cols = st.columns([2] + [1] * len(subjects))
                    row_cols[0].text(s["name"])
                    subject_scores = {}
                    for i, sub in enumerate(subjects):
                        val = row_cols[i + 1].number_input(
                            label=f"{s['name']}_{sub}",
                            min_value=0.0, max_value=150.0, value=0.0, step=0.5,
                            label_visibility="collapsed",
                            key=f"score_{s['id']}_{sub}"
                        )
                        subject_scores[sub] = val
                    score_data[s["id"]] = subject_scores
                submitted = st.form_submit_button("💾 保存本次周测成绩", use_container_width=True)

            if submitted:
                exam_id = add_exam(exam_title.strip(), str(exam_date), class_id)
                for student_id, sub_scores in score_data.items():
                    chinese = sub_scores.get("语文", 0)
                    math    = sub_scores.get("数学", 0)
                    english = sub_scores.get("英语", 0)
                    science = sub_scores.get("科学", 0)
                    upsert_score(exam_id, student_id, chinese, math, english, science)
                st.success(f"✅ 已保存「{exam_title}」成绩，共 {len(students)} 名学生")
                st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Excel 批量导入
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📥 Excel 批量导入成绩")
    col_info, col_upload = st.columns([1, 1])

    with col_info:
        if show_science:
            st.markdown("**模板格式（含科学）：**")
            st.markdown("""
            | 姓名 | 语文 | 数学 | 英语 | 科学 |
            |------|------|------|------|------|
            | 张三 | 92 | 88 | 95 | 90 |
            """)
            template_df = pd.DataFrame({
                "姓名": [s["name"] for s in students],
                "语文": [0] * len(students),
                "数学": [0] * len(students),
                "英语": [0] * len(students),
                "科学": [0] * len(students),
            })
        else:
            st.markdown("**模板格式：**")
            st.markdown("""
            | 姓名 | 语文 | 数学 |
            |------|------|------|
            | 张三 | 92 | 88 |
            """)
            template_df = pd.DataFrame({
                "姓名": [s["name"] for s in students],
                "语文": [0] * len(students),
                "数学": [0] * len(students),
            })
        buf = BytesIO()
        template_df.to_excel(buf, index=False)
        st.download_button(
            "⬇️ 下载本班成绩录入模板",
            buf.getvalue(),
            f"{selected_class['grade']}{selected_class['name']}_成绩模板.xlsx",
            use_container_width=True
        )

    with col_upload:
        ex_title2 = st.text_input("考试名称", placeholder="例如：第6次周测", key="ex_title2")
        ex_date2  = st.date_input("考试日期", value=date.today(), key="ex_date2")
        uploaded  = st.file_uploader("上传成绩 Excel", type=["xlsx", "xls"])

        if uploaded and ex_title2.strip():
            try:
                df = pd.read_excel(uploaded)
                if "姓名" not in df.columns:
                    st.error("Excel 中必须包含「姓名」列")
                else:
                    df = df.dropna(subset=["姓名"])
                    df["姓名"] = df["姓名"].astype(str).str.strip()
                    df = df[~df["姓名"].str.lower().isin(["", "nan", "none", "null", "nat"])]

                    st.dataframe(df, use_container_width=True)
                    name_to_id = {s["name"]: s["id"] for s in students}
                    matched   = df[df["姓名"].isin(name_to_id)]
                    unmatched = df[~df["姓名"].isin(name_to_id)]

                    if len(unmatched):
                        unmatched_names = [str(n) for n in unmatched["姓名"].tolist()
                                           if pd.notna(n) and str(n).lower() not in ["nan","none","null","","nat"]]
                        if unmatched_names:
                            st.warning(f"⚠️ 以下学生未找到匹配：{', '.join(unmatched_names)}")

                    st.info(f"匹配到 {len(matched)} 名学生")

                    if st.button("✅ 确认导入成绩", use_container_width=True):
                        exam_id = add_exam(ex_title2.strip(), str(ex_date2), class_id)
                        rows = []
                        for _, row in matched.iterrows():
                            sid     = name_to_id[row["姓名"]]
                            chinese = 0.0 if pd.isna(row.get("语文")) else float(row.get("语文", 0))
                            math    = 0.0 if pd.isna(row.get("数学")) else float(row.get("数学", 0))
                            english = 0.0 if pd.isna(row.get("英语")) else float(row.get("英语", 0))
                            science = 0.0 if pd.isna(row.get("科学")) else float(row.get("科学", 0)) if show_science else 0.0
                            rows.append((sid, chinese, math, english, science))
                        bulk_upsert_scores(exam_id, rows)
                        st.success(f"✅ 成功导入 {len(rows)} 名学生成绩")
                        st.balloons()
            except Exception as e:
                import traceback
                st.error(f"解析失败：{e}")
                st.code(traceback.format_exc())

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — 历史考试管理
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📋 历史考试记录")
    exams = get_exams_by_class(class_id)
    if not exams:
        st.info("该班级暂无考试记录")
    else:
        for exam in exams:
            scores = get_scores_for_exam(exam["id"])
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            c1.markdown(f"**{exam['title']}**")
            c2.text(exam["exam_date"])
            c3.text(f"{len(scores)} 人")
            if c4.button("🗑️", key=f"del_exam_{exam['id']}", help="删除此次考试"):
                delete_exam(exam["id"])
                st.rerun()
