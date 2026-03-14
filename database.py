import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor


# ── 连接 ──────────────────────────────────────────────────────────────────────

def get_connection():
    url = st.secrets["SUPABASE_DB_URL"]
    conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            grade TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            student_no TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS exams (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scores (
            id SERIAL PRIMARY KEY,
            exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            chinese REAL DEFAULT 0,
            math REAL DEFAULT 0,
            english REAL DEFAULT 0,
            total REAL DEFAULT 0,
            rank INTEGER DEFAULT 0,
            UNIQUE(exam_id, student_id)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()



# ── Classes ───────────────────────────────────────────────────────────────────

def get_all_classes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM classes ORDER BY grade, name")
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def add_class(name, grade):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO classes (name, grade) VALUES (%s, %s)", (name, grade))
    conn.commit(); cur.close(); conn.close()


def delete_class(class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM classes WHERE id=%s", (class_id,))
    conn.commit(); cur.close(); conn.close()


# ── Students ──────────────────────────────────────────────────────────────────

def get_students_by_class(class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM students WHERE class_id=%s ORDER BY student_no, name",
        (class_id,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def add_student(name, class_id, student_no=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (name, class_id, student_no) VALUES (%s, %s, %s)",
        (name, class_id, student_no)
    )
    conn.commit(); cur.close(); conn.close()


def delete_student(student_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id=%s", (student_id,))
    conn.commit(); cur.close(); conn.close()


def bulk_add_students(class_id, student_list):
    conn = get_connection()
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO students (name, class_id, student_no) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        [(name, class_id, no) for name, no in student_list]
    )
    conn.commit(); cur.close(); conn.close()


# ── Exams ─────────────────────────────────────────────────────────────────────

def get_exams_by_class(class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM exams WHERE class_id=%s ORDER BY exam_date DESC",
        (class_id,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def get_all_exams():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.*, c.name as class_name, c.grade
        FROM exams e JOIN classes c ON e.class_id = c.id
        ORDER BY e.exam_date DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def add_exam(title, exam_date, class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO exams (title, exam_date, class_id) VALUES (%s, %s, %s) RETURNING id",
        (title, exam_date, class_id)
    )
    exam_id = cur.fetchone()["id"]
    conn.commit(); cur.close(); conn.close()
    return exam_id


def delete_exam(exam_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM exams WHERE id=%s", (exam_id,))
    conn.commit(); cur.close(); conn.close()


# ── Scores ────────────────────────────────────────────────────────────────────

def upsert_score(exam_id, student_id, chinese, math, english):
    total = chinese + math + english
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO scores (exam_id, student_id, chinese, math, english, total)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (exam_id, student_id) DO UPDATE SET
            chinese=EXCLUDED.chinese, math=EXCLUDED.math,
            english=EXCLUDED.english, total=EXCLUDED.total
    """, (exam_id, student_id, chinese, math, english, total))
    conn.commit()
    _recalculate_ranks(exam_id, cur)
    conn.commit(); cur.close(); conn.close()


def bulk_upsert_scores(exam_id, score_rows):
    conn = get_connection()
    cur = conn.cursor()
    for student_id, chinese, math, english in score_rows:
        total = chinese + math + english
        cur.execute("""
            INSERT INTO scores (exam_id, student_id, chinese, math, english, total)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (exam_id, student_id) DO UPDATE SET
                chinese=EXCLUDED.chinese, math=EXCLUDED.math,
                english=EXCLUDED.english, total=EXCLUDED.total
        """, (exam_id, student_id, chinese, math, english, total))
    conn.commit()
    _recalculate_ranks(exam_id, cur)
    conn.commit(); cur.close(); conn.close()


def _recalculate_ranks(exam_id, cur):
    cur.execute(
        "SELECT id, total FROM scores WHERE exam_id=%s ORDER BY total DESC",
        (exam_id,)
    )
    rows = cur.fetchall()
    rank = 1
    prev_total = None
    for i, row in enumerate(rows):
        if row["total"] != prev_total:
            rank = i + 1
        cur.execute("UPDATE scores SET rank=%s WHERE id=%s", (rank, row["id"]))
        prev_total = row["total"]


def get_scores_for_exam(exam_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id as score_id, st.name, st.student_no,
               s.chinese, s.math, s.english, s.total, s.rank
        FROM scores s
        JOIN students st ON s.student_id = st.id
        WHERE s.exam_id=%s
        ORDER BY s.rank
    """, (exam_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def get_student_history(student_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.title, e.exam_date, s.chinese, s.math, s.english, s.total, s.rank
        FROM scores s
        JOIN exams e ON s.exam_id = e.id
        WHERE s.student_id=%s
        ORDER BY e.exam_date ASC
    """, (student_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def get_class_history(class_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.title, e.exam_date,
               AVG(s.chinese) as avg_chinese,
               AVG(s.math)    as avg_math,
               AVG(s.english) as avg_english,
               AVG(s.total)   as avg_total,
               MAX(s.total)   as max_total,
               MIN(s.total)   as min_total
        FROM scores s
        JOIN exams e     ON s.exam_id   = e.id
        JOIN students st ON s.student_id = st.id
        WHERE st.class_id=%s
        GROUP BY e.id, e.title, e.exam_date
        ORDER BY e.exam_date ASC
    """, (class_id,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def get_top_students(exam_id, n=5):
    rows = get_scores_for_exam(exam_id)
    return [r for r in rows if r["rank"] <= n]


def get_latest_exam_per_class():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (e.class_id)
               e.id, e.title, e.exam_date, e.class_id,
               c.name as class_name, c.grade,
               AVG(s.total) OVER (PARTITION BY e.id) as avg_total,
               COUNT(s.id)  OVER (PARTITION BY e.id) as student_count
        FROM exams e
        JOIN classes c ON e.class_id = c.id
        LEFT JOIN scores s ON s.exam_id = e.id
        ORDER BY e.class_id, e.exam_date DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows