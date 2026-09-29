import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "placement.db")

def get_db():
    """Return a database connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize SQLite database tables and seed data if not already present."""
    conn = get_db()
    cursor = conn.cursor()

    # Students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        branch TEXT NOT NULL,
        batch_year INTEGER NOT NULL,
        cgpa REAL NOT NULL,
        phone TEXT NOT NULL,
        skills TEXT,
        resume_link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Admins table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Jobs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        role_title TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        package_lpa REAL NOT NULL,
        min_cgpa REAL NOT NULL,
        eligible_branches TEXT NOT NULL,
        deadline TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Applications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Applied',
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
        UNIQUE (job_id, student_id)
    );
    """)

    # Seed Admin if not exists
    cursor.execute("SELECT id FROM admins WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        admin_pass_hash = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO admins (username, password_hash, name) VALUES (?, ?, ?)",
            ("admin", admin_pass_hash, "Placement Cell Officer")
        )

    # Seed Sample Jobs if none exist
    cursor.execute("SELECT COUNT(*) AS count FROM jobs")
    job_count = cursor.fetchone()["count"]
    if job_count == 0:
        sample_jobs = [
            (
                "Microsoft",
                "Software Development Engineer (SDE-1)",
                "Join Microsoft's Core Services Engineering & Operations team to design, build, and deploy hyper-scale cloud platforms and services. You will work on distributed systems, modern API architectures, Azure microservices, and high-performance algorithms. Ideal candidates possess strong problem-solving skills, solid data structures and algorithms foundations, and clean code practices in C++, Java, or C#.",
                "Bengaluru / Hyderabad",
                18.5,
                7.5,
                "Computer Science, Information Technology, Electronics & Communication",
                "2026-10-30"
            ),
            (
                "Deloitte",
                "Technology Consulting Analyst",
                "Deloitte is seeking high-energy tech graduates to transform business operations for Fortune 500 enterprises. As a Consulting Analyst, you will leverage enterprise architectures, cloud transformation frameworks, modern database designs, and data analytics tools to solve strategic enterprise challenges. Strong communication, analytical mindset, and willingness to collaborate across global cross-functional teams are required.",
                "Gurugram / Mumbai / Bengaluru",
                9.0,
                6.5,
                "Computer Science, Information Technology, Electronics & Communication, Electrical, Mechanical",
                "2026-10-25"
            ),
            (
                "Amazon",
                "Cloud Support Associate",
                "Amazon Web Services (AWS) provides cloud computing infrastructure to millions of customers globally. As a Cloud Support Associate, you will act as the technical point of contact for enterprise cloud architectures, troubleshooting complex network configurations, Linux/Windows cloud environments, virtualization layers, and automated container workloads. AWS Cloud Practitioner or Solutions Architect certifications are an added advantage.",
                "Bengaluru / Hyderabad",
                14.2,
                7.0,
                "Computer Science, Information Technology, Electronics & Communication, Electrical",
                "2026-11-15"
            ),
            (
                "Cisco",
                "Network Software Engineer",
                "Cisco is revolutionizing enterprise networking with automated AI-driven campus and data center fabrics. You will engineer software-defined networking (SDN) protocols, high-throughput packet processing microservices, and network telemetry engines. Key technologies include Python, C/C++, Linux kernel networking, TCP/IP stack internals, and container orchestration.",
                "Bengaluru",
                16.0,
                8.0,
                "Computer Science, Information Technology",
                "2026-10-18"
            )
        ]

        cursor.executemany(
            """
            INSERT INTO jobs (
                company_name, role_title, description, location, 
                package_lpa, min_cgpa, eligible_branches, deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            sample_jobs
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
