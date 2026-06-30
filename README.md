# QR Attendance System (v2.0)

A secure, location-based attendance tracking system with real-time analytics, anti-cheating measures, and subject-wise reporting. Built with Flask, Supabase (PostgreSQL), and Bootstrap 5.

## 🚀 Key Features

### 🔐 Authentication & Security
- **Dual Portals**: Separate secure entry points for Students and Faculty.
- **Hashed Passwords**: Password security implemented via `werkzeug.security` (PBKDF2-SHA256).
- **Faculty Safeguard**: Faculty registration is restricted by a configurable `ADMIN_PASSWORD`.
- **Hacker-Proof Auth**: Username-based authentication (replacing email-only flows).

### ⚡ Anti-Cheat QR System
- **Time-Rotating Payloads**: QR codes auto-refresh every **10-15 seconds**.
- **HMAC Signatures**: Every payload is digitally signed with a server secret (`SECRET_KEY`).
- **Strict Expiry**: QR codes expire instantly after 15s; photo-sharing or proxy scanning is impossible.
- **Geofencing**: Haversine distance verification ensures attendees are within 10-50m of the professor.

### 📊 Advanced Analytics & Reporting
- **Faculty Dashboard**: Chart.js doughnut graphs showing global engagement at a glance.
- **Subject Filtering**: Drill down analytics by course (e.g., Machine Learning, Mobile App Dev).
- **CSV Export**: Instantly export attendance logs to Excel-ready CSV files.
- **Secure Access**: Analytics data is locked behind an administrative password wall.

### 📱 Student History Portal
- **Performance Tracking**: Students see their personal attendance percentage in real-time.
- **Subject Breakdown**: Course-wise attendance cards (e.g., "75% in ML", "90% in OR").
- **Verification Log**: Full history of past scans with distance and time data.

---

## ⚙️ Environment Configuration

Copy `.env.template` to `.env` and configure the following:

```env
# Supabase Database
SUPABASE_URL=https://<id>.supabase.co
SUPABASE_KEY=<your-anon-key>

# Security
SECRET_KEY=<generate_random_bits>
ADMIN_PASSWORD=qrattendance
```

---

## 📂 Directory Structure

```text
qrat/
├── app.py                 # Core Flask Backend (Auth, API, HMAC Logic)
├── static/
│   └── js/main.js         # Navigation & UI Helper Functions
├── templates/
│   ├── base.html          # Global Layout & Icon library
│   ├── login.html         # Premium Glassmorphism Auth Interface
│   ├── faculty.html       # Rotating QR Generator & Admin Modal
│   ├── student_scanner.html # Unified Scan/History Dashboard
│   └── analytics.html     # Secure Chart.js Global Reporter
└── requirements.txt       # dependencies (flask, supabase, werkzeug)
```

## 🛠️ Installation

1. Create a virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Database Setup:
   - Create a Supabase project.
   - Initialize tables: `profiles` (Auth), `lectures` (Sessions), `attendance` (Logs).
   - Ensure the `lectures` table has a `subject` column (Type: text).
3. Run the development server:
   ```bash
   python app.py
   ```

---

## 📈 Commercial Value
This system is architected to be sold as a **SaaS (Software as a Service)**. It uses a stateless HMAC-based token system that is horizontally scalable and extremely secure against attendance fraud, making it a high-value asset for educational institutions.
