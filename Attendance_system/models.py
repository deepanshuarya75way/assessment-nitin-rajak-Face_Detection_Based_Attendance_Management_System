from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Student specific fields
    roll_number = db.Column(db.String(20), unique=True)
    class_name = db.Column(db.String(20))
    
    # Teacher specific fields
    teacher_id = db.Column(db.String(20), unique=True)
    department = db.Column(db.String(50))
    qualification = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    
    # Relationships
    subjects_taught = db.relationship('Subject', backref='teacher', lazy=True, foreign_keys='Subject.teacher_id')
    attendance_marked = db.relationship('Attendance', backref='marker', lazy=True, foreign_keys='Attendance.marked_by')
    attendances = db.relationship('Attendance', backref='student', lazy=True, foreign_keys='Attendance.student_id')
    enrolled_subjects = db.relationship('StudentSubject', backref='student', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username} - {self.role}>'


class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(20), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('StudentSubject', backref='subject', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='subject', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Subject {self.name} - {self.class_name}>'


class StudentSubject(db.Model):
    __tablename__ = 'student_subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a student can be enrolled in a subject only once
    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', name='unique_enrollment'),
    )
    
    def __repr__(self):
        return f'<Enrollment Student:{self.student_id} Subject:{self.subject_id}>'


class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    period = db.Column(db.Integer, nullable=False)  # 1, 2, 3, 4, etc.
    status = db.Column(db.String(10), nullable=False)  # 'present' or 'absent'
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique attendance record per student per subject per date per period
    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'date', 'period', 
                           name='unique_attendance'),
    )
    
    def __repr__(self):
        return f'<Attendance {self.date} P{self.period} - {self.status}>'


# Optional: Add indexes for better query performance
db.Index('idx_attendance_student', Attendance.student_id)
db.Index('idx_attendance_subject', Attendance.subject_id)
db.Index('idx_attendance_date', Attendance.date)
db.Index('idx_user_role', User.role)
db.Index('idx_subject_teacher', Subject.teacher_id)