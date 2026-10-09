"""Idempotent seed: safe to run multiple times (no duplicates)."""
import os, sqlite3, sys
from werkzeug.security import generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DATABASE", os.path.join(BASE, "placement.db"))

def ensure_schema(db):
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())

SAMPLE_OPPS = [
    ("Python Backend Intern", "NexaSoft Labs", "Pune", "Internship", "Hybrid", 1, "₹12,000/month", "3 months",
     "Python, Flask, SQL", "B.E./B.Tech CS/IT, 2025-2026", "Build REST APIs with Flask and SQLite. (SAMPLE listing for training.)",
     "Apply via portal with cover letter.", "2026-12-31", "published"),
    ("Frontend Developer Intern", "PixelKraft Studio", "Remote", "Internship", "Remote", 1, "₹10,000/month", "3 months",
     "HTML, CSS, JavaScript", "Any student with JS basics", "Responsive UI tasks and landing pages. (SAMPLE listing.)",
     "Apply via portal.", "2026-12-15", "published"),
    ("Data Analyst Trainee", "InsightMetrics", "Mumbai", "Trainee", "On-site", 1, "₹15,000/month", "6 months",
     "SQL, Excel, Python", "Statistics/CS background preferred", "Dashboards and weekly reports. (SAMPLE listing.)",
     "Apply with resume text.", "2026-11-30", "published"),
    ("Campus Ambassador (Unpaid)", "EduSpark", "Remote", "Apprenticeship", "Remote", 0, "Unpaid (Certificate + LOR)", "2 months",
     "Communication, Social Media", "Open to all colleges", "Outreach and event promotion. (SAMPLE listing.)",
     "One-click apply.", "2026-12-20", "published"),
    ("Graduate Placement Drive", "TechMahindra-like Hiring (Sample)", "Hyderabad", "Placement", "On-site", 1, "₹4.5 LPA", "Full-time",
     "Java, DBMS, Aptitude", "2025 batch, 60%+", "Sample placement record for testing archived flow.", "Via admin referral.", "2026-10-31", "archived"),
]

def main():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    ensure_schema(db)
    # admin (idempotent)
    admin = db.execute("SELECT id FROM users WHERE email='admin@example.com'").fetchone()
    if not admin:
        db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                   ("Admin", "admin@example.com", generate_password_hash("admin123"), "admin"))
        print("created admin@example.com / admin123")
    else:
        print("admin exists, skip")
    # demo student
    stu = db.execute("SELECT id FROM users WHERE email='student@example.com'").fetchone()
    if not stu:
        db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                   ("Demo Student", "student@example.com", generate_password_hash("student123"), "student"))
        print("created student@example.com / student123")
    else:
        print("demo student exists, skip")
    admin_id = db.execute("SELECT id FROM users WHERE email='admin@example.com'").fetchone()["id"]
    stu_id = db.execute("SELECT id FROM users WHERE email='student@example.com'").fetchone()["id"]
    db.execute("INSERT OR IGNORE INTO student_profiles(user_id) VALUES(?)", (stu_id,))
    db.execute("UPDATE student_profiles SET college='Sample College', degree='B.Tech CSE', grad_year='2026', cgpa='8.2', interests='Web dev, AI', resume_text='Demo student resume.' WHERE user_id=?", (stu_id,))
    for s in ["Python", "Flask", "SQL", "HTML", "JavaScript"]:
        db.execute("INSERT OR IGNORE INTO skills(name) VALUES(?)", (s,))
    sid = db.execute("SELECT id FROM skills WHERE name='Python'").fetchone()["id"]
    db.execute("INSERT OR IGNORE INTO student_skills(user_id,skill_id,proficiency) VALUES(?,?,?)", (stu_id, sid, "Intermediate"))
    for o in SAMPLE_OPPS:
        exists = db.execute("SELECT id FROM opportunities WHERE title=? AND company=?", (o[0], o[1])).fetchone()
        if not exists:
            db.execute("""INSERT INTO opportunities(title,company,location,type,mode,paid,stipend,duration,
                        skills_required,eligibility,description,instructions,deadline,status,created_by)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*o, admin_id))
            print("seeded:", o[0])
        else:
            print("exists, skip:", o[0])
    db.commit()
    db.close()
    print("Seed OK ->", DB)

if __name__ == "__main__":
    main()
