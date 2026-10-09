<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&pause=1000&color=2563EB&center=true&vCenter=true&width=650&lines=Discover+internships+%F0%9F%94%8D;Track+every+application+%F0%9F%93%8A;Build+skills+%2B+resume+%F0%9F%9A%80" alt="typing"/>

<p>
<img src="https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="python"/>
<img src="https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white" alt="flask"/>
<img src="https://img.shields.io/badge/SQLite-DB-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="sqlite"/>
<img src="https://img.shields.io/badge/pytest-13_passed-16a34a?style=for-the-badge&logo=pytest&logoColor=white" alt="tests"/>
<img src="https://img.shields.io/badge/CSRF-protected-dc2626?style=for-the-badge&logo=shield&logoColor=white" alt="security"/>
</p>

<p>
<img src="https://skillicons.dev/icons?i=python,flask,sqlite,html,css,js,git&theme=light" alt="stack"/>
</p>

</div>

---

## ✨ What it does

<details open>
<summary><b>🔐 Auth & profiles</b></summary>

- Student registration, login, logout — hashed passwords, sessions, CSRF, role-based access
- Education + skills + interests profile, printable resume page
- Secure resume upload (extension whitelist, `secure_filename`, random rename, 2&nbsp;MB cap, never executed)

</details>

<details open>
<summary><b>🔍 Internship discovery</b></summary>

- Browse + search by title, company, skill, location, type
- Filter by Remote / On-site / Hybrid, paid / unpaid, deadline
- Eligibility, skills, duration, stipend & instructions on every listing
- Admin add / edit / publish / archive with date validation

</details>

<details open>
<summary><b>📝 Application tracking</b></summary>

```text
Applied → Under Review → Shortlisted → Selected / Rejected
```

- Internal application form (cover letter ≥ 10 chars)
- Duplicate applications blocked at UI **and** DB (`UNIQUE(user, opportunity)`)
- Full status history + timestamps, student sees **only their own data** (IDOR-tested)

</details>

<details open>
<summary><b>📊 Dashboards & reports</b></summary>

- Student: totals · under review · shortlisted · selected · upcoming deadlines · recent activity
- Admin: users · listings · reviews · aggregate stats (all server-validated)
- Reports filtered by status + date, CSV export with empty-state handling

</details>

---

## 🚀 Quick start

```powershell
cd student-internship-placement-system
pip install -r requirements.txt
python seed.py        # placement.db + demo accounts (idempotent — safe to re-run)
python app.py         # http://127.0.0.1:5000
python -m pytest tests -v
```

### 🔑 Demo accounts (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@example.com` | `admin123` |
| Student | `student@example.com` | `student123` |

> First registered user on a fresh DB becomes admin automatically.

---

## 🗂️ Project tour

```text
app.py  templates/ (15 pages)  static/  schema.sql  seed.py  config.py
tests/  report/*.docx  screenshots/  README.md  ARCHITECTURE.md  TESTING.md
```

| Page | Route |
|------|-------|
| 🏠 Landing | `/` |
| 📊 Student dashboard | `/dashboard` |
| 🔍 Discovery | `/opportunities` |
| 📄 Details + apply | `/opportunities/<id>` |
| 🧾 My applications | `/applications` |
| 👤 Profile + resume | `/profile` → `/resume` 🖨️ |
| 🛠️ Admin | `/admin` · `/admin/users` · `/admin/applications` |
| 📈 Reports + CSV | `/reports` → `/reports/export.csv` |

---

## 🎬 Screenshots

> Genuine captures go here — see [`screenshots/README.md`](screenshots/README.md) for steps. No fakes.

| Landing | Dashboard | Discovery |
|---------|-----------|-----------|
| *coming soon* | *coming soon* | *coming soon* |

---

## 🧪 Testing

```powershell
python -m pytest tests -v
# 13 passed — registration, login, RBAC, CRUD, search,
# duplicates, status history, IDOR 403, CSV, bad dates, empty states, CSRF
```

Full matrix: [`TESTING.md`](TESTING.md) · Design: [`ARCHITECTURE.md`](ARCHITECTURE.md) · Report: [`report/Internship_Task_3_Report.docx`](report/Internship_Task_3_Report.docx)

---

## ⚙️ Config & Troubleshooting

Copy `.env.example` → `.env` and set `SECRET_KEY`. Ignored by git: `*.db`, `uploads/`, `.env`, `__pycache__/`.

| Symptom | Fix |
|---------|-----|
| `no such table` | run `python seed.py` |
| CSRF `400` | submit via rendered forms (token included) |
| Port busy | app uses `5000` — change port in `app.py` |

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=120&section=footer" alt="footer"/>

⭐ Star the repo after you push it · Replace with your real link — never commit secrets ⭐

</div>
