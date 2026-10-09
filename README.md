# Student Internship & Placement Management System (Task 3)

Separate, original project for **Internship Task 3**. Does NOT modify Task 2 (`student-attendance-system/`).

## Features
- Student registration/login/logout (hashed passwords, sessions, CSRF, role-based access)
- Browse/search/filter internships (title, company, skill, location, type, mode, paid, deadline)
- Admin CRUD: add/edit/publish/archive/delete listings with date validation
- Apply with cover letter, duplicate-application block, status tracking (Applied → Under Review → Shortlisted → Selected/Rejected) + history + timestamps
- Student dashboard (totals, under-review, shortlisted, selected, upcoming deadlines, recent activity) — students see only their own data (IDOR tested)
- Skills + education profile, printable resume page, secure resume upload (ext whitelist, `secure_filename`, random rename, size cap, never executed)
- Admin dashboard (users, listings, review apps, aggregate stats), server-side validation everywhere
- Reports: filter by status/date + CSV export (empty-result + invalid-filter handling)

> Sample listings are clearly labelled as training samples, not verified live vacancies.

## Quick start
```powershell
cd student-internship-placement-system
pip install -r requirements.txt
python seed.py        # creates placement.db + admin@example.com/admin123 + student@example.com/student123 (idempotent)
python app.py         # http://127.0.0.1:5000
python -m pytest tests -v
```

## Config
Copy `.env.example` → `.env` and set `SECRET_KEY`. Defaults work for local dev. Never commit secrets (`placement.db`, `uploads/`, `.env` are git-ignored).

## Structure
```
app.py  templates/  static/  schema.sql  seed.py  config.py  tests/  report/  screenshots/
```

## Troubleshooting
- `no such table`: run `python seed.py` (runs schema first).
- CSRF 400: use forms as rendered (token included); don't POST via bare curl.
- Port busy: `python app.py` uses 5000; set `PORT` or edit last line.
