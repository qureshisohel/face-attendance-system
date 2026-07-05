from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
    Response,
    send_file,
)
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import cv2, numpy as np, face_recognition, base64, os, pickle, csv, io
import random, string, hashlib
from datetime import datetime, timedelta
from functools import wraps
import socket
import time
import cv2

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

# print(generate_password_hash("abcd1234"))
# LOAD ENV FILE
load_dotenv()

# FLASK APP
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

app.permanent_session_lifetime = timedelta(hours=2)

# DATABASE CONFIG
DB = dict(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
)


@app.context_processor
def inject_globals():
    from flask import request as req

    return dict(req=req.endpoint or "", session=session)


def db():
    try:
        return mysql.connector.connect(**DB)
    except Error as e:
        print(f"DB Error: {e}")
        return None


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


# ── Auth helpers ──────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if "uid" not in session:
            # flash('Please login.','warning');
            flash("Session expired. Please login again.", "warning")
            return redirect(url_for("login"))
        return f(*a, **kw)

    return dec


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def dec(*a, **kw):
            if session.get("role") not in roles:
                # flash('Access denied.','danger');
                flash(
                    "Access denied. You do not have permission to access this page.",
                    "danger",
                )
                return redirect(url_for("dashboard"))
            return f(*a, **kw)

        return dec

    return decorator


def save_photo(b64_str, folder, filename):
    """Decode base64 image and save. Returns relative path."""
    try:
        data = base64.b64decode(b64_str.split(",")[1])
        arr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)   
        path = f"uploads/{folder}/{filename}"
        os.makedirs(f"static/uploads/{folder}", exist_ok=True)
        cv2.imwrite(f"static/{path}", frame)
        return path
    except Exception as e:
        print(f"Photo save error: {e}")
        return None


def encode_faces(images_b64):
    """Return averaged face encoding from list of base64 images, or None."""
    encodings = []
    for b64 in images_b64:
        try:
            data = base64.b64decode(b64.split(",")[1])
            arr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR) 
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb, model="hog")
            encs = face_recognition.face_encodings(rgb, locs)
            if encs:
                encodings.append(encs[0])
        except Exception as e:
            print(f"Encoding error: {e}")
    if not encodings:
        return None
    return pickle.dumps(np.mean(encodings, axis=0))


def gen_token(n=32):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def gen_otp():
    return str(random.randint(100000, 999999))


def get_depts():
    c = db()
    if not c:
        return []
    cur = c.cursor(dictionary=True)
    cur.execute("SELECT * FROM departments ORDER BY name")
    rows = cur.fetchall()
    c.close()
    return rows


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/")
def index():
    return redirect(url_for("dashboard") if "uid" in session else url_for("login"))


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]

        c = db()

        if not c:
            flash("Database connection error.", "danger")
            return redirect(url_for("login"))

        cur = c.cursor(dictionary=True)

        # ADMIN LOGIN
        if role == "admin":

            cur.execute("SELECT * FROM admin WHERE email=%s", (email,))

            user = cur.fetchone()

            if user and check_password_hash(user["password"], password):

                session.update(
                    {
                        "uid": user["id"],
                        "role": "admin",
                        "name": user["name"],
                        "photo": user.get("photo_path", ""),
                    }
                )

                flash("Admin login successful.", "success")
                return redirect(url_for("dashboard"))

        # FACULTY LOGIN
        elif role == "faculty":

            cur.execute(
                "SELECT * FROM faculty WHERE email=%s AND is_active=1", (email,)
            )

            user = cur.fetchone()

            if user and check_password_hash(user["password"], password):

                session.update(
                    {
                        "uid": user["id"],
                        "role": "faculty",
                        "name": user["name"],
                        "photo": user["photo_path"],
                        "dept": user["dept"],
                    }
                )

                flash("Faculty login successful.", "success")
                return redirect(url_for("dashboard"))

        # STUDENT LOGIN
        elif role == "student":

            cur.execute(
                "SELECT * FROM students WHERE email=%s AND is_active=1", (email,)
            )

            user = cur.fetchone()

            if user and check_password_hash(user["password"], password):

                session.update(
                    {
                        "uid": user["id"],
                        "role": "student",
                        "name": user["name"],
                        "photo": user["photo_path"],
                        "dept": user["dept"],
                        # "sid": user["roll_no"],
                        "semester": user["semester"],
                    }
                )

                flash("Login successful.", "success")
                return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/switch")
def switch():
    session.clear()
    flash("Login with a different account.", "info")
    return redirect(url_for("login"))


