from flask import Flask, render_template, request, redirect, session,url_for
import psycopg2
import psycopg2.extras
from werkzeug.utils import secure_filename
import os
import bcrypt
from datetime import datetime
# Database connection parameters
PGHOST = 'ep-little-sea-a5ywe6cf.us-east-2.aws.neon.tech'
PGDATABASE = 'neondb'
PGUSER = 'neondb_owner'
PGPASSWORD = 'imdrf05pWZVv'

app = Flask(__name__)
app.secret_key = 'xyz3231'
app.config['UPLOAD_FOLDER'] = 'static/uploads/profile_images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
database_session = psycopg2.connect(
    host=PGHOST,

    database=PGDATABASE,
    user=PGUSER,
    password=PGPASSWORD

)
cursor = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
@app.route('/home')
def home_page():

    return render_template('Home.html')
@app.route('/',methods=['GET','POST'])
def home():
    msg = ''
    email = request.form.get('email')
    password = request.form.get('password')
    if email:
        # Fetch the user's id and hashed password from the database
        cursor.execute('SELECT id, password FROM patient WHERE email = %s', (email,))
        result = cursor.fetchone()

        if result:
            user_id = result['id']
            hashed_password = result['password']

            # Verify the password using bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                session['user'] = {'id': user_id}
                return redirect('/home')
            else:
                msg = 'Please enter correct email/password'
        else:
            msg = 'Please enter correct email/password'

    return render_template('index.html', msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    email = request.form.get('email')
    password = request.form.get('password')
    if email:
        cursor.execute('SELECT id, password FROM patient WHERE email = %s', (email,))
        result = cursor.fetchone()

        if result and bcrypt.checkpw(password.encode('utf-8'), result['password'].encode('utf-8')):
            session['user'] = {'id': result['id']}
            return redirect('/home')
        else:
            message = 'Please enter correct email/password'

    return render_template('login.html' , msg=message)
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        midname = request.form.get('midname')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        profile_image = None

        cursor.execute('SELECT email FROM patient where email = %s', (email,))
        if cursor.fetchone():
            message = 'Account already exists!'
        else:
            if 'profile_image' in request.files:
                file = request.files['profile_image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    profile_image = filename

            try:
                cursor.execute(
                    'INSERT INTO patient(fname,midname,lname,email,phone,password,profile_image) VALUES (%s ,%s, %s, %s ,%s, %s, %s)',
                    (fname, midname, lname, email, phone, hashed_password, profile_image))
                database_session.commit()
                message = 'You have successfully registered'
                return redirect('/login')
            except psycopg2.DatabaseError as e:
                database_session.rollback()
                message = str(e)
                print("Database Error: ", e)

    return render_template('register.html', msg=message)

@app.route('/profilepage', methods=['GET', 'POST'])
def profilepage():
    # Check if user is logged in
    if 'user' not in session or not session['user']:
        return redirect('/index')

    user_id = session['user']['id']
    cursor.execute('SELECT  fname,midname, lname,email, phone, profile_image FROM patient WHERE id = %s', (user_id,))
    patient = cursor.fetchone()

    if patient is None:
        return redirect('/index')
    return render_template('profile.html', user=patient)

@app.route('/editprofile', methods=['GET', 'POST'])
def edit_profile():
    if 'user' not in session or not session['user']:
        return redirect('/login')

    user_id = session['user']['id']
    message = ''

    if request.method == 'POST':
        new_password = request.form.get('password')
        new_phone = request.form.get('phone')
        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                profile_image = filename

        update_fields = {}
        # Hash the new password if provided
        if new_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            update_fields['password'] = hashed_password
        if new_phone:
            update_fields['phone'] = new_phone
        if profile_image:
            update_fields['profile_image'] = profile_image

        # Construct the update query based on the fields provided
        if update_fields:
            update_query = 'UPDATE patient SET '
            update_query += ', '.join([f"{key} = %s" for key in update_fields.keys()])
            update_query += ' WHERE id = %s'

            cursor.execute(update_query, list(update_fields.values()) + [user_id])
            database_session.commit()
            message = 'Profile updated successfully.'
        else:
            message = 'No changes made to the profile.'
    return render_template('editprofile.html', msg=message)


@app.route('/doctorlogin', methods=['GET', 'POST'])
def doctor_login():
    message = ''
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email:
            # Direct password comparison in the database (insecure)
            cursor.execute('SELECT id FROM doctors WHERE email = %s AND password = %s', (email, password))
            result = cursor.fetchone()

            if result:
                session['doctor_user'] = {'id': result['id']}
                return redirect('/doctor_home')  # Redirect to a specific home page for doctors
            else:
                message = 'Please enter correct email/password'

    return render_template('doctor_login.html', msg=message)

@app.route('/appointment')
def appointment():
    try:
        # Query to fetch distinct specializations only
        cursor.execute('SELECT DISTINCT specialization FROM doctors')
        specializations = cursor.fetchall()  # Returns [(specialization,), ...]

        # Extract specializations as a flat list
        specializations = [row[0] for row in specializations]

        return render_template('appointment.html', specializations=specializations)

    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/doctor_home')
def doctor_home():
    if 'doctor_user' not in session or not session['doctor_user']:
        return redirect('/doctorlogin')  # Redirect to login if not authenticated

    doctor_id = session['doctor_user']['id']
    cursor.execute('SELECT fname, lname, image FROM doctors WHERE id = %s', (doctor_id,))
    doctor_details = cursor.fetchone()

    if doctor_details:
        doctor_name = f"{doctor_details['fname']} {doctor_details['lname']}"
        image = doctor_details['image']  # Fetching the 'image' column from the database
        return render_template('doctor_home.html', doctor_name=doctor_name, profile_image=image)
    else:
        return "Doctor not found", 404  # or render a specific template with an error message




@app.route('/appointmentsdoctor')
def appointments_doctor():
    doctor_id = session.get('doctor_user', {}).get('id')
    if not doctor_id:
        return "Error: Doctor not logged in", 401

    current_time = datetime.now()

    query = """
    SELECT 
        a.appointment_id,
        a.appointment_date, 
        p.first_name, 
        p.last_name
    FROM 
        appointment a
    JOIN 
        patients p ON a.patient_id = p.patient_id
    WHERE 
        a.appointment_doctor_id = %s
    ORDER BY 
        a.appointment_date DESC;
    """
    cursor.execute(query, (doctor_id,))
    appointments = cursor.fetchall()

    upcoming_appointments = [app for app in appointments if app['appointment_date'] > current_time]
    previous_appointments = [app for app in appointments if app['appointment_date'] <= current_time]

    return render_template(
        'appointment_doctor.html',
        upcoming_appointments=upcoming_appointments,
        previous_appointments=previous_appointments
    )

@app.route('/view_scans/<int:appointment_id>')
def view_scans(appointment_id):
    try:
        # Fetch scans for the patient related to the appointment
        query = """
            SELECT s.scan_file_paths
            FROM scans s
            JOIN appointment a ON s.patient_id = a.patient_id
            WHERE a.appointment_id = %s;
        """
        cursor.execute(query, (appointment_id,))
        result = cursor.fetchone()

        scans = result['scan_file_paths'] if result else []

        return render_template('view_scans.html', scans=scans)
    except Exception as e:
        print(f"Error fetching scans: {e}")
        return render_template('view_scans.html', scans=[], error="An error occurred while fetching scans.")


@app.route('/view_diagnoses/<int:appointment_id>')
def view_diagnoses(appointment_id):
    try:
        # Fetch the patient_id associated with the appointment_id
        cursor.execute("""
            SELECT patient_id 
            FROM appointment 
            WHERE appointment_id = %s;
        """, (appointment_id,))
        result = cursor.fetchone()

        if not result:
            return "No diagnoses found for this appointment.", 404

        patient_id = result['patient_id']

        # Fetch all diagnoses for the patient
        cursor.execute("""
            SELECT diagnosis, diagnosis_date 
            FROM diagnoses 
            WHERE patient_id = %s;
        """, (patient_id,))
        diagnosis_results = cursor.fetchall()

        diagnoses = [
            {
                'diagnosis': row['diagnosis'],
                'diagnosis_date': row['diagnosis_date'].strftime('%Y-%m-%d %H:%M:%S') if row['diagnosis_date'] else "No date available"
            }
            for row in diagnosis_results
        ]

        return render_template('view_diagnosis.html', diagnoses=diagnoses)

    except Exception as e:
        print(f"Error fetching diagnoses: {e}")
        return render_template('view_diagnosis.html', diagnoses=[], error="An error occurred while fetching diagnoses.")






@app.route('/update_patient', methods=['GET', 'POST'])
def update_patient():
    try:
        if request.method == 'GET':
            return render_template('update_patient.html', patient=None, message=None)

        patient_ssn = request.form.get('patient_ssn')
        if not patient_ssn:
            return render_template('update_patient.html', patient=None, message="Please provide a valid SSN.")

        # Fetch patient data
        cursor.execute("""
            SELECT patient_id, first_name, last_name, ssn
            FROM patients
            WHERE ssn = %s;
        """, (patient_ssn,))
        patient = cursor.fetchone()

        if not patient:
            return render_template('update_patient.html', patient=None, message="No patient found with this SSN.")

        patient_id = patient['patient_id']

        # Handle updates
        diagnosis = request.form.get('diagnosis', '').strip()
        uploaded_files = request.files.getlist('scans')

        if diagnosis or uploaded_files:
            # Insert new diagnosis (if provided)
            if diagnosis:
                cursor.execute("""
                    INSERT INTO diagnoses (patient_id, diagnosis, diagnosis_date, patient_ssn)
                    VALUES (%s, %s, NOW(), %s);
                """, (patient_id, diagnosis, patient_ssn))

            # Handle uploaded files
            if uploaded_files:
                scan_files = []
                for file in uploaded_files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'Scans', filename)
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)  # Ensure folder exists
                        file.save(filepath)
                        scan_files.append(filename)

                # Update or insert scans
                cursor.execute("""
                    SELECT scan_file_paths
                    FROM scans
                    WHERE patient_id = %s;
                """, (patient_id,))
                existing_scans = cursor.fetchone()

                if existing_scans:
                    updated_scan_files = existing_scans['scan_file_paths'] + scan_files
                    cursor.execute("""
                        UPDATE scans
                        SET scan_file_paths = %s
                        WHERE patient_id = %s;
                    """, (updated_scan_files, patient_id))
                else:
                    cursor.execute("""
                        INSERT INTO scans (patient_id, scan_file_paths, patient_ssn)
                        VALUES (%s, %s, %s);
                    """, (patient_id, scan_files, patient_ssn))

            database_session.commit()
            return render_template('update_patient.html', patient=patient, message="Patient data updated successfully!")

        return render_template('update_patient.html', patient=patient, message=None)

    except Exception as e:
        database_session.rollback()
        print(f"Error: {e}")  # Log the error
        return render_template('update_patient.html', patient=None, message="An error occurred while updating the patient.")




