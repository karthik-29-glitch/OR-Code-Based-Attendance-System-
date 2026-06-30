import os
import json
import time
import uuid
import math
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
# Used for securely signing session cookies
app.secret_key = os.environ.get('SECRET_KEY', 'default_dev_key')

# --- Supabase Initialization ---
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_KEY')

supabase_initialized = False
try:
    if supabase_url and supabase_key:
        import socket
        
        # Globally force Supabase resolution to a verified Cloudflare Edge IP
        # This completely circumvents Windows DNS poisoning / IPv6 blackholes (WinError 10060)
        old_getaddrinfo = socket.getaddrinfo
        def new_getaddrinfo(host, *args, **kwargs):
            if host and 'supabase.co' in host:
                # 172.64.149.246 is the official Cloudflare Anycast IP for Supabase
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('172.64.149.246', 443))]
            return old_getaddrinfo(host, *args, **kwargs)
        socket.getaddrinfo = new_getaddrinfo
        
        supabase: Client = create_client(supabase_url, supabase_key)
        supabase_initialized = True
    else:
        print("Warning: Missing SUPABASE_URL or SUPABASE_KEY in environment.")
except Exception as e:
    print(f"Warning: Supabase initialization failed. Error: {e}")

# --- Haversine Formula ---
def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth surface.
    Returns distance in meters.
    """
    R = 6371000 # Radius of the earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

# --- Authentication Decorator ---
def login_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session or session.get('role') != role:
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Routes ---

@app.route('/')
def index():
    if 'user' in session:
        if session.get('role') == 'faculty':
            return redirect(url_for('faculty_dashboard'))
        return redirect(url_for('student_scanner'))
    return render_template('index.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    """Secure login and registration separated by role."""
    if role not in ['student', 'faculty']:
        return redirect(url_for('index'))
        
    error = None
    if request.method == 'POST':
        action = request.form.get('action') # 'login' or 'register'
        password = request.form.get('password')
        
        if not supabase_initialized:
            error = "Database configuration error. Please check your .env settings."
            return render_template('login.html', error=error, role=role)
            
        # Get username (fallback to email just in case)
        username = request.form.get('username') or request.form.get('email')
        
        try:
            from werkzeug.security import generate_password_hash, check_password_hash
            
            if action == 'register':
                # Security Check: Faculty MUST provide the Admin Master Password to create an account
                if role == 'faculty':
                    admin_pwd = request.form.get('admin_password', '').strip()
                    actual_admin_pwd = os.environ.get('ADMIN_PASSWORD', 'supersecret123').strip().replace('"', '').replace("'", "")
                    if admin_pwd != actual_admin_pwd:
                        error = "Invalid Admin Registration Code! You are not authorized to create a Faculty profile."
                        return render_template('login.html', error=error, role=role)
                        
                # Password constraint check
                if len(password) < 6:
                    error = "Password minimum length is 6 characters."
                    return render_template('login.html', error=error, role=role)
                        
                # Register new user in profiles table
                existing = supabase.table('profiles').select('email').eq('email', username).execute()
                if existing.data:
                    error = "Account already exists! Please just sign in."
                else:
                    name = username.split('@')[0].capitalize()
                    # explicitly use pbkdf2 to prevent extremely slow scrypt defaults which cause timeouts
                    hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
                    supabase.table('profiles').insert({
                        "email": username, 
                        "name": name, 
                        "role": role,
                        "password_hash": hashed_pw
                    }).execute()
                    
                    flash(f"Account created successfully! Welcome, {name}.", "success")
                    session['user'] = username
                    session['role'] = role
                    if role == 'faculty':
                        return redirect(url_for('faculty_dashboard'))
                    return redirect(url_for('student_scanner'))
                    
            elif action == 'login':
                # Login existing user
                response = supabase.table('profiles').select('*').eq('email', username).execute()
                if response.data:
                    user_data = response.data[0]
                    stored_hash = user_data.get('password_hash')
                    
                    if stored_hash and check_password_hash(stored_hash, password):
                        if user_data.get('role') != role:
                            error = f"This account is registered for {(user_data.get('role') or 'another').capitalize()}. Please use that portal."
                        else:
                            session['user'] = username
                            session['role'] = role
                            if role == 'faculty':
                                return redirect(url_for('faculty_dashboard'))
                            return redirect(url_for('student_scanner'))
                    else:
                        error = "Invalid username or incorrect password."
                else:
                    error = "Username does not exist. Please register for a new account."
                    
        except Exception as e:
            print(f"Auth Error: {e}")
            error = f"Authentication failed: {str(e)}"
                
    return render_template('login.html', error=error, role=role)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/faculty')
@login_required('faculty')
def faculty_dashboard():
    return render_template('faculty.html', user=session['user'])

@app.route('/faculty/analytics', methods=['GET', 'POST'])
@login_required('faculty')
def analytics_dashboard():
    error = None
    if request.method == 'POST':
        admin_pwd = request.form.get('admin_password', '').strip()
        actual_admin_pwd = os.environ.get('ADMIN_PASSWORD', 'supersecret123').strip().replace('"', '').replace("'", "")
        if admin_pwd == actual_admin_pwd:
            session['is_admin'] = True
        else:
            error = "Invalid Admin Password! Access Denied."
            return render_template('faculty.html', user=session['user'], error=error, show_admin_modal=True)
            
    if not session.get('is_admin'):
        # Reject direct GET requests without session
        return redirect(url_for('faculty_dashboard'))
        
    try:
        # Fetch all global data for the dashboard
        lectures_res = supabase.table('lectures').select('*').order('created_at', desc=True).execute()
        attendance_res = supabase.table('attendance').select('*').execute()
        profiles_res = supabase.table('profiles').select('email, name').eq('role', 'student').execute()
        
        return render_template('analytics.html', 
                               user=session['user'], 
                               lectures=lectures_res.data, 
                               attendance=attendance_res.data,
                               profiles=profiles_res.data)
    except Exception as e:
        print(f"Analytics Error: {e}")
        return redirect(url_for('faculty_dashboard'))

@app.route('/student')
@login_required('student')
def student_scanner():
    try:
        # Calculate total possible lectures AND store them for subject-wise mapping
        lectures_res = supabase.table('lectures').select('*').execute()
        all_lectures = lectures_res.data if lectures_res.data else []
        total_lectures = len(all_lectures)
        
        # Fetch this specific student's actual attendance records
        attendance_res = supabase.table('attendance').select('*').eq('student_email', session['user']).order('marked_at', desc=True).execute()
        student_records = attendance_res.data if attendance_res.data else []
        
        # Map lecture_id -> subject
        lecture_map = {l['lecture_id']: l.get('subject', 'Unknown') for l in all_lectures}
        
        # Calculate subject-wise totals
        subject_totals = {}
        for l in all_lectures:
            subj = l.get('subject', 'Unknown')
            subject_totals[subj] = subject_totals.get(subj, 0) + 1
            
        subject_attended = {}
        for r in student_records:
            subj = lecture_map.get(r['lecture_id'], 'Unknown')
            subject_attended[subj] = subject_attended.get(subj, 0) + 1
            r['subject_name'] = subj # Attach it to the record for the template!
            
        subject_stats = []
        for subj, total in subject_totals.items():
            attended = subject_attended.get(subj, 0)
            subject_stats.append({
                'subject': subj,
                'total': total,
                'attended': attended,
                'percent': int((attended / total) * 100) if total > 0 else 0
            })
            
        # Sort subjects alphabetically
        subject_stats = sorted(subject_stats, key=lambda x: x['subject'])
        
        return render_template('student_scanner.html', 
                               user=session['user'],
                               total_lectures=total_lectures,
                               student_records=student_records,
                               subject_stats=subject_stats)
    except Exception as e:
        print(f"Student Portal Error: {e}")
        return render_template('student_scanner.html', user=session['user'], total_lectures=0, student_records=[], subject_stats=[])

# --- API Endpoints ---

@app.route('/api/create_lecture', methods=['POST'])
@login_required('faculty')
def create_lecture():
    """Faculty creates a new lecture and receives data for the QR code."""
    if not supabase_initialized:
        return jsonify({'error': 'Supabase not initialized. Check server settings.'}), 500
        
    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')
    subject = data.get('subject', 'General/Other')
    
    if lat is None or lng is None:
        return jsonify({'error': 'Location is required to generate the QR code.'}), 400
        
    lecture_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    try:
        # Store in Supabase 'lectures' table
        supabase.table('lectures').insert({
            'lecture_id': lecture_id,
            'faculty_email': session['user'],
            'subject': subject,
            'lat': float(lat),
            'lng': float(lng),
            'active': True
        }).execute()
        
        return jsonify({
            'success': True, 
            'lecture_id': lecture_id,
            'subject': subject
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import hmac
import hashlib

def generate_qr_signature(lecture_id, timestamp):
    msg = f"{lecture_id}:{timestamp}"
    return hmac.new(app.secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()

@app.route('/api/get_qr_payload/<lecture_id>', methods=['GET'])
@login_required('faculty')
def get_qr_payload(lecture_id):
    """Generates a dynamic 10-second HMAC signed QR payload."""
    timestamp = int(time.time())
    sig = generate_qr_signature(lecture_id, timestamp)
    qr_data = {
        'lecture_id': lecture_id,
        'timestamp': timestamp,
        'sig': sig
    }
    return jsonify({'success': True, 'qr_data': json.dumps(qr_data)})

@app.route('/api/submit_attendance', methods=['POST'])
@login_required('student')
def submit_attendance():
    """Student submits attendance carrying their location and QR code data."""
    if not supabase_initialized:
        return jsonify({'error': 'Server error: Supabase not initialized.'}), 500
        
    data = request.json
    student_lat = data.get('lat')
    student_lng = data.get('lng')
    qr_data_str = data.get('qr_data')
    
    if not all([student_lat, student_lng, qr_data_str]):
        return jsonify({'error': 'Missing required location or QR data.'}), 400
        
    try:
        # Decode the scanned QR data
        qr_data = json.loads(qr_data_str)
        lecture_id = qr_data.get('lecture_id')
        qr_timestamp = qr_data.get('timestamp')
        qr_sig = qr_data.get('sig')
        
        if not lecture_id or not qr_timestamp or not qr_sig:
            return jsonify({'error': 'Invalid or corrupted QR code format.'}), 400
            
        current_time = int(time.time())
        # Security Check #1: Expire dynamic QR codes after 15 seconds!!
        # Instantly stops WhatsApp/Screenshot cheating.
        if current_time - qr_timestamp > 15:
            return jsonify({'error': 'This QR code expired! Please point your camera at the live screen.'}), 400
            
        # Security Check #2: Cryptographic HMAC Verification
        # Prevents students from forging a payload with a fake recent timestamp
        expected_sig = generate_qr_signature(lecture_id, qr_timestamp)
        if not hmac.compare_digest(qr_sig, expected_sig):
            return jsonify({'error': 'Forged QR code signature detected! incident logged.'}), 403
            
        # Fetch actual lecture data from DB
        response = supabase.table('lectures').select('*').eq('lecture_id', lecture_id).execute()
        
        if not response.data or not response.data[0].get('active'):
            return jsonify({'error': 'Invalid or inactive lecture session.'}), 400
            
        lecture = response.data[0]
        faculty_lat = lecture.get('lat')
        faculty_lng = lecture.get('lng')
        
        # Security Check #2: Verifying Location Distance
        distance = haversine(float(student_lat), float(student_lng), faculty_lat, faculty_lng)
        
        if distance <= 1000.0:
            # Update student attendance in Supabase
            supabase.table('attendance').insert({
                'lecture_id': lecture_id,
                'student_email': session["user"],
                'distance': distance,
                'verified': True
            }).execute()
            return jsonify({'success': True, 'message': 'Attendance marked successfully!', 'distance': round(distance, 2)})
        else:
            return jsonify({'error': f'Attendance Denied. Distance: {round(distance, 2)}m. Must be within 500m of the faculty.'}), 403
            
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid QR format. Could not parse JSON.'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    # Ad-hoc SSL setup could be added here for local mobile testing (getUserMedia requires HTTPS).
    # Services like Render/Vercel provide HTTPS by default.
    app.run(host='0.0.0.0', port=5000, debug=True)
