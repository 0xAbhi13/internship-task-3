# ARCHITECTURE.md

## Style
Monolithic Flask app with clear module sections inside `app.py` (auth / opportunities / applications / profiles / admin / reports), plus `config.py`, `schema.sql`, `seed.py`. Server-rendered Jinja templates + one CSS file + tiny JS. SQLite via `sqlite3` with parameterized queries only. No ORM/Docker/heavy deps — per task constraints.

## Request flow
Browser → Flask route → `login_required`/`admin_required` → server validation → parameterized SQL (transaction per write) → redirect + flash → Jinja render. Session holds `user_id`, `role`, `_csrf`.

## Database (SQLite)
- `users(id PK, name, email UNIQUE NOCASE, password_hash, role student|admin, created_at)` — index on email, role.
- `student_profiles(id PK, user_id UNIQUE FK→users CASCADE, phone, college, degree, grad_year, cgpa, interests, linkedin, github, address, resume_text, resume_file, updated_at)`.
- `skills(id PK, name UNIQUE NOCASE)` + `student_skills(id PK, user_id FK, skill_id FK, proficiency, UNIQUE(user_id,skill_id))` — many-to-many.
- `opportunities(id PK, title, company, location, type, mode, paid 0/1, stipend, duration, skills_required, eligibility, description, instructions, deadline YYYY-MM-DD, status draft|published|archived, created_by FK, created_at)` — indexes on status/deadline/company/mode.
- `applications(id PK, user_id FK, opportunity_id FK, cover_letter, status, applied_at, updated_at, UNIQUE(user_id, opportunity_id))` — duplicate block at DB level; indexes on user/opp/status.
- `application_status_history(id PK, application_id FK CASCADE, old_status, new_status, changed_by FK, note, changed_at)` — audit trail.

Relationships: user 1—1 profile; user N—M skills; user N—M opportunities via applications; application 1—N history. FKs with `ON DELETE CASCADE` (user data) / `SET NULL` (created_by). `PRAGMA foreign_keys=ON` per connection.

## Key decisions
- `UNIQUE(user_id, opportunity_id)` enforces no-duplicate at DB, not just UI.
- Status history table (not just column) for audit + dashboard "recent activity".
- CSRF: per-session token, validated on every POST; 400 on mismatch (tested).
- Ownership: `application_detail` checks `user_id == session` unless admin (403 otherwise; tested IDOR).
- Uploads: whitelist `.pdf/.doc/.docx/.txt`, `secure_filename` + random prefix, 2 MB cap, stored outside templates, never executed.
- First registered user → admin (bootstraps fresh DB); seed creates fixed demo accounts idempotently (`INSERT OR IGNORE` / existence checks).
- Students query `status='published'` only; admins may filter by status.

## Security / reliability
Werkzeug password hashing, server-side validation (email regex, lengths, enums, `valid_date`), HttpOnly + SameSite=Lax cookies, safe error pages (no stack leaks), CSV via `csv` module with content-disposition.

## Performance
Indexed filters, `LIMIT` on dashboard/featured, single-query counts, no N+1 (joins for list pages). No caching needed at this scale.