@app.route('/doctors/<specialization>')
def doctors_by_specialization(specialization):
    try:
        cursor.execute("""
            SELECT id, fname, lname, image 
            FROM doctors 
            WHERE specialization = %s
        """, (specialization,))
        doctors = cursor.fetchall()
        return render_template('doctors.html', specialization=specialization, doctors=doctors)
    except Exception as e:
        return f"An error occurred: {str(e)}"


from datetime import datetime


@app.route('/book_appointment/<int:doctor_id>/<string:doctor_fname>/<string:doctor_lname>', methods=['GET', 'POST'])
def book_appointment(doctor_id, doctor_fname, doctor_lname):
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            age = request.form['age']
            gender = request.form['gender']
            ssn = request.form['ssn']
            appointment_date = request.form['appointment_date']

            # Convert appointment_date string to datetime object
            appointment_datetime = datetime.strptime(appointment_date, '%Y-%m-%dT%H:%M')

            # Check if appointment date is in the past
            if appointment_datetime < datetime.now():
                return render_template('book_appointment.html',
                                       doctor_fname=doctor_fname,
                                       doctor_lname=doctor_lname,
                                       msg="Error: Cannot book appointments in the past!")

            # Check if patient with SSN exists
            cursor.execute("SELECT patient_id FROM patients WHERE ssn = %s", (ssn,))
            existing_patient = cursor.fetchone()

            if existing_patient:
                # Use existing patient_id if patient already exists
                patient_id = existing_patient[0]
            else:
                # Insert new patient if they don't exist
                cursor.execute("""
                    INSERT INTO patients (first_name, last_name, age, gender, ssn)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING patient_id
                """, (first_name, last_name, age, gender, ssn))
                patient_id = cursor.fetchone()[0]

            # Check for appointment conflicts
            cursor.execute("""
                SELECT COUNT(*) FROM appointment 
                WHERE appointment_doctor_id = %s 
                AND appointment_date = %s
            """, (doctor_id, appointment_datetime))

            if cursor.fetchone()[0] > 0:
                return render_template('book_appointment.html',
                                       doctor_fname=doctor_fname,
                                       doctor_lname=doctor_lname,
                                       msg="Error: This time slot is already booked!")

            # Insert the appointment
            cursor.execute("""
                INSERT INTO appointment (
                    patient_name, patient_lname, patient_age, 
                    patient_gender, appointment_date, 
                    appointment_doctor_id, appointment_doctor_fname, 
                    appointment_doctor_lname, patient_id, patient_ssn
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                first_name, last_name, age,
                gender, appointment_datetime,
                doctor_id, doctor_fname,
                doctor_lname, patient_id, ssn
            ))

            database_session.commit()
            return render_template('book_appointment.html',
                                   doctor_fname=doctor_fname,
                                   doctor_lname=doctor_lname,
                                   msg="Appointment booked successfully!")

        except ValueError as e:
            return render_template('book_appointment.html',
                                   doctor_fname=doctor_fname,
                                   doctor_lname=doctor_lname,
                                   msg="Invalid date format provided!")
        except Exception as e:
            database_session.rollback()
            return render_template('book_appointment.html',
                                   doctor_fname=doctor_fname,
                                   doctor_lname=doctor_lname,
                                   msg=f"Error booking appointment: {str(e)}")

    return render_template('book_appointment.html',
                           doctor_fname=doctor_fname,
                           doctor_lname=doctor_lname)
@app.route('/admin_home')
def admin_home():
    if 'admin' not in session or not session['admin']:
        return redirect('/admin_login')
    return render_template('admin_home.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    msg = None  # Message to show on the login page
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cur = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            # Securely verify admin credentials
            cur.execute('SELECT * FROM admin WHERE email=%s', (email,))
            userdata = cur.fetchone()

            if userdata and userdata['password'] == password:
                # Successful login
                session['admin'] = {'id': userdata['id'], 'email': userdata['email']}
                return redirect('/admin_home')
            else:
                # Invalid credentials
                msg = 'Email or password incorrect'
        except Exception as e:
            msg = f"An error occurred: {str(e)}"
        finally:
            cur.close()

    return render_template('admin_login.html', msg=msg)


@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cur = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Get the database connection and cursor

        try:
            # Check if the email already exists
            cur.execute('SELECT * FROM admin WHERE email=%s', (email,))
            if cur.fetchone():
                message = 'Email is already registered!'
            else:
                # Insert new admin data
                cur.execute('INSERT INTO admin (email, password) VALUES (%s, %s)', (email, password))

                # Commit the changes to save the data
                database_session.commit()

                message = 'Successfully registered!'
        except Exception as e:
            message = f"Error: {str(e)}"
        finally:
            # Close the cursor and connection
            cur.close()


        return render_template('admin_register.html', msg=message)

    return render_template('admin_register.html')

@app.route('/admin_add_doctor', methods=['GET', 'POST'])
def admin_add_doctor():
    message = None
    if request.method == 'POST':
        fname = request.form.get('fname')
        midname = request.form.get('midname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        age = request.form.get('age')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        degree = request.form.get('degree')
        ssn = request.form.get('ssn')
        specialization = request.form.get('specialization')
        password = request.form.get('password')
        image = None

        cur = database_session.cursor()

        # Check if doctor already exists
        cur.execute('SELECT * FROM doctors WHERE ssn = %s OR phone = %s OR email = %s', (ssn, phone, email))
        existing_doctor = cur.fetchone()

        if existing_doctor:
            message = 'A doctor with the provided SSN, phone number, or email already exists.'
        else:
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    image = filename

            try:

                cur.execute(
                    'INSERT INTO doctors (fname, midname, lname, email, age, gender, phone, degree, ssn,specialization,password, image) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)',
                    (fname, midname, lname, email, age, gender, phone, degree, ssn,specialization,password, image))
                database_session.commit()
                message = 'Doctor successfully added!'
            except Exception as e:
                message = f"Error: {str(e)}"
                database_session.rollback()
            finally:
                cur.close()

    return render_template('admin_add_doctor.html', msg=message)




@app.route('/admin_delete_doctor', methods=['GET', 'POST'])
def admin_delete_doctor():
    message = None
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        if doctor_id:
            try:
                cursor.execute('DELETE FROM doctors WHERE id = %s', (doctor_id,))
                database_session.commit()
                message = 'Doctor deleted successfully.'
            except Exception as e:
                database_session.rollback()
                message = f"Error deleting doctor: {str(e)}"

    # Fetch all doctors to display
    cursor.execute('SELECT * FROM doctors')
    doctors = cursor.fetchall()

    return render_template('admin_delete_doctor.html', doctors=doctors, msg=message)



@app.route('/admin_view_patients', methods=['GET'])
def admin_view_patients():
    cur = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)
    patients = []
    try:
        # Retrieve all patient data
        cur.execute('SELECT id, FName, MidName, LName, Image, UserName, Password, Email, Phone FROM Patient')
        patients = cur.fetchall()
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        cur.close()

    return render_template('admin_view_patients.html', patients=patients)



@app.route('/delete_patient/<int:patient_id>', methods=['GET'])
def delete_patient(patient_id):
    cur = database_session.cursor()
    try:
        # Delete patient from the database
        cur.execute('DELETE FROM Patient WHERE id = %s', (patient_id,))
        database_session.commit()
        return redirect('/admin_view_patients')
    except Exception as e:
        print(f"Error: {str(e)}")
        database_session.rollback()
        return "Error deleting patient."
    finally:
        cur.close()


@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    cur = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        # Update patient details in the database
        fname = request.form['fname']
        midname = request.form['midname']
        lname = request.form['lname']
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        try:
            cur.execute('''
                UPDATE Patient
                SET FName = %s, MidName = %s, LName = %s, UserName = %s, Email = %s, Phone = %s
                WHERE id = %s
            ''', (fname, midname, lname, username, email, phone, patient_id))
            database_session.commit()
            return redirect('/admin_view_patients')
        except Exception as e:
            print(f"Error: {str(e)}")
            database_session.rollback()
            return "Error updating patient."
        finally:
            cur.close()
    else:
        # Retrieve patient details for the form
        cur.execute('SELECT * FROM Patient WHERE id = %s', (patient_id,))
        patient = cur.fetchone()
        cur.close()
        return render_template('edit_patient.html', patient=patient)

@app.route('/show_appointments', methods=['GET', 'POST'])
def show_appointments():
        cur = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)
        appointments = []
        message = None

        try:
            # Fetch all appointments from the database with case-sensitive table name
            cur.execute('''
                SELECT "appointment_id", "patient_name", "patient_lname", "patient_age", "patient_gender", "appointment_date", "appointment_doctor_id", 
                       "appointment_doctor_fname", "appointment_doctor_lname", "appointment_status", "patient_id", "patient_ssn"
                FROM "appointment"
            ''')
            appointments = cur.fetchall()

            if request.method == 'POST':
                action = request.form.get('action')
                appointment_id = request.form.get('appointment_id')

                if action == 'delete' and appointment_id:
                    # Deleting an appointment
                    cur.execute('DELETE FROM "appointment" WHERE "appointment_id" = %s', (appointment_id,))
                    database_session.commit()
                    message = 'Appointment deleted successfully.'
                elif action == 'update' and appointment_id:
                    # Updating an appointment status
                    new_status = request.form.get('new_status')
                    cur.execute('UPDATE "appointment" SET "Status" = %s WHERE "appointment_id" = %s',
                                (new_status, appointment_id))
                    database_session.commit()
                    message = 'Appointment updated successfully.'

                # After any action (delete/update), fetch all appointments again to show the updated list
                cur.execute('''
                           SELECT "appointment_id", "patient_name", "patient_lname", "patient_age", "patient_gender", "appointment_date", "appointment_doctor_id", 
                                  "appointment_doctor_fname", "appointment_doctor_lname", "appointment_status", "patient_id", "patient_ssn"
                           FROM "appointment"
                       ''')
                appointments = cur.fetchall()

        except Exception as e:
            print(f"Error: {str(e)}")
            database_session.rollback()
            message = f"Error: {str(e)}"
        finally:
            cur.close()

        # Render the template with the appointments and message
        return render_template('show_appointments.html', appointments=appointments, msg=message)

    # @app.route('/update_appointment/<int:appointment_id>', methods=['GET', 'POST'])
    # def update_appointment(appointment_id):
    #     cur = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)
    #     message = None
    #
    #     try:
    #         if request.method == 'POST':
    #             # Retrieve the new status from the form
    #             new_status = request.form.get('new_status')
    #
    #             # Check if the new status is provided
    #             if new_status:
    #                 # Update the appointment status in the database
    #                 cur.execute('''
    #                     UPDATE "appointment"
    #                     SET "appointment_status" = %s
    #                     WHERE "appointment_id" = %s
    #                 ''', (new_status, appointment_id))
    #                 database_session.commit()
    #                 message = 'Appointment status updated successfully.'
    #             else:
    #                 message = 'Please provide a valid status.'
    #
    #         # Fetch the current appointment details for display
    #         cur.execute('''
    #             SELECT "appointment_id", "patient_name", "patient_lname", "patient_age", "patient_gender", "appointment_date",
    #                    "appointment_doctor_fname", "appointment_doctor_lname", "appointment_status", "patient_id", "patient_ssn"
    #             FROM "appointment"
    #             WHERE "appointment_id" = %s
    #         ''', (appointment_id,))
    #         appointment = cur.fetchone()
    #
    #     except Exception as e:
    #         print(f"Error: {str(e)}")
    #         database_session.rollback()
    #         message = f"Error: {str(e)}"
    #     finally:
    #         cur.close()
    #
    #     # Render the template with the appointment data and message
    #     return render_template('update_appointment.html', appointment=appointment, msg=message)
    #

@app.route('/logout')
def logout():
    session['user'] = None
    return redirect('/')

if __name__ == '__main__':
    app.run()