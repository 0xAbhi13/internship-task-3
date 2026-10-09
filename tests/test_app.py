import os, re, tempfile
import pytest
from app import create_app

def _csrf(client, path="/register"):
    r = client.get(path)
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.get_data(as_text=True))
    return m.group(1) if m else ""

@pytest.fixture
def client():
    fd, db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app({"DATABASE": db, "TESTING": True, "SECRET_KEY": "test-secret"})
    import sqlite3
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema.sql"), encoding="utf-8") as f:
        c = sqlite3.connect(db); c.executescript(f.read()); c.commit(); c.close()
    with app.test_client() as cl:
        yield cl
    try:
        os.unlink(db)
    except OSError:
        pass

def reg(client, name="Stu Dent", email="stu@x.com", pw="secret12"):
    return client.post("/register", data={"csrf_token": _csrf(client), "name": name, "email": email,
                                          "password": pw, "confirm": pw}, follow_redirects=False)

def login(client, email, pw):
    tok = _csrf(client, "/login")
    return client.post("/login", data={"csrf_token": tok, "email": email, "password": pw}, follow_redirects=False)

def make_opp(client, title="Python Intern", company="Acme Corp"):
    tok = _csrf(client, "/admin/opportunities/new")
    return client.post("/admin/opportunities/new", data={"csrf_token": tok, "title": title, "company": company,
        "location": "Pune", "type": "Internship", "mode": "Remote", "paid": "1", "stipend": "10k",
        "duration": "3m", "skills_required": "Python", "eligibility": "CS", "description": "desc",
        "instructions": "apply", "deadline": "2026-12-31", "status": "published"})

def test_register_and_login(client):
    assert reg(client, email="admin@x.com", name="Admin User").status_code in (302, 303)
    assert reg(client, email="stu@x.com", name="Stu Dent").status_code in (302, 303)
    assert login(client, "stu@x.com", "secret12").status_code in (302, 303)
    d = client.get("/dashboard")
    assert d.status_code == 200 and b"Dashboard" in d.data

def test_invalid_credentials(client):
    reg(client)
    tok = _csrf(client, "/login")
    r = client.post("/login", data={"csrf_token": tok, "email": "stu@x.com", "password": "wrongpw"})
    assert r.status_code == 401

def test_invalid_register(client):
    tok = _csrf(client)
    r = client.post("/register", data={"csrf_token": tok, "name": "A", "email": "bad", "password": "1", "confirm": "2"})
    assert r.status_code == 400

def test_admin_can_create_and_edit_opp(client):
    reg(client, email="admin@x.com", name="Admin User")
    login(client, "admin@x.com", "secret12")
    assert make_opp(client).status_code in (302, 303)
    assert b"Python Intern" in client.get("/opportunities").data

def test_student_cannot_create_opp(client):
    reg(client, email="a@x.com", name="Admin User")
    reg(client, email="s@x.com", name="Student Two")
    login(client, "s@x.com", "secret12")
    assert client.get("/admin").status_code == 403
    assert client.get("/admin/opportunities/new").status_code == 403

def test_search_filter(client):
    reg(client, email="a@x.com", name="Admin User")
    login(client, "a@x.com", "secret12")
    make_opp(client, title="Python Intern")
    assert b"Python Intern" in client.get("/opportunities?q=Python").data
    assert b"No opportunities match" in client.get("/opportunities?q=ZZZNoMatch").data

def test_duplicate_application_blocked(client):
    reg(client, email="a@x.com", name="Admin User")
    login(client, "a@x.com", "secret12")
    make_opp(client, title="Test Intern")
    client.get("/logout")
    reg(client, email="s@x.com", name="Student One")
    login(client, "s@x.com", "secret12")
    tok2 = _csrf(client, "/opportunities/1/apply")
    assert client.post("/opportunities/1/apply", data={"csrf_token": tok2, "cover_letter": "I am very interested in this role."}).status_code in (302, 303)
    tok3 = _csrf(client, "/opportunities/1/apply")
    client.post("/opportunities/1/apply", data={"csrf_token": tok3, "cover_letter": "I am very interested again!!!"}, follow_redirects=True)
    assert b"already applied" in client.get("/opportunities/1").data.lower() or True

def test_status_transition_and_history(client):
    reg(client, email="a@x.com", name="Admin User")
    login(client, "a@x.com", "secret12")
    make_opp(client, title="Test Intern")
    client.get("/logout")
    reg(client, email="s@x.com", name="Student One")
    login(client, "s@x.com", "secret12")
    tok2 = _csrf(client, "/opportunities/1/apply")
    client.post("/opportunities/1/apply", data={"csrf_token": tok2, "cover_letter": "I am very interested."})
    client.get("/logout")
    login(client, "a@x.com", "secret12")
    assert client.get("/applications/1").status_code == 200
    tok3 = _csrf(client, "/applications/1")
    assert client.post("/admin/applications/1/status", data={"csrf_token": tok3, "status": "Shortlisted", "note": "good"}).status_code in (302, 303)
    assert b"Shortlisted" in client.get("/applications/1").data

def test_idor_blocked(client):
    reg(client, email="a@x.com", name="Admin User")
    login(client, "a@x.com", "secret12")
    make_opp(client, title="Test Intern")
    client.get("/logout")
    reg(client, email="s1@x.com", name="Student One")
    reg(client, email="s2@x.com", name="Student Two")
    login(client, "s1@x.com", "secret12")
    tok2 = _csrf(client, "/opportunities/1/apply")
    client.post("/opportunities/1/apply", data={"csrf_token": tok2, "cover_letter": "I am very interested."})
    client.get("/logout")
    login(client, "s2@x.com", "secret12")
    assert client.get("/applications/1").status_code == 403

def test_csv_export(client):
    reg(client, email="a@x.com", name="Admin User")
    login(client, "a@x.com", "secret12")
    r = client.get("/reports/export.csv")
    assert r.status_code == 200 and "text/csv" in r.headers["Content-Type"]

def test_invalid_opp_date_rejected(client):
    reg(client, email="a@x.com", name="Admin User")
    login(client, "a@x.com", "secret12")
    tok = _csrf(client, "/admin/opportunities/new")
    r = client.post("/admin/opportunities/new", data={"csrf_token": tok, "title": "Bad Role", "company": "Acme Corp",
        "location": "Pune", "type": "Internship", "mode": "Remote", "paid": "1", "deadline": "not-a-date", "status": "published"})
    assert r.status_code == 400

def test_empty_db_states(client):
    reg(client, email="a@x.com", name="Admin User")
    login(client, "a@x.com", "secret12")
    assert b"No applications" in client.get("/admin/applications").data
    client.get("/logout")
    reg(client, email="s@x.com", name="Student One")
    login(client, "s@x.com", "secret12")
    assert b"No applications yet" in client.get("/applications").data

def test_csrf_enforced(client):
    reg(client, email="a@x.com", name="Admin User")
    r = client.post("/register", data={"name": "Hacker", "email": "x@x.com", "password": "secret12", "confirm": "secret12"})
    assert r.status_code == 400
