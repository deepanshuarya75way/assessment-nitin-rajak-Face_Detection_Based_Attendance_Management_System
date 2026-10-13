# Face_Detection_Based_Attendance_Management_System

A web-based attendance management system that uses face recognition to automatically mark student attendance in real time, eliminating manual roll calls and proxy attendance.

Overview

Traditional attendance methods — manual roll calls, paper registers, RFID cards — are time-consuming, error-prone, and vulnerable to proxy attendance. This project solves that by combining a face recognition pipeline with a full-featured web application: a standard webcam captures live video, detects and recognizes registered students, and automatically logs their attendance with date, time, and period — no extra hardware required.

Features
Face-based attendance marking — real-time detection and recognition from a live webcam feed
Student registration module — captures 20–30 face images per student to train the recognition model
Role-based dashboards
Teachers: register students, manage subjects, enroll students in subjects, mark/view attendance, generate reports
Students: view subject-wise attendance summaries (total classes, present, absent, percentage) and date/period attendance matrices
Admin: manage teacher accounts (add, edit, reset password, delete)
Date-wise and period-wise attendance matrix visualization
Export attendance data to Excel (XLSX) and CSV
Secure authentication with hashed passwords (PBKDF2) and role-based access control
Privacy-conscious storage — stores face encodings, not raw images, in the production database

Tech Stack
Component	Technology
Face Recognition	face_recognition library (built on dlib's deep learning model, ResNet-34)
Backend	Flask (Python)
Database	SQLite with SQLAlchemy ORM
Frontend	Bootstrap 5, Chart.js
Computer Vision	OpenCV
Camera Input	Standard USB/built-in webcam

How It Works
A teacher registers a student by capturing 20–30 face images via webcam.
The system trains a face recognition model on the captured images, storing face encodings (not raw photos).
During a class period, the webcam captures a live feed; the system detects faces and matches them against the trained model.
Matched students are automatically marked present in the database, tagged with date, time, and period.
Teachers and students can view attendance through role-specific dashboards, with matrix views and exportable reports.
Project Scope

In scope: face-based attendance marking, student registration, teacher/student/admin dashboards, SQLite-backed storage, Excel/CSV export, date & period attendance matrices.

Out of scope (possible future work): mobile app, external biometric hardware integration, real-time SMS/email alerts, multi-campus sync, advanced liveness detection (e.g., eye-blink checks).

Getting Started

Note: the trained face recognition model, student face dataset, and local virtual environment are intentionally excluded from this repository (see .gitignore) to protect student privacy and keep the repo lightweight.

Clone the repository
bash
   git clone https://github.com/Nitin-8053/Face_Detection_Based_Attendance_Management_System.git
   cd Face_Detection_Based_Attendance_Management_System/Attendance_system

Create a virtual environment and install dependencies
bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   pip install -r requirements.txt

Run the application
bash
   python app.py

Register students via the teacher dashboard to build your own face dataset, then train the model before marking attendance.