# ── REGISTER ──────────────────────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    depts = get_depts()
    if request.method == "POST":
        role = request.form.get("role", "student")
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form.get("phone", "")
        passwd = request.form["password"]
        dept = request.form.get("dept", "")

        c = db()
        if not c:
            flash("DB error.", "danger")
            return redirect(url_for("register"))
        cur = c.cursor()

        try:
            if role == "faculty":
                title = request.form.get("title", "Prof.")
                emp_id = request.form.get("employee_id", "").strip()
                photo_b64 = request.form.get("profile_image", "")
                photo = (
                    save_photo(
                        photo_b64,
                        "profiles",
                        f"F_{emp_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
                    )
                    if photo_b64
                    else None
                )
                face_images = request.form.getlist("face_images[]")
                # face_blob = encode_faces(face_images)
                if len(face_images) < 3:
                    flash("Capture at least 3 face images", "warning")
                    return redirect(url_for("register"))

                face_blob = encode_faces(face_images)

                if not face_blob:
                    flash("Face not detected properly", "danger")
                    return redirect(url_for("register"))
                hashed_pw = generate_password_hash(passwd)

                cur.execute(
                    """
                INSERT INTO faculty
                (title,name,employee_id,email,phone,password,dept,photo_path,face_encoding)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                    (
                        title,
                        name,
                        emp_id,
                        email,
                        phone,
                        hashed_pw,
                        dept,
                        photo,
                        face_blob,
                    ),
                )

            elif role == "student":
                roll_no = request.form.get("roll_no", "").strip()
                semester_val = request.form.get("semester")
                
                if not semester_val:
                    flash("Please select a semester.", "warning")
                    c.close()
                    return redirect(url_for("register"))
                
                semester = int(semester_val)
                
                # ✅ DUPLICATE CHECK - ROLL NUMBER
                cur.execute("SELECT id FROM students WHERE roll_no = %s", (roll_no,))
                existing_roll = cur.fetchone()
                if existing_roll:
                    c.close()
                    flash(f"Roll number '{roll_no}' is already registered! Please use a unique roll number.", "danger")
                    return redirect(url_for("register"))
                
                # ✅ DUPLICATE CHECK - EMAIL
                cur.execute("SELECT id FROM students WHERE email = %s", (email,))
                existing_email = cur.fetchone()
                if existing_email:
                    c.close()
                    flash(f"Email '{email}' is already registered! Please use a different email.", "danger")
                    return redirect(url_for("register"))
                
                images = request.form.getlist("face_images[]")
                face_blob = encode_faces(images) if images else None
                photo = None
                if images:
                    photo = save_photo(
                        images[0],
                        "faces",
                        f"S_{roll_no}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
                    )
                if not face_blob:
                    flash("No face detected. Please capture face photos.", "danger")
                    flash("Face not detected. Please capture 3 to 5 clear face images.", "warning")
                    c.close()
                    return redirect(url_for("register"))
                hashed_pw = generate_password_hash(passwd)
                
                cur.execute(
                    """
                INSERT INTO students
                (name,roll_no,email,phone,password,dept,semester,photo_path,face_encoding)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                    (name, roll_no, email, phone, hashed_pw, dept, semester, photo, face_blob),
                )

            c.commit()
            c.close()
            flash("Account created successfully! You can now log in.", "success")
            return redirect(url_for("login"))
        except Error as e:
            c.close()
            if "Duplicate" in str(e):
                # flash('Email or ID already registered.','danger')
                flash("Email address or ID is already registered.", "danger")
            else:
                flash(f"Error: {e}", "danger")

    return render_template("register.html", depts=depts)


