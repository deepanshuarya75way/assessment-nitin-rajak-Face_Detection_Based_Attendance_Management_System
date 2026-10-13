import cv2
import numpy as np
import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, Subject, StudentSubject, Attendance
from functools import wraps
import pandas as pd
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['DATASET_FOLDER'] = 'dataset'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATASET_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Role-based access decorators
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('Access denied. Teachers only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables and default data
with app.app_context():
    db.create_all()
    
    # Create default admin/teacher if not exists
    if not User.query.filter_by(username='teacher').first():
        teacher = User(
            username='teacher',
            email='teacher@school.com',
            role='teacher',
            name='Default Teacher',
            teacher_id='T001',
            department='Computer Science',
            qualification='PhD',
            phone='9876543210'
        )
        teacher.set_password('teacher123')
        db.session.add(teacher)
        db.session.commit()
        print("Default teacher created: username='teacher', password='teacher123'")
    
    # Create sample teachers
    if User.query.filter_by(role='teacher').count() <= 1:  # If only default teacher exists
        sample_teachers = [
            {
                'name': 'Dr. Rajesh Kumar',
                'teacher_id': 'T001',
                'email': 'rajesh.kumar@college.edu',
                'department': 'Computer Science',
                'qualification': 'PhD, M.Tech',
                'phone': '9876543210',
                'password': 'teacher123'
            },
            {
                'name': 'Prof. Sunita Sharma',
                'teacher_id': 'T002',
                'email': 'sunita.sharma@college.edu',
                'department': 'Mathematics',
                'qualification': 'M.Sc, B.Ed',
                'phone': '9876543211',
                'password': 'teacher123'
            },
            {
                'name': 'Dr. Amit Patel',
                'teacher_id': 'T003',
                'email': 'amit.patel@college.edu',
                'department': 'Physics',
                'qualification': 'PhD',
                'phone': '9876543212',
                'password': 'teacher123'
            }
        ]
        
        for teacher_data in sample_teachers:
            if not User.query.filter_by(teacher_id=teacher_data['teacher_id']).first():
                teacher = User(
                    username=f"teacher_{teacher_data['teacher_id']}",
                    email=teacher_data['email'],
                    role='teacher',
                    name=teacher_data['name'],
                    teacher_id=teacher_data['teacher_id'],
                    department=teacher_data['department'],
                    qualification=teacher_data['qualification'],
                    phone=teacher_data['phone']
                )
                teacher.set_password(teacher_data['password'])
                db.session.add(teacher)
        
        db.session.commit()
        print("Sample teachers created!")

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        role = request.form.get('role')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            role=role,
            name=name
        )
        
        if role == 'student':
            user.roll_number = request.form.get('roll_number')
            user.class_name = request.form.get('class_name')
        elif role == 'teacher':
            user.teacher_id = request.form.get('teacher_id')
            user.department = request.form.get('department')
            user.qualification = request.form.get('qualification')
            user.phone = request.form.get('phone')
        
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))
# ==================== TEST ROUTE ====================
@app.route('/test')
def test():
    return render_template('test.html')
# ==================== DASHBOARD ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'teacher':
        # Get teacher's subjects
        subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
        
        # Get recent attendance
        recent_attendance = Attendance.query.join(Subject).filter(
            Subject.teacher_id == current_user.id
        ).order_by(Attendance.date.desc()).limit(10).all()
        
        return render_template('teacher/dashboard.html', 
                             subjects=subjects, 
                             recent_attendance=recent_attendance)
    
    else:  # student
        # Get student's enrolled subjects
        enrollments = StudentSubject.query.filter_by(student_id=current_user.id).all()
        
        total_classes = 0
        total_present = 0
        attendance_summary = []
        
        for enrollment in enrollments:
            subject = enrollment.subject
            
            # Total classes for this subject (unique date+period combinations)
            total = Attendance.query.filter_by(
                subject_id=subject.id
            ).distinct(Attendance.date, Attendance.period).count()
            
            # Student's present count for this subject
            present = Attendance.query.filter_by(
                student_id=current_user.id,
                subject_id=subject.id,
                status='present'
            ).count()
            
            absent = total - present
            percentage = (present / total * 100) if total > 0 else 0
            
            total_classes += total
            total_present += present
            
            attendance_summary.append({
                'subject': subject.name,
                'teacher': subject.teacher.name if subject.teacher else 'Unknown',
                'total': total,
                'present': present,
                'absent': absent,
                'percentage': round(percentage, 2),
                'subject_id': subject.id
            })
        
        total_absent = total_classes - total_present
        overall_percentage = (total_present / total_classes * 100) if total_classes > 0 else 0
        
        return render_template('student/dashboard.html',
                             attendance_summary=attendance_summary,
                             total_subjects=len(enrollments),
                             total_classes=total_classes,
                             total_present=total_present,
                             total_absent=total_absent,
                             overall_percentage=round(overall_percentage, 2))

