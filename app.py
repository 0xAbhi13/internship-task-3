"""Student Internship & Placement Management System (Task 3)."""
import csv
import io
import os
import re
import secrets
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import (Flask, abort, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import config as cfg

VALID_STATUSES = ["Applied", "Under Review", "Shortlisted", "Selected", "Rejected"]
VALID_OPP_TYPES = ["Internship", "Placement", "Trainee", "Apprenticeship"]
VALID_MODES = ["Remote", "On-site", "Hybrid"]
VALID_OPP_STATUS = ["draft", "published", "archived"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", cfg.SECRET_KEY)
    app.config["DATABASE"] = cfg.DATABASE
    app.config["UPLOAD_FOLDER"] = cfg.UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = cfg.MAX_UPLOAD_MB * 1024 * 1024
    if test_config:
        app.config.update(test_config)

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ---------- DB ----------
    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    app.get_db = get_db

    def init_db():
        with open(os.path.join(os.path.dirname(__file__), "schema.sql"), encoding="utf-8") as f:
            sql = f.read()
        db = sqlite3.connect(app.config["DATABASE"])
        db.executescript(sql)
        db.commit()
        db.close()

    app.init_db = init_db

    @app.teardown_appcontext
    def close_db(exc=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # ---------- CSRF ----------
    @app.before_request
    def ensure_csrf():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)

    @app.context_processor
    def inject_csrf():
        return {"csrf_token": session.get("_csrf", "")}

    def validate_csrf():
        if app.config.get("TESTING") and app.config.get("WTF_CSRF_ENABLED") is False:
            return True
        tok = request.form.get("csrf_token", "")
        if not tok or tok != session.get("_csrf"):
            abort(400, description="Invalid CSRF token")
        return True

    app.validate_csrf = validate_csrf

    # ---------- helpers ----------
    def current_user():
        uid = session.get("user_id")
        if not uid:
            return None
        db = get_db()
        return db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    app.current_user = current_user

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    def login_required(view):
        @wraps(view)
        def w(*a, **kw):
            if not session.get("user_id"):
                flash("Please log in first.", "error")
                return redirect(url_for("login", next=request.path))
            return view(*a, **kw)
        return w

    def admin_required(view):
        @wraps(view)
        def w(*a, **kw):
            if not session.get("user_id"):
                flash("Please log in first.", "error")
                return redirect(url_for("login"))
            if session.get("role") != "admin":
                abort(403)
            return view(*a, **kw)
        return w

    app.login_required = login_required
    app.admin_required = admin_required

    def valid_date(s):
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except Exception:
            return False

    # ================= LANDING =================
    @app.route("/")
    def index():
        db = get_db()
        count_opp = db.execute("SELECT COUNT(*) c FROM opportunities WHERE status='published'").fetchone()["c"]
        count_stu = db.execute("SELECT COUNT(*) c FROM users WHERE role='student'").fetchone()["c"]
        count_app = db.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"]
        featured = db.execute(
            "SELECT * FROM opportunities WHERE status='published' ORDER BY deadline ASC LIMIT 3"
        ).fetchall()
        return render_template("index.html", count_opp=count_opp, count_stu=count_stu,
                               count_app=count_app, featured=featured)

    # ================= AUTH =================
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            validate_csrf()
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            pw = request.form.get("password", "")
            pw2 = request.form.get("confirm", "")
            errors = []
            if len(name) < 2:
                errors.append("Name must be at least 2 characters.")
            if not EMAIL_RE.match(email):
                errors.append("Enter a valid email address.")
            if len(pw) < 6:
                errors.append("Password must be at least 6 characters.")
            if pw != pw2:
                errors.append("Passwords do not match.")
            db = get_db()
            if not errors:
                exists = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
                if exists:
                    errors.append("Email already registered. Please log in.")
            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("register.html"), 400
            role = "admin" if db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0 else "student"
            # First user becomes admin so project is usable out of the box.
            db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                       (name, email, generate_password_hash(pw), role))
            uid = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]
            db.execute("INSERT INTO student_profiles(user_id) VALUES(?)", (uid,))
            db.commit()
            flash(f"Registered as {role}. Please log in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            validate_csrf()
            email = request.form.get("email", "").strip().lower()
            pw = request.form.get("password", "")
            db = get_db()
            u = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not u or not check_password_hash(u["password_hash"], pw):
                flash("Invalid email or password.", "error")
                return render_template("login.html"), 401
            session.clear()
            session["user_id"] = u["id"]
            session["role"] = u["role"]
            session["_csrf"] = secrets.token_hex(16)
            flash(f"Welcome, {u['name']}!", "success")
            nxt = request.args.get("next") or request.form.get("next") or ""
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("admin" if u["role"] == "admin" else "dashboard"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "success")
        return redirect(url_for("index"))

    # ================= STUDENT DASHBOARD =================
    @app.route("/dashboard")
    @login_required
    def dashboard():
        if session.get("role") == "admin":
            return redirect(url_for("admin"))
        db = get_db()
        uid = session["user_id"]
        total = db.execute("SELECT COUNT(*) c FROM applications WHERE user_id=?", (uid,)).fetchone()["c"]
        under = db.execute("SELECT COUNT(*) c FROM applications WHERE user_id=? AND status IN ('Applied','Under Review')", (uid,)).fetchone()["c"]
        shorted = db.execute("SELECT COUNT(*) c FROM applications WHERE user_id=? AND status='Shortlisted'", (uid,)).fetchone()["c"]
        selected = db.execute("SELECT COUNT(*) c FROM applications WHERE user_id=? AND status='Selected'", (uid,)).fetchone()["c"]
        upcoming = db.execute(
            """SELECT o.* FROM opportunities o WHERE o.status='published' AND o.deadline >= date('now')
               AND o.id NOT IN (SELECT opportunity_id FROM applications WHERE user_id=?)
               ORDER BY o.deadline ASC LIMIT 5""", (uid,)).fetchall()
        recent = db.execute(
            """SELECT a.*, o.title, o.company FROM applications a
               JOIN opportunities o ON o.id=a.opportunity_id
               WHERE a.user_id=? ORDER BY a.updated_at DESC LIMIT 5""", (uid,)).fetchall()
        return render_template("dashboard.html", total=total, under=under, shorted=shorted,
                               selected=selected, upcoming=upcoming, recent=recent)

    # ================= OPPORTUNITIES =================
    @app.route("/opportunities")
    @login_required
    def opportunities():
        db = get_db()
        q = request.args.get("q", "").strip()
        location = request.args.get("location", "").strip()
        otype = request.args.get("type", "").strip()
        mode = request.args.get("mode", "").strip()
        paid = request.args.get("paid", "").strip()
        skill = request.args.get("skill", "").strip()
        sql = "SELECT * FROM opportunities WHERE 1=1"
        params = []
        # Students see published only; admins see all (with optional status filter)
        if session.get("role") != "admin":
            sql += " AND status='published'"
        else:
            st = request.args.get("status", "").strip()
            if st in VALID_OPP_STATUS:
                sql += " AND status=?"
                params.append(st)
        if q:
            sql += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        if location:
            sql += " AND location LIKE ?"
            params.append(f"%{location}%")
        if otype and otype in VALID_OPP_TYPES:
            sql += " AND type=?"
            params.append(otype)
        if mode and mode in VALID_MODES:
            sql += " AND mode=?"
            params.append(mode)
        if paid == "paid":
            sql += " AND paid=1"
        elif paid == "unpaid":
            sql += " AND paid=0"
        if skill:
            sql += " AND skills_required LIKE ?"
            params.append(f"%{skill}%")
        sql += " ORDER BY deadline ASC"
        rows = db.execute(sql, params).fetchall()
        # applied set for student
        applied = set()
        if session.get("role") == "student":
            ar = db.execute("SELECT opportunity_id FROM applications WHERE user_id=?", (session["user_id"],)).fetchall()
            applied = {r["opportunity_id"] for r in ar}
        return render_template("opportunities.html", rows=rows, applied=applied,
                               f={"q": q, "location": location, "type": otype, "mode": mode, "paid": paid, "skill": skill})

    @app.route("/opportunities/<int:oid>")
    @login_required
    def opportunity_detail(oid):
        db = get_db()
        o = db.execute("SELECT * FROM opportunities WHERE id=?", (oid,)).fetchone()
        if not o:
            abort(404)
        if o["status"] != "published" and session.get("role") != "admin":
            abort(404)
        mine = None
        if session.get("role") == "student":
            mine = db.execute("SELECT * FROM applications WHERE user_id=? AND opportunity_id=?",
                              (session["user_id"], oid)).fetchone()
        return render_template("opportunity_detail.html", o=o, mine=mine)

    @app.route("/opportunities/<int:oid>/apply", methods=["GET", "POST"])
    @login_required
    def apply(oid):
        if session.get("role") != "student":
            flash("Only students can apply.", "error")
            return redirect(url_for("opportunity_detail", oid=oid))
        db = get_db()
        o = db.execute("SELECT * FROM opportunities WHERE id=?", (oid,)).fetchone()
        if not o or o["status"] != "published":
            abort(404)
        if o["deadline"] < date.today().isoformat():
            flash("Application deadline has passed.", "error")
            return redirect(url_for("opportunity_detail", oid=oid))
        uid = session["user_id"]
        if request.method == "POST":
            validate_csrf()
            cover = request.form.get("cover_letter", "").strip()
            if len(cover) < 10:
                flash("Cover letter must be at least 10 characters.", "error")
                return render_template("apply.html", o=o), 400
            try:
                cur = db.execute("INSERT INTO applications(user_id,opportunity_id,cover_letter) VALUES(?,?,?)",
                                 (uid, oid, cover))
                aid = cur.lastrowid
                db.execute("INSERT INTO application_status_history(application_id,old_status,new_status,changed_by,note) VALUES(?,?,?,?,?)",
                           (aid, "", "Applied", uid, "Application submitted"))
                db.commit()
            except sqlite3.IntegrityError:
                flash("You have already applied for this opportunity.", "error")
                return redirect(url_for("opportunity_detail", oid=oid))
            flash("Application submitted!", "success")
            return redirect(url_for("applications"))
        return render_template("apply.html", o=o)

    # ================= APPLICATIONS (student) =================
    @app.route("/applications")
    @login_required
    def applications():
        if session.get("role") == "admin":
            return redirect(url_for("admin_apps"))
        db = get_db()
        uid = session["user_id"]
        rows = db.execute(
            """SELECT a.*, o.title, o.company, o.deadline, o.mode FROM applications a
               JOIN opportunities o ON o.id=a.opportunity_id
               WHERE a.user_id=? ORDER BY a.updated_at DESC""", (uid,)).fetchall()
        return render_template("applications.html", rows=rows)

    @app.route("/applications/<int:aid>")
    @login_required
    def application_detail(aid):
        db = get_db()
        a = db.execute(
            """SELECT a.*, o.title, o.company, o.location, o.deadline FROM applications a
               JOIN opportunities o ON o.id=a.opportunity_id WHERE a.id=?""", (aid,)).fetchone()
        if not a:
            abort(404)
        # ownership check: students only their own; admin any
        if session.get("role") != "admin":
            own = db.execute("SELECT id FROM applications WHERE id=? AND user_id=?", (aid, session["user_id"])).fetchone()
            if not own:
                abort(403)
        hist = db.execute(
            """SELECT h.*, u.name AS changer FROM application_status_history h
               LEFT JOIN users u ON u.id=h.changed_by WHERE h.application_id=? ORDER BY h.changed_at ASC""",
            (aid,)).fetchall()
        return render_template("application_detail.html", a=a, hist=hist)

    # ================= PROFILE / SKILLS / RESUME =================
    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        db = get_db()
        uid = session["user_id"]
        prof = db.execute("SELECT * FROM student_profiles WHERE user_id=?", (uid,)).fetchone()
        if not prof:
            db.execute("INSERT INTO student_profiles(user_id) VALUES(?)", (uid,))
            db.commit()
            prof = db.execute("SELECT * FROM student_profiles WHERE user_id=?", (uid,)).fetchone()
        user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        myskills = db.execute(
            """SELECT s.name, ss.proficiency, ss.skill_id FROM student_skills ss
               JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? ORDER BY s.name""", (uid,)).fetchall()
        if request.method == "POST":
            validate_csrf()
            action = request.form.get("action", "profile")
            if action == "profile":
                phone = request.form.get("phone", "").strip()[:30]
                college = request.form.get("college", "").strip()[:120]
                degree = request.form.get("degree", "").strip()[:120]
                grad_year = request.form.get("grad_year", "").strip()[:10]
                cgpa = request.form.get("cgpa", "").strip()[:10]
                interests = request.form.get("interests", "").strip()[:500]
                linkedin = request.form.get("linkedin", "").strip()[:200]
                github = request.form.get("github", "").strip()[:200]
                address = request.form.get("address", "").strip()[:300]
                resume_text = request.form.get("resume_text", "").strip()[:4000]
                name = request.form.get("name", "").strip()
                if len(name) < 2:
                    flash("Name must be at least 2 characters.", "error")
                    return render_template("profile.html", prof=prof, user=user, myskills=myskills), 400
                db.execute("UPDATE users SET name=? WHERE id=?", (name, uid))
                db.execute("""UPDATE student_profiles SET phone=?,college=?,degree=?,grad_year=?,cgpa=?,
                              interests=?,linkedin=?,github=?,address=?,resume_text=?,updated_at=datetime('now')
                              WHERE user_id=?""",
                           (phone, college, degree, grad_year, cgpa, interests, linkedin, github, address, resume_text, uid))
                db.commit()
                flash("Profile updated.", "success")
                return redirect(url_for("profile"))
            elif action == "add_skill":
                sname = request.form.get("skill_name", "").strip()[:60]
                prof_lvl = request.form.get("proficiency", "Beginner").strip()
                if not sname:
                    flash("Skill name required.", "error")
                    return render_template("profile.html", prof=prof, user=user, myskills=myskills), 400
                if prof_lvl not in ("Beginner", "Intermediate", "Advanced", "Expert"):
                    prof_lvl = "Beginner"
                db.execute("INSERT OR IGNORE INTO skills(name) VALUES(?)", (sname,))
                sid = db.execute("SELECT id FROM skills WHERE name=? COLLATE NOCASE", (sname,)).fetchone()["id"]
                try:
                    db.execute("INSERT INTO student_skills(user_id,skill_id,proficiency) VALUES(?,?,?)", (uid, sid, prof_lvl))
                    db.commit()
                    flash(f"Skill '{sname}' added.", "success")
                except sqlite3.IntegrityError:
                    flash("Skill already added.", "error")
                return redirect(url_for("profile"))
            elif action == "del_skill":
                sid = request.form.get("skill_id", "")
                db.execute("DELETE FROM student_skills WHERE user_id=? AND skill_id=?", (uid, sid))
                db.commit()
                flash("Skill removed.", "success")
                return redirect(url_for("profile"))
        return render_template("profile.html", prof=prof, user=user, myskills=myskills)

    @app.route("/profile/upload", methods=["POST"])
    @login_required
    def upload_resume():
        validate_csrf()
        f = request.files.get("resume")
        if not f or not f.filename:
            flash("No file selected.", "error")
            return redirect(url_for("profile"))
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in cfg.ALLOWED_RESUME_EXTS:
            flash("Only PDF/DOC/DOCX/TXT allowed.", "error")
            return redirect(url_for("profile"), ), 400
        safe = secure_filename(f.filename)
        if not safe:
            flash("Invalid filename.", "error")
            return redirect(url_for("profile"))
        fname = f"u{session['user_id']}_{secrets.token_hex(4)}{ext}"
        dest = os.path.join(app.config["UPLOAD_FOLDER"], fname)
        f.save(dest)
        db = get_db()
        # remove old file
        old = app.get_db().execute("SELECT resume_file FROM student_profiles WHERE user_id=?", (session["user_id"],)).fetchone()
        if old and old["resume_file"]:
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], old["resume_file"]))
            except OSError:
                pass
        db.execute("UPDATE student_profiles SET resume_file=? WHERE user_id=?", (fname, session["user_id"]))
        db.commit()
        flash("Resume uploaded.", "success")
        return redirect(url_for("profile"))

    @app.route("/resume")
    @login_required
    def resume():
        db = get_db()
        uid = session["user_id"]
        user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        prof = db.execute("SELECT * FROM student_profiles WHERE user_id=?", (uid,)).fetchone()
        myskills = db.execute(
            """SELECT s.name, ss.proficiency FROM student_skills ss
               JOIN skills s ON s.id=ss.skill_id WHERE ss.user_id=? ORDER BY s.name""", (uid,)).fetchall()
        return render_template("resume.html", user=user, prof=prof, myskills=myskills)

    # ================= ADMIN =================
    @app.route("/admin")
    @admin_required
    def admin():
        db = get_db()
        stats = {
            "students": db.execute("SELECT COUNT(*) c FROM users WHERE role='student'").fetchone()["c"],
            "opps": db.execute("SELECT COUNT(*) c FROM opportunities WHERE status='published'").fetchone()["c"],
            "apps": db.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"],
            "selected": db.execute("SELECT COUNT(*) c FROM applications WHERE status='Selected'").fetchone()["c"],
        }
        by_status = db.execute("SELECT status, COUNT(*) c FROM applications GROUP BY status").fetchall()
        recent = db.execute(
            """SELECT a.*, u.name AS student, o.title FROM applications a
               JOIN users u ON u.id=a.user_id JOIN opportunities o ON o.id=a.opportunity_id
               ORDER BY a.applied_at DESC LIMIT 8""").fetchall()
        return render_template("admin.html", stats=stats, by_status=by_status, recent=recent)

    @app.route("/admin/users")
    @admin_required
    def admin_users():
        db = get_db()
        users = db.execute("SELECT u.*, (SELECT COUNT(*) FROM applications a WHERE a.user_id=u.id) AS napp FROM users u ORDER BY u.created_at DESC").fetchall()
        return render_template("admin_users.html", users=users)

    @app.route("/admin/users/<int:uid>/delete", methods=["POST"])
    @admin_required
    def admin_user_delete(uid):
        validate_csrf()
        if uid == session["user_id"]:
            flash("Cannot delete yourself.", "error")
            return redirect(url_for("admin_users"))
        db = get_db()
        db.execute("DELETE FROM users WHERE id=?", (uid,))
        db.commit()
        flash("User deleted.", "success")
        return redirect(url_for("admin_users"))

    def _opp_form_data(form):
        return {
            "title": form.get("title", "").strip(),
            "company": form.get("company", "").strip(),
            "location": form.get("location", "").strip(),
            "type": form.get("type", "Internship").strip(),
            "mode": form.get("mode", "On-site").strip(),
            "paid": 1 if form.get("paid") == "1" else 0,
            "stipend": form.get("stipend", "").strip(),
            "duration": form.get("duration", "").strip(),
            "skills_required": form.get("skills_required", "").strip(),
            "eligibility": form.get("eligibility", "").strip(),
            "description": form.get("description", "").strip(),
            "instructions": form.get("instructions", "").strip(),
            "deadline": form.get("deadline", "").strip(),
            "status": form.get("status", "published").strip(),
        }

    def _opp_validate(d):
        errs = []
        if len(d["title"]) < 3:
            errs.append("Title must be at least 3 characters.")
        if len(d["company"]) < 2:
            errs.append("Company required.")
        if d["type"] not in VALID_OPP_TYPES:
            errs.append("Invalid internship type.")
        if d["mode"] not in VALID_MODES:
            errs.append("Invalid mode.")
        if d["status"] not in VALID_OPP_STATUS:
            errs.append("Invalid status.")
        if not valid_date(d["deadline"]):
            errs.append("Deadline must be a valid date (YYYY-MM-DD).")
        return errs

    @app.route("/admin/opportunities/new", methods=["GET", "POST"])
    @admin_required
    def admin_opp_new():
        if request.method == "POST":
            validate_csrf()
            d = _opp_form_data(request.form)
            errs = _opp_validate(d)
            if errs:
                for e in errs:
                    flash(e, "error")
                return render_template("admin_opportunity_form.html", d=d, mode2="new"), 400
            db = get_db()
            db.execute("""INSERT INTO opportunities(title,company,location,type,mode,paid,stipend,duration,
                          skills_required,eligibility,description,instructions,deadline,status,created_by)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (d["title"], d["company"], d["location"], d["type"], d["mode"], d["paid"], d["stipend"],
                        d["duration"], d["skills_required"], d["eligibility"], d["description"], d["instructions"],
                        d["deadline"], d["status"], session["user_id"]))
            db.commit()
            flash("Opportunity created.", "success")
            return redirect(url_for("opportunities", status=d["status"]))
        return render_template("admin_opportunity_form.html", d={}, mode2="new")

    @app.route("/admin/opportunities/<int:oid>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_opp_edit(oid):
        db = get_db()
        o = db.execute("SELECT * FROM opportunities WHERE id=?", (oid,)).fetchone()
        if not o:
            abort(404)
        if request.method == "POST":
            validate_csrf()
            d = _opp_form_data(request.form)
            errs = _opp_validate(d)
            if errs:
                for e in errs:
                    flash(e, "error")
                return render_template("admin_opportunity_form.html", d=d, mode2="edit", o=o), 400
            db.execute("""UPDATE opportunities SET title=?,company=?,location=?,type=?,mode=?,paid=?,stipend=?,
                          duration=?,skills_required=?,eligibility=?,description=?,instructions=?,deadline=?,status=?
                          WHERE id=?""",
                       (d["title"], d["company"], d["location"], d["type"], d["mode"], d["paid"], d["stipend"],
                        d["duration"], d["skills_required"], d["eligibility"], d["description"], d["instructions"],
                        d["deadline"], d["status"], oid))
            db.commit()
            flash("Opportunity updated.", "success")
            return redirect(url_for("opportunity_detail", oid=oid))
        return render_template("admin_opportunity_form.html", d=dict(o), mode2="edit", o=o)

    @app.route("/admin/opportunities/<int:oid>/delete", methods=["POST"])
    @admin_required
    def admin_opp_delete(oid):
        validate_csrf()
        db = get_db()
        db.execute("DELETE FROM opportunities WHERE id=?", (oid,))
        db.commit()
        flash("Opportunity deleted.", "success")
        return redirect(url_for("opportunities"))

    @app.route("/admin/applications")
    @admin_required
    def admin_apps():
        db = get_db()
        status = request.args.get("status", "").strip()
        sql = """SELECT a.*, u.name AS student, u.email, o.title, o.company FROM applications a
                 JOIN users u ON u.id=a.user_id JOIN opportunities o ON o.id=a.opportunity_id WHERE 1=1"""
        params = []
        if status in VALID_STATUSES:
            sql += " AND a.status=?"
            params.append(status)
        sql += " ORDER BY a.applied_at DESC"
        rows = db.execute(sql, params).fetchall()
        return render_template("admin_applications.html", rows=rows, fstatus=status, statuses=VALID_STATUSES)

    @app.route("/admin/applications/<int:aid>/status", methods=["POST"])
    @admin_required
    def admin_app_status(aid):
        validate_csrf()
        new = request.form.get("status", "").strip()
        note = request.form.get("note", "").strip()[:500]
        if new not in VALID_STATUSES:
            flash("Invalid status.", "error")
            return redirect(url_for("admin_apps")), 400
        db = get_db()
        a = db.execute("SELECT * FROM applications WHERE id=?", (aid,)).fetchone()
        if not a:
            abort(404)
        old = a["status"]
        db.execute("UPDATE applications SET status=?, updated_at=datetime('now') WHERE id=?", (new, aid))
        db.execute("INSERT INTO application_status_history(application_id,old_status,new_status,changed_by,note) VALUES(?,?,?,?,?)",
                   (aid, old, new, session["user_id"], note))
        db.commit()
        flash(f"Status: {old} → {new}.", "success")
        return redirect(url_for("application_detail", aid=aid))

    # ================= REPORTS =================
    @app.route("/reports")
    @login_required
    def reports():
        db = get_db()
        status = request.args.get("status", "").strip()
        frm = request.args.get("from", "").strip()
        to = request.args.get("to", "").strip()
        errs = []
        if frm and not valid_date(frm):
            errs.append("Invalid 'from' date.")
        if to and not valid_date(to):
            errs.append("Invalid 'to' date.")
        base = """SELECT a.*, u.name AS student, u.email, o.title, o.company FROM applications a
                  JOIN users u ON u.id=a.user_id JOIN opportunities o ON o.id=a.opportunity_id WHERE 1=1"""
        params = []
        if session.get("role") != "admin":
            base += " AND a.user_id=?"
            params.append(session["user_id"])
        if status in VALID_STATUSES:
            base += " AND a.status=?"
            params.append(status)
        elif status:
            errs.append("Invalid status filter.")
        if frm and valid_date(frm):
            base += " AND date(a.applied_at) >= date(?)"
            params.append(frm)
        if to and valid_date(to):
            base += " AND date(a.applied_at) <= date(?)"
            params.append(to)
        rows = []
        if not errs:
            rows = db.execute(base + " ORDER BY a.applied_at DESC", params).fetchall()
        for e in errs:
            flash(e, "error")
        return render_template("reports.html", rows=rows, statuses=VALID_STATUSES,
                               f={"status": status, "from": frm, "to": to})

    @app.route("/reports/export.csv")
    @login_required
    def export_csv():
        db = get_db()
        status = request.args.get("status", "").strip()
        frm = request.args.get("from", "").strip()
        to = request.args.get("to", "").strip()
        if status and status not in VALID_STATUSES:
            flash("Invalid status filter.", "error")
            return redirect(url_for("reports"))
        if (frm and not valid_date(frm)) or (to and not valid_date(to)):
            flash("Invalid date filter.", "error")
            return redirect(url_for("reports"))
        sql = """SELECT a.id, u.name AS student, u.email, o.title, o.company, a.status, a.applied_at, a.updated_at
                 FROM applications a JOIN users u ON u.id=a.user_id
                 JOIN opportunities o ON o.id=a.opportunity_id WHERE 1=1"""
        params = []
        if session.get("role") != "admin":
            sql += " AND a.user_id=?"
            params.append(session["user_id"])
        if status in VALID_STATUSES:
            sql += " AND a.status=?"
            params.append(status)
        if frm:
            sql += " AND date(a.applied_at) >= date(?)"
            params.append(frm)
        if to:
            sql += " AND date(a.applied_at) <= date(?)"
            params.append(to)
        sql += " ORDER BY a.applied_at DESC"
        rows = db.execute(sql, params).fetchall()
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["id", "student", "email", "opportunity", "company", "status", "applied_at", "updated_at"])
        for r in rows:
            w.writerow([r["id"], r["student"], r["email"], r["title"], r["company"], r["status"], r["applied_at"], r["updated_at"]])
        resp = make_response(out.getvalue())
        resp.headers["Content-Type"] = "text/csv"
        resp.headers["Content-Disposition"] = "attachment; filename=applications.csv"
        return resp

    # ---------- errors ----------
    @app.errorhandler(403)
    def e403(e):
        return render_template("error.html", code=403, msg="Forbidden. You don't have access."), 403

    @app.errorhandler(404)
    def e404(e):
        return render_template("error.html", code=404, msg="Page not found."), 404

    @app.errorhandler(400)
    def e400(e):
        return render_template("error.html", code=400, msg=getattr(e, "description", "Bad request.")), 400

    return app


app = create_app()

if __name__ == "__main__":
    if not os.path.exists(cfg.DATABASE):
        app.init_db()
        print("Database initialised at", cfg.DATABASE)
    app.run(debug=True, port=5000)
