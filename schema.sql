PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student','admin')),
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE TABLE IF NOT EXISTS student_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  phone TEXT DEFAULT '',
  college TEXT DEFAULT '',
  degree TEXT DEFAULT '',
  grad_year TEXT DEFAULT '',
  cgpa TEXT DEFAULT '',
  interests TEXT DEFAULT '',
  linkedin TEXT DEFAULT '',
  github TEXT DEFAULT '',
  address TEXT DEFAULT '',
  resume_text TEXT DEFAULT '',
  resume_file TEXT DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_profiles_user ON student_profiles(user_id);

CREATE TABLE IF NOT EXISTS skills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS student_skills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  proficiency TEXT NOT NULL DEFAULT 'Beginner' CHECK (proficiency IN ('Beginner','Intermediate','Advanced','Expert')),
  UNIQUE(user_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_stuskill_user ON student_skills(user_id);
CREATE INDEX IF NOT EXISTS idx_stuskill_skill ON student_skills(skill_id);

CREATE TABLE IF NOT EXISTS opportunities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  location TEXT NOT NULL DEFAULT '',
  type TEXT NOT NULL DEFAULT 'Internship' CHECK (type IN ('Internship','Placement','Trainee','Apprenticeship')),
  mode TEXT NOT NULL DEFAULT 'On-site' CHECK (mode IN ('Remote','On-site','Hybrid')),
  paid INTEGER NOT NULL DEFAULT 1 CHECK (paid IN (0,1)),
  stipend TEXT DEFAULT '',
  duration TEXT DEFAULT '',
  skills_required TEXT DEFAULT '',
  eligibility TEXT DEFAULT '',
  description TEXT DEFAULT '',
  instructions TEXT DEFAULT '',
  deadline TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'published' CHECK (status IN ('draft','published','archived')),
  created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opp_deadline ON opportunities(deadline);
CREATE INDEX IF NOT EXISTS idx_opp_company ON opportunities(company);
CREATE INDEX IF NOT EXISTS idx_opp_mode ON opportunities(mode);

CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
  cover_letter TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'Applied' CHECK (status IN ('Applied','Under Review','Shortlisted','Selected','Rejected')),
  applied_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, opportunity_id)
);
CREATE INDEX IF NOT EXISTS idx_app_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_app_opp ON applications(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status);

CREATE TABLE IF NOT EXISTS application_status_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  old_status TEXT DEFAULT '',
  new_status TEXT NOT NULL,
  changed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
  note TEXT DEFAULT '',
  changed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_hist_app ON application_status_history(application_id);
