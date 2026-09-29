import functools
import os
import re
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, 
    url_for, flash, session, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "campus_placement_secret_key_2026_xyz")

# Auto-initialize database on application startup
with app.app_context():
    init_db()

# --- Common Branch Mapping for Smart Eligibility ---
BRANCH_MAPPINGS = {
    "cse": ["computer science", "cs", "cse", "computer engineering", "computer science and engineering"],
    "it": ["information technology", "it"],
    "ece": ["electronics & communication", "electronics and communication", "ece", "electronics"],
    "ee": ["electrical", "electrical engineering", "eee", "ee"],
    "mech": ["mechanical", "mechanical engineering", "mech"],
    "civil": ["civil", "civil engineering"]
}

def normalize_text(text: str) -> str:
    """Lowercase and strip whitespace and punctuation for loose comparisons."""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def is_branch_eligible(student_branch: str, eligible_branches_str: str) -> bool:
    """
    Check if the student's branch satisfies the eligible branches requirement.
    Supports comma-separated lists, abbreviations (e.g. CSE -> Computer Science),
    and 'All Branches'.
    """
    if not eligible_branches_str:
        return True
    
    clean_target = eligible_branches_str.lower()
    if "all" in clean_target:
        return True

    # Parse individual branches in job requirements
    required_branches = [b.strip() for b in re.split(r'[,/|;]+', eligible_branches_str) if b.strip()]
    
    norm_student = normalize_text(student_branch)

    # Direct substring / exact check
    for req in required_branches:
        norm_req = normalize_text(req)
        if norm_req == norm_student or norm_req in norm_student or norm_student in norm_req:
            return True

    # Check alias groups
    student_aliases = set()
    for key, aliases in BRANCH_MAPPINGS.items():
        if any(normalize_text(a) == norm_student or normalize_text(a) in norm_student for a in aliases):
            student_aliases.update([normalize_text(a) for a in aliases])
            student_aliases.add(normalize_text(key))

    for req in required_branches:
        norm_req = normalize_text(req)
        if norm_req in student_aliases:
            return True
        for key, aliases in BRANCH_MAPPINGS.items():
            if norm_req == normalize_text(key) or any(normalize_text(a) == norm_req for a in aliases):
                if any(sa in [normalize_text(a) for a in aliases] or sa == normalize_text(key) for sa in student_aliases):
                    return True

    return False

def check_eligibility(student, job):
    """
    Evaluates student eligibility against job requirements.
    Returns: (is_eligible: bool, reasons: list[str])
    """
    reasons = []
    
    # 1. CGPA check
    try:
        student_cgpa = float(student["cgpa"])
        min_cgpa = float(job["min_cgpa"])
        if student_cgpa < min_cgpa:
            reasons.append(f"Minimum CGPA required is {min_cgpa:.2f} (Your current CGPA is {student_cgpa:.2f})")
    except (ValueError, TypeError):
        reasons.append("Invalid CGPA recorded on profile.")

    # 2. Branch check
    student_branch = student["branch"] or ""
    eligible_branches = job["eligible_branches"] or ""
    if not is_branch_eligible(student_branch, eligible_branches):
        reasons.append(
            f"Your branch ({student_branch}) is not listed in the eligible branches ({eligible_branches})"
        )

    # 3. Deadline check
    try:
        deadline_date = datetime.strptime(job["deadline"], "%Y-%m-%d").date()
        if deadline_date < datetime.now().date():
            reasons.append(f"Application deadline has passed ({job['deadline']})")
    except (ValueError, TypeError):
        pass

    return (len(reasons) == 0, reasons)

# --- Authentication Helpers & Decorators ---