# ── FORGOT PASSWORD ───────────────────────────────────────────────────────────
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        role = request.form["role"]
        c = db()
        if not c:
            flash("DB error", "danger")
            return redirect(url_for("forgot"))
        cur = c.cursor(dictionary=True)

        found = False
        tables = {"admin": "admin", "faculty": "faculty", "student": "students"}
        tbl = tables.get(role, "students")
        cur.execute(f"SELECT id,email FROM `{tbl}` WHERE email=%s", (email,))
        user = cur.fetchone()

        if user:
            token = gen_token()
            expiry = datetime.now() + timedelta(hours=1)
            cur2 = c.cursor()
            cur2.execute(
                "DELETE FROM password_resets WHERE email=%s AND role=%s", (email, role)
            )
            cur2.execute(
                "INSERT INTO password_resets (email,role,token,expires_at) VALUES(%s,%s,%s,%s)",
                (email, role, token, expiry),
            )
            c.commit()
            # In production, email the token. For demo, show it.
            flash(f'Reset token (share via email in production): {token}','info')
            # 
        # flash("Password reset token generated successfully.", "info")
            found = True
        c.close()
        if not found:
            flash("Account not found. Please verify your email address.", "danger")
        # flash('Email not found for this role.','danger')
    return render_template("forgot.html")


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    c = db()
    if not c:
        flash("DB error", "danger")
        return redirect(url_for("login"))
    cur = c.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM password_resets WHERE token=%s AND used=0 AND expires_at>NOW()",
        (token,),
    )
    rec = cur.fetchone()
    if not rec:
        c.close()
        flash("Invalid or expired token.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        new_pw = request.form["password"]
        confirm = request.form["confirm"]
        if new_pw != confirm:
            flash(
                "Passwords do not match. Please enter the same password in both fields.",
                "warning",
            )
            return render_template("reset.html", token=token)
        # flash('Passwords do not match.','danger');
        tables = {"admin": "admin", "faculty": "faculty", "student": "students"}
        tbl = tables.get(rec["role"], "students")
        cur2 = c.cursor()
        hashed_pw = generate_password_hash(new_pw)

        cur2.execute(
            f"UPDATE `{tbl}` SET password=%s WHERE email=%s", (hashed_pw, rec["email"])
        )
        cur2.execute("UPDATE password_resets SET used=1 WHERE token=%s", (token,))
        c.commit()
        c.close()
        # flash('Password reset successful! Please login.','success')
        flash(
            "Password reset successfully. Please login with your new password.",
            "success",
        )
        return redirect(url_for("login"))
    c.close()
    return render_template(
        "reset.html", token=token, role=rec["role"], email=rec["email"]
    )


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/dashboard")
@login_required
def dashboard():
    c = db()
    role = session["role"]
    data = {}
    if c:
        cur = c.cursor(dictionary=True)
        
        if role == "admin":
            cur.execute("SELECT COUNT(*) AS n FROM students WHERE is_active=1")
            data["students"] = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM faculty WHERE is_active=1")
            data["faculty"] = cur.fetchone()["n"]
            cur.execute(
                "SELECT COUNT(DISTINCT student_id) AS n FROM attendance WHERE DATE(timestamp)=CURDATE()"
            )
            data["today"] = cur.fetchone()["n"]
            cur.execute(
                """SELECT s.name,s.roll_no,s.dept,s.semester,s.photo_path,a.timestamp,a.confidence
                   FROM attendance a JOIN students s ON a.student_id=s.id
                   ORDER BY a.timestamp DESC LIMIT 10"""
            )
            data["recent"] = cur.fetchall()
            
        elif role == "faculty":
            faculty_dept = session.get('dept', '')
            
            # ✅ Total students in faculty's department
            cur.execute(
                "SELECT COUNT(*) AS n FROM students WHERE dept=%s AND is_active=1",
                (faculty_dept,)
            )
            result = cur.fetchone()
            data["students"] = result["n"] if result else 0
            
            # ✅ Today's attendance in faculty's department
            cur.execute(
                """SELECT COUNT(DISTINCT a.student_id) AS n 
                   FROM attendance a 
                   JOIN students s ON a.student_id = s.id 
                   WHERE s.dept = %s AND DATE(a.timestamp) = CURDATE()""",
                (faculty_dept,)
            )
            result = cur.fetchone()
            data["today"] = result["n"] if result else 0
            
            # ✅ Recent attendance records
            cur.execute(
                """SELECT s.name, s.roll_no, s.photo_path, a.timestamp, a.confidence
                   FROM attendance a 
                   JOIN students s ON a.student_id = s.id 
                   WHERE s.dept = %s 
                   ORDER BY a.timestamp DESC 
                   LIMIT 8""",
                (faculty_dept,)
            )
            data["recent"] = cur.fetchall()
            
        elif role == "student":
            cur.execute(
                "SELECT COUNT(*) AS n FROM attendance WHERE student_id=%s",
                (session["uid"],)
            )
            data["days"] = cur.fetchone()["n"]
            cur.execute(
                "SELECT COUNT(*) AS n FROM attendance WHERE student_id=%s AND DATE(timestamp)=CURDATE()",
                (session["uid"],)
            )
            data["today"] = cur.fetchone()["n"]
            cur.execute("SELECT * FROM students WHERE id=%s", (session["uid"],))
            data["profile"] = cur.fetchone()
            cur.execute(
                "SELECT timestamp,status,confidence FROM attendance WHERE student_id=%s ORDER BY timestamp DESC LIMIT 8",
                (session["uid"],)
            )
            data["recent"] = cur.fetchall()
            
        c.close()
        
    return render_template("dashboard.html", data=data, lip=local_ip())


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN CRUD
# ══════════════════════════════════════════════════════════════════════════════


# ── Admin: All Students ───────────────────────────────
@app.route("/admin/students")
@login_required
@role_required("admin")
def admin_students():
    c = db()
    rows = []
    if c:
        cur = c.cursor(dictionary=True)
        dept = request.args.get("dept", "")
        sem = request.args.get("sem", "")
        q = "SELECT * FROM students WHERE 1=1"
        params = []
        if dept:
            q += " AND dept=%s"
            params.append(dept)
        if sem:
            q += " AND semester=%s"
            params.append(sem)
        q += " ORDER BY dept,semester,name"
        cur.execute(q, params)
        rows = cur.fetchall()
        cur.execute("SELECT DISTINCT dept FROM students ORDER BY dept")
        depts = [r["dept"] for r in cur.fetchall()]
        c.close()
    return render_template(
        "admin/students.html", students=rows, depts=depts, sel_dept=dept, sel_sem=sem
    )


@app.route("/admin/students/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_add_student():
    depts = get_depts()
    if request.method == "POST":
        name = request.form["name"]
        roll = request.form["roll_no"]
        email = request.form["email"]
        phone = request.form.get("phone", "")
        passwd = request.form["password"]
        dept = request.form["dept"]
        sem = int(request.form["semester"])
        images = request.form.getlist("face_images[]")
        face_blob = encode_faces(images) if images else None
        photo = None
        if images:
            photo = save_photo(
                images[0],
                "faces",
                f"S_{roll}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
            )
        if not face_blob:
            flash("No face detected. Capture at least 1 photo.", "danger")
            return render_template("admin/add_student.html", depts=depts)
        
        c = db()
        if c:
            cur = c.cursor(dictionary=True)
            
            # ✅ DUPLICATE CHECK - ROLL NUMBER
            cur.execute("SELECT id FROM students WHERE roll_no = %s", (roll,))
            existing_roll = cur.fetchone()
            if existing_roll:
                cur.close()
                c.close()
                flash(f"Roll number '{roll}' already exists! Please use a unique roll number.", "danger")
                return render_template("admin/add_student.html", depts=depts)
            
            # ✅ DUPLICATE CHECK - EMAIL
            cur.execute("SELECT id FROM students WHERE email = %s", (email,))
            existing_email = cur.fetchone()
            if existing_email:
                cur.close()
                c.close()
                flash(f"Email '{email}' is already registered! Please use a different email.", "danger")
                return render_template("admin/add_student.html", depts=depts)
            
            try:
                hashed_pw = generate_password_hash(passwd)
                cur.execute(
                    "INSERT INTO students (name,roll_no,email,phone,password,dept,semester,photo_path,face_encoding) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (name, roll, email, phone, hashed_pw, dept, sem, photo, face_blob),
                )
                c.commit()
                c.close()
                flash("Student added successfully.", "success")
                return redirect(url_for("admin_students"))
            except Error as e:
                c.close()
                flash(f"Database error: {e}", "danger")
    
    return render_template("admin/add_student.html", depts=depts)


@app.route("/admin/students/edit/<int:sid>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_edit_student(sid):
    depts = get_depts()
    c = db()
    if not c:
        flash("DB error", "danger")
        return redirect(url_for("admin_students"))
    cur = c.cursor(dictionary=True)
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form.get("phone", "")
        dept = request.form["dept"]
        sem = int(request.form["semester"])
        active = int(request.form.get("is_active", 1))
        passwd = request.form.get("new_password", "")
        images = request.form.getlist("face_images[]")
        cur2 = c.cursor()
        if passwd:
            hashed_pw = generate_password_hash(passwd)

            cur2.execute(
                """
            UPDATE students
            SET name=%s,email=%s,phone=%s,
            dept=%s,semester=%s,
            is_active=%s,password=%s
            WHERE id=%s
            """,
                (name, email, phone, dept, sem, active, hashed_pw, sid),
            )
        else:
            cur2.execute(
                "UPDATE students SET name=%s,email=%s,phone=%s,dept=%s,semester=%s,is_active=%s WHERE id=%s",
                (name, email, phone, dept, sem, active, sid),
            )
        if images:
            face_blob = encode_faces(images)
            photo = save_photo(
                images[0],
                "faces",
                f"S_{sid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
            )
            if face_blob:
                cur2.execute(
                    "UPDATE students SET face_encoding=%s,photo_path=%s WHERE id=%s",
                    (face_blob, photo, sid),
                )
        c.commit()
        c.close()
        flash("Student information updated successfully.", "success")
        return redirect(url_for("admin_students"))
        # flash('Student updated!','success');
    cur.execute("SELECT * FROM students WHERE id=%s", (sid,))
    s = cur.fetchone()
    c.close()
    return render_template("admin/edit_student.html", s=s, depts=depts)


@app.route("/admin/students/delete/<int:sid>", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_student(sid):
    c = db()
    if c:
        cur = c.cursor(dictionary=True)
        cur.execute("SELECT photo_path FROM students WHERE id=%s", (sid,))
        r = cur.fetchone()
        if r and r["photo_path"]:
            try:
                os.remove(f"static/{r['photo_path']}")
            except:
                pass
        cur2 = c.cursor()
        cur2.execute("DELETE FROM students WHERE id=%s", (sid,))
        c.commit()
        c.close()
        # flash('Student deleted.','success')
        flash("Student record deleted successfully.", "success")
    return redirect(url_for("admin_students"))


# ── Admin: All Faculty ────────────────────────────────
@app.route("/admin/faculty")
@login_required
@role_required("admin")
def admin_faculty():
    c = db()
    rows = []
    if c:
        cur = c.cursor(dictionary=True)
        cur.execute("SELECT * FROM faculty ORDER BY dept,name")
        rows = cur.fetchall()
        c.close()
    return render_template("admin/faculty.html", faculty=rows)


@app.route("/admin/faculty/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_add_faculty():
    depts = get_depts()
    if request.method == "POST":
        title = request.form["title"]
        name = request.form["name"]
        emp = request.form["employee_id"]
        email = request.form["email"]
        phone = request.form.get("phone", "")
        passwd = request.form["password"]
        dept = request.form["dept"]
        photo_b64 = request.form.get("profile_image", "")
        
        # ✅ Face images optional - agar hain toh process karo
        face_images = request.form.getlist("face_images[]")
        
        # ✅ YEH CHANGE - Optional banaya
        face_blob = None
        if len(face_images) > 0:
            if len(face_images) < 3:
                flash("For face recognition, capture at least 3 face images (optional, can skip)", "warning")
                return render_template("admin/add_faculty.html", depts=depts)
            
            face_blob = encode_faces(face_images)
            if not face_blob:
                flash("Face not detected properly. Face recognition will not work.", "warning")
        
        # ✅ Photo save karo
        photo = (
            save_photo(
                photo_b64,
                "profiles",
                f"F_{emp}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
            )
            if photo_b64
            else None
        )
        
        c = db()
        if c:
            try:
                cur = c.cursor()
                hashed_pw = generate_password_hash(passwd)
                
                # ✅ INSERT - face_encoding NULL ho sakta hai ab
                cur.execute("""
                    INSERT INTO faculty
                    (title, name, employee_id, email, phone, password, dept, photo_path, face_encoding)
                    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (title, name, emp, email, phone, hashed_pw, dept, photo, face_blob))
                
                c.commit()
                c.close()
                flash("Faculty added successfully.", "success")
                return redirect(url_for("admin_faculty"))
            except Error as e:
                c.close()
                flash(f"Error: {e}", "danger")
    
    return render_template("admin/add_faculty.html", depts=depts)


@app.route("/admin/faculty/edit/<int:fid>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_edit_faculty(fid):
    depts = get_depts()
    c = db()
    if not c:
        return redirect(url_for("admin_faculty"))
    cur = c.cursor(dictionary=True)
    if request.method == "POST":
        title = request.form["title"]
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form.get("phone", "")
        dept = request.form["dept"]
        active = int(request.form.get("is_active", 1))
        passwd = request.form.get("new_password", "")
        photo_b64 = request.form.get("profile_image", "")
        cur2 = c.cursor()
        if passwd:
            hashed_pw = generate_password_hash(passwd)

            cur2.execute(
                """
                UPDATE faculty
                SET title=%s,
                   name=%s,
                    email=%s,
                    phone=%s,
                    dept=%s,
                    is_active=%s,
                    password=%s
                WHERE id=%s
            """,
                (title, name, email, phone, dept, active, hashed_pw, fid),
            )

        else:
            cur2.execute(
                """
                UPDATE faculty
                SET title=%s,
                    name=%s,
                    email=%s,
                    phone=%s,
                    dept=%s,
                    is_active=%s
                WHERE id=%s
            """,
                (title, name, email, phone, dept, active, fid),
            )
        if photo_b64:
            photo = save_photo(
                photo_b64,
                "profiles",
                f"F_{fid}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
            )
            if photo:
                cur2.execute(
                    "UPDATE faculty SET photo_path=%s WHERE id=%s", (photo, fid)
                )   
        c.commit()
        c.close()
        flash("Faculty information updated successfully.", "success")
        return redirect(url_for("admin_faculty"))
    # flash('Faculty updated!','success');
    cur.execute("SELECT * FROM faculty WHERE id=%s", (fid,))
    f = cur.fetchone()
    c.close()
    return render_template("admin/edit_faculty.html", f=f, depts=depts)


@app.route("/admin/faculty/delete/<int:fid>", methods=["POST"])
@login_required
@role_required("admin")
def admin_delete_faculty(fid):
    c = db()
    if c:
        cur = c.cursor(dictionary=True)
        cur.execute("SELECT photo_path FROM faculty WHERE id=%s", (fid,))
        r = cur.fetchone()
        if r and r["photo_path"]:
            try:
                os.remove(f"static/{r['photo_path']}")
            except:
                pass
        cur2 = c.cursor()
        cur2.execute("DELETE FROM faculty WHERE id=%s", (fid,))
        c.commit()
        c.close()
        # flash('Faculty deleted.','success')
        flash("Faculty record deleted successfully.", "success")
    return redirect(url_for("admin_faculty"))


# ══════════════════════════════════════════════════════════════════════════════
#  MARK ATTENDANCE
# ══════════════════════════════════════════════════════════════════════════════


@app.route("/mark")
@login_required
@role_required("admin", "faculty")
def mark():
    return render_template("mark.html")


@app.route("/api/recognize", methods=["POST"])
@login_required
def recognize():
    d = request.get_json()
    img_b64 = d.get("image", "")
    try:
        data = base64.b64decode(img_b64.split(",")[1])
        arr = np.frombuffer(data, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # ✅ FAST - only HOG model (no CNN)
        locs = face_recognition.face_locations(rgb, model="hog")
        encs = face_recognition.face_encodings(rgb, locs)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    if not encs:
        return jsonify({"status": "no_face"})

    role = session["role"]
    c = db()
    if not c:
        return jsonify({"status": "error", "message": "DB error"})
    cur = c.cursor(dictionary=True)

    results = []

    if role in ("faculty", "admin"):
        if role == "faculty":
            cur.execute(
                "SELECT id,name,roll_no,dept,semester,photo_path,face_encoding FROM students WHERE dept=%s AND is_active=1 AND face_encoding IS NOT NULL",
                (session["dept"],),
            )
        else:
            cur.execute(
                "SELECT id,name,roll_no,dept,semester,photo_path,face_encoding FROM students WHERE is_active=1 AND face_encoding IS NOT NULL"
            )
        known = cur.fetchall()

        for enc in encs:
            best = None
            best_d = 0.45
            for s in known:
                try:
                    ke = pickle.loads(s["face_encoding"])
                    dist = face_recognition.face_distance([ke], enc)[0]
                    if dist < best_d:
                        best_d = dist
                        best = s
                except:
                    continue
            if best:
                conf = round((1 - best_d) * 100, 1)
                cur.execute(
                    "SELECT id FROM attendance WHERE student_id=%s AND DATE(timestamp)=CURDATE()",
                    (best["id"],),
                )
                already = cur.fetchone()
                if not already:
                    cur2 = c.cursor()
                    cur2.execute(
                        "INSERT INTO attendance (student_id,faculty_id,status,confidence,semester) VALUES(%s,%s,'Present',%s,%s)",
                        (
                            best["id"],
                            session["uid"] if role == "faculty" else None,
                            conf,
                            best["semester"],
                        ),
                    )
                    c.commit()
                    results.append(
                        {
                            "status": "marked",
                            "name": best["name"],
                            "roll_no": best["roll_no"],
                            "dept": best["dept"],
                            "sem": best["semester"],
                            "confidence": conf,
                            "photo": best["photo_path"] or "",
                        }
                    )
                else:
                    results.append(
                        {
                            "status": "already",
                            "name": best["name"],
                            "roll_no": best["roll_no"],
                            "dept": best["dept"],
                            "sem": best["semester"],
                            "confidence": conf,
                            "photo": best["photo_path"] or "",
                        }
                    )
            else:
                results.append({"status": "unknown"})

    c.close()
    return jsonify({"status": "ok", "results": results})


@app.route("/api/check_roll")
@login_required
def check_roll():
    roll = request.args.get("roll", "")
    if not roll:
        return jsonify({"exists": False})
    
    c = db()
    if not c:
        return jsonify({"exists": False})
    
    cur = c.cursor(dictionary=True)
    cur.execute("SELECT id FROM students WHERE roll_no = %s", (roll,))
    exists = cur.fetchone() is not None
    c.close()
    
    return jsonify({"exists": exists})

def mark_absent_students():
    c = db()
    if not c:
        return

    cur = c.cursor()

    cur.execute("""
        INSERT INTO attendance
        (student_id, status, semester)
        SELECT
            s.id,
            'Absent',
            s.semester
        FROM students s
        WHERE s.is_active = 1
        AND s.id NOT IN (
            SELECT student_id
            FROM attendance
            WHERE DATE(timestamp) = CURDATE()
        )
    """)

    c.commit()
    c.close()

@app.route("/attendance")
@login_required
def attendance():
    c = db()
    records = []
    depts = []
    date_f = request.args.get("date", "")
    dept_f = request.args.get("dept", "")
    sem_f = request.args.get("sem", "")
    if c:
        cur = c.cursor(dictionary=True)
        role = session["role"]
        if role == "admin":
            q = """SELECT s.name,s.roll_no,s.dept,s.semester,s.photo_path,
                        a.timestamp,a.status,a.confidence,a.id
                 FROM attendance a JOIN students s ON a.student_id=s.id WHERE 1=1"""
            params = []
            if date_f:
                q += " AND DATE(a.timestamp)=%s"
                params.append(date_f)
            if dept_f:
                q += " AND s.dept=%s"
                params.append(dept_f)
            if sem_f:
                q += " AND s.semester=%s"
                params.append(sem_f)
            q += " ORDER BY a.timestamp DESC"
            cur.execute(q, params)
            records = cur.fetchall()
        elif role == "faculty":
            # ✅ FIXED: Faculty ko unke department ke SARE students dikhenge (faculty_id NULL wale bhi)
            faculty_dept = session.get('dept', '')
            
            q = """SELECT s.name,s.roll_no,s.dept,s.semester,s.photo_path,
                        a.timestamp,a.status,a.confidence,a.id
                 FROM attendance a 
                 JOIN students s ON a.student_id = s.id
                 WHERE s.dept = %s"""
            params = [faculty_dept]
            if date_f:
                q += " AND DATE(a.timestamp)=%s"
                params.append(date_f)
            if sem_f:
                q += " AND s.semester=%s"
                params.append(sem_f)
            q += " ORDER BY a.timestamp DESC"
            cur.execute(q, params)
            records = cur.fetchall()
        elif role == "student":
            q = "SELECT a.timestamp,a.status,a.confidence FROM attendance a WHERE a.student_id=%s"
            params = [session["uid"]]
            if date_f:
                q += " AND DATE(a.timestamp)=%s"
                params.append(date_f)
            q += " ORDER BY a.timestamp DESC"
            cur.execute(q, params)
            records = cur.fetchall()
        cur.execute("SELECT DISTINCT dept FROM students ORDER BY dept")
        depts = [r["dept"] for r in cur.fetchall()]
        c.close()
    return render_template(
        "attendance.html",
        records=records,
        depts=depts,
        date_f=date_f,
        dept_f=dept_f,
        sem_f=sem_f,
    )


@app.route("/attendance/csv")
@login_required
def download_csv():
    c = db()
    role = session["role"]
    date_f = request.args.get("date", "")
    dept_f = request.args.get("dept", "")
    sem_f = request.args.get("sem", "")
    who = request.args.get("who", "student")  # student or faculty
    if not c:
        flash("DB error", "danger")
        return redirect(url_for("attendance"))
    cur = c.cursor(dictionary=True)

    if who == "faculty" and role == "admin":
        cur.execute(
            """SELECT f.title,f.name,f.employee_id,f.dept,fa.timestamp,fa.status,fa.confidence
                       FROM faculty_attendance fa JOIN faculty f ON fa.faculty_id=f.id
                       ORDER BY fa.timestamp DESC"""
        )
        rows = cur.fetchall()
        fieldnames = [
            "title",
            "name",
            "employee_id",
            "dept",
            "timestamp",
            "status",
            "confidence",
        ]
        fname = "faculty_attendance.csv"
    else:
        q = """SELECT s.name,s.roll_no,s.dept,s.semester,a.timestamp,a.status,a.confidence
             FROM attendance a JOIN students s ON a.student_id=s.id WHERE 1=1"""
        params = []
        if role == "faculty":
            q += " AND a.faculty_id=%s"
            params.append(session["uid"])
        if date_f:
            q += " AND DATE(a.timestamp)=%s"
            params.append(date_f)
        if dept_f:
            q += " AND s.dept=%s"
            params.append(dept_f)
        if sem_f:
            q += " AND s.semester=%s"
            params.append(sem_f)
        q += " ORDER BY a.timestamp DESC"
        cur.execute(q, params)
        rows = cur.fetchall()
        fieldnames = [
            "name",
            "roll_no",
            "dept",
            "semester",
            "timestamp",
            "status",
            "confidence",
        ]
        fname = "student_attendance.csv"

    c.close()
    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    output = io.BytesIO()
    output.write(si.getvalue().encode("utf-8"))
    output.seek(0)
    return send_file(
        output, mimetype="text/csv", as_attachment=True, download_name=fname
    )


@app.route("/faculty_attendance")
@login_required
@role_required("admin")
def faculty_attendance():
    c = db()
    records = []
    date_f = request.args.get("date", "")
    if c:
        cur = c.cursor(dictionary=True)
        q = """SELECT f.title,f.name,f.employee_id,f.dept,f.photo_path,
                    fa.timestamp,fa.status,fa.confidence,fa.id
             FROM faculty_attendance fa JOIN faculty f ON fa.faculty_id=f.id WHERE 1=1"""
        params = []
        if date_f:
            q += " AND DATE(fa.timestamp)=%s"
            params.append(date_f)
        q += " ORDER BY fa.timestamp DESC"
        cur.execute(q, params)
        records = cur.fetchall()
        c.close()
    return render_template("faculty_attendance.html", records=records, date_f=date_f)


# ── Students list (faculty) ────────────────
@app.route("/students")
@login_required
@role_required("admin", "faculty")
def students():
    c = db()
    rows = []
    if c:
        cur = c.cursor(dictionary=True)
        if session["role"] == "faculty":
            cur.execute(
                "SELECT * FROM students WHERE dept=%s AND is_active=1 ORDER BY semester,name",
                (session["dept"],),
            )
        else:
            cur.execute(
                "SELECT * FROM students WHERE is_active=1 ORDER BY dept,semester,name"
            )
        rows = cur.fetchall()
        c.close()
    return render_template("students.html", students=rows)


# ── Faculty list ──────────────────────────────────────
@app.route("/faculty")
@login_required
@role_required("admin")
def faculty_list():
    c = db()
    rows = []
    if c:
        cur = c.cursor(dictionary=True)
        cur.execute("SELECT * FROM faculty WHERE is_active=1 ORDER BY dept,name")
        rows = cur.fetchall()
        c.close()
    return render_template("faculty_list.html", faculty=rows)


# ── Profile ───────────────────────────────────────────
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    c = db()
    if request.method == "POST" and c:
        name = request.form["name"]
        phone = request.form.get("phone", "")
        photo_b64 = request.form.get("profile_image", "")
        role = session["role"]
        tbl = {"admin": "admin", "faculty": "faculty", "student": "students"}[role]
        cur = c.cursor()
        if photo_b64:
            folder = "faces" if role == "student" else "profiles"
            photo = save_photo(
                photo_b64,
                folder,
                f"PF_{session['uid']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
            )
            if photo:
                cur.execute(
                    f"UPDATE `{tbl}` SET name=%s,phone=%s,photo_path=%s WHERE id=%s",
                    (name, phone, photo, session["uid"]),
                )
                session["photo"] = photo
            else:
                cur.execute(
                    f"UPDATE `{tbl}` SET name=%s,phone=%s WHERE id=%s",
                    (name, phone, session["uid"]),
                )
        else:
            cur.execute(
                f"UPDATE `{tbl}` SET name=%s,phone=%s WHERE id=%s",
                (name, phone, session["uid"]),
            )
        c.commit()
        c.close()
        session["name"] = name
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))
        # flash('Profile updated!','success');
    user = None
    if c:
        cur = c.cursor(dictionary=True)
        tbl = {"admin": "admin", "faculty": "faculty", "student": "students"}[
            session["role"]
        ]
        cur.execute(f"SELECT * FROM `{tbl}` WHERE id=%s", (session["uid"],))
        user = cur.fetchone()
        c.close()
    return render_template("profile.html", user=user)


# ── Reports ───────────────────────────────────────────
@app.route("/reports")
@login_required
@role_required("admin", "faculty")
def reports():
    
    c = db()
    data = {}
    
    # Initialize summary values
    data["total_students"] = 0
    data["total_present"] = 0
    data["total_absent"] = 0
    
    if c:
        cur = c.cursor(dictionary=True)
        role = session["role"]
        
        total_working_days = 52
        
        if role == "admin":
            # Admin: Total students count
            cur.execute("SELECT COUNT(*) as total FROM students WHERE is_active=1")
            data["total_students"] = cur.fetchone()['total'] or 0
            
            # Admin: Total presents and absents
            cur.execute("""
                SELECT 
                    COUNT(CASE WHEN status='Present' THEN 1 END) as total_present,
                    COUNT(CASE WHEN status='Absent' THEN 1 END) as total_absent
                FROM attendance
            """)
            summary = cur.fetchone()
            data["total_present"] = summary['total_present'] or 0
            data["total_absent"] = summary['total_absent'] or 0
            
            # Trend data
            cur.execute("""
                SELECT DATE(timestamp) as day, 
                    COUNT(CASE WHEN status='Present' THEN 1 END) as present,
                    COUNT(CASE WHEN status='Absent' THEN 1 END) as absent
                FROM attendance 
                WHERE timestamp >= NOW() - INTERVAL 30 DAY 
                GROUP BY DATE(timestamp) 
                ORDER BY day
            """)
            data["trend"] = cur.fetchall()
            
            # Today's department stats
            cur.execute("""
                SELECT s.dept,
                    COUNT(CASE WHEN a.status='Present' THEN 1 END) as present,
                    COUNT(CASE WHEN a.status='Absent' THEN 1 END) as absent
                FROM attendance a 
                JOIN students s ON a.student_id=s.id 
                WHERE DATE(a.timestamp)=CURDATE() 
                GROUP BY s.dept
            """)
            data["dept_today"] = cur.fetchall()
            
            # Top students
            cur.execute("""
                SELECT s.id, s.name, s.roll_no, s.dept, s.photo_path,
                    COUNT(CASE WHEN a.status='Present' THEN 1 END) as present_days,
                    COUNT(CASE WHEN a.status='Absent' THEN 1 END) as absent_days
                FROM attendance a 
                JOIN students s ON a.student_id=s.id 
                GROUP BY a.student_id 
                ORDER BY present_days DESC 
                LIMIT 10
            """)
            top_students = cur.fetchall()
            
        elif role == "faculty":
            faculty_dept = session.get('dept', '')
            
            # Faculty: Total students in their department
            cur.execute("SELECT COUNT(*) as total FROM students WHERE dept=%s AND is_active=1", (faculty_dept,))
            data["total_students"] = cur.fetchone()['total'] or 0
            
            # Faculty: Total presents and absents for their department
            cur.execute("""
                SELECT 
                    COUNT(CASE WHEN a.status='Present' THEN 1 END) as total_present,
                    COUNT(CASE WHEN a.status='Absent' THEN 1 END) as total_absent
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE s.dept = %s
            """, (faculty_dept,))
            summary = cur.fetchone()
            data["total_present"] = summary['total_present'] or 0
            data["total_absent"] = summary['total_absent'] or 0
            
            # Faculty: Trend data for their department
            cur.execute("""
                SELECT DATE(a.timestamp) as day, 
                    COUNT(CASE WHEN a.status='Present' THEN 1 END) as present,
                    COUNT(CASE WHEN a.status='Absent' THEN 1 END) as absent
                FROM attendance a 
                JOIN students s ON a.student_id = s.id
                WHERE s.dept = %s 
                AND a.timestamp >= NOW() - INTERVAL 30 DAY 
                GROUP BY DATE(a.timestamp) 
                ORDER BY day
            """, (faculty_dept,))
            data["trend"] = cur.fetchall()
            
            # Faculty: Today's stats by semester
            cur.execute("""
                SELECT s.semester,
                    COUNT(CASE WHEN a.status='Present' THEN 1 END) as present,
                    COUNT(CASE WHEN a.status='Absent' THEN 1 END) as absent
                FROM attendance a 
                JOIN students s ON a.student_id = s.id 
                WHERE s.dept = %s AND DATE(a.timestamp)=CURDATE() 
                GROUP BY s.semester
            """, (faculty_dept,))
            data["dept_today"] = cur.fetchall()
            
            # Faculty: Top students in their department
            cur.execute("""
                SELECT s.id, s.name, s.roll_no, s.dept, s.photo_path,
                    COUNT(CASE WHEN a.status='Present' THEN 1 END) as present_days,
                    COUNT(CASE WHEN a.status='Absent' THEN 1 END) as absent_days
                FROM attendance a 
                JOIN students s ON a.student_id = s.id 
                WHERE s.dept = %s
                GROUP BY a.student_id 
                ORDER BY present_days DESC 
                LIMIT 10
            """, (faculty_dept,))
            top_students = cur.fetchall()
        
        # Calculate percentage for each student
        for s in top_students:
            s['attendance_percent'] = round((s['present_days'] / total_working_days) * 100, 1) if total_working_days > 0 else 0
            s['total_days'] = total_working_days
        
        data["top"] = top_students
        data["total_working_days"] = total_working_days
        
        c.close()
    
    return render_template("reports.html", data=data)


if __name__ == "__main__":
    ip = local_ip()
    print(f"\n{'='*55}")
    print(f" Face Attendance System ")
    print(f"  Local:   http://127.0.0.1:5000")
    print(f"  Mobile:  http://{ip}:5000 ")
    print(f"{'='*55}\n")
    app.run(host="0.0.0.0", port=5000, debug=False)


# Face Attendance System
#   Local:   http://127.0.0.1:5000
#   Mobile:  http://10.153.209.250:5000

#   Admin:   admin@college.edu / Admin@123
# print(f"  Admin:   admin@college.edu / Admin@123")