# ==================== TEACHER MANAGEMENT ROUTES ====================

@app.route('/admin/teachers')
@login_required
@teacher_required
def manage_teachers():
    """View all teachers"""
    teachers = User.query.filter_by(role='teacher').all()

    teachers_data = []
    for t in teachers:
        teachers_data.append({
            "id": t.id,
            "username": t.username,
            "name": t.name,
            "email": t.email,
            "teacher_id": t.teacher_id,
            "department": t.department,
            "qualification": t.qualification,
            "phone": t.phone
        })

    return render_template('admin/teachers.html', teachers=teachers_data)


@app.route('/admin/add-teacher', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_teacher():
    """Add a new teacher"""
    if request.method == 'POST':
        name = request.form.get('name')
        teacher_id = request.form.get('teacher_id')
        email = request.form.get('email')
        department = request.form.get('department')
        qualification = request.form.get('qualification')
        phone = request.form.get('phone')
        password = request.form.get('password', 'teacher123')
        
        # Check if teacher_id already exists
        existing = User.query.filter_by(teacher_id=teacher_id).first()
        if existing:
            flash('Teacher ID already exists!', 'danger')
            return redirect(url_for('add_teacher'))
        
        # Check if email exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered!', 'danger')
            return redirect(url_for('add_teacher'))
        
        # Create username from teacher_id
        username = f"teacher_{teacher_id}"
        
        # Create new teacher
        teacher = User(
            username=username,
            email=email,
            role='teacher',
            name=name,
            teacher_id=teacher_id,
            department=department,
            qualification=qualification,
            phone=phone
        )
        teacher.set_password(password)
        
        db.session.add(teacher)
        db.session.commit()
        
        flash(f'Teacher added successfully! Username: {username}, Password: {password}', 'success')
        return redirect(url_for('manage_teachers'))
    
    return render_template('admin/add_teacher.html')

@app.route('/admin/edit-teacher/<int:teacher_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_teacher(teacher_id):
    """Edit teacher details"""
    teacher = User.query.get_or_404(teacher_id)
    
    if teacher.role != 'teacher':
        flash('Invalid teacher ID!', 'danger')
        return redirect(url_for('manage_teachers'))
    
    if request.method == 'POST':
        teacher.name = request.form.get('name')
        teacher.email = request.form.get('email')
        teacher.department = request.form.get('department')
        teacher.qualification = request.form.get('qualification')
        teacher.phone = request.form.get('phone')
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            teacher.set_password(new_password)
        
        db.session.commit()
        flash('Teacher updated successfully!', 'success')
        return redirect(url_for('manage_teachers'))
    
    return render_template('admin/edit_teacher.html', teacher=teacher)

@app.route('/admin/delete-teacher/<int:teacher_id>', methods=['POST'])
@login_required
@teacher_required
def delete_teacher(teacher_id):
    """Delete a teacher"""
    teacher = User.query.get_or_404(teacher_id)
    
    # Don't allow deleting yourself
    if teacher.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('manage_teachers'))
    
    # Check if teacher has subjects
    subjects = Subject.query.filter_by(teacher_id=teacher_id).first()
    if subjects:
        flash('Cannot delete teacher who has subjects assigned! Remove subjects first.', 'danger')
        return redirect(url_for('manage_teachers'))
    
    db.session.delete(teacher)
    db.session.commit()
    
    flash('Teacher deleted successfully!', 'success')
    return redirect(url_for('manage_teachers'))

@app.route('/admin/reset-teacher-password/<int:teacher_id>', methods=['POST'])
@login_required
@teacher_required
def reset_teacher_password(teacher_id):
    """Reset teacher password"""
    teacher = User.query.get_or_404(teacher_id)
    
    new_password = request.form.get('new_password', 'teacher123')
    teacher.set_password(new_password)
    db.session.commit()
    
    flash(f'Password for {teacher.name} reset to: {new_password}', 'success')
    return redirect(url_for('manage_teachers'))

# ==================== SUBJECT MANAGEMENT ROUTES ====================

@app.route('/teacher/subjects')
@login_required
@teacher_required
def manage_subjects():
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    students = User.query.filter_by(role='student').all()
    return render_template('teacher/subjects.html', subjects=subjects, students=students)

@app.route('/teacher/subject/add', methods=['POST'])
@login_required
@teacher_required
def add_subject():
    name = request.form.get('name')
    class_name = request.form.get('class_name')
    
    subject = Subject(
        name=name,
        class_name=class_name,
        teacher_id=current_user.id
    )
    db.session.add(subject)
    db.session.commit()
    
    flash('Subject added successfully!', 'success')
    return redirect(url_for('manage_subjects'))

@app.route('/teacher/subject/<int:subject_id>/enroll', methods=['POST'])
@login_required
@teacher_required
def enroll_student(subject_id):
    student_id = request.form.get('student_id')
    
    # Check if already enrolled
    existing = StudentSubject.query.filter_by(
        student_id=student_id,
        subject_id=subject_id
    ).first()
    
    if not existing:
        enrollment = StudentSubject(
            student_id=student_id,
            subject_id=subject_id
        )
        db.session.add(enrollment)
        db.session.commit()
        flash('Student enrolled successfully!', 'success')
    else:
        flash('Student already enrolled!', 'warning')
    
    return redirect(url_for('manage_subjects'))

@app.route('/teacher/subject/<int:subject_id>/remove-student/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def remove_student_from_subject(subject_id, student_id):
    enrollment = StudentSubject.query.filter_by(
        student_id=student_id,
        subject_id=subject_id
    ).first()
    
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
        flash('Student removed from subject!', 'success')
    
    return redirect(url_for('manage_subjects'))

# ==================== STUDENT MANAGEMENT ROUTES ====================

@app.route('/teacher/add-student', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_student():
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        class_name = request.form.get('class_name', '').strip()
        email = request.form.get('email', '').strip()
        
        # Validate required fields
        if not first_name or not last_name:
            flash('First name and last name are required!', 'danger')
            return redirect(url_for('add_student'))
            
        if not roll_number:
            flash('Roll number is required!', 'danger')
            return redirect(url_for('add_student'))
            
        if not class_name:
            flash('Class is required!', 'danger')
            return redirect(url_for('add_student'))
        
        # Combine first and last name
        full_name = f"{first_name} {last_name}".strip()
        
        # Check if student already exists
        existing = User.query.filter_by(roll_number=roll_number).first()
        if existing:
            flash('Student with this roll number already exists!', 'danger')
            return redirect(url_for('add_student'))
        
        # Create username from roll number
        username = f"student_{roll_number}"
        
        # Create new student user
        student = User(
            username=username,
            email=email if email else f"{roll_number}@student.edu",  # Default email if empty
            role='student',
            name=full_name,  # ← This was missing!
            roll_number=roll_number,
            class_name=class_name
        )
        student.set_password('student123')  # Default password
        
        try:
            db.session.add(student)
            db.session.commit()
            flash(f'Student {full_name} added successfully! Username: {username}, Password: student123', 'success')
            return redirect(url_for('capture_faces', student_id=student.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')
            return redirect(url_for('add_student'))
    
    return render_template('teacher/add_student.html')

@app.route('/teacher/capture-faces/<int:student_id>')
@login_required
@teacher_required
def capture_faces(student_id):
    student = User.query.get_or_404(student_id)
    return render_template('teacher/capture_faces.html', student=student)

@app.route('/api/save-face', methods=['POST'])
@login_required
@teacher_required
def save_face():
    data = request.json
    student_id = data.get('student_id')
    image_data = data.get('image')  # Base64 image
    
    # Create student directory
    student_dir = os.path.join(app.config['DATASET_FOLDER'], str(student_id))
    os.makedirs(student_dir, exist_ok=True)
    
    # Save image
    import base64
    import uuid
    
    # Remove header from base64
    img_data = base64.b64decode(image_data.split(',')[1])
    
    # Generate unique filename
    img_count = len(os.listdir(student_dir))
    img_filename = f"{img_count+1}_{uuid.uuid4().hex[:8]}.jpg"
    img_path = os.path.join(student_dir, img_filename)
    
    with open(img_path, 'wb') as f:
        f.write(img_data)
    
    return jsonify({
        'success': True, 
        'count': img_count + 1,
        'message': f'Captured {img_count + 1} images'
    })

@app.route('/teacher/train-model/<int:student_id>')
@login_required
@teacher_required
def train_model(student_id):
    print("🔥 TRAIN ROUTE HIT")

    try:
        from face_recognizer import FaceRecognizer
        
        student = User.query.get_or_404(student_id)
        print("Student found:", student.id)

        recognizer = FaceRecognizer()
        print("Recognizer created")

        num_faces = recognizer.train_from_dataset(dataset_path="dataset")
        print("Faces found:", num_faces)

        if num_faces > 0:
            recognizer.save_model()
            print("Model saved ✅")
            flash(f'Model trained successfully with {num_faces} face samples!', 'success')
        else:
            print("⚠️ No faces found")
            flash('No faces found to train!', 'warning')

    except Exception as e:
        print("❌ ERROR:", e)
        flash(f'Error training model: {str(e)}', 'danger')
    
    return redirect(url_for('manage_subjects'))

# ==================== ATTENDANCE MARKING ROUTES ====================

@app.route('/teacher/mark-attendance')
@login_required
@teacher_required
def mark_attendance_page():
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher/mark_attendance.html', subjects=subjects)

@app.route('/teacher/mark-attendance/<int:subject_id>')
@login_required
@teacher_required
def mark_attendance_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    students = User.query.join(StudentSubject).filter(
        StudentSubject.subject_id == subject_id
    ).all()
    
    return render_template('teacher/mark_attendance_camera.html', 
                         subject=subject, 
                         students=students)

@app.route('/api/recognize-face', methods=['POST'])
@login_required
@teacher_required
def recognize_face():
    """API endpoint for face recognition"""
    try:
        from face_recognizer import FaceRecognizer
        
        data = request.json
        image_data = data.get('image')
        subject_id = data.get('subject_id')
        
        # Decode base64 image
        import base64
        from PIL import Image
        from io import BytesIO
        
        # Remove header from base64
        img_str = image_data.split(',')[1]
        img_bytes = base64.b64decode(img_str)
        
        # Convert to numpy array
        img = Image.open(BytesIO(img_bytes))
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Load model if not loaded
        recognizer = FaceRecognizer()
        if not recognizer.load_model():
            return jsonify({'success': False, 'message': 'Model not trained yet'})
        
        # Recognize faces
        student_ids = recognizer.recognize_faces(frame)
        
        # Get student details
        students = []
        for sid in student_ids:
            student = User.query.get(sid)
            if student:
                # Check if student is enrolled in this subject
                enrolled = StudentSubject.query.filter_by(
                    student_id=sid, 
                    subject_id=subject_id
                ).first()
                
                if enrolled:
                    students.append({
                        'id': student.id,
                        'name': student.name,
                        'roll_number': student.roll_number
                    })
        
        return jsonify({'success': True, 'students': students})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/teacher/process-attendance', methods=['POST'])
@login_required
@teacher_required
def process_attendance():
    data = request.json
    subject_id = data.get('subject_id')
    date_str = data.get('date')
    period = data.get('period')
    present_students = data.get('present_students', [])
    
    attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Get all enrolled students
    enrolled = StudentSubject.query.filter_by(subject_id=subject_id).all()
    student_ids = [e.student_id for e in enrolled]
    
    # Mark attendance for each student
    for student_id in student_ids:
        status = 'present' if student_id in present_students else 'absent'
        
        # Check if attendance already marked
        existing = Attendance.query.filter_by(
            student_id=student_id,
            subject_id=subject_id,
            date=attendance_date,
            period=period
        ).first()
        
        if existing:
            existing.status = status
        else:
            attendance = Attendance(
                student_id=student_id,
                subject_id=subject_id,
                date=attendance_date,
                period=period,
                status=status,
                marked_by=current_user.id
            )
            db.session.add(attendance)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Attendance marked successfully!'})

# ==================== ATTENDANCE VIEWING ROUTES ====================

@app.route('/teacher/view-attendance')
@login_required
@teacher_required
def view_attendance():
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher/view_attendance.html', subjects=subjects)

@app.route('/teacher/attendance-data')
@login_required
@teacher_required
def attendance_data():
    subject_id = request.args.get('subject_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = Attendance.query.join(Subject).filter(Subject.teacher_id == current_user.id)
    
    if subject_id and subject_id != '':
        query = query.filter(Attendance.subject_id == int(subject_id))
    if date_from:
        query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    attendance = query.order_by(Attendance.date.desc(), Attendance.period).all()
    
    data = []
    for a in attendance:
        data.append({
            'date': a.date.strftime('%Y-%m-%d'),
            'period': a.period,
            'student': a.student.name if a.student else 'Unknown',
            'roll': a.student.roll_number if a.student else 'N/A',
            'subject': a.subject.name if a.subject else 'Unknown',
            'status': a.status,
            'marked_by': a.marker.name if a.marker else 'Unknown'  # ← FIXED HERE
        })
    
    return jsonify(data)

@app.route('/teacher/matrix-data')
@login_required
@teacher_required
def matrix_data():
    subject_id = request.args.get('subject_id')
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    
    subject = Subject.query.get_or_404(subject_id)
    
    # Get all students enrolled
    students = User.query.join(StudentSubject).filter(
        StudentSubject.subject_id == subject_id
    ).order_by(User.roll_number).all()
    
    # Get attendance records for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    attendance = Attendance.query.filter(
        Attendance.subject_id == subject_id,
        Attendance.date >= start_date,
        Attendance.date < end_date
    ).all()
    
    # Build matrix
    matrix = {}
    dates = set()
    periods = set()
    
    for a in attendance:
        dates.add(a.date)
        periods.add(a.period)
        date_str = a.date.strftime('%Y-%m-%d')
        key = f"{a.student_id}_{date_str}_{a.period}"
        matrix[key] = a.status
    
    # Convert to sorted lists
    dates = sorted(list(dates))
    periods = sorted(list(periods))
    
    # If no periods found, set default periods (1-6)
    if not periods:
        periods = [1, 2, 3, 4, 5, 6]
    
    # Calculate present and absent counts for summary cards
    present_count = sum(1 for v in matrix.values() if v == 'present')
    absent_count = sum(1 for v in matrix.values() if v == 'absent')
    
    return render_template('teacher/matrix_table.html',
                         subject=subject,
                         students=students,
                         dates=dates,
                         periods=periods,
                         matrix=matrix,
                         month=month,
                         year=year,
                         present_count=present_count,
                         absent_count=absent_count)


@app.route('/teacher/matrix-view')
@login_required
@teacher_required
def matrix_view():
    """Display subject selection page for attendance matrix"""
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher/matrix_view.html', subjects=subjects)

# ==================== STUDENT ATTENDANCE VIEWING ROUTES ====================

@app.route('/student/attendance')
@login_required
@student_required
def student_attendance():
    # Get subject-wise summary
    enrollments = StudentSubject.query.filter_by(student_id=current_user.id).all()
    summary = []
    
    for enrollment in enrollments:
        subject = enrollment.subject
        total = Attendance.query.filter_by(
            subject_id=subject.id
        ).distinct(Attendance.date, Attendance.period).count()
        
        present = Attendance.query.filter_by(
            student_id=current_user.id,
            subject_id=subject.id,
            status='present'
        ).count()
        
        absent = total - present
        percentage = (present / total * 100) if total > 0 else 0
        
        summary.append({
            'subject': subject.name,
            'teacher': subject.teacher.name,
            'total': total,
            'present': present,
            'absent': absent,
            'percentage': round(percentage, 2)
        })
    
    return render_template('student/attendance_summary.html', summary=summary)

@app.route('/student/matrix-view')
@login_required
@student_required
def student_matrix():
    subjects = Subject.query.join(StudentSubject).filter(
        StudentSubject.student_id == current_user.id
    ).all()
    
    return render_template('student/matrix_view.html', subjects=subjects)

@app.route('/student/matrix-data')
@login_required
@student_required
def student_matrix_data():
    subject_id = request.args.get('subject_id')
    
    # CRITICAL: Convert to integers
    try:
        month = int(request.args.get('month', datetime.now().month))
        year = int(request.args.get('year', datetime.now().year))
    except (TypeError, ValueError):
        month = datetime.now().month
        year = datetime.now().year
    
    subject = Subject.query.get_or_404(subject_id)
    
    # Check if student is enrolled
    is_enrolled = StudentSubject.query.filter_by(
        student_id=current_user.id,
        subject_id=subject_id
    ).first()
    
    if not is_enrolled:
        flash('You are not enrolled in this subject!', 'warning')
        return redirect(url_for('student_matrix'))
    
    # Get attendance records for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    attendance = Attendance.query.filter(
        Attendance.subject_id == subject_id,
        Attendance.student_id == current_user.id,
        Attendance.date >= start_date,
        Attendance.date < end_date
    ).order_by(Attendance.date, Attendance.period).all()
    
    # Build matrix
    matrix = {}
    dates = set()
    periods = set()
    
    for a in attendance:
        dates.add(a.date)
        periods.add(a.period)
        key = f"{a.date}_{a.period}"
        matrix[key] = a.status
    
    dates = sorted(list(dates))
    periods = sorted(list(periods))
    
    return render_template('student/matrix_table.html',
                         subject=subject,
                         dates=dates,
                         periods=periods,
                         matrix=matrix,
                         month=month,
                         year=year)
# ==================== TEMPLATE CONTEXT PROCESSOR ====================

@app.context_processor
def utility_processor():
    def now():
        return datetime.now()
    return dict(now=now)

if __name__ == '__main__':
    app.run(debug=True)