def get_current_student():
    """Retrieve logged-in student record, if available."""
    if session.get("role") == "student" and "user_id" in session:
        conn = get_db()
        student = conn.execute("SELECT * FROM students WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()
        return student
    return None

def get_current_admin():
    """Retrieve logged-in admin record, if available."""
    if session.get("role") == "admin" and "admin_id" in session:
        conn = get_db()
        admin = conn.execute("SELECT * FROM admins WHERE id = ?", (session["admin_id"],)).fetchone()
        conn.close()
        return admin
    return None

@app.context_processor
def inject_user_context():
    """Make current_user and role accessible to all Jinja templates."""
    student = get_current_student()
    admin = get_current_admin()
    return {
        "current_student": student,
        "current_admin": admin,
        "current_role": session.get("role")
    }

def student_required(view_func):
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "student" or "user_id" not in session:
            flash("Please log in as a student to access this page.", "warning")
            return redirect(url_for("student_login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped_view

def admin_required(view_func):
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("role") != "admin" or "admin_id" not in session:
            flash("Administrator login required.", "warning")
            return redirect(url_for("admin_login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped_view


# --- General / Landing Routes ---

@app.route("/")
def index():
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))
    elif session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("job_list"))


# --- Student Auth Routes ---

@app.route("/register", methods=["GET", "POST"])
def student_register():
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        roll_number = request.form.get("roll_number", "").strip().upper()
        branch = request.form.get("branch", "").strip()
        batch_year = request.form.get("batch_year", "").strip()
        cgpa = request.form.get("cgpa", "").strip()
        phone = request.form.get("phone", "").strip()
        skills = request.form.get("skills", "").strip()
        resume_link = request.form.get("resume_link", "").strip()

        # Validation
        if not (name and email and password and roll_number and branch and batch_year and cgpa and phone):
            flash("Please fill in all required fields.", "danger")
            return render_template("auth/student_register.html", form=request.form)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/student_register.html", form=request.form)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/student_register.html", form=request.form)

        try:
            cgpa_val = float(cgpa)
            if not (0.0 <= cgpa_val <= 10.0):
                flash("CGPA must be between 0.0 and 10.0.", "danger")
                return render_template("auth/student_register.html", form=request.form)
            batch_year_val = int(batch_year)
        except ValueError:
            flash("Please enter valid numeric values for CGPA and Batch Year.", "danger")
            return render_template("auth/student_register.html", form=request.form)

        conn = get_db()
        cursor = conn.cursor()

        # Check existing email or roll number
        existing_email = cursor.execute("SELECT id FROM students WHERE email = ?", (email,)).fetchone()
        if existing_email:
            conn.close()
            flash("An account with this email address already exists.", "danger")
            return render_template("auth/student_register.html", form=request.form)

        existing_roll = cursor.execute("SELECT id FROM students WHERE roll_number = ?", (roll_number,)).fetchone()
        if existing_roll:
            conn.close()
            flash("An account with this roll number already exists.", "danger")
            return render_template("auth/student_register.html", form=request.form)

        # Create student
        hashed_password = generate_password_hash(password)
        cursor.execute(
            """
            INSERT INTO students (
                name, email, password_hash, roll_number, branch, 
                batch_year, cgpa, phone, skills, resume_link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, email, hashed_password, roll_number, branch, batch_year_val, cgpa_val, phone, skills, resume_link)
        )
        new_student_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Automatically log in the registered student
        session.clear()
        session["user_id"] = new_student_id
        session["user_name"] = name
        session["role"] = "student"

        flash("Registration successful! Welcome to the Campus Placement Portal.", "success")
        return redirect(url_for("student_dashboard"))

    return render_template("auth/student_register.html")


@app.route("/login", methods=["GET", "POST"])
def student_login():
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        student = conn.execute("SELECT * FROM students WHERE email = ?", (email,)).fetchone()
        conn.close()

        if student and check_password_hash(student["password_hash"], password):
            session.clear()
            session["user_id"] = student["id"]
            session["user_name"] = student["name"]
            session["role"] = "student"
            flash(f"Welcome back, {student['name']}!", "success")
            
            next_url = request.args.get("next")
            return redirect(next_url or url_for("student_dashboard"))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("auth/student_login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("student_login"))


# --- Student Dashboard & Profile ---

@app.route("/student/dashboard")
@student_required
def student_dashboard():
    student = get_current_student()
    conn = get_db()

    # Fetch student's applications with job details
    applications = conn.execute(
        """
        SELECT 
            a.id AS app_id, 
            a.status, 
            a.applied_at, 
            j.id AS job_id, 
            j.company_name, 
            j.role_title, 
            j.package_lpa, 
            j.location, 
            j.deadline
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.student_id = ?
        ORDER BY a.applied_at DESC
        """,
        (student["id"],)
    ).fetchall()

    applied_job_ids = {app["job_id"] for app in applications}

    # Fetch all jobs to compute eligible openings
    all_jobs = conn.execute("SELECT * FROM jobs ORDER BY deadline ASC").fetchall()
    conn.close()

    eligible_jobs = []
    for job in all_jobs:
        if job["id"] not in applied_job_ids:
            is_elig, reasons = check_eligibility(student, job)
            if is_elig:
                eligible_jobs.append(job)

    # Statistics for dashboard cards
    stats = {
        "applied": len(applications),
        "shortlisted": sum(1 for a in applications if a["status"] == "Shortlisted"),
        "selected": sum(1 for a in applications if a["status"] == "Selected"),
        "eligible_openings": len(eligible_jobs)
    }

    return render_template(
        "student/dashboard.html",
        student=student,
        applications=applications,
        eligible_jobs=eligible_jobs[:6], # Show top 6 eligible jobs
        stats=stats
    )


@app.route("/profile", methods=["GET", "POST"])
@student_required
def profile():
    student = get_current_student()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        branch = request.form.get("branch", "").strip()
        batch_year = request.form.get("batch_year", "").strip()
        cgpa = request.form.get("cgpa", "").strip()
        phone = request.form.get("phone", "").strip()
        skills = request.form.get("skills", "").strip()
        resume_link = request.form.get("resume_link", "").strip()

        if not (name and branch and batch_year and cgpa and phone):
            flash("All fields except resume/skills are required.", "danger")
            return render_template("student/profile.html", student=student)

        try:
            cgpa_val = float(cgpa)
            if not (0.0 <= cgpa_val <= 10.0):
                flash("CGPA must be between 0.0 and 10.0.", "danger")
                return render_template("student/profile.html", student=student)
            batch_year_val = int(batch_year)
        except ValueError:
            flash("Invalid numeric value for CGPA or Batch Year.", "danger")
            return render_template("student/profile.html", student=student)

        conn = get_db()
        conn.execute(
            """
            UPDATE students 
            SET name = ?, branch = ?, batch_year = ?, cgpa = ?, phone = ?, skills = ?, resume_link = ?
            WHERE id = ?
            """,
            (name, branch, batch_year_val, cgpa_val, phone, skills, resume_link, student["id"])
        )
        conn.commit()
        conn.close()

        session["user_name"] = name
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("student/profile.html", student=student)


# --- Job Browsing & Applications ---

@app.route("/jobs")
def job_list():
    query = request.args.get("q", "").strip()
    branch_filter = request.args.get("branch", "").strip()

    conn = get_db()
    sql = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if query:
        sql += " AND (company_name LIKE ? OR role_title LIKE ? OR location LIKE ? OR eligible_branches LIKE ?)"
        term = f"%{query}%"
        params.extend([term, term, term, term])

    if branch_filter:
        sql += " AND (eligible_branches LIKE ? OR eligible_branches LIKE '%All%')"
        params.append(f"%{branch_filter}%")

    sql += " ORDER BY created_at DESC"
    jobs = conn.execute(sql, params).fetchall()

    student = get_current_student()
    applied_job_ids = set()
    eligibility_map = {}

    if student:
        apps = conn.execute("SELECT job_id FROM applications WHERE student_id = ?", (student["id"],)).fetchall()
        applied_job_ids = {a["job_id"] for a in apps}

        for j in jobs:
            is_elig, reasons = check_eligibility(student, j)
            eligibility_map[j["id"]] = {
                "eligible": is_elig,
                "reasons": reasons,
                "applied": j["id"] in applied_job_ids
            }
    conn.close()

    return render_template(
        "student/jobs.html",
        jobs=jobs,
        query=query,
        branch_filter=branch_filter,
        eligibility_map=eligibility_map,
        applied_job_ids=applied_job_ids
    )


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        flash("The requested job opening does not exist.", "warning")
        return redirect(url_for("job_list"))

    student = get_current_student()
    existing_application = None
    is_eligible = False
    reasons = []

    if student:
        existing_application = conn.execute(
            "SELECT * FROM applications WHERE job_id = ? AND student_id = ?", 
            (job_id, student["id"])
        ).fetchone()
        is_eligible, reasons = check_eligibility(student, job)

    # Applicant count
    count_row = conn.execute("SELECT COUNT(*) AS count FROM applications WHERE job_id = ?", (job_id,)).fetchone()
    applicant_count = count_row["count"] if count_row else 0
    conn.close()

    return render_template(
        "student/job_detail.html",
        job=job,
        student=student,
        existing_application=existing_application,
        is_eligible=is_eligible,
        reasons=reasons,
        applicant_count=applicant_count
    )


@app.route("/jobs/<int:job_id>/apply", methods=["POST"])
@student_required
def apply_job(job_id):
    student = get_current_student()
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    if not job:
        conn.close()
        flash("Job posting not found.", "danger")
        return redirect(url_for("job_list"))

    # 1. Check duplicate application
    existing = conn.execute(
        "SELECT id, status FROM applications WHERE job_id = ? AND student_id = ?",
        (job_id, student["id"])
    ).fetchone()

    if existing:
        conn.close()
        flash(f"You have already applied for this position (Current status: {existing['status']}).", "warning")
        return redirect(url_for("job_detail", job_id=job_id))

    # 2. Check eligibility
    is_eligible, reasons = check_eligibility(student, job)
    if not is_eligible:
        conn.close()
        reason_msg = " | ".join(reasons)
        flash(f"Application rejected: You do not satisfy the eligibility criteria ({reason_msg}).", "danger")
        return redirect(url_for("job_detail", job_id=job_id))

    # 3. Create application
    conn.execute(
        "INSERT INTO applications (job_id, student_id, status) VALUES (?, ?, 'Applied')",
        (job_id, student["id"])
    )
    conn.commit()
    conn.close()

    flash(f"Congratulations! Your application for {job['role_title']} at {job['company_name']} has been submitted.", "success")
    return redirect(url_for("student_dashboard"))


# --- Admin Routes ---

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            session["role"] = "admin"
            flash(f"Welcome, {admin['name']} (Placement Cell Admin)!", "success")
            
            next_url = request.args.get("next")
            return redirect(next_url or url_for("admin_dashboard"))
        else:
            flash("Invalid administrator credentials.", "danger")

    return render_template("auth/admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Administrator logged out successfully.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()

    # Metrics
    total_jobs = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
    total_students = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
    total_applications = conn.execute("SELECT COUNT(*) AS c FROM applications").fetchone()["c"]
    selected_count = conn.execute("SELECT COUNT(*) AS c FROM applications WHERE status = 'Selected'").fetchone()["c"]

    # All job postings with applicant count
    jobs = conn.execute(
        """
        SELECT 
            j.*, 
            COUNT(a.id) AS applicant_count
        FROM jobs j
        LEFT JOIN applications a ON j.id = a.job_id
        GROUP BY j.id
        ORDER BY j.created_at DESC
        """
    ).fetchall()
    conn.close()

    metrics = {
        "total_jobs": total_jobs,
        "total_students": total_students,
        "total_applications": total_applications,
        "selected_count": selected_count
    }

    return render_template("admin/dashboard.html", jobs=jobs, metrics=metrics)


@app.route("/admin/jobs/new", methods=["GET", "POST"])
@admin_required
def post_job():
    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        role_title = request.form.get("role_title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        package_lpa = request.form.get("package_lpa", "").strip()
        min_cgpa = request.form.get("min_cgpa", "").strip()
        eligible_branches = request.form.get("eligible_branches", "").strip()
        deadline = request.form.get("deadline", "").strip()

        if not (company_name and role_title and description and location and package_lpa and min_cgpa and eligible_branches and deadline):
            flash("All fields are required to post an opening.", "danger")
            return render_template("admin/post_job.html", form=request.form)

        try:
            pkg_val = float(package_lpa)
            cgpa_val = float(min_cgpa)
            if pkg_val <= 0 or not (0.0 <= cgpa_val <= 10.0):
                flash("Please check package and CGPA values.", "danger")
                return render_template("admin/post_job.html", form=request.form)
            # Validate date format
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            flash("Invalid format for Package, CGPA, or Deadline date.", "danger")
            return render_template("admin/post_job.html", form=request.form)

        conn = get_db()
        conn.execute(
            """
            INSERT INTO jobs (
                company_name, role_title, description, location, 
                package_lpa, min_cgpa, eligible_branches, deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (company_name, role_title, description, location, pkg_val, cgpa_val, eligible_branches, deadline)
        )
        conn.commit()
        conn.close()

        flash(f"Job opening '{role_title}' at '{company_name}' successfully posted!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/post_job.html")


@app.route("/admin/jobs/<int:job_id>/applicants")
@admin_required
def view_applicants(job_id):
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        conn.close()
        flash("Job not found.", "warning")
        return redirect(url_for("admin_dashboard"))

    applicants = conn.execute(
        """
        SELECT 
            a.id AS app_id,
            a.status,
            a.applied_at,
            s.id AS student_id,
            s.name,
            s.email,
            s.roll_number,
            s.branch,
            s.batch_year,
            s.cgpa,
            s.phone,
            s.skills,
            s.resume_link
        FROM applications a
        JOIN students s ON a.student_id = s.id
        WHERE a.job_id = ?
        ORDER BY s.cgpa DESC, a.applied_at ASC
        """,
        (job_id,)
    ).fetchall()
    conn.close()

    return render_template("admin/applicants.html", job=job, applicants=applicants)


@app.route("/admin/applications/<int:app_id>/status", methods=["POST"])
@admin_required
def update_application_status(app_id):
    new_status = request.form.get("status", "").strip()
    valid_statuses = ["Applied", "Shortlisted", "Selected", "Rejected"]

    if new_status not in valid_statuses:
        flash("Invalid status choice.", "danger")
        return redirect(request.referrer or url_for("admin_dashboard"))

    conn = get_db()
    app_record = conn.execute(
        """
        SELECT a.id, a.job_id, s.name, j.company_name 
        FROM applications a 
        JOIN students s ON a.student_id = s.id 
        JOIN jobs j ON a.job_id = j.id 
        WHERE a.id = ?
        """,
        (app_id,)
    ).fetchone()

    if not app_record:
        conn.close()
        flash("Application record not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn.execute("UPDATE applications SET status = ? WHERE id = ?", (new_status, app_id))
    conn.commit()
    conn.close()

    flash(f"Updated {app_record['name']}'s status for {app_record['company_name']} to '{new_status}'.", "success")
    return redirect(url_for("view_applicants", job_id=app_record["job_id"]))


@app.route("/admin/jobs/<int:job_id>/delete", methods=["POST"])
@admin_required
def delete_job(job_id):
    conn = get_db()
    job = conn.execute("SELECT company_name, role_title FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        flash(f"Job posting '{job['role_title']}' at '{job['company_name']}' was deleted.", "info")
    else:
        flash("Job not found.", "warning")
    conn.close()

    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
