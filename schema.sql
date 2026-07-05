-- ════════════════════════════════════════════════════════
--   Face Attendance System  — Complete Schema
--   Roles: admin(1), professor/dr/sir/madam, student
-- ════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS fas_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fas_db;

-- ── Admin (only one, hardcoded) ───────────────────────
CREATE TABLE IF NOT EXISTS admin (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL DEFAULT 'admin',
    password   VARCHAR(255) NOT NULL,
    email      VARCHAR(150) NOT NULL DEFAULT 'admin@college.edu',
    name       VARCHAR(100) NOT NULL DEFAULT 'Administrator'
);
INSERT IGNORE INTO admin (id,username,password,email,name)
VALUES (1,'admin',MD5('Admin@123'),'admin@college.edu','Administrator');

-- ── Faculty (Professor / Dr / Sir / Madam) ────────────
CREATE TABLE IF NOT EXISTS faculty (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           ENUM('Prof.','Dr.','Mr.','Mrs.','Ms.') NOT NULL DEFAULT 'Prof.',
    name            VARCHAR(100) NOT NULL,
    employee_id     VARCHAR(30)  UNIQUE NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    phone           VARCHAR(15),
    password        VARCHAR(255) NOT NULL,
    dept            VARCHAR(100) NOT NULL,
    photo_path      VARCHAR(255),
    face_encoding   LONGBLOB,
    is_active       TINYINT DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Departments ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS departments (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) UNIQUE NOT NULL,
    degree     VARCHAR(50),
    semesters  INT DEFAULT 6
);

INSERT IGNORE INTO departments (name,degree,semesters) VALUES
  ('MCA','Master of Computer Applications',8),
  ('MBA','Master of Business Administration',4),
  ('BCA','Bachelor of Computer Applications',6),
  ('B.Sc CS','Bachelor of Science (Computer Science)',6),
  ('B.Sc IT','Bachelor of Science (Information Technology)',6),
  ('B.Sc Maths','Bachelor of Science (Mathematics)',6),
  ('M.Sc CS','Master of Science (Computer Science)',4),
  ('M.Sc IT','Master of Science (Information Technology)',4),
  ('B.Com','Bachelor of Commerce',6),
  ('M.Com','Master of Commerce',4),
  ('B.E. CS','Bachelor of Engineering (CS)',8),
  ('B.E. IT','Bachelor of Engineering (IT)',8),
  ('M.E. CS','Master of Engineering (CS)',4),
  ('BBA','Bachelor of Business Administration',6),
  ('B.Sc Physics','Bachelor of Science (Physics)',6),
  ('B.Sc Chemistry','Bachelor of Science (Chemistry)',6),
  ('B.A.','Bachelor of Arts',6),
  ('M.A.','Master of Arts',4),
  ('LLB','Bachelor of Laws',6),
  ('LLM','Master of Laws',4),
  ('MBBS','Bachelor of Medicine',10),
  ('B.Pharm','Bachelor of Pharmacy',8),
  ('D.Pharm','Diploma in Pharmacy',4);

-- ── Students ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    roll_no         VARCHAR(30)  UNIQUE NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    phone           VARCHAR(15),
    password        VARCHAR(255) NOT NULL,
    dept            VARCHAR(100) NOT NULL,
    semester        INT NOT NULL DEFAULT 1,
    photo_path      VARCHAR(255),
    face_encoding   LONGBLOB,
    is_active       TINYINT DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Attendance ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT NOT NULL,
    faculty_id      INT,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('Present','Absent','Late') DEFAULT 'Present',
    confidence      FLOAT,
    semester        INT,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    INDEX idx_faculty   (faculty_id)
);

-- ── Faculty Attendance (admin marks faculty) ──────
CREATE TABLE IF NOT EXISTS faculty_attendance (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id      INT NOT NULL,
    marked_by       INT,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('Present','Absent','Late') DEFAULT 'Present',
    confidence      FLOAT,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
);



-- ── Password Reset Tokens ─────────────────────────────
CREATE TABLE IF NOT EXISTS password_resets (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    email      VARCHAR(150) NOT NULL,
    role       VARCHAR(20)  NOT NULL,
    token      VARCHAR(64)  NOT NULL,
    expires_at DATETIME     NOT NULL,
    used       TINYINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token (token),
    INDEX idx_email (email)
);

-- ── Useful views ──────────────────────────────────────
CREATE OR REPLACE VIEW v_today_attendance AS
SELECT s.name, s.roll_no, s.dept, s.semester, s.photo_path,
       a.timestamp, a.status, a.confidence, a.faculty_id
FROM attendance a JOIN students s ON a.student_id=s.id
WHERE DATE(a.timestamp)=CURDATE();

CREATE OR REPLACE VIEW v_student_summary AS
SELECT s.id, s.name, s.roll_no, s.dept, s.semester,
       COUNT(a.id) AS total_days, MAX(a.timestamp) AS last_seen
FROM students s LEFT JOIN attendance a ON s.id=a.student_id
GROUP BY s.id;



SELECT * FROM admin;
SELECT * FROM  faculty;
SELECT * FROM attendance;
SELECT * FROM  departments;
SELECT * FROM faculty_attendance;