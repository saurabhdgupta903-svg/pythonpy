import os
import unittest
import tempfile
import sqlite3
from werkzeug.security import check_password_hash

# Set a test database before importing app/db
import db
import app as flask_app

class CampusPlacementTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        db.DB_PATH = self.db_path
        flask_app.DB_PATH = self.db_path

        flask_app.app.config["TESTING"] = True
        flask_app.app.config["SECRET_KEY"] = "test-secret-key"
        self.client = flask_app.app.test_client()

        # Initialize and seed temporary database
        with flask_app.app.app_context():
            db.init_db()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_database_initialization_and_seeding(self):
        """Verify that default admin and 4 sample jobs are auto-seeded."""
        conn = db.get_db()
        admin = conn.execute("SELECT * FROM admins WHERE username = 'admin'").fetchone()
        self.assertIsNotNone(admin)
        self.assertTrue(check_password_hash(admin["password_hash"], "admin123"))

        job_count = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
        self.assertEqual(job_count, 4)
        conn.close()

    def test_student_registration_and_login(self):
        """Test student sign up and sign in flow."""
        # 1. Register student
        res = self.client.post("/register", data={
            "name": "Rohan Gupta",
            "email": "rohan@college.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "21CS101",
            "branch": "Computer Science",
            "batch_year": "2026",
            "cgpa": "8.75",
            "phone": "9876543210",
            "skills": "Python, Flask, Docker",
            "resume_link": "https://drive.google.com/test-resume"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Rohan Gupta", res.data)
        self.assertIn(b"21CS101", res.data)

        # 2. Log out before testing duplicate registration
        self.client.get("/logout")

        # 3. Block duplicate email
        res_dup = self.client.post("/register", data={
            "name": "Another Student",
            "email": "rohan@college.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "21CS102",
            "branch": "Computer Science",
            "batch_year": "2026",
            "cgpa": "7.5",
            "phone": "9876543211",
            "skills": "Java",
            "resume_link": ""
        }, follow_redirects=True)
        self.assertIn(b"already exists", res_dup.data)

        # 3. Log out
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b"Student Sign In", res_logout.data)

        # 4. Log in with credentials
        res_login = self.client.post("/login", data={
            "email": "rohan@college.edu",
            "password": "password123"
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"Welcome back, Rohan Gupta", res_login.data)

    def test_job_application_eligibility_and_duplicate_prevention(self):
        """Test eligibility logic (CGPA & Branch) and duplicate application blocking."""
        # Register a high CGPA CSE student
        self.client.post("/register", data={
            "name": "Priya Sharma",
            "email": "priya@college.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "21CS050",
            "branch": "Computer Science",
            "batch_year": "2026",
            "cgpa": "9.10",
            "phone": "9876543220",
            "skills": "C++, Algorithms",
            "resume_link": "https://example.com/resume"
        }, follow_redirects=True)

        conn = db.get_db()
        msft_job = conn.execute("SELECT * FROM jobs WHERE company_name = 'Microsoft'").fetchone()
        conn.close()

        # Apply to Microsoft (Min CGPA 7.5, CSE is eligible)
        apply_res = self.client.post(f"/jobs/{msft_job['id']}/apply", follow_redirects=True)
        self.assertEqual(apply_res.status_code, 200)
        self.assertIn(b"Congratulations! Your application", apply_res.data)

        # Attempt to apply again (duplicate check)
        dup_res = self.client.post(f"/jobs/{msft_job['id']}/apply", follow_redirects=True)
        self.assertIn(b"already applied for this position", dup_res.data)

        # Register a low CGPA Civil student
        self.client.get("/logout")
        self.client.post("/register", data={
            "name": "Amit Kumar",
            "email": "amit@college.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "21CE020",
            "branch": "Civil",
            "batch_year": "2026",
            "cgpa": "6.20",
            "phone": "9876543230",
            "skills": "AutoCAD",
            "resume_link": ""
        }, follow_redirects=True)

        # Try to apply for Cisco (Min CGPA 8.0, CSE/IT only)
        conn = db.get_db()
        cisco_job = conn.execute("SELECT * FROM jobs WHERE company_name = 'Cisco'").fetchone()
        conn.close()

        inelig_res = self.client.post(f"/jobs/{cisco_job['id']}/apply", follow_redirects=True)
        self.assertIn(b"Application rejected: You do not satisfy the eligibility criteria", inelig_res.data)

    def test_student_profile_update(self):
        """Test updating student profile details."""
        self.client.post("/register", data={
            "name": "Kavya Patel",
            "email": "kavya@college.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "21IT030",
            "branch": "Information Technology",
            "batch_year": "2026",
            "cgpa": "8.00",
            "phone": "9876543240",
            "skills": "Java",
            "resume_link": ""
        }, follow_redirects=True)

        update_res = self.client.post("/profile", data={
            "name": "Kavya Patel (Updated)",
            "branch": "Information Technology",
            "batch_year": "2026",
            "cgpa": "8.65",
            "phone": "9876543299",
            "skills": "Java, Spring Boot, Microservices",
            "resume_link": "https://drive.google.com/kavya-resume"
        }, follow_redirects=True)
        self.assertEqual(update_res.status_code, 200)
        self.assertIn(b"Profile updated successfully", update_res.data)

        # Verify in database
        conn = db.get_db()
        student = conn.execute("SELECT * FROM students WHERE email = 'kavya@college.edu'").fetchone()
        self.assertEqual(student["name"], "Kavya Patel (Updated)")
        self.assertEqual(student["cgpa"], 8.65)
        self.assertEqual(student["skills"], "Java, Spring Boot, Microservices")
        conn.close()

    def test_admin_workflows(self):
        """Test admin login, posting a job, viewing applicants, updating status, and deleting a job."""
        # 1. Admin Login
        login_res = self.client.post("/admin/login", data={
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Placement Cell Management", login_res.data)

        # 2. Post a new Job Opening
        new_job_res = self.client.post("/admin/jobs/new", data={
            "company_name": "Atlassian",
            "role_title": "Site Reliability Engineer",
            "description": "Maintain reliability, scalability, and performance of Jira and Confluence cloud architectures.",
            "location": "Bengaluru",
            "package_lpa": "24.0",
            "min_cgpa": "8.5",
            "eligible_branches": "Computer Science, Information Technology",
            "deadline": "2026-11-30"
        }, follow_redirects=True)
        self.assertEqual(new_job_res.status_code, 200)
        self.assertIn(b"Atlassian", new_job_res.data)

        conn = db.get_db()
        atlassian_job = conn.execute("SELECT * FROM jobs WHERE company_name = 'Atlassian'").fetchone()
        self.assertIsNotNone(atlassian_job)
        job_id = atlassian_job["id"]
        conn.close()

        # 3. Register a student and apply to Atlassian
        self.client.get("/admin/logout")
        self.client.post("/register", data={
            "name": "Devansh Roy",
            "email": "devansh@college.edu",
            "password": "password123",
            "confirm_password": "password123",
            "roll_number": "21CS099",
            "branch": "Computer Science",
            "batch_year": "2026",
            "cgpa": "9.20",
            "phone": "9876543255",
            "skills": "Go, Kubernetes, Linux",
            "resume_link": "https://devansh.io/resume"
        }, follow_redirects=True)

        apply_res = self.client.post(f"/jobs/{job_id}/apply", follow_redirects=True)
        self.assertIn(b"Congratulations! Your application", apply_res.data)

        # 4. Admin checks applicant list
        self.client.get("/logout")
        self.client.post("/admin/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)

        applicants_res = self.client.get(f"/admin/jobs/{job_id}/applicants")
        self.assertEqual(applicants_res.status_code, 200)
        self.assertIn(b"Devansh Roy", applicants_res.data)
        self.assertIn(b"21CS099", applicants_res.data)

        # 5. Admin updates applicant status to "Shortlisted", then "Selected"
        conn = db.get_db()
        app_record = conn.execute("SELECT id FROM applications WHERE job_id = ?", (job_id,)).fetchone()
        conn.close()
        app_id = app_record["id"]

        status_res = self.client.post(f"/admin/applications/{app_id}/status", data={
            "status": "Selected"
        }, follow_redirects=True)
        self.assertEqual(status_res.status_code, 200)
        self.assertIn(b"Selected", status_res.data)

        # 6. Admin deletes the job
        del_res = self.client.post(f"/admin/jobs/{job_id}/delete", follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        conn = db.get_db()
        deleted = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        self.assertIsNone(deleted)
        # Verify cascade
        app_after_del = conn.execute("SELECT * FROM applications WHERE job_id = ?", (job_id,)).fetchall()
        self.assertEqual(len(app_after_del), 0)
        conn.close()

    def test_auth_access_guards_and_invalid_logins(self):
        """Test route protection for student and admin areas, and failed login handling."""
        # 1. Anonymous access to protected student pages should redirect
        res1 = self.client.get("/student/dashboard", follow_redirects=False)
        self.assertEqual(res1.status_code, 302)
        self.assertIn("/login", res1.location)

        res2 = self.client.get("/profile", follow_redirects=False)
        self.assertEqual(res2.status_code, 302)

        # 2. Anonymous access to admin dashboard should redirect
        res3 = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(res3.status_code, 302)
        self.assertIn("/admin/login", res3.location)

        # 3. Invalid student login
        bad_login = self.client.post("/login", data={
            "email": "nonexistent@college.edu",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", bad_login.data)

        # 4. Invalid admin login
        bad_admin_login = self.client.post("/admin/login", data={
            "username": "admin",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid administrator credentials", bad_admin_login.data)

        # 5. Password mismatch during student registration
        mismatch_res = self.client.post("/register", data={
            "name": "Test Mismatch",
            "email": "mismatch@college.edu",
            "password": "password123",
            "confirm_password": "password456",
            "roll_number": "21CS999",
            "branch": "Computer Science",
            "batch_year": "2026",
            "cgpa": "8.0",
            "phone": "9876543200"
        }, follow_redirects=True)
        self.assertIn(b"Passwords do not match", mismatch_res.data)

    def test_job_search_and_filtering(self):
        """Test searching jobs by company name and branch filter."""
        # Search by company name
        search_ms = self.client.get("/jobs?q=Microsoft")
        self.assertEqual(search_ms.status_code, 200)
        self.assertIn(b"Microsoft", search_ms.data)
        self.assertNotIn(b"Cisco", search_ms.data)

        # Filter by branch
        branch_filter = self.client.get("/jobs?branch=Mechanical")
        self.assertEqual(branch_filter.status_code, 200)
        self.assertIn(b"Deloitte", branch_filter.data)
        self.assertNotIn(b"Cisco", branch_filter.data)

if __name__ == "__main__":
    unittest.main()
