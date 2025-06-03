from flask import Flask, request, render_template, flash, redirect, url_for, session, logging, send_file, jsonify, Response, render_template_string
from flask_pymongo import PyMongo
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, DateTimeField, BooleanField, IntegerField, DecimalField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_mail import Mail, Message
from functools import wraps
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from coolname import generate_slug
from datetime import timedelta, datetime
from objective import ObjectiveTest
from subjective import SubjectiveTest
from deepface import DeepFace
import pandas as pd
import stripe
import operator
import functools
import math, random
import csv
import cv2
import numpy as np
import json
import base64
from wtforms_components import TimeField
from wtforms.fields import EmailField, DateField
from wtforms.validators import ValidationError, NumberRange
from flask_session import Session
from flask_cors import CORS, cross_origin
import camera
from bson.objectid import ObjectId # Import ObjectId for MongoDB _id
from flask import Request

app = Flask(__name__)
app.secret_key = 'sem8project'

# Increase Flask’s request size limit
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/myproctor"
mongo = PyMongo(app)

# --- EMAIL CONFIGURATION: YOU MUST UPDATE THESE VALUES ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com' 
app.config['MAIL_PORT'] = 587 # Your SMTP port (usually 587 for TLS, or 465 for SSL)
app.config['MAIL_USERNAME'] = 'mayankmewari210@gmail.com'
app.config['MAIL_PASSWORD'] = 'quhq gded zcyc qblp'
app.config['MAIL_USE_TLS'] = True # Set to True for TLS, False for SSL
app.config['MAIL_USE_SSL'] = False # Set to True for SSL, False for TLS (only one should be True)
# --- END EMAIL CONFIGURATION ---

app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_TYPE'] = 'filesystem'
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SESSION_PERMANENT'] = False

stripe_keys = {
    "secret_key": "dummy",
    "publishable_key": "dummy",
}

stripe.api_key = stripe_keys["secret_key"]

mail = Mail(app)
Session(app)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'



sender = 'mayankmewari210@gmail.com' 

YOUR_DOMAIN = 'http://localhost:5000'

@app.route("/test_mail")
def test_mail():
    try:
        msg = Message("Hello from MyProctor", sender="mayankmewari210@gmail.com", recipients=["your_email@gmail.com"])
        msg.body = "✅ This is a test email sent via Flask-Mail and Gmail SMTP."
        mail.send(msg)
        return "✅ Test email sent successfully!"
    except Exception as e:
        return f"❌ Failed to send test email: {str(e)}"

@app.before_request
def make_session_permanent():
    session.permanent = True

