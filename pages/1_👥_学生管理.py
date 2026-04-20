import streamlit as st
import pandas as pd
from database import (
    get_all_classes, add_class, delete_class,
    get_students_by_class, add_student, delete_student, bulk_add_students
)
from io import BytesIO

st.set_page_config(page_title="学生管理", page_icon="👥", layout="wide")
st.title("👥 学生管理")

tab1, tab2 = st.tabs(["🏫 班级管理", "📋 学生名单"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — 班级管理
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("➕ 添加班级")
        with st.form("add_class_form", clear_on_submit=True):
            grade = st.selectbox("年级", ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级"])
            class_name = st.text_input("班级名称", placeholder="例如：1班、2班")
            submitted = st.form_submit_button("添加班级", use_container_width=True)
            if submitted:
                if class_name.strip():
                    add_class(class_name.strip(), grade)
                    st.success(f"✅ 已添加 {grade} {class_name}")
                    st.rerun()
                else:
                    st.warning("请输入班级名称")

    with col_right:
        st.subheader("📋 现有班级")
        classes = get_all_classes()
        if not classes:
            st.info("暂无班级，请先添加")
        else:
            for cls in classes:
                students = get_students_by_class(cls["id"])
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{cls['grade']} {cls['name']}**　{len(students)} 名学生")
                if c3.button("🗑️ 删除", key=f"del_cls_{cls['id']}",
                             help="删除班级及其所有学生数据"):
                    delete_class(cls["id"])
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — 学生名单
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    classes = get_all_classes()
    if not classes:
        st.warning("请先在「班级管理」页创建班级")
        st.stop()

    selected_class = st.selectbox(
        "选择班级",
        classes,
        format_func=lambda c: f"{c['grade']} {c['name']}"
    )
    class_id = selected_class["id"]

    col_a, col_b = st.columns([1, 2])

    # ── 单个添加 ─────────────────────────────────────────────────────────────
    with col_a:
        st.subheader("➕ 添加学生")
        with st.form("add_student_form", clear_on_submit=True):
            s_name = st.text_input("姓名", placeholder="学生姓名")
            s_no = st.text_input("学号（可选）", placeholder="例如：001")
            sub = st.form_submit_button("添加", use_container_width=True)
            if sub:
                if s_name.strip():
                    add_student(s_name.strip(), class_id, s_no.strip())
                    st.success(f"✅ 已添加 {s_name}")
                    st.rerun()
                else:
                    st.warning("请输入学生姓名")

        # ── Excel 批量导入 ────────────────────────────────────────────────────
        st.subheader("📥 Excel 批量导入")
        st.markdown("""
        **模板格式：**
        | 姓名 | 学号 |
        |------|------|
        | 张三 | 001 |
        """)

        # 下载模板
        template_df = pd.DataFrame({"姓名": ["张三", "李四"], "学号": ["001", "002"]})
        buf = BytesIO()
        template_df.to_excel(buf, index=False)
        st.download_button(
            "⬇️ 下载导入模板",
            buf.getvalue(),
            "学生名单模板.xlsx",
            use_container_width=True
        )

        uploaded = st.file_uploader("上传学生名单 Excel", type=["xlsx", "xls"])
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
                if "姓名" not in df.columns:
                    st.error("Excel 中必须包含「姓名」列")
                else:
                    df["学号"] = df.get("学号", "").fillna("").apply(lambda x: str(int(float(x))) if str(x).replace('.','').isdigit() else str(x))
                    preview = df[["姓名", "学号"]].head(5)
                    st.dataframe(preview, use_container_width=True)
                    st.caption(f"共 {len(df)} 名学生")
                    if st.button("✅ 确认导入", use_container_width=True):
                        pairs = list(zip(df["姓名"].astype(str), df["学号"].astype(str)))
                        bulk_add_students(class_id, pairs)
                        st.success(f"✅ 成功导入 {len(pairs)} 名学生")
                        st.rerun()
            except Exception as e:
                st.error(f"解析失败：{e}")

    # ── 学生列表 ─────────────────────────────────────────────────────────────
    with col_b:
        st.subheader(f"📋 {selected_class['grade']} {selected_class['name']} 学生名单")
        students = get_students_by_class(class_id)
        if not students:
            st.info("暂无学生，请先添加或导入")
        else:
            # 导出名单
            export_df = pd.DataFrame(students)[["student_no", "name"]]
            export_df.columns = ["学号", "姓名"]
            buf2 = BytesIO()
            export_df.to_excel(buf2, index=False)
            st.download_button(
                "⬇️ 导出名单 Excel",
                buf2.getvalue(),
                f"{selected_class['grade']}{selected_class['name']}名单.xlsx",
                use_container_width=False
            )

            for s in students:
                c1, c2, c3 = st.columns([2, 3, 1])
                c1.text(s["student_no"] or "--")
                c2.text(s["name"])
                if c3.button("删除", key=f"del_s_{s['id']}"):
                    delete_student(s["id"])
                    st.rerun()
