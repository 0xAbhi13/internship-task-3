# TESTING.md

## Stack: pytest (13 tests in `tests/test_app.py`, temp SQLite DB per test, CSRF tokens parsed from forms)

## Results (actual, 2026-10-09)
```
13 passed in ~13s
test_register_and_login PASSED
test_invalid_credentials PASSED
test_invalid_register PASSED
test_admin_can_create_and_edit_opp PASSED
test_student_cannot_create_opp PASSED
test_search_filter PASSED
test_duplicate_application_blocked PASSED
test_status_transition_and_history PASSED
test_idor_blocked PASSED
test_csv_export PASSED
test_invalid_opp_date_rejected PASSED
test_empty_db_states PASSED
test_csrf_enforced PASSED
```
Run: `python -m pytest tests -v`

## Coverage map (task §7)
| Requirement | Test |
|---|---|
| Registration + login | test_register_and_login |
| Invalid credentials | test_invalid_credentials, test_invalid_register |
| Student/admin permissions | test_student_cannot_create_opp |
| Creation + editing | test_admin_can_create_and_edit_opp |
| Search/filter | test_search_filter |
| Duplicate applications | test_duplicate_application_blocked (UNIQUE + flash) |
| Status transitions + history | test_status_transition_and_history |
| Unauthorized private-record access (IDOR) | test_idor_blocked (`/applications/1` → 403 for non-owner) |
| CSV export | test_csv_export (200 + text/csv) |
| Invalid form data | test_invalid_register, test_invalid_opp_date_rejected |
| Empty DB states | test_empty_db_states |
| Invalid dates / DB errors | test_invalid_opp_date_rejected |

## Bugs found & fixed (real)
1. **First-user-is-admin vs test assumption** — `test_register_and_login` expected `/dashboard` 200 for first user, got 302 (admin redirect). Fixed test to register admin + student, assert student dashboard.
2. **Over-strict fixture data** — titles like `"T"` / company `"C"` / name `"S"` failed server validation (min lengths), causing 404s in status/IDOR tests. Fixed fixtures to valid values (`"Test Intern"`, `"Acme Corp"`, `"Student One"`).
3. **Wrong detail URL in test** — used `/admin/applications/1` (list route) instead of `/applications/1` (detail). Fixed test; app code unchanged.
4. **Accidental mass-replace** during patching corrupted test file (replaced every "T"); rewrote file cleanly, re-ran green.
5. **CSRF helper after logout** — verified token refresh on `session.clear()` + re-login works; kept enforcement ON in tests.

## Manual checks
- Seeded twice: second run prints "exists, skip" for all rows (idempotent) — verified.
- Student A cannot view student B's `/applications/<id>` by URL tampering (403) — automated + manually reasoned.
- CSV with no rows still returns header; invalid `?status=` redirects with flash.
- Expired deadline blocks apply with flash.
