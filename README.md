# Campus Placement Registration Portal (Naukri-Style)

A lightweight, production-grade Campus Placement and Recruitment Drive Management Portal built with **Python (Flask)**, built-in **SQLite3**, **Bootstrap 5**, and vanilla **JavaScript**.

---

## Features

### Student Portal
- **Registration**: Full student profile creation including:
  - Full Name
  - College Email (unique)
  - Password (securely hashed with `werkzeug.security`)
  - University Roll Number (unique)
  - Academic Branch (CSE, IT, ECE, EE, Mechanical, Civil, etc.)
  - Batch Year & Mobile Number
  - Current CGPA (0.00 – 10.00 scale)
  - Technical Skills (comma-separated)
  - Resume Link (Google Drive / cloud portfolio)
- **Authentication**: Session-based login and logout with protected routes.
- **Student Dashboard**:
  - Live metric counters: Total Applied, Shortlisted, Selected, and Eligible Openings.
  - **My Placement Applications**: Status tracking with distinct semantic badges (`Applied`, `Shortlisted`, `Selected`, `Rejected`).
  - **Recommended Drives**: Personalized feed of openings the student qualifies for.
- **Search & Filter Openings**:
  - Full-text search across company names, role titles, and locations.
  - Branch filter dropdown.
  - Real-time eligibility indicators on every listing (`Eligible to Apply` vs `Not Eligible`).
- **Job Detail & Automated Eligibility Validation**:
  - Comprehensive drive details: package (LPA), location, cut-off CGPA, eligible branches, deadline, and applicant count.
  - **Automated Eligibility Engine**: Dynamically compares student's CGPA and branch against company requirements, providing clear eligibility feedback or exact reasons for disqualification.
  - **Application Submission**: 1-click apply for eligible candidates; prevents duplicate applications.
- **Profile Management**: Update contact details, CGPA, technical skills, and resume link at any time.

### Placement Cell (Admin) Portal
- **Dedicated Admin Authentication**: Separate administration portal pre-seeded with authorized credentials.
- **Admin Dashboard**:
  - Summary metrics: Active Openings, Registered Students, Total Applications, and Placed Students.
  - Overview table of all posted jobs with live applicant counters.
  - Delete postings with client-side confirmation.
- **Post Recruitment Drives**: Form to publish new corporate drives with:
  - Company name & job role title
  - Location & package (CTC in LPA)
  - Cut-off minimum CGPA & eligible branches
  - Application deadline & comprehensive description
- **Candidate Screening & Management**:
  - View all applicants sorted by CGPA (merit order).
  - Inspect student roll number, email, mobile, branch, batch, skills, and resume link.
  - Change applicant status inline: `Applied` &rarr; `Shortlisted` &rarr; `Selected` &rarr; `Rejected`.

---

## Design System & UX
- **Naukri-Style White & Blue Palette**:
  - Primary Blue: Deep royal blue (`#1D4ED8` / `#2563EB`) with darker hover state (`#1E40AF`).
  - Page Canvas: Light cool grey (`#F8FAFC`).
  - Cards: Crisp white surfaces (`#FFFFFF`) with subtle border separation (`#E2E8F0`).
  - Semantic Status Accents: Clean emerald green for `Selected`, warm amber for `Shortlisted`, muted red for `Rejected`, and soft brand blue for `Applied`.
- **Client-Side Interactions**:
  - Live password confirmation match verification on registration.
  - Confirm-before-delete prompts on admin deletions.
  - Auto-dismissing flash notifications with fade-out animation.
  - Fully mobile-responsive layout.

---

## Seed Data & Default Credentials

The SQLite database (`placement.db`) automatically initializes on first run with:
1. **1 Admin Account**:
   - **Username**: `admin`
   - **Password**: `admin123`
2. **4 Realistic Sample Job Drives**:
   - **Microsoft**: Software Development Engineer (SDE-1) &bull; 18.5 LPA &bull; Min CGPA: 7.50
   - **Deloitte**: Technology Consulting Analyst &bull; 9.0 LPA &bull; Min CGPA: 6.50
   - **Amazon**: Cloud Support Associate &bull; 14.2 LPA &bull; Min CGPA: 7.00
   - **Cisco**: Network Software Engineer &bull; 16.0 LPA &bull; Min CGPA: 8.00

---

## Project Structure

```
pythonpy/
├── app.py                  # Main Flask application, routes, eligibility engine, session auth
├── db.py                   # SQLite connection, table schema creation, and automatic seeding
├── test_app.py             # Complete automated test suite (7 comprehensive test cases)
├── placement.db            # SQLite database file (created automatically on startup)
├── static/
│   ├── css/
│   │   └── style.css       # Custom Naukri white-and-blue theme, status badges, typography
│   └── js/
│       └── main.js         # Client-side validations, alert auto-dismiss, delete confirmation
├── templates/
│   ├── base.html           # Unified layout with responsive navbar, notifications, and footer
│   ├── auth/
│   │   ├── student_register.html   # Student account registration
│   │   ├── student_login.html      # Student login
│   │   └── admin_login.html        # Placement cell admin login
│   ├── student/
│   │   ├── dashboard.html          # Student dashboard (applications & eligible jobs)
│   │   ├── jobs.html               # Job listings with search & branch filtering
│   │   ├── job_detail.html         # Job details + eligibility checker + apply action
│   │   └── profile.html            # Profile viewing and updating
│   └── admin/
│       ├── dashboard.html          # Placement cell overview & job management
│       ├── post_job.html           # New job posting form
│       └── applicants.html         # Applicant review, candidate details, & status update
└── README.md               # Documentation and usage guide
```

---

## Quickstart & Setup Instructions

### 1. Prerequisites
- Python 3.10+ installed on your system.
- Standard libraries: `sqlite3` is built into Python.
- Dependencies: `Flask` and `Werkzeug`.

Install dependencies if needed:
```bash
pip install Flask Werkzeug
```

### 2. Run the Portal
From the project folder (`pythonpy`), run:
```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### 3. Running Automated Tests
To run the automated test suite verifying database integrity, registration, eligibility criteria, and admin workflows:
```bash
python -m unittest test_app.py
```

---

## Testing Scenarios

1. **Student Registration & Dashboard**:
   - Register a student account with CGPA (e.g. `8.2`) and branch (e.g. `Computer Science`).
   - Notice the student is automatically signed in and lands on their personalized dashboard.
2. **Eligibility Checking**:
   - View **Cisco** (Min CGPA 8.0, CSE/IT): Notice "Eligible to Apply" badge & submit application.
   - View job with higher CGPA or mismatched branch: Notice clear warning indicating why the student is ineligible and the disabled apply button.
   - Duplicate prevention: Attempt to apply again to the same drive; system notifies that application was already submitted.
3. **Admin Actions**:
   - Navigate to `/admin/login` and log in with `admin` / `admin123`.
   - Post a new company opening from **Post New Job**.
   - Open **Review Applicants** for a job to view candidate details, resume link, and update status from `Applied` to `Shortlisted` or `Selected`.
   - Verify on student dashboard that status updates immediately reflect to the candidate.
