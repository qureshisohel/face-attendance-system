# 🎓 Face Attendance System v3
### MCA Final Year Project — Complete & Production-Ready

---

## 🚀 Quick Start

### Step 1 — Install Python dependencies
```bash
# Windows: First install CMake + Visual Studio Build Tools
# Then:
pip install -r requirements.txt
```

### Step 2 — MySQL Setup (MySQL Workbench)
```sql
-- Open schema.sql in MySQL Workbench and Execute All (Ctrl+Shift+Enter)
```

### Step 3 — Configure Database Password
Edit `app.py` line 18:
```python
DB = dict(host='localhost', user='root', password='YOUR_PASSWORD', database='fas_db')
```

### Step 4 — Run
```bash
python app.py
```

Open browser: **http://127.0.0.1:5000**

📱 **Mobile access:** The terminal shows your network IP, e.g. `http://192.168.1.5:5000`
Open this on any phone connected to the same WiFi.

---

## 🔐 Default Login

| Role | Email | Password |
|---|---|---|
| Admin | admin@college.edu | Admin@123 |
| Others | Register via /register | You set it |

**Admin is the only fixed account** — only 1 admin exists. All others register themselves.

---

## 👥 Roles & Permissions

| Feature | Admin | Principal | Faculty | Student |
|---|---|---|---|---|
| Mark student attendance | ✅ | ✅ | ✅ | ❌ |
| Mark **faculty** attendance | ❌ | ✅ | ❌ | ❌ |
| View student records | ✅ | ✅ | Own dept | Own only |
| View faculty records | ✅ | ✅ | ❌ | ❌ |
| Add/Edit/Delete students | ✅ | ❌ | ❌ | ❌ |
| Add/Edit/Delete faculty | ✅ | ❌ | ❌ | ❌ |
| Add/Edit/Delete principals | ✅ | ❌ | ❌ | ❌ |
| Download CSV | ✅ | ✅ | ✅ | ❌ |
| Reports & Charts | ✅ | ✅ | ✅ | ❌ |
| Forgot Password | ✅ | ✅ | ✅ | ✅ |

---

## 📁 Project Structure

```
fas/
├── app.py                          ← Main Flask app (all routes)
├── schema.sql                      ← MySQL database schema
├── requirements.txt                ← Python packages
├── README.md                       ← This file
│
├── static/
│   ├── css/style.css               ← Full mobile-responsive CSS
│   ├── js/cam.js                   ← Fixed camera module
│   └── uploads/
│       ├── faces/                  ← Student face photos
│       └── profiles/               ← Faculty/Principal photos
│
└── templates/
    ├── base.html                   ← Layout with mobile sidebar
    ├── login.html                  ← 4-role login with tabs
    ├── register.html               ← Principal/Faculty/Student register
    ├── forgot.html                 ← Forgot password
    ├── reset.html                  ← Reset password
    ├── dashboard.html              ← Role-aware dashboard
    ├── mark.html                   ← Live camera attendance
    ├── attendance.html             ← Records + CSV download
    ├── students.html               ← Student list with photos
    ├── faculty_list.html           ← Faculty list
    ├── faculty_attendance.html     ← Faculty attendance (principal)
    ├── profile.html                ← Edit profile + photo
    ├── reports.html                ← Charts + analytics
    └── admin/
        ├── students.html           ← Admin: manage all students
        ├── add_student.html        ← Admin: add student + face capture
        ├── edit_student.html       ← Admin: edit student
        ├── faculty.html            ← Admin: manage all faculty
        ├── add_faculty.html        ← Admin: add faculty
        ├── edit_faculty.html       ← Admin: edit faculty
        ├── principals.html         ← Admin: manage principals
        └── add_principal.html      ← Admin: add/edit principal
```

---

## 🗄️ Database Tables

| Table | Purpose |
|---|---|
| `admin` | Single admin account |
| `principal` | Principal accounts |
| `faculty` | Faculty with title (Prof./Dr./Mr./Mrs./Ms.) |
| `students` | Students with face encoding + semester |
| `attendance` | Student attendance records |
| `faculty_attendance` | Faculty attendance (marked by principal) |
| `departments` | 23 departments with semester count |
| `password_resets` | Password reset tokens |

---

## 🎥 How Camera Works

The `cam.js` module uses the **Web API** (`getUserMedia`):

```javascript
// Works on desktop Chrome/Firefox/Edge + mobile Chrome/Safari
navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
```

**Requirements:**
- Browser must allow camera permission
- Run on `localhost` OR HTTPS (browser blocks camera on HTTP for non-localhost)
- For mobile access: run on same WiFi, open `http://192.168.x.x:5000`

**Face Recognition Threshold:** 55% confidence (distance < 0.55)
**Duplicate Prevention:** 2-hour window per person per session

---

## 📊 Departments Included (23)

MCA(8 sem), MBA(4), BCA(6), B.Sc CS(6), B.Sc IT(6), B.Sc Maths(6),
M.Sc CS(4), M.Sc IT(4), B.Com(6), M.Com(4), B.E. CS(8), B.E. IT(8),
M.E. CS(4), BBA(6), B.Sc Physics(6), B.Sc Chemistry(6), B.A.(6),
M.A.(4), LLB(6), LLM(4), MBBS(10), B.Pharm(8), D.Pharm(4)

---

## 🔑 Viva Answers

**Q: What is your project?**
> "Sir/Madam, this is a Face Recognition-based Smart Attendance System. It uses Python Flask for backend, OpenCV and face_recognition library for face detection and identification, and MySQL for database. The system supports four roles — Admin, Principal, Faculty, and Student. Faculty marks student attendance via live webcam, Principal marks faculty attendance, and Admin has full CRUD control over all users."

**Q: How does face recognition work?**
> "When a student registers, we capture 3–5 photos. The face_recognition library converts each face into a 128-dimensional encoding vector. We store the average encoding in MySQL as a binary blob. During attendance, the live camera frame is compared with stored encodings using Euclidean distance. If the distance is below 0.55, attendance is marked."

**Q: What is the database design?**
> "We have 8 tables — admin, principal, faculty, students, attendance, faculty_attendance, departments, and password_resets. Attendance has a foreign key to students, and faculty_attendance has a foreign key to faculty."

---

*MCA Final Year Project | Face Attendance System v3*
