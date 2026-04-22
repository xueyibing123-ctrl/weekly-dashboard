import streamlit as st
    from database import init_db, get_all_classes, get_latest_exam_per_class, get_top_students, get_all_exams
    import pandas as pd
    
    st.set_page_config(
        page_title="校园周测数据看板",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_db()
    
    ICONS = {
        'building': '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18"/><path d="M5 21V7l8-4 8 4v14"/><path d="M17 21v-8.5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0-.5.5V21"/><path d="M9 11V7"/><path d="M15 11V7"/><path d="M9 17v-4"/><path d="M15 17v-4"/></svg>',
        'document': '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>',
        'users': '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
        'calendar': '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/><path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/></svg>',
        'trophy': '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17"/><path d="M14 14.66V17"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/><path d="M8.5 22l1.078-3.5a2 2 0 0 1 3.844 0L14.5 22"/></svg>',
    }
    
    COLORS = {
        'primary': '#2E86AB',
        'secondary': '#56A3A6',
        'accent': '#F6C90E',
        'bg': '#F8F9FA',
    }
    
    st.markdown("""
    <style>
        .main-title { font-size: 2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.3rem; }
        .sub-title { font-size: 1rem; color: #6b7280; margin-bottom: 2rem; }
        .metric-card { background: linear-gradient(135deg, #2E86AB 0%, #56A3A6 100%); border-radius: 16px; padding: 1.5rem 1.8rem; color: white; text-align: center; box-shadow: 0 4px 6px rgba(46, 134, 171, 0.15); }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 12px rgba(46, 134, 171, 0.25); }
        .metric-card .icon { margin-bottom: 0.5rem; display: flex; justify-content: center; }
        .metric-card .icon svg { width: 36px; height: 36px; opacity: 0.95; }
        .metric-card .value { font-size: 2.5rem; font-weight: 700; margin: 0.3rem 0; line-height: 1.2; }
        .metric-card .label { opacity: 0.9; font-size: 0.95rem; font-weight: 500; }
        .metric-card.primary { background: linear-gradient(135deg, #2E86AB 0%, #56A3A6 100%); }
        .metric-card.secondary { background: linear-gradient(135deg, #4A7C59 0%, #7FB069 100%); }
        .metric-card.accent { background: linear-gradient(135deg, #F6C90E 0%, #F9A826 100%); }
        .metric-card.info { background: linear-gradient(135deg, #5B7C99 0%, #7B9BB5 100%); }
        .main { background: #F8F9FA; }
        .stApp { background: #F8F9FA; }
        .rank-card { background:#fffbeb; border-left:4px solid #F6C90E; border-radius:8px; padding:0.7rem 0.8rem; text-align:center; }
        .rank-label { font-size:1rem; font-weight:600; color:#2E86AB; }
        .rank-name { font-weight:600; font-size:1.1rem; margin:0.3rem 0; }
        .rank-score { color:#666; font-size:0.85rem; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-title">校园周测数据看板</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">统一管理周测成绩 · 自动排名评优 · 数据趋势一目了然</div>', unsafe_allow_html=True)
    
    classes = get_all_classes()
    all_exams = get_all_exams()
    total_classes = len(classes)
    total_exams = len(all_exams)
    latest_exams = get_latest_exam_per_class()
    total_students = sum(e.get("student_count", 0) for e in latest_exams)
    
    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.2, 1.5])
    
    def metric_card(col, icon_svg, value, label, card_class):
        col.markdown(f"""
        <div class="metric-card {card_class}">
            <div class="icon">{icon_svg}</div>
            <div class="value">{value}</div>
            <div class="label">{label}</div>
        </div>
        """, unsafe_allow_html=True)
    
    metric_card(col1, ICONS['building'], total_classes, "参与班级", "primary")
    metric_card(col2, ICONS['document'], total_exams, "累计周测场次", "secondary")
    metric_card(col3, ICONS['users'], total_students, "本期参测学生", "accent")
    metric_card(col4, ICONS['calendar'], all_exams[0]["exam_date"] if all_exams else "暂无", "最近一次考试", "info")
    
    st.markdown("---")
    
    if not latest_exams:
        st.info("暂无数据。请先在「学生管理」页添加班级和学生，再录入成绩。")
    else:
        st.subheader("各班最新周测概览")
        for exam in latest_exams:
            with st.expander(
                f"{exam['grade']} {exam['class_name']} | {exam['title']} | {exam['exam_date']} | "
                f"参测 {exam['student_count']} 人 | 班级均分 {round(exam['avg_total'], 1) if exam['avg_total'] else '--'}",
                expanded=False
            ):
                top5 = get_top_students(exam["id"], 5)
                if top5:
                    st.markdown("本次前五名")
                    cols = st.columns(len(top5))
                    for i, (col, s) in enumerate(zip(cols, top5)):
                        rank_label = f"第{s['rank']}名" if s["rank"] > 3 else ["冠军", "亚军", "季军"][s["rank"]-1]
                        col.markdown(f"""
                        <div class="rank-card">
                            <div class="rank-label">{ICONS['trophy']} {rank_label}</div>
                            <div class="rank-name">{s['name']}</div>
                            <div class="rank-score">总分 <strong>{int(s['total'])}</strong></div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("该次考试暂未录入成绩")
    
        st.markdown("---")
        st.subheader("各班最新均分横向对比")
        chart_data = [e for e in latest_exams if e["avg_total"]]
        if chart_data:
            import plotly.graph_objects as go
            labels = [f"{e['grade']}{e['class_name']}" for e in chart_data]
            values = [round(e["avg_total"], 1) for e in chart_data]
            chart_colors = ["#2E86AB", "#56A3A6", "#4A7C59", "#7FB069", "#5B7C99", "#7B9BB5", "#F6C90E", "#F9A826"][:len(labels)]
            fig = go.Figure(go.Bar(x=labels, y=values, marker_color=chart_colors, text=values, textposition="outside"))
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=40, r=20), yaxis_title="班级均分",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Microsoft YaHei, sans-serif", size=12),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#E5E7EB"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("录入成绩后将在此显示各班对比图")