def user_role_professor(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            if session['user_role'] == "teacher":
                return f(*args, **kwargs)
            else:
                flash('You don\'t have privilege to access this page!', 'danger')
                return render_template("404.html")
        else:
            flash('Unauthorized, Please login!', 'danger')
            return redirect(url_for('login'))
    return wrap

def user_role_student(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            if session['user_role'] == "student":
                return f(*args, **kwargs)
            else:
                flash('You don\'t have privilege to access this page!', 'danger')
                return render_template("404.html")
        else:
            flash('Unauthorized, Please login!', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route("/config")
@user_role_professor
def get_publishable_key():
    stripe_config = {"publicKey": stripe_keys["publishable_key"]}
    return jsonify(stripe_config)

@app.route('/video_feed', methods=['GET', 'POST'])
@user_role_student
def video_feed():
    if request.method == "POST":
        imgData = request.form['data[imgData]']
        testid = request.form['data[testid]']
        voice_db = request.form['data[voice_db]']
        proctorData = camera.get_frame(imgData)
        jpg_as_text = proctorData['jpg_as_text']
        mob_status = proctorData['mob_status']
        person_status = proctorData['person_status']
        user_move1 = proctorData['user_move1']
        user_move2 = proctorData['user_move2']
        eye_movements = proctorData['eye_movements']

        # MongoDB: Insert into proctoring_log collection
        proctor_log_entry = {
            "email": session['email'],
            "name": session['name'],
            "test_id": testid,
            "voice_db": voice_db,
            "img_log": jpg_as_text.decode('utf-8'), # Store as string
            "user_movements_updown": user_move1,
            "user_movements_lr": user_move2,
            "user_movements_eyes": eye_movements,
            "phone_detection": mob_status,
            "person_status": person_status,
            "uid": session['uid'],
            "timestamp": datetime.now() # Add timestamp for logging
        }
        result = mongo.db.proctoring_log.insert_one(proctor_log_entry)

        if result.inserted_id:
            return "recorded image of video"
        else:
            return "error in video"

@app.route('/window_event', methods=['GET', 'POST'])
@user_role_student
def window_event():
    if request.method == "POST":
        testid = request.form['testid']
        # MongoDB: Insert into window_estimation_log collection
        window_event_entry = {
            "email": session['email'],
            "test_id": testid,
            "name": session['name'],
            "window_event": 1, # Assuming 1 means window event occurred
            "uid": session['uid'],
            "timestamp": datetime.now() # Add timestamp
        }
        result = mongo.db.window_estimation_log.insert_one(window_event_entry)

        if result.inserted_id:
            return "recorded window"
        else:
            return "error in window"

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'inr',
                        'unit_amount': 499 * 100,
                        'product_data': {
                            'name': 'Basic Exam Plan of 10 units',
                            'images': ['https://i.imgur.com/LsvO3kL_d.webp?maxwidth=760&fidelity=grand'],
                        },
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + '/success',
            cancel_url=YOUR_DOMAIN + '/cancelled',
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route("/livemonitoringtid")
@user_role_professor
def livemonitoringtid():
    # MongoDB: Find tests where proctoring_type is 1 (Live Monitoring)
    cresults = list(mongo.db.teachers.find({
        "email": session['email'],
        "uid": session['uid'],
        "proctoring_type": "1" # Assuming proctor_type is stored as string "0" or "1"
    }))

    if cresults:
        now = datetime.now()
        testids = []
        for a in cresults:
            # Convert string dates back to datetime objects for comparison
            start_dt = datetime.strptime(a['start'], "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(a['end'], "%Y-%m-%d %H:%M:%S")
            if start_dt <= now and end_dt >= now:
                testids.append(a['test_id'])
        return render_template("livemonitoringtid.html", cresults=testids)
    else:
        return render_template("livemonitoringtid.html", cresults=None)

@app.route('/live_monitoring', methods=['GET', 'POST'])
@user_role_professor
def live_monitoring():
    if request.method == 'POST':
        testid = request.form['choosetid']
        return render_template('live_monitoring.html', testid=testid)
    else:
        return render_template('live_monitoring.html', testid=None)

@app.route("/success")
@user_role_professor
def success():
    # MongoDB: Update user's examcredits
    result = mongo.db.users.update_one(
        {"email": session['email'], "uid": session['uid']},
        {"$inc": {"examcredits": 10}} # Increment examcredits by 10
    )
    if result.modified_count > 0:
        flash('Exam credits updated successfully.', 'success')
    else:
        flash('Failed to update exam credits.', 'danger')
    return render_template("success.html")

@app.route("/cancelled")
@user_role_professor
def cancelled():
    return render_template("cancelled.html")

@app.route("/payment")
@user_role_professor
def payment():
    # MongoDB: Fetch user's examcredits
    user = mongo.db.users.find_one(
        {"email": session['email'], "uid": session['uid']},
        {"examcredits": 1} # Project only examcredits field
    )
    callresults = user if user else {"examcredits": 0} # Default to 0 if user not found
    return render_template("payment.html", key=stripe_keys['publishable_key'], callresults=callresults)

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html")

@app.route('/calc')
def calc():
    return render_template('calc.html')

@app.route('/report_professor')
@user_role_professor
def report_professor():
    return render_template('report_professor.html')

@app.route('/student_index')
@user_role_student
def student_index():
    return render_template('student_index.html')

@app.route('/professor_index')
@user_role_professor
def professor_index():
    return render_template('professor_index.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/report_student')
@user_role_student
def report_student():
    return render_template('report_student.html')

@app.route('/report_professor_email', methods=['GET', 'POST'])
@user_role_professor
def report_professor_email():
    if request.method == 'POST':
        careEmail = "narender.rk10@gmail.com"
        cname = session['name']
        cemail = session['email']
        ptype = request.form['prob_type']
        cquery = request.form['rquery']
        msg1 = Message('PROBLEM REPORTED', sender=sender, recipients=[careEmail])
        mail.send(msg1)
        flash('Your Problem has been recorded.', 'success')
    return render_template('report_professor.html')

@app.route('/report_student_email', methods=['GET', 'POST'])
@user_role_student
def report_student_email():
    if request.method == 'POST':
        careEmail = "narender.rk10@gmail.com"
        cname = session['name']
        cemail = session['email']
        ptype = request.form['prob_type']
        cquery = request.form['rquery']
        msg1 = Message('PROBLEM REPORTED', sender=sender, recipients=[careEmail])
        msg1.body = " ".join(["NAME:", cname, "PROBLEM TYPE:", ptype, "EMAIL:", cemail, "", "QUERY:", cquery])
        mail.send(msg1)
        flash('Your Problem has been recorded.', 'success')
    return render_template('report_student.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        careEmail = "narender.rk10@gmail.com"
        cname = request.form['cname']
        cemail = request.form['cemail']
        cquery = request.form['cquery']
        msg1 = Message('Hello', sender=sender, recipients=[cemail])
        msg2 = Message('Hello', sender=sender, recipients=[careEmail])
        msg1.body = "YOUR QUERY WILL BE PROCESSED! WITHIN 24 HOURS"
        msg2.body = " ".join(["NAME:", cname, "EMAIL:", cemail, "QUERY:", cquery])
        mail.send(msg1)
        mail.send(msg2)
        flash('Your Query has been recorded.', 'success')
    return render_template('contact.html')

@app.route('/lostpassword', methods=['GET', 'POST'])
def lostpassword():
    if request.method == 'POST':
        lpemail = request.form['lpemail']
        # MongoDB: Find user by email
        user = mongo.db.users.find_one({'email': lpemail})
        if user:
            sesOTPfp = generateOTP()
            session['tempOTPfp'] = sesOTPfp
            session['seslpemail'] = lpemail
            try:
                msg1 = Message('Hillproctor.ai - OTP Verification for Lost Password', sender=sender, recipients=[lpemail])
                msg1.body = "Your OTP Verfication code for reset password is " + sesOTPfp + "."
                mail.send(msg1)
                return redirect(url_for('verifyOTPfp'))
            except Exception as mail_e:
                print(f"Error sending OTP email for lost password: {mail_e}")
                flash('Failed to send OTP email. Please check mail server configuration and try again.', 'danger')
                return render_template('lostpassword.html')
        else:
            return render_template('lostpassword.html', error="Account not found.")
    return render_template('lostpassword.html')

@app.route('/verifyOTPfp', methods=['GET', 'POST'])
def verifyOTPfp():
    if request.method == 'POST':
        fpOTP = request.form['fpotp']
        fpsOTP = session.get('tempOTPfp')
        if fpOTP == fpsOTP:
            return redirect(url_for('lpnewpwd'))
        else:
            flash("OTP is incorrect. Please try again.", "danger")
    return render_template('verifyOTPfp.html')

@app.route('/lpnewpwd', methods=['GET', 'POST'])
def lpnewpwd():
    if request.method == 'POST':
        npwd = request.form['npwd']
        cpwd = request.form['cpwd']
        slpemail = session.get('seslpemail')
        if npwd == cpwd:
            # MongoDB: Update user's password
            result = mongo.db.users.update_one(
                {"email": slpemail},
                {"$set": {"password": generate_password_hash(npwd)}}
            )
            if result.modified_count > 0:
                session.clear()
                return render_template('login.html', success="Your password was successfully changed.")
            else:
                flash("Failed to change password. User not found or password is the same.", "danger")
                return render_template('lpnewpwd.html')
        else:
            return render_template('lpnewpwd.html', error="Password doesn't matched.")
    return render_template('lpnewpwd.html')

@app.route('/generate_test')
@user_role_professor
def generate_test():
    return render_template('generatetest.html')

@app.route('/changepassword_professor')
@user_role_professor
def changepassword_professor():
    return render_template('changepassword_professor.html')

@app.route('/changepassword_student')
@user_role_student
def changepassword_student():
    return render_template('changepassword_student.html')

def generateOTP():
    digits = "0123456789"
    OTP = ""
    for i in range(5):
        OTP += digits[math.floor(random.random() * 10)]
    return OTP

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            print("Form data received:")
            for key, value in request.form.items():
                if key == 'image_hidden':
                    print(f"{key}: {len(value) if value else 0} characters")
                else:
                    print(f"{key}: {value}")

            required_fields = ['name', 'email', 'password', 'user_type', 'image_hidden']
            missing_fields = [field for field in required_fields if not request.form.get(field)]
            if missing_fields:
                error = f"Missing required fields: {', '.join(missing_fields)}"
                print(f"Registration failed: {error}")
                flash(error, 'danger')
                return render_template('register.html')

            # Extract form data
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            user_type = request.form['user_type']
            imgdata = request.form['image_hidden']

            # Check if user already exists
            existing_user = mongo.db.users.find_one({'email': email})
            if existing_user:
                flash("User with this email already exists.", "danger")
                return render_template("register.html")

            # Store in session temporarily for OTP verification
            session['tempName'] = name
            session['tempEmail'] = email
            session['tempPassword'] = password
            session['tempUT'] = user_type
            session['tempImage'] = imgdata

            # Generate and send OTP
            sesOTP = generateOTP()
            session['tempOTP'] = sesOTP

            try:
                msg1 = Message('Hillproctor.ai - OTP Verification', sender=sender, recipients=[email])
                msg1.body = f"New Account Opening - Your OTP Verification code is: {sesOTP}"
                mail.send(msg1)
                print("OTP sent successfully.")
            except Exception as mail_e:
                print(f"Error sending OTP email: {mail_e}")
                flash('Failed to send OTP email. Please check mail server configuration and try again.', 'danger')
                # If email sending fails, we should not proceed to verifyEmail as OTP won't be received.
                return render_template('register.html')

            return redirect(url_for('verifyEmail'))

        except Exception as e:
            print("Error during registration (general):", str(e))
            flash('An unexpected error occurred during registration. Please try again.', 'danger')
            return render_template('register.html')

    # GET request
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session and request.method == 'GET':
        flash('You appear to be already logged in.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password_candidate = request.form['password'].strip()
        user_type = request.form['user_type']
        imgdata1 = request.form['image_hidden']
        # Corrected query: Look for user_login: 0 (not currently logged in)
        user = mongo.db.users.find_one({"email": email, "user_type": user_type, "user_login": 0})

        print(f"DEBUG: Attempting login for email: {email}, user_type: {user_type}") # Temporary debug

        if user:
            print(f"DEBUG: User found in DB: {user.get('name')}") # Temporary debug
            imgdata2 = user['user_image']
            password_from_db = user.get('password') # Use .get() for safer access
            name = user['name']
            uid = str(user['_id']) # MongoDB uses _id for primary key

            if not password_from_db:
                print(f"DEBUG: Password field missing or empty in DB for user {email}") # Temporary debug
                error = "Password data is missing for this user. Please contact support or reset your password."
                return render_template('login.html', error=error)

            nparr1 = np.frombuffer(base64.b64decode(imgdata1), np.uint8)
            nparr2 = np.frombuffer(base64.b64decode(imgdata2), np.uint8)
            image1 = cv2.imdecode(nparr1, cv2.COLOR_BGR2GRAY)
            image2 = cv2.imdecode(nparr2, cv2.COLOR_BGR2GRAY)

            print(f"DEBUG: Password candidate from form: '{password_candidate}'") # Temporary debug
            print(f"DEBUG: Hashed password from DB: '{password_from_db}' (Type: {type(password_from_db)})") # Temporary debug

            img_result = DeepFace.verify(image1, image2, enforce_detection=False)
            is_password_correct = check_password_hash(password_from_db, password_candidate)
            print(f"DEBUG: DeepFace verification result: {img_result.get('verified')}") # Temporary debug
            print(f"DEBUG: check_password_hash result: {is_password_correct}") # Temporary debug

            if img_result["verified"] and is_password_correct:
                mongo.db.users.update_one({"email": email}, {"$set": {"user_login": 1}})
                session['logged_in'] = True
                session['email'] = email
                session['name'] = name
                session['user_role'] = user_type
                session['uid'] = uid
                print(f"DEBUG: Login successful for {email}") # Temporary debug
                if user_type == "student":
                    return redirect(url_for('student_index'))
                else:
                    return redirect(url_for('professor_index'))
            else:
                # Refined error message for when user is found (user_login was 0) but auth fails
                error_details = []
                if not img_result["verified"]:
                    error_details.append("Image not verified")
                if not is_password_correct:
                    error_details.append("Wrong password")
                error = ', '.join(error_details) if error_details else 'Login failed due to invalid credentials or image.'
                print(f"DEBUG: Login failed for {email}. Reason: {error}") # Temporary debug
                return render_template('login.html', error=error)
        else:
            print(f"DEBUG: User not found for email: {email}, user_type: {user_type}, or already logged in.") # Temporary debug
            error = 'Email Not Found, Invalid User Type, or User Already Logged In' # More descriptive
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/verifyEmail', methods=['GET', 'POST'])
def verifyEmail():
    if request.method == 'POST':
        theOTP = request.form['eotp']
        mOTP = session.get('tempOTP')
        print("Entered OTP:", theOTP)
        print("Session OTP:", mOTP)
        dbName = session.get('tempName')
        dbEmail = session.get('tempEmail')
        dbPassword = session.get('tempPassword')
        dbUser_type = session.get('tempUT')
        dbImgdata = session.get('tempImage')

        if theOTP == mOTP:
            try:
                # Check if user already exists (prevent duplicate insert)
                existing_user = mongo.db.users.find_one({'email': dbEmail})
                if existing_user:
                    flash("User with this email already exists. Please login.", "warning")
                    session.clear()
                    return redirect(url_for('login'))

                # Insert user into MongoDB
                hashed_password = generate_password_hash(dbPassword) # Hash the password
                user_doc = {
                    "name": dbName,
                    "email": dbEmail,
                    "password": hashed_password, # Store the hashed password
                    "user_type": dbUser_type,
                    "user_image": dbImgdata,
                    "user_login": 0, # User is not logged in upon registration
                }
                mongo.db.users.insert_one(user_doc) 
                session.clear()
                flash("Thanks for registering! You are successfully verified.", "success")
                return redirect(url_for('login'))

            except Exception as e:
                print("DB Insert Error:", str(e))
                flash("An error occurred while saving your data. Please try again.", "danger")
                return redirect(url_for('register'))
        else:
            flash("OTP is incorrect. Please try again.", "danger")
            return render_template('verifyEmail.html')

    return render_template('verifyEmail.html')

@app.route('/changepassword', methods=["GET", "POST"])
def changePassword():
    if request.method == "POST":
        oldPassword = request.form['oldpassword']
        newPassword = request.form['newpassword']
        # MongoDB: Find user by email and uid
        user = mongo.db.users.find_one({"email": session['email'], "uid": session['uid']})

        if user:
            stored_password_hash = user['password']
            usertype = user['user_type']
            # Correctly compare the old password entered by the user with the stored hash
            if check_password_hash(stored_password_hash, oldPassword):
                # MongoDB: Update user's password
                result = mongo.db.users.update_one(
                    {"email": session['email'], "uid": session['uid']},
                    {"$set": {"password": generate_password_hash(newPassword)}}
                )
                if result.modified_count > 0:
                    flash('Changed successfully.', 'success')
                    if usertype == "student":
                        return render_template("student_index.html", success="Changed successfully.")
                    else:
                        return render_template("professor_index.html", success="Changed successfully.")
                else:
                    flash('Failed to change password.', 'danger')
                    if usertype == "student":
                        return render_template("student_index.html", error="Failed to change password.")
                    else:
                        return render_template("professor_index.html", error="Failed to change password.")
            else:
                error = "Wrong password"
                if usertype == "student":
                    return render_template("student_index.html", error=error)
                else:
                    return render_template("professor_index.html", error=error)
        else:
            flash('User not found or unauthorized.', 'danger')
            return redirect(url_for('/'))

@app.route('/logout', methods=["GET", "POST"])
def logout():
    if 'email' in session:
        # MongoDB: Update user_login status
        mongo.db.users.update_one({"email": session['email']}, {"$set": {"user_login": 0}})
        session.clear()
        return "success"
    else:
        return "error"

def examcreditscheck():
    # MongoDB: Check user's examcredits
    user = mongo.db.users.find_one(
        {"email": session['email'], "uid": session['uid'], "examcredits": {"$gte": 1}},
        {"examcredits": 1}
    )
    return user is not None # Returns True if user has at least 1 credit, False otherwise

class QAUploadForm(FlaskForm):
    subject = StringField('Subject')
    topic = StringField('Topic')
    doc = FileField('CSV Upload', validators=[FileRequired()])
    start_date = DateField('Start Date')
    start_time = TimeField('Start Time', default=datetime.utcnow() + timedelta(hours=5.5))
    end_date = DateField('End Date')
    end_time = TimeField('End Time', default=datetime.utcnow() + timedelta(hours=5.5))
    duration = IntegerField('Duration(in min)')
    password = PasswordField('Exam Password', [validators.Length(min=3, max=6)])
    proctor_type = RadioField('Proctoring Type', choices=[('0', 'Automatic Monitoring'), ('1', 'Live Monitoring')])

    def validate_end_date(form, field):
        if field.data < form.start_date.data:
            raise ValidationError("End date must not be earlier than start date.")

    def validate_end_time(form, field):
        start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
        end_date_time = datetime.strptime(str(field.data) + " " + str(field.data), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
        if start_date_time >= end_date_time:
            raise ValidationError("End date time must not be earlier/equal than start date time")

    def validate_start_date(form, field):
        if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data), "%Y-%m-%d %H:%M:%S") < datetime.now():
            raise ValidationError("Start date and time must not be earlier than current")

@app.route('/create_test_lqa', methods=['GET', 'POST'])
@user_role_professor
def create_test_lqa():
    form = QAUploadForm()
    if request.method == 'POST' and form.validate_on_submit():
        test_id = generate_slug(2)
        filename = secure_filename(form.doc.data.filename)
        filestream = form.doc.data
        filestream.seek(0)
        ef = pd.read_csv(filestream)
        fields = ['qid', 'q', 'marks']
        df = pd.DataFrame(ef, columns=fields)

        ecc = examcreditscheck()
        if ecc:
            questions_to_insert = []
            for index, row in df.iterrows():
                questions_to_insert.append({
                    "test_id": test_id,
                    "qid": str(row['qid']), # Store qid as string
                    "q": row['q'],
                    "marks": int(row['marks']),
                    "uid": session['uid']
                })
            
            # MongoDB: Insert many questions
            if questions_to_insert:
                mongo.db.longqa.insert_many(questions_to_insert)

            start_date = form.start_date.data
            end_date = form.end_date.data
            start_time = form.start_time.data
            end_time = form.end_time.data
            start_date_time = str(start_date) + " " + str(start_time) + ":00" # Add seconds
            end_date_time = str(end_date) + " " + str(end_time) + ":00" # Add seconds
            duration = int(form.duration.data) * 60
            password = form.password.data
            subject = form.subject.data
            topic = form.topic.data
            proctor_type = form.proctor_type.data

            # MongoDB: Insert teacher test info
            teacher_test_info = {
                "email": session['email'],
                "test_id": test_id,
                "test_type": "subjective",
                "start": start_date_time,
                "end": end_date_time,
                "duration": duration,
                "show_ans": 0,
                "password": password,
                "subject": subject,
                "topic": topic,
                "neg_marks": 0,
                "calc": 0,
                "proctoring_type": proctor_type,
                "uid": session['uid']
            }
            mongo.db.teachers.insert_one(teacher_test_info)

            # MongoDB: Update exam credits
            mongo.db.users.update_one(
                {"email": session['email'], "uid": session['uid']},
                {"$inc": {"examcredits": -1}}
            )

            flash(f'Exam ID: {test_id}', 'success')
            return redirect(url_for('professor_index'))
        else:
            flash("No exam credits points are found! Please pay it!", 'danger')
            return redirect(url_for('professor_index'))
    return render_template('create_test_lqa.html', form=form)

class UploadForm(FlaskForm):
    subject = StringField('Subject')
    topic = StringField('Topic')
    doc = FileField('CSV Upload', validators=[FileRequired()])
    start_date = DateField('Start Date')
    start_time = TimeField('Start Time', default=datetime.utcnow() + timedelta(hours=5.5))
    end_date = DateField('End Date')
    end_time = TimeField('End Time', default=datetime.utcnow() + timedelta(hours=5.5))
    calc = BooleanField('Enable Calculator')
    neg_mark = DecimalField('Enable negative marking in % ', validators=[NumberRange(min=0, max=100)])
    duration = IntegerField('Duration(in min)')
    password = PasswordField('Exam Password', [validators.Length(min=3, max=6)])
    proctor_type = RadioField('Proctoring Type', choices=[('0', 'Automatic Monitoring'), ('1', 'Live Monitoring')])

    def validate_end_date(form, field):
        if field.data < form.start_date.data:
            raise ValidationError("End date must not be earlier than start date.")

    def validate_end_time(form, field):
        start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
        end_date_time = datetime.strptime(str(field.data) + " " + str(field.data), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
        if start_date_time >= end_date_time:
            raise ValidationError("End date time must not be earlier/equal than start date time")

    def validate_start_date(form, field):
        if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data), "%Y-%m-%d %H:%M:%S") < datetime.now():
            raise ValidationError("Start date and time must not be earlier than current")

class TestForm(Form):
    test_id = StringField('Exam ID')
    password = PasswordField('Exam Password')
    img_hidden_form = HiddenField(label=(''))

@app.route('/create-test', methods=['GET', 'POST'])
@user_role_professor
def create_test():
    form = UploadForm()
    if request.method == 'POST' and form.validate_on_submit():
        test_id = generate_slug(2)
        filename = secure_filename(form.doc.data.filename)
        filestream = form.doc.data
        filestream.seek(0)
        ef = pd.read_csv(filestream)
        fields = ['qid', 'q', 'a', 'b', 'c', 'd', 'ans', 'marks']
        df = pd.DataFrame(ef, columns=fields)

        ecc = examcreditscheck()
        if ecc:
            questions_to_insert = []
            for index, row in df.iterrows():
                questions_to_insert.append({
                    "test_id": test_id,
                    "qid": str(row['qid']), # Store qid as string
                    "q": row['q'],
                    "a": row['a'],
                    "b": row['b'],
                    "c": row['c'],
                    "d": row['d'],
                    "ans": row['ans'],
                    "marks": int(row['marks']),
                    "uid": session['uid']
                })
            
            # MongoDB: Insert many questions
            if questions_to_insert:
                mongo.db.questions.insert_many(questions_to_insert)

            start_date = form.start_date.data
            end_date = form.end_date.data
            start_time = form.start_time.data
            end_time = form.end_time.data
            start_date_time = str(start_date) + " " + str(start_time) + ":00" # Add seconds
            end_date_time = str(end_date) + " " + str(end_time) + ":00" # Add seconds
            neg_mark = int(form.neg_mark.data)
            calc = int(form.calc.data)
            duration = int(form.duration.data) * 60
            password = form.password.data
            subject = form.subject.data
            topic = form.topic.data
            proctor_type = form.proctor_type.data

            # MongoDB: Insert teacher test info
            teacher_test_info = {
                "email": session['email'],
                "test_id": test_id,
                "test_type": "objective",
                "start": start_date_time,
                "end": end_date_time,
                "duration": duration,
                "show_ans": 1, # Objective tests show answers by default? (based on original code)
                "password": password,
                "subject": subject,
                "topic": topic,
                "neg_marks": neg_mark,
                "calc": calc,
                "proctoring_type": proctor_type,
                "uid": session['uid']
            }
            mongo.db.teachers.insert_one(teacher_test_info)

            # MongoDB: Update exam credits
            mongo.db.users.update_one(
                {"email": session['email'], "uid": session['uid']},
                {"$inc": {"examcredits": -1}}
            )

            flash(f'Exam ID: {test_id}', 'success')
            return redirect(url_for('professor_index'))
        else:
            flash("No exam credits points are found! Please pay it!", 'danger')
            return redirect(url_for('professor_index'))
    return render_template('create_test.html', form=form)

class PracUploadForm(FlaskForm):
    subject = StringField('Subject')
    topic = StringField('Topic')
    questionprac = StringField('Question')
    marksprac = IntegerField('Marks')
    start_date = DateField('Start Date')
    start_time = TimeField('Start Time', default=datetime.utcnow() + timedelta(hours=5.5))
    end_date = DateField('End Date')
    end_time = TimeField('End Time', default=datetime.utcnow() + timedelta(hours=5.5))
    duration = IntegerField('Duration(in min)')
    compiler = SelectField(u'Compiler/Interpreter', choices=[('11', 'C'), ('27', 'C#'), ('1', 'C++'), ('114', 'Go'), ('10', 'Java'), ('47', 'Kotlin'), ('56', 'Node.js'),
                                                             ('43', 'Objective-C'), ('29', 'PHP'), ('54', 'Perl-6'), ('116', 'Python 3x'), ('117', 'R'), ('17', 'Ruby'), ('93', 'Rust'), ('52', 'SQLite-queries'), ('40', 'SQLite-schema'),
                                                             ('39', 'Scala'), ('85', 'Swift'), ('57', 'TypeScript')])
    password = PasswordField('Exam Password', [validators.Length(min=3, max=10)])
    proctor_type = RadioField('Proctoring Type', choices=[('0', 'Automatic Monitoring'), ('1', 'Live Monitoring')])

    def validate_end_date(form, field):
        if field.data < form.start_date.data:
            raise ValidationError("End date must not be earlier than start date.")

    def validate_end_time(form, field):
        start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
        end_date_time = datetime.strptime(str(field.data) + " " + str(field.data), "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
        if start_date_time >= end_date_time:
            raise ValidationError("End date time must not be earlier/equal than start date time")

    def validate_start_date(form, field):
        if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data), "%Y-%m-%d %H:%M:%S") < datetime.now():
            raise ValidationError("Start date and time must not be earlier than current")

@app.route('/create_test_pqa', methods=['GET', 'POST'])
@user_role_professor
def create_test_pqa():
    form = PracUploadForm()
    if request.method == 'POST' and form.validate_on_submit():
        test_id = generate_slug(2)
        ecc = examcreditscheck()
        print(ecc)
        if ecc:
            compiler = form.compiler.data
            questionprac = form.questionprac.data
            marksprac = int(form.marksprac.data)

            # MongoDB: Insert practical question
            practical_question_entry = {
                "test_id": test_id,
                "qid": "1", # Assuming only one question per practical test
                "q": questionprac,
                "compiler": compiler,
                "marks": marksprac,
                "uid": session['uid']
            }
            mongo.db.practicalqa.insert_one(practical_question_entry)

            start_date = form.start_date.data
            end_date = form.end_date.data
            start_time = form.start_time.data
            end_time = form.end_time.data
            start_date_time = str(start_date) + " " + str(start_time) + ":00" # Add seconds
            end_date_time = str(end_date) + " " + str(end_time) + ":00" # Add seconds
            duration = int(form.duration.data) * 60
            password = form.password.data
            subject = form.subject.data
            topic = form.topic.data
            proctor_type = form.proctor_type.data

            # MongoDB: Insert teacher test info
            teacher_test_info = {
                "email": session['email'],
                "test_id": test_id,
                "test_type": "practical",
                "start": start_date_time,
                "end": end_date_time,
                "duration": duration,
                "show_ans": 0,
                "password": password,
                "subject": subject,
                "topic": topic,
                "neg_marks": 0,
                "calc": 0,
                "proctoring_type": proctor_type,
                "uid": session['uid']
            }
            mongo.db.teachers.insert_one(teacher_test_info)

            # MongoDB: Update exam credits
            mongo.db.users.update_one(
                {"email": session['email'], "uid": session['uid']},
                {"$inc": {"examcredits": -1}}
            )

            flash(f'Exam ID: {test_id}', 'success')
            return redirect(url_for('professor_index'))
        else:
            flash("No exam credits points are found! Please pay it!", 'danger')
            return redirect(url_for('professor_index'))
    return render_template('create_prac_qa.html', form=form)

@app.route('/deltidlist', methods=['GET'])
@user_role_professor
def deltidlist():
    # MongoDB: Find tests created by the professor
    cresults = list(mongo.db.teachers.find({
        "email": session['email'],
        "uid": session['uid']
    }))

    if cresults:
        now = datetime.now()
        testids = []
        for a in cresults:
            # Convert string dates back to datetime objects for comparison
            start_dt = datetime.strptime(a['start'], "%Y-%m-%d %H:%M:%S")
            if start_dt > now: # Only show tests that haven't started yet
                testids.append(a['test_id'])
        return render_template("deltidlist.html", cresults=testids)
    else:
        return render_template("deltidlist.html", cresults=None)

@app.route('/deldispques', methods=['GET', 'POST'])
@user_role_professor
def deldispques():
    if request.method == 'POST':
        tidoption = request.form['choosetid']
        et = examtypecheck(tidoption)
        if et and 'test_type' in et:
            if et['test_type'] == "objective":
                callresults = list(mongo.db.questions.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("deldispques.html", callresults=callresults, tid=tidoption)
            elif et['test_type'] == "subjective":
                callresults = list(mongo.db.longqa.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("deldispquesLQA.html", callresults=callresults, tid=tidoption)
            elif et['test_type'] == "practical":
                callresults = list(mongo.db.practicalqa.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("deldispquesPQA.html", callresults=callresults, tid=tidoption)
            else:
                flash("Some Error Occurred!", 'danger')
                return redirect(url_for('deltidlist'))
        else:
            flash("Test type not found for the selected test ID!", 'danger')
            return redirect(url_for('deltidlist'))

@app.route('/delete_questions/<testid>', methods=['GET', 'POST'])
@user_role_professor
def delete_questions(testid):
    et = examtypecheck(testid)
    if not et or 'test_type' not in et:
        flash("Test type not found!", 'danger')
        return redirect(url_for('deltidlist'))

    if request.method == 'POST':
        testqdel = request.json['qids']
        if testqdel:
            qids_to_delete = testqdel.split(',') if ',' in testqdel else [testqdel]
            
            if et['test_type'] == "objective":
                result = mongo.db.questions.delete_many({
                    "test_id": testid,
                    "qid": {"$in": qids_to_delete},
                    "uid": session['uid']
                })
            elif et['test_type'] == "subjective":
                result = mongo.db.longqa.delete_many({
                    "test_id": testid,
                    "qid": {"$in": qids_to_delete},
                    "uid": session['uid']
                })
            elif et['test_type'] == "practical":
                result = mongo.db.practicalqa.delete_many({
                    "test_id": testid,
                    "qid": {"$in": qids_to_delete},
                    "uid": session['uid']
                })
            else:
                flash("Invalid test type for deletion!", 'danger')
                return jsonify('<span style=\'color:red;\'>Error: Invalid test type.</span>'), 400

            if result.deleted_count > 0:
                resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
                resp.status_code = 200
                return resp
            else:
                resp = jsonify('<span style=\'color:red;\'>No questions found or deleted.</span>')
                resp.status_code = 404
                return resp
        else:
            resp = jsonify('<span style=\'color:red;\'>No QIDs provided for deletion.</span>')
            resp.status_code = 400
            return resp
    else:
        flash("Invalid request method for deletion!", 'danger')
        return redirect(url_for('deltidlist'))

@app.route('/updatetidlist', methods=['GET'])
@user_role_professor
def updatetidlist():
    # MongoDB: Find tests created by the professor
    cresults = list(mongo.db.teachers.find({
        "email": session['email'],
        "uid": session['uid']
    }))

    if cresults:
        now = datetime.now()
        testids = []
        for a in cresults:
            # Convert string dates back to datetime objects for comparison
            start_dt = datetime.strptime(a['start'], "%Y-%m-%d %H:%M:%S")
            if start_dt > now: # Only show tests that haven't started yet
                testids.append(a['test_id'])
        return render_template("updatetidlist.html", cresults=testids)
    else:
        return render_template("updatetidlist.html", cresults=None)

@app.route('/updatedispques', methods=['GET', 'POST'])
@user_role_professor
def updatedispques():
    if request.method == 'POST':
        tidoption = request.form['choosetid']
        et = examtypecheck(tidoption)
        if et and 'test_type' in et:
            if et['test_type'] == "objective":
                callresults = list(mongo.db.questions.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("updatedispques.html", callresults=callresults)
            elif et['test_type'] == "subjective":
                callresults = list(mongo.db.longqa.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("updatedispquesLQA.html", callresults=callresults)
            elif et['test_type'] == "practical":
                callresults = list(mongo.db.practicalqa.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("updatedispquesPQA.html", callresults=callresults)
            else:
                flash('Error Occured!', 'danger')
                return redirect(url_for('updatetidlist'))
        else:
            flash("Test type not found for the selected test ID!", 'danger')
            return redirect(url_for('updatetidlist'))

@app.route('/update/<testid>/<qid>', methods=['GET', 'POST'])
@user_role_professor
def update_quiz(testid, qid):
    if request.method == 'GET':
        # MongoDB: Find the question to update
        uresults = mongo.db.questions.find_one({"test_id": testid, "qid": qid, "uid": session['uid']})
        if uresults:
            return render_template("updateQuestions.html", uresults=[uresults]) # Pass as list for consistency with original
        else:
            flash('Question not found.', 'danger')
            return redirect(url_for('updatetidlist'))
    if request.method == 'POST':
        ques = request.form['ques']
        ao = request.form['ao']
        bo = request.form['bo']
        co = request.form['co']
        do = request.form['do']
        anso = request.form['anso']
        markso = request.form['mko']
        # MongoDB: Update the question
        result = mongo.db.questions.update_one(
            {"test_id": testid, "qid": qid, "uid": session['uid']},
            {"$set": {
                "q": ques,
                "a": ao,
                "b": bo,
                "c": co,
                "d": do,
                "ans": anso,
                "marks": int(markso)
            }}
        )
        if result.modified_count > 0:
            flash('Updated successfully.', 'success')
            return redirect(url_for('updatetidlist'))
        else:
            flash('No changes made or question not found.', 'info')
            return redirect(url_for('updatetidlist'))
    else:
        flash('ERROR OCCURED.', 'danger')
        return redirect(url_for('updatetidlist'))

@app.route('/updateLQA/<testid>/<qid>', methods=['GET', 'POST'])
@user_role_professor
def update_lqa(testid, qid):
    if request.method == 'GET':
        # MongoDB: Find the long answer question to update
        uresults = mongo.db.longqa.find_one({"test_id": testid, "qid": qid, "uid": session['uid']})
        if uresults:
            return render_template("updateQuestionsLQA.html", uresults=[uresults])
        else:
            flash('Question not found.', 'danger')
            return redirect(url_for('updatetidlist'))
    if request.method == 'POST':
        ques = request.form['ques']
        markso = request.form['mko']
        # MongoDB: Update the long answer question
        result = mongo.db.longqa.update_one(
            {"test_id": testid, "qid": qid, "uid": session['uid']},
            {"$set": {
                "q": ques,
                "marks": int(markso)
            }}
        )
        if result.modified_count > 0:
            flash('Updated successfully.', 'success')
            return redirect(url_for('updatetidlist'))
        else:
            flash('No changes made or question not found.', 'info')
            return redirect(url_for('updatetidlist'))
    else:
        flash('ERROR OCCURED.', 'danger')
        return redirect(url_for('updatetidlist'))

@app.route('/updatePQA/<testid>/<qid>', methods=['GET', 'POST'])
@user_role_professor
def update_PQA(testid, qid):
    if request.method == 'GET':
        # MongoDB: Find the practical question to update
        uresults = mongo.db.practicalqa.find_one({"test_id": testid, "qid": qid, "uid": session['uid']})
        if uresults:
            return render_template("updateQuestionsPQA.html", uresults=[uresults])
        else:
            flash('Question not found.', 'danger')
            return redirect(url_for('updatetidlist'))
    if request.method == 'POST':
        ques = request.form['ques']
        markso = request.form['mko']
        # MongoDB: Update the practical question
        result = mongo.db.practicalqa.update_one(
            {"test_id": testid, "qid": qid, "uid": session['uid']},
            {"$set": {
                "q": ques,
                "marks": int(markso)
            }}
        )
        if result.modified_count > 0:
            flash('Updated successfully.', 'success')
            return redirect(url_for('updatetidlist'))
        else:
            flash('No changes made or question not found.', 'info')
            return redirect(url_for('updatetidlist'))
    else:
        flash('ERROR OCCURED.', 'danger')
        return redirect(url_for('updatetidlist'))

@app.route('/viewquestions', methods=['GET'])
@user_role_professor
def viewquestions():
    # MongoDB: Find test IDs created by the professor
    cresults = list(mongo.db.teachers.find(
        {"email": session['email'], "uid": session['uid']},
        {"test_id": 1, "_id": 0} # Project only test_id
    ))
    if cresults:
        return render_template("viewquestions.html", cresults=cresults)
    else:
        return render_template("viewquestions.html", cresults=None)

def examtypecheck(tidoption):
    # MongoDB: Find test type for a given test_id
    callresults = mongo.db.teachers.find_one(
        {"test_id": tidoption, "email": session['email'], "uid": session['uid']},
        {"test_type": 1, "_id": 0} # Project only test_type
    )
    return callresults

@app.route('/displayquestions', methods=['GET', 'POST'])
@user_role_professor
def displayquestions():
    if request.method == 'POST':
        tidoption = request.form['choosetid']
        et = examtypecheck(tidoption)
        if et and 'test_type' in et:
            if et['test_type'] == "objective":
                callresults = list(mongo.db.questions.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("displayquestions.html", callresults=callresults)
            elif et['test_type'] == "subjective":
                callresults = list(mongo.db.longqa.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("displayquestionslong.html", callresults=callresults)
            elif et['test_type'] == "practical":
                callresults = list(mongo.db.practicalqa.find({"test_id": tidoption, "uid": session['uid']}))
                return render_template("displayquestionspractical.html", callresults=callresults)
        flash("Test type not found or error occurred!", 'danger')
        return redirect(url_for('viewquestions'))

@app.route('/viewstudentslogs', methods=['GET'])
@user_role_professor
def viewstudentslogs():
    # MongoDB: Find tests with automatic monitoring
    cresults = list(mongo.db.teachers.find({
        "email": session['email'],
        "uid": session['uid'],
        "proctoring_type": "0"
    }, {"test_id": 1, "_id": 0}))
    if cresults:
        return render_template("viewstudentslogs.html", cresults=cresults)
    else:
        return render_template("viewstudentslogs.html", cresults=None)

@app.route('/insertmarkstid', methods=['GET'])
@user_role_professor
def insertmarkstid():
    # MongoDB: Find tests that are subjective or practical and show_ans is 0 (not published)
    cresults = list(mongo.db.teachers.find({
        "email": session['email'],
        "uid": session['uid'],
        "test_type": {"$in": ["subjective", "practical"]},
        "show_ans": 0
    }, {"test_id": 1, "end": 1, "_id": 0}))

    if cresults:
        now = datetime.now()
        testids = []
        for a in cresults:
            end_dt = datetime.strptime(a['end'], "%Y-%m-%d %H:%M:%S")
            if end_dt < now: # Only show tests that have ended
                testids.append(a['test_id'])
        return render_template("insertmarkstid.html", cresults=testids)
    else:
        return render_template("insertmarkstid.html", cresults=None)

@app.route('/displaystudentsdetails', methods=['GET', 'POST'])
@user_role_professor
def displaystudentsdetails():
    if request.method == 'POST':
        tidoption = request.form['choosetid']
        # MongoDB: Find distinct emails for a given test_id from proctoring_log
        # Using aggregation pipeline to get distinct emails
        pipeline = [
            {"$match": {"test_id": tidoption}},
            {"$group": {"_id": {"email": "$email", "test_id": "$test_id"}}},
            {"$project": {"email": "$_id.email", "test_id": "$_id.test_id", "_id": 0}}
        ]
        callresults = list(mongo.db.proctoring_log.aggregate(pipeline))
        return render_template("displaystudentsdetails.html", callresults=callresults)

@app.route('/insertmarksdetails', methods=['GET', 'POST'])
@user_role_professor
def insertmarksdetails():
    if request.method == 'POST':
        tidoption = request.form['choosetid']
        et = examtypecheck(tidoption)
        if et and 'test_type' in et:
            if et['test_type'] == "subjective":
                pipeline = [
                    {"$match": {"test_id": tidoption}},
                    {"$group": {"_id": {"email": "$email", "test_id": "$test_id"}}},
                    {"$project": {"email": "$_id.email", "test_id": "$_id.test_id", "_id": 0}}
                ]
                callresults = list(mongo.db.longtest.aggregate(pipeline))
                return render_template("subdispstudentsdetails.html", callresults=callresults)
            elif et['test_type'] == "practical":
                pipeline = [
                    {"$match": {"test_id": tidoption}},
                    {"$group": {"_id": {"email": "$email", "test_id": "$test_id"}}},
                    {"$project": {"email": "$_id.email", "test_id": "$_id.test_id", "_id": 0}}
                ]
                callresults = list(mongo.db.practicaltest.aggregate(pipeline))
                return render_template("pracdispstudentsdetails.html", callresults=callresults)
            else:
                flash("Some Error was occurred!", 'error')
                return redirect(url_for('insertmarkstid'))
        else:
            flash("Test type not found for the selected test ID!", 'error')
            return redirect(url_for('insertmarkstid'))

@app.route('/insertsubmarks/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def insertsubmarks(testid, email):
    if request.method == "GET":
        # MongoDB: Join longtest and longqa collections to get student answers and question details
        pipeline = [
            {"$match": {"test_id": testid, "email": email}},
            {"$lookup": {
                "from": "longqa",
                "localField": "qid",
                "foreignField": "qid",
                "as": "question_details"
            }},
            {"$unwind": "$question_details"},
            {"$project": {
                "email": "$email",
                "inputmarks": "$marks", # This is the marks entered by professor, initially null or 0
                "test_id": "$test_id",
                "qid": "$qid",
                "ans": "$ans", # Student's answer
                "marks": "$question_details.marks", # Max marks for the question
                "uid": "$uid",
                "q": "$question_details.q"
            }},
            {"$sort": {"qid": 1}} # Sort by qid
        ]
        callresults = list(mongo.db.longtest.aggregate(pipeline))
        return render_template("insertsubmarks.html", callresults=callresults)
    if request.method == "POST":
        # MongoDB: Count questions for the test
        results1 = mongo.db.longqa.count_documents({"test_id": testid})
        
        for sa in range(1, results1 + 1):
            marksByProfessor = request.form[str(sa)]
            # MongoDB: Update marks in longtest collection
            mongo.db.longtest.update_one(
                {"test_id": testid, "email": email, "qid": str(sa)},
                {"$set": {"marks": int(marksByProfessor)}}
            )
        flash('Marks Entered Successfully!', 'success')
        return redirect(url_for('insertmarkstid'))

@app.route('/insertpracmarks/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def insertpracmarks(testid, email):
    if request.method == "GET":
        # MongoDB: Join practicaltest and practicalqa collections
        pipeline = [
            {"$match": {"test_id": testid, "email": email}},
            {"$lookup": {
                "from": "practicalqa",
                "localField": "qid",
                "foreignField": "qid",
                "as": "question_details"
            }},
            {"$unwind": "$question_details"},
            {"$project": {
                "email": "$email",
                "inputmarks": "$marks",
                "test_id": "$test_id",
                "qid": "$qid",
                "code": "$code",
                "input": "$input",
                "executed": "$executed",
                "marks": "$question_details.marks",
                "uid": "$uid",
                "q": "$question_details.q"
            }},
            {"$sort": {"qid": 1}}
        ]
        callresults = list(mongo.db.practicaltest.aggregate(pipeline))
        return render_template("insertpracmarks.html", callresults=callresults)
    if request.method == "POST":
        # MongoDB: Count questions for the test
        results1 = mongo.db.practicalqa.count_documents({"test_id": testid})
        
        for sa in range(1, results1 + 1):
            marksByProfessor = request.form[str(sa)]
            # MongoDB: Update marks in practicaltest collection
            mongo.db.practicaltest.update_one(
                {"test_id": testid, "email": email, "qid": str(sa)},
                {"$set": {"marks": int(marksByProfessor)}}
            )
        flash('Marks Entered Successfully!', 'success')
        return redirect(url_for('insertmarkstid'))

def displaywinstudentslogs(testid, email):
    # MongoDB: Find window events for a student in a test
    callresults = list(mongo.db.window_estimation_log.find({"test_id": testid, "email": email, "window_event": 1}))
    return callresults

def countwinstudentslogs(testid, email):
    # MongoDB: Count window events
    winc = mongo.db.window_estimation_log.count_documents({"test_id": testid, "email": email, "window_event": 1})
    return [winc]

def countMobStudentslogs(testid, email):
    # MongoDB: Count mobile phone detections
    mobc = mongo.db.proctoring_log.count_documents({"test_id": testid, "email": email, "phone_detection": 1})
    return [mobc]

def countPersonStudentslogs(testid, email): # Renamed from countMTOPstudentslogs to avoid confusion
    # MongoDB: Count multiple person detections
    perc = mongo.db.proctoring_log.count_documents({"test_id": testid, "email": email, "person_status": 1})
    return [perc]

def countTotalstudentslogs(testid, email):
    # MongoDB: Count total proctoring logs
    tot = mongo.db.proctoring_log.count_documents({"test_id": testid, "email": email})
    return [tot]

@app.route('/studentmonitoringstats/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def studentmonitoringstats(testid, email):
    return render_template("stat_student_monitoring.html", testid=testid, email=email)

@app.route('/ajaxstudentmonitoringstats/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def ajaxstudentmonitoringstats(testid, email):
    win = countwinstudentslogs(testid, email)
    mob = countMobStudentslogs(testid, email)
    per = countPersonStudentslogs(testid, email) # Using the renamed function
    tot = countTotalstudentslogs(testid, email)
    return jsonify({"win": win, "mob": mob, "per": per, "tot": tot})

@app.route('/displaystudentslogs/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def displaystudentslogs(testid, email):
    # MongoDB: Find all proctoring logs for a student in a test
    callresults = list(mongo.db.proctoring_log.find({"test_id": testid, "email": email}))
    return render_template("displaystudentslogs.html", testid=testid, email=email, callresults=callresults)

@app.route('/mobdisplaystudentslogs/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def mobdisplaystudentslogs(testid, email):
    # MongoDB: Find mobile phone detection logs
    callresults = list(mongo.db.proctoring_log.find({"test_id": testid, "email": email, "phone_detection": 1}))
    return render_template("mobdisplaystudentslogs.html", testid=testid, email=email, callresults=callresults)

@app.route('/persondisplaystudentslogs/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def persondisplaystudentslogs(testid, email):
    # MongoDB: Find multiple person detection logs
    callresults = list(mongo.db.proctoring_log.find({"test_id": testid, "email": email, "person_status": 1}))
    return render_template("persondisplaystudentslogs.html", testid=testid, email=email, callresults=callresults)

@app.route('/audiodisplaystudentslogs/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def audiodisplaystudentslogs(testid, email):
    # MongoDB: Find all proctoring logs (assuming voice_db is part of these)
    callresults = list(mongo.db.proctoring_log.find({"test_id": testid, "email": email}))
    return render_template("audiodisplaystudentslogs.html", testid=testid, email=email, callresults=callresults)

@app.route('/wineventstudentslogs/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def wineventstudentslogs(testid, email):
    callresults = displaywinstudentslogs(testid, email)
    return render_template("wineventstudentlog.html", testid=testid, email=email, callresults=callresults)

@app.route('/<email>/<testid>/share_details', methods=['GET', 'POST'])
@user_role_professor
def share_details(testid, email):
    # MongoDB: Find teacher test details
    callresults = mongo.db.teachers.find_one({"test_id": testid, "email": email})
    if callresults:
        return render_template("share_details.html", callresults=[callresults]) # Pass as list for consistency
    else:
        flash("Test details not found.", "danger")
        return redirect(url_for('professor_index'))

@app.route('/share_details_emails', methods=['GET', 'POST'])
@user_role_professor
def share_details_emails():
    if request.method == 'POST':
        tid = request.form['tid']
        subject = request.form['subject']
        topic = request.form['topic']
        duration = request.form['duration']
        start = request.form['start']
        end = request.form['end']
        password = request.form['password']
        neg_marks = request.form['neg_marks']
        calc = request.form['calc']
        emailssharelist = request.form['emailssharelist']
        msg1 = Message('EXAM DETAILS - Hillproctor.ai', sender=sender, recipients=[emailssharelist])
        msg1.body = " ".join(["EXAM-ID:", tid, "SUBJECT:", subject, "TOPIC:", topic, "DURATION:", duration, "START", start, "END", end, "PASSWORD", password, "NEGATIVE MARKS in %:", neg_marks, "CALCULATOR ALLOWED:", calc])
        mail.send(msg1)
        flash('Emails sent successfully!', 'success')
    return render_template('share_details.html')

@app.route("/publish-results-testid", methods=['GET', 'POST'])
@user_role_professor
def publish_results_testid():
    # MongoDB: Find tests that are not objective, not yet published, and have ended
    cresults = list(mongo.db.teachers.find({
        "email": session['email'],
        "uid": session['uid'],
        "test_type": {"$ne": "objective"}, # Not objective
        "show_ans": 0 # Not published yet
    }, {"test_id": 1, "end": 1, "_id": 0}))

    if cresults:
        now = datetime.now()
        testids = []
        for a in cresults:
            end_dt = datetime.strptime(a['end'], "%Y-%m-%d %H:%M:%S")
            if end_dt < now: # Only show tests that have ended
                testids.append(a['test_id'])
        return render_template("publish_results_testid.html", cresults=testids)
    else:
        return render_template("publish_results_testid.html", cresults=None)

@app.route('/viewresults', methods=['GET', 'POST'])
@user_role_professor
def viewresults():
    if request.method == 'POST':
        tidoption = request.form['choosetid']
        et = examtypecheck(tidoption)
        if et and 'test_type' in et:
            if et['test_type'] == "subjective":
                # MongoDB: Aggregate marks for subjective tests
                pipeline = [
                    {"$match": {"test_id": tidoption}},
                    {"$group": {"_id": "$email", "marks": {"$sum": "$marks"}}},
                    {"$project": {"email": "$_id", "marks": 1, "_id": 0}}
                ]
                callresults = list(mongo.db.longtest.aggregate(pipeline))
                return render_template("publish_viewresults.html", callresults=callresults, tid=tidoption)
            elif et['test_type'] == "practical":
                # MongoDB: Aggregate marks for practical tests
                pipeline = [
                    {"$match": {"test_id": tidoption}},
                    {"$group": {"_id": "$email", "marks": {"$sum": "$marks"}}},
                    {"$project": {"email": "$_id", "marks": 1, "_id": 0}}
                ]
                callresults = list(mongo.db.practicaltest.aggregate(pipeline))
                return render_template("publish_viewresults.html", callresults=callresults, tid=tidoption)
            else:
                flash("Some Error Occurred!", 'danger')
                return redirect(url_for('publish-results-testid'))
        else:
            flash("Test type not found for the selected test ID!", 'danger')
            return redirect(url_for('publish-results-testid'))

@app.route('/publish_results', methods=['GET', 'POST'])
@user_role_professor
def publish_results():
    if request.method == 'POST':
        tidoption = request.form['testidsp']
        # MongoDB: Update teachers collection to show answers
        result = mongo.db.teachers.update_one(
            {"test_id": tidoption},
            {"$set": {"show_ans": 1}}
        )
        if result.modified_count > 0:
            flash("Results published successfully!", 'success')
        else:
            flash("Failed to publish results or results already published.", 'info')
        return redirect(url_for('professor_index'))

@app.route('/test_update_time', methods=['GET', 'POST'])
@user_role_student
def test_update_time():
    if request.method == 'POST':
        time_left = request.form['time']
        testid = request.form['testid']

        # MongoDB: Try to update existing studentTestInfo
        result = mongo.db.studentTestInfo.update_one(
            {"test_id": testid, "email": session['email'], "uid": session['uid'], "completed": 0},
            {"$set": {"time_left": int(time_left)}} # Store time_left as integer seconds
        )
        if result.modified_count > 0:
            return "time recorded updated"
        else:
            # If no existing document, insert a new one
            insert_result = mongo.db.studentTestInfo.insert_one({
                "email": session['email'],
                "test_id": testid,
                "time_left": int(time_left),
                "uid": session['uid'],
                "completed": 0
            })
            if insert_result.inserted_id:
                return "time recorded inserted"
            else:
                return "time error"

@app.route("/give-test", methods=['GET', 'POST'])
@user_role_student
def give_test():
    global duration, marked_ans, calc, subject, topic, proctortype
    form = TestForm(request.form)
    if request.method == 'POST' and form.validate():
        test_id = form.test_id.data
        password_candidate = form.password.data
        imgdata1 = form.img_hidden_form.data

        # MongoDB: Find user image for verification
        user_img_data = mongo.db.users.find_one(
            {"email": session['email'], "user_type": "student"},
            {"user_image": 1, "_id": 0}
        )
        if user_img_data:
            imgdata2 = user_img_data['user_image']
            nparr1 = np.frombuffer(base64.b64decode(imgdata1), np.uint8)
            nparr2 = np.frombuffer(base64.b64decode(imgdata2), np.uint8)
            image1 = cv2.imdecode(nparr1, cv2.COLOR_BGR2GRAY)
            image2 = cv2.imdecode(nparr2, cv2.COLOR_BGR2GRAY)
            img_result = DeepFace.verify(image1, image2, enforce_detection=False)

            if img_result["verified"] == True:
                # MongoDB: Find teacher test details
                test_details = mongo.db.teachers.find_one({"test_id": test_id})
                if test_details:
                    password = test_details['password']
                    duration = test_details['duration']
                    calc = test_details['calc']
                    subject = test_details['subject']
                    topic = test_details['topic']
                    start = test_details['start']
                    end = test_details['end']
                    proctortype = test_details['proctoring_type']

                    if password == password_candidate:
                        now = datetime.now()
                        start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                        end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

                        if start_dt < now and end_dt > now:
                            # MongoDB: Check studentTestInfo
                            student_test_info = mongo.db.studentTestInfo.find_one(
                                {"email": session['email'], "test_id": test_id}
                            )
                            if student_test_info:
                                is_completed = student_test_info.get('completed', 0)
                                if is_completed == 0:
                                    time_left = student_test_info.get('time_left', duration)
                                    if time_left <= duration:
                                        duration = time_left
                                        # MongoDB: Get marked answers for objective test
                                        marked_ans_docs = list(mongo.db.students.find(
                                            {"email": session['email'], "test_id": test_id, "uid": session['uid']},
                                            {"qid": 1, "ans": 1, "_id": 0}
                                        ))
                                        marked_ans = {doc['qid']: doc['ans'] for doc in marked_ans_docs}
                                        marked_ans = json.dumps(marked_ans)
                                else:
                                    flash('Exam already given', 'success')
                                    return redirect(url_for('give_test'))
                            else:
                                # MongoDB: Insert initial studentTestInfo
                                mongo.db.studentTestInfo.insert_one({
                                    "email": session['email'],
                                    "test_id": test_id,
                                    "time_left": duration,
                                    "uid": session['uid'],
                                    "completed": 0
                                })
                                # Re-fetch to ensure consistency (or just use initial duration)
                                student_test_info = mongo.db.studentTestInfo.find_one(
                                    {"email": session['email'], "test_id": test_id, "uid": session['uid']}
                                )
                                if student_test_info:
                                    is_completed = student_test_info.get('completed', 0)
                                    if is_completed == 0:
                                        time_left = student_test_info.get('time_left', duration)
                                        if time_left <= duration:
                                            duration = time_left
                                            marked_ans_docs = list(mongo.db.students.find(
                                                {"email": session['email'], "test_id": test_id, "uid": session['uid']},
                                                {"qid": 1, "ans": 1, "_id": 0}
                                            ))
                                            marked_ans = {doc['qid']: doc['ans'] for doc in marked_ans_docs}
                                            marked_ans = json.dumps(marked_ans)
                        else:
                            if start_dt > now:
                                flash(f'Exam start time is {start_dt.strftime("%Y-%m-%d %H:%M:%S")}', 'danger')
                            else:
                                flash(f'Exam has ended', 'danger')
                            return redirect(url_for('give_test'))
                        return redirect(url_for('test', testid=test_id))
                    else:
                        flash('Invalid password', 'danger')
                        return redirect(url_for('give_test'))
                flash('Invalid test ID', 'danger')
                return redirect(url_for('give_test'))
            else:
                flash('Image not Verified', 'danger')
                return redirect(url_for('give_test'))
        else:
            flash('User image not found for verification.', 'danger')
            return redirect(url_for('give_test'))
    return render_template('give_test.html', form=form)

@app.route('/give-test/<testid>', methods=['GET', 'POST'])
@user_role_student
def test(testid):
    # MongoDB: Get test type
    test_type_doc = mongo.db.teachers.find_one({"test_id": testid}, {"test_type": 1, "_id": 0})
    
    if not test_type_doc or 'test_type' not in test_type_doc:
        flash("Test not found or invalid test ID.", 'danger')
        return redirect(url_for('give_test'))

    test_type = test_type_doc['test_type']

    if test_type == "objective":
        global duration, marked_ans, calc, subject, topic, proctortype
        if request.method == 'GET':
            try:
                data = {'duration': duration, 'marks': '', 'q': '', 'a': '', 'b': '', 'c': '', 'd': ''}
                return render_template('testquiz.html', **data, answers=marked_ans, calc=calc, subject=subject, topic=topic, tid=testid, proctortype=proctortype)
            except NameError: # Handle case where global variables might not be set (e.g., direct access)
                flash("Please start the test from the 'Give Test' page.", 'danger')
                return redirect(url_for('give_test'))
        else:
            flag = request.form['flag']
            if flag == 'get':
                num = request.form['no']
                # MongoDB: Get question details
                question_data = mongo.db.questions.find_one({"test_id": testid, "qid": num})
                if question_data:
                    del question_data['ans'] # Don't send correct answer to client
                    question_data['_id'] = str(question_data['_id']) # Convert ObjectId to string
                    return json.dumps(question_data)
                else:
                    return json.dumps({}) # Return empty if question not found
            elif flag == 'mark':
                qid = request.form['qid']
                ans = request.form['ans']
                # MongoDB: Update or insert student's answer
                mongo.db.students.update_one(
                    {"test_id": testid, "qid": qid, "email": session['email'], "uid": session['uid']},
                    {"$set": {"ans": ans}},
                    upsert=True # Insert if not found
                )
                return json.dumps({'status': 'marked'})
            elif flag == 'time':
                time_left = request.form['time']
                # MongoDB: Update remaining time
                mongo.db.studentTestInfo.update_one(
                    {"test_id": testid, "email": session['email'], "uid": session['uid'], "completed": 0},
                    {"$set": {"time_left": int(time_left)}}
                )
                return json.dumps({'time': 'fired'})
            else: # Submit test
                # MongoDB: Mark test as completed and set time_left to 0
                mongo.db.studentTestInfo.update_one(
                    {"test_id": testid, "email": session['email'], "uid": session['uid']},
                    {"$set": {"completed": 1, "time_left": 0}}
                )
                flash("Exam submitted successfully", 'info')
                return json.dumps({'sql': 'fired'})

    elif test_type == "subjective":
        if request.method == 'GET':
            # MongoDB: Get subjective questions
            callresults1 = list(mongo.db.longqa.find({"test_id": testid}).sort([("qid", 1)])) # Sort by qid
            
            # MongoDB: Get studentTestInfo for duration
            studentTestInfo = mongo.db.studentTestInfo.find_one(
                {"completed": 0, "test_id": testid, "email": session['email'], "uid": session['uid']},
                {"time_left": 1, "_id": 0}
            )
            
            testDetails = mongo.db.teachers.find_one({"test_id": testid})

            if studentTestInfo and testDetails:
                duration_val = studentTestInfo['time_left']
                subject_val = testDetails['subject']
                topic_val = testDetails['topic']
                proctortypes_val = testDetails['proctoring_type']
                return render_template("testsubjective.html", callresults=callresults1, subject=subject_val, duration=duration_val, test_id=testid, topic=topic_val, proctortypes=proctortypes_val)
            elif testDetails: # If studentTestInfo not found (first time taking test)
                duration_val = testDetails['duration']
                subject_val = testDetails['subject']
                topic_val = testDetails['topic']
                proctortypes_val = testDetails['proctoring_type']
                return render_template("testsubjective.html", callresults=callresults1, subject=subject_val, duration=duration_val, test_id=testid, topic=topic_val, proctortypes=proctortypes_val)
            else:
                flash("Test details not found.", 'danger')
                return redirect(url_for('give_test'))
        elif request.method == 'POST':
            test_id = request.form["test_id"]
            # MongoDB: Count questions to iterate through student answers
            num_questions = mongo.db.longqa.count_documents({"test_id": testid})
            
            answers_to_insert = []
            for sa in range(1, num_questions + 1):
                answerByStudent = request.form[str(sa)]
                answers_to_insert.append({
                    "email": session['email'],
                    "test_id": testid,
                    "qid": str(sa),
                    "ans": answerByStudent,
                    "uid": session['uid'],
                    "marks": 0 # Initialize marks to 0, professor will update
                })

            if answers_to_insert:
                mongo.db.longtest.insert_many(answers_to_insert)
                # MongoDB: Update studentTestInfo to completed
                mongo.db.studentTestInfo.update_one(
                    {"test_id": test_id, "email": session['email'], "uid": session['uid']},
                    {"$set": {"completed": 1, "time_left": 0}}
                )
                flash('Successfully Exam Submitted', 'success')
                return redirect(url_for('student_index'))
            else:
                flash('Some Error was occurred or no answers submitted!', 'error')
                return redirect(url_for('student_index'))

    elif test_type == "practical":
        if request.method == 'GET':
            # MongoDB: Get practical questions
            callresults1 = list(mongo.db.practicalqa.find({"test_id": testid}).sort([("qid", 1)]))
            
            # MongoDB: Get studentTestInfo for duration
            studentTestInfo = mongo.db.studentTestInfo.find_one(
                {"completed": 0, "test_id": testid, "email": session['email'], "uid": session['uid']},
                {"time_left": 1, "_id": 0}
            )
            
            testDetails = mongo.db.teachers.find_one({"test_id": testid})

            if studentTestInfo and testDetails:
                duration_val = studentTestInfo['time_left']
                subject_val = testDetails['subject']
                topic_val = testDetails['topic']
                proctortypep_val = testDetails['proctoring_type']
                return render_template("testpractical.html", callresults=callresults1, subject=subject_val, duration=duration_val, test_id=testid, topic=topic_val, proctortypep=proctortypep_val)
            elif testDetails: # If studentTestInfo not found (first time taking test)
                duration_val = testDetails['duration']
                subject_val = testDetails['subject']
                topic_val = testDetails['topic']
                proctortypep_val = testDetails['proctoring_type']
                return render_template("testpractical.html", callresults=callresults1, subject=subject_val, duration=duration_val, test_id=testid, topic=topic_val, proctortypep=proctortypep_val)
            else:
                flash("Test details not found.", 'danger')
                return redirect(url_for('give_test'))
        elif request.method == 'POST':
            test_id = request.form["test_id"]
            codeByStudent = request.form["codeByStudent"]
            inputByStudent = request.form["inputByStudent"]
            executedByStudent = request.form["executedByStudent"]
            
            # MongoDB: Insert practical test submission
            insertStudentData = mongo.db.practicaltest.insert_one({
                "email": session['email'],
                "test_id": testid,
                "qid": "1", # Assuming only one question for practical
                "code": codeByStudent,
                "input": inputByStudent,
                "executed": executedByStudent,
                "uid": session['uid'],
                "marks": 0 # Initialize marks to 0
            })
            
            if insertStudentData.inserted_id:
                # MongoDB: Update studentTestInfo to completed
                mongo.db.studentTestInfo.update_one(
                    {"test_id": test_id, "email": session['email'], "uid": session['uid']},
                    {"$set": {"completed": 1, "time_left": 0}}
                )
                flash('Successfully Exam Submitted', 'success')
                return redirect(url_for('student_index'))
            else:
                flash('Some Error was occurred!', 'error')
                return redirect(url_for('student_index'))

@app.route('/randomize', methods=['POST'])
def random_gen():
    if request.method == "POST":
        id = request.form['id']
        # MongoDB: Get count of questions for the test
        total = mongo.db.questions.count_documents({"test_id": id})
        if total > 0:
            nos = list(range(1, int(total) + 1))
            random.Random(id).shuffle(nos)
            return json.dumps(nos)
        else:
            return json.dumps([]) # Return empty list if no questions found

@app.route('/<email>/<testid>')
@user_role_student
def check_result(email, testid):
    if email == session['email']:
        # MongoDB: Get teacher test details
        teacher_test = mongo.db.teachers.find_one({"test_id": testid})
        if teacher_test:
            check = teacher_test.get('show_ans', 0)
            if check == 1:
                # MongoDB: Aggregate to get questions, correct answers, and student's marked answers
                pipeline = [
                    {"$match": {"test_id": testid}},
                    {"$lookup": {
                        "from": "students",
                        "let": {"qid_str": "$qid"},
                        "pipeline": [
                            {"$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$test_id", testid]},
                                        {"$eq": ["$email", email]},
                                        {"$eq": ["$uid", session['uid']]},
                                        {"$eq": ["$qid", "$$qid_str"]}
                                    ]
                                }
                            }},
                            {"$project": {"ans": 1, "_id": 0}}
                        ],
                        "as": "student_answer"
                    }},
                    {"$addFields": {
                        "marked": {"$arrayElemAt": ["$student_answer.ans", 0]}
                    }},
                    {"$project": {
                        "q": 1, "a": 1, "b": 1, "c": 1, "d": 1, "marks": 1, "qid": 1,
                        "correct": "$ans", # Correct answer from questions collection
                        "marked": {"$ifNull": ["$marked", "0"]}, # Default to "0" if not marked
                        "_id": 0
                    }},
                    {"$sort": {"qid": 1}} # Sort by qid
                ]
                results = list(mongo.db.questions.aggregate(pipeline))
                if results:
                    return render_template('tests_result.html', results=results)
                else:
                    flash('No results found for this test.', 'info')
                    return redirect(url_for('tests_given', email=email))
            else:
                flash('You are not authorized to check the result', 'danger')
                return redirect(url_for('tests_given', email=email))
        else:
            flash('Test not found.', 'danger')
            return redirect(url_for('tests_given', email=email))
    else:
        flash('You are not authorized', 'danger')
        return redirect(url_for('student_index'))

def neg_marks(email, testid, negm):
    # MongoDB: Get questions and student answers for negative marking calculation
    pipeline = [
        {"$match": {"test_id": testid}},
        {"$lookup": {
            "from": "students",
            "let": {"qid_str": "$qid"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$test_id", testid]},
                            {"$eq": ["$email", email]},
                            {"$eq": ["$qid", "$$qid_str"]}
                        ]
                    }
                }},
                {"$project": {"ans": 1, "_id": 0}}
            ],
            "as": "student_answer"
        }},
        {"$addFields": {
            "marked": {"$arrayElemAt": ["$student_answer.ans", 0]}
        }},
        {"$project": {
            "marks": 1,
            "qid": 1,
            "correct": "$ans",
            "marked": {"$ifNull": ["$marked", "0"]},
            "_id": 0
        }},
        {"$sort": {"qid": 1}}
    ]
    data = list(mongo.db.questions.aggregate(pipeline))

    total_score = 0.0
    for item in data:
        marked_ans = str(item['marked']).upper()
        correct_ans = str(item['correct']).upper()
        question_marks = int(item['marks'])

        if marked_ans != '0':
            if marked_ans != correct_ans:
                total_score -= (float(negm) / 100) * question_marks
            elif marked_ans == correct_ans:
                total_score += question_marks
    return total_score

def marks_calc(email, testid):
    # MongoDB: Get negative marks percentage from teachers collection
    teacher_test = mongo.db.teachers.find_one({"test_id": testid}, {"neg_marks": 1, "_id": 0})
    negm = teacher_test.get('neg_marks', 0) if teacher_test else 0
    return neg_marks(email, testid, negm)

@app.route('/<email>/tests-given', methods=['POST', 'GET'])
@user_role_student
def tests_given(email):
    if request.method == "GET":
        if email == session['email']:
            # MongoDB: Find completed tests for the student where results are published
            pipeline = [
                {"$match": {"email": session['email'], "uid": session['uid'], "completed": 1}},
                {"$lookup": {
                    "from": "teachers",
                    "localField": "test_id",
                    "foreignField": "test_id",
                    "as": "test_details"
                }},
                {"$unwind": "$test_details"},
                {"$match": {"test_details.show_ans": 1}}, # Only tests where answers are shown
                {"$project": {"test_id": "$test_id", "_id": 0}}
            ]
            resultsTestids = list(mongo.db.studentTestInfo.aggregate(pipeline))
            return render_template('tests_given.html', cresults=resultsTestids)
        else:
            flash('You are not authorized', 'danger')
            return redirect(url_for('student_index'))
    if request.method == "POST":
        tidoption = request.form['choosetid']
        et = examtypecheck(tidoption)
        if et and 'test_type' in et:
            if et['test_type'] == "objective":
                # MongoDB: Get objective test results for student
                pipeline = [
                    {"$match": {"email": email, "test_id": tidoption}},
                    {"$lookup": {
                        "from": "teachers",
                        "localField": "test_id",
                        "foreignField": "test_id",
                        "as": "test_info"
                    }},
                    {"$unwind": "$test_info"},
                    {"$match": {"test_info.test_type": "objective", "test_info.show_ans": 1}},
                    {"$project": {
                        "test_id": "$test_id",
                        "email": "$email",
                        "subject": "$test_info.subject",
                        "topic": "$test_info.topic",
                        "neg_marks": "$test_info.neg_marks",
                        "_id": 0
                    }}
                ]
                results = list(mongo.db.students.aggregate(pipeline)) # Using students collection as starting point

                studentResults = []
                for a in results:
                    score = marks_calc(a['email'], a['test_id'])
                    # Create a dictionary that mimics the original tuple-like structure for zip
                    studentResults.append({"test_id": a['test_id'], "email": a['email'], "subject": a['subject'], "topic": a['topic'], "neg_marks": a['neg_marks'], "score": score})
                
                # Zip the results with their calculated scores
                final_results_for_template = [(item, item['score']) for item in studentResults]

                return render_template('obj_result_student.html', tests=final_results_for_template)
            elif et['test_type'] == "subjective":
                # MongoDB: Aggregate subjective test results for student
                pipeline = [
                    {"$match": {"email": email, "test_id": tidoption}},
                    {"$group": {"_id": {"test_id": "$test_id", "email": "$email"}, "marks": {"$sum": "$marks"}}},
                    {"$lookup": {
                        "from": "teachers",
                        "localField": "_id.test_id",
                        "foreignField": "test_id",
                        "as": "test_info"
                    }},
                    {"$unwind": "$test_info"},
                    {"$match": {"test_info.show_ans": 1}},
                    {"$project": {
                        "marks": 1,
                        "test_id": "$_id.test_id",
                        "subject": "$test_info.subject",
                        "topic": "$test_info.topic",
                        "_id": 0
                    }}
                ]
                studentResults = list(mongo.db.longtest.aggregate(pipeline))
                return render_template('sub_result_student.html', tests=studentResults)
            elif et['test_type'] == "practical":
                # MongoDB: Aggregate practical test results for student
                pipeline = [
                    {"$match": {"email": email, "test_id": tidoption}},
                    {"$group": {"_id": {"test_id": "$test_id", "email": "$email"}, "marks": {"$sum": "$marks"}}},
                    {"$lookup": {
                        "from": "teachers",
                        "localField": "_id.test_id",
                        "foreignField": "test_id",
                        "as": "test_info"
                    }},
                    {"$unwind": "$test_info"},
                    {"$match": {"test_info.show_ans": 1}},
                    {"$project": {
                        "marks": 1,
                        "test_id": "$_id.test_id",
                        "subject": "$test_info.subject",
                        "topic": "$test_info.topic",
                        "_id": 0
                    }}
                ]
                studentResults = list(mongo.db.practicaltest.aggregate(pipeline))
                return render_template('prac_result_student.html', tests=studentResults)
        else:
            flash('You are not authorized', 'danger')
            return redirect(url_for('student_index'))
    else:
        flash('You are not authorized', 'danger')
        return redirect(url_for('student_index'))

@app.route('/<email>/tests-created')
@user_role_professor
def tests_created(email):
    if email == session['email']:
        # MongoDB: Find tests created by the professor that have published results
        results = list(mongo.db.teachers.find({"email": email, "uid": session['uid'], "show_ans": 1}))
        return render_template('tests_created.html', tests=results)
    else:
        flash('You are not authorized', 'danger')
        return redirect(url_for('professor_index'))

@app.route('/<email>/tests-created/<testid>', methods=['POST', 'GET'])
@user_role_professor
def student_results(email, testid):
    if email == session['email']:
        et = examtypecheck(testid)
        if request.method == 'GET':
            if et and 'test_type' in et:
                if et['test_type'] == "objective":
                    # MongoDB: Aggregate objective test results for all students
                    pipeline = [
                        {"$match": {"test_id": testid, "completed": 1}},
                        {"$lookup": {
                            "from": "users",
                            "localField": "email",
                            "foreignField": "email",
                            "as": "user_details"
                        }},
                        {"$unwind": "$user_details"},
                        {"$match": {"user_details.user_type": "student"}},
                        {"$project": {
                            "name": "$user_details.name",
                            "email": "$email",
                            "test_id": "$test_id",
                            "_id": 0
                        }}
                    ]
                    results = list(mongo.db.studentTestInfo.aggregate(pipeline))
                    
                    final = []
                    names = []
                    scores = []
                    count = 1
                    for user in results:
                        score = marks_calc(user['email'], user['test_id'])
                        user_data = {
                            'srno': count,
                            'name': user['name'],
                            'email': user['email'],
                            'test_id': user['test_id'],
                            'marks': score
                        }
                        final.append(user_data)
                        names.append(user['name'])
                        scores.append(score)
                        count += 1
                    return render_template('student_results.html', data=final, labels=names, values=scores)
                elif et['test_type'] == "subjective":
                    # MongoDB: Aggregate subjective test results for all students
                    pipeline = [
                        {"$match": {"test_id": testid}},
                        {"$group": {"_id": {"email": "$email", "test_id": "$test_id"}, "marks": {"$sum": "$marks"}}},
                        {"$lookup": {
                            "from": "users",
                            "localField": "_id.email",
                            "foreignField": "email",
                            "as": "user_details"
                        }},
                        {"$unwind": "$user_details"},
                        {"$match": {"user_details.user_type": "student"}},
                        {"$project": {
                            "name": "$user_details.name",
                            "email": "$_id.email",
                            "test_id": "$_id.test_id",
                            "marks": 1,
                            "_id": 0
                        }}
                    ]
                    results = list(mongo.db.longtest.aggregate(pipeline))
                    names = [user['name'] for user in results]
                    scores = [user['marks'] for user in results]
                    return render_template('student_results_lqa.html', data=results, labels=names, values=scores)
                elif et['test_type'] == "practical":
                    # MongoDB: Aggregate practical test results for all students
                    pipeline = [
                        {"$match": {"test_id": testid}},
                        {"$group": {"_id": {"email": "$email", "test_id": "$test_id"}, "marks": {"$sum": "$marks"}}},
                        {"$lookup": {
                            "from": "users",
                            "localField": "_id.email",
                            "foreignField": "email",
                            "as": "user_details"
                        }},
                        {"$unwind": "$user_details"},
                        {"$match": {"user_details.user_type": "student"}},
                        {"$project": {
                            "name": "$user_details.name",
                            "email": "$_id.email",
                            "test_id": "$_id.test_id",
                            "marks": 1,
                            "_id": 0
                        }}
                    ]
                    results = list(mongo.db.practicaltest.aggregate(pipeline))
                    names = [user['name'] for user in results]
                    scores = [user['marks'] for user in results]
                    return render_template('student_results_pqa.html', data=results, labels=names, values=scores)
                else:
                    flash('Error: Unknown test type.', 'danger')
                    return redirect(url_for('tests_created', email=email))
            else:
                flash('Error: Test type not found.', 'danger')
                return redirect(url_for('tests_created', email=email))
    else:
        flash('You are not authorized', 'danger')
        return redirect(url_for('professor_index'))

@app.route('/<email>/disptests')
@user_role_professor
def disptests(email):
    if email == session['email']:
        # MongoDB: Find all tests created by the professor
        results = list(mongo.db.teachers.find({"email": email, "uid": session['uid']}))
        return render_template('disptests.html', tests=results)
    else:
        flash('You are not authorized', 'danger')
        return redirect(url_for('professor_index'))

@app.route('/<email>/student_test_history')
@user_role_student
def student_test_history(email):
    if email == session['email']:
        # MongoDB: Find student test history
        pipeline = [
            {"$match": {"email": email, "completed": 1}},
            {"$lookup": {
                "from": "teachers",
                "localField": "test_id",
                "foreignField": "test_id",
                "as": "test_details"
            }},
            {"$unwind": "$test_details"},
            {"$project": {
                "test_id": "$test_id",
                "subject": "$test_details.subject",
                "topic": "$test_details.topic",
                "_id": 0
            }}
        ]
        results = list(mongo.db.studentTestInfo.aggregate(pipeline))
        return render_template('student_test_history.html', tests=results)
    else:
        flash('You are not authorized', 'danger')
        return redirect(url_for('student_index'))

@app.route('/test_generate', methods=["GET", "POST"])
@user_role_professor
def test_generate():
    if request.method == "POST":
        inputText = request.form.get("itext")
        testType = request.form.get("test_type")
        noOfQues_str = request.form.get("noq")

        # Validate required fields
        if not inputText or not testType or not noOfQues_str:
            flash("All fields (Input Text, Test Type, Number of Questions) are required.", "danger")
            return render_template('generatetest.html')

        try:
            noOfQues = int(noOfQues_str)
            if noOfQues <= 0:
                flash("Number of questions must be a positive integer.", "danger")
                return render_template('generatetest.html')
        except ValueError:
            flash("Invalid input for number of questions. Please enter a number.", "danger")
            return render_template('generatetest.html')

        if testType == "objective":
            objective_generator = ObjectiveTest(inputText, noOfQues)
            question_list, answer_list = objective_generator.generate_test()
            testgenerate = zip(question_list, answer_list)
            return render_template('generatedtestdata.html', cresults=testgenerate)
        elif testType == "subjective":
            subjective_generator = SubjectiveTest(inputText, noOfQues)
            question_list, answer_list = subjective_generator.generate_test()
            testgenerate = zip(question_list, answer_list)
            return render_template('generatedtestdata.html', cresults=testgenerate)
        else:
            # This case should ideally not be reached if the HTML select is correctly used.
            flash("Invalid test type selected. Please choose 'Objective' or 'Subjective'.", "danger")
            return render_template('generatetest.html') # Re-render the form with an error
    
    # Handle GET request: display the form
    return render_template('generatetest.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
    app.run(debug=True)
