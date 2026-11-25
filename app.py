
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from database import get_db_connection

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import os
import smtplib
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from datetime import date, datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def send_customer_email(to_email, subject, body):
    """Send a customer notification through Gmail SMTP using STARTTLS (port 587)."""
    host = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    try:
        port = int(os.getenv('MAIL_PORT', '587'))
    except (TypeError, ValueError):
        print('Email Sending Error: MAIL_PORT must be a number.')
        return False

    username = os.getenv('MAIL_USERNAME', '').strip()
    password = os.getenv('MAIL_PASSWORD', '').replace(' ', '').strip()
    sender = os.getenv('MAIL_DEFAULT_SENDER', username).strip()

    if not all([to_email, username, password, sender]):
        print('Email not sent: configure MAIL_USERNAME, MAIL_PASSWORD and MAIL_DEFAULT_SENDER in .env.')
        return False

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = to_email
    message.set_content(body)

    try:
        print(f'Connecting to SMTP server {host}:{port} using STARTTLS...')
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.send_message(message)
        print(f'Email sent successfully to: {to_email}')
        return True
    except Exception as error:
        print('Email Sending Error:', repr(error))
        return False


# =====================================
# FLASK APPLICATION CONFIGURATION
# =====================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "laborconnect-development-secret-key"
)



# =====================================
# HOME PAGE
# =====================================

@app.route('/')
def home():

    return render_template('index.html')


# =====================================
# USER REGISTRATION
# =====================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', '')
        location = request.form.get('location', '').strip()
        district = request.form.get('district', '').strip()

        # Validate required fields

        if not all([
            full_name,
            email,
            phone,
            password,
            confirm_password,
            role,
            location,
            district
        ]):

            flash('Please complete all fields.', 'error')

            return redirect(url_for('register'))

        # Validate account type

        if role not in ['customer', 'laborer']:

            flash('Invalid account type.', 'error')

            return redirect(url_for('register'))

        # Validate name

        if len(full_name) < 3:

            flash('Name must contain at least 3 characters.', 'error')

            return redirect(url_for('register'))

        # Validate phone number

        if (
            not phone.isdigit()
            or len(phone) != 10
            or not phone.startswith('07')
        ):

            flash('Enter a valid Sri Lankan mobile number.', 'error')

            return redirect(url_for('register'))

        # Validate password length

        if len(password) < 8:

            flash('Password must contain at least 8 characters.', 'error')

            return redirect(url_for('register'))

        # Confirm password

        if password != confirm_password:

            flash('Passwords do not match.', 'error')

            return redirect(url_for('register'))

        # Hash password

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()

        if connection is None:

            flash('Database connection failed.', 'error')

            return redirect(url_for('register'))

        cursor = None

        try:

            cursor = connection.cursor()

            sql = """
                INSERT INTO users
                (
                    full_name,
                    email,
                    phone,
                    password,
                    role,
                    location,
                    district
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                full_name,
                email,
                phone,
                hashed_password,
                role,
                location,
                district
            )

            cursor.execute(sql, values)

            connection.commit()

            flash(
                'Registration successful! Please login.',
                'success'
            )

            return redirect(url_for('login'))

        except Exception as error:

            connection.rollback()

            if getattr(error, 'errno', None) == 1062:

                flash(
                    'This email is already registered.',
                    'error'
                )

            else:

                print("Registration Error:", error)

                flash(
                    'Registration failed. Please try again.',
                    'error'
                )

        finally:

            if cursor:
                cursor.close()

            connection.close()

    return render_template('register.html')


# =====================================
# USER LOGIN
# =====================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email', '').strip().lower()

        password = request.form.get('password', '')

        connection = get_db_connection()

        if connection is None:

            flash('Database connection failed.', 'error')

            return redirect(url_for('login'))

        cursor = None

        try:

            cursor = connection.cursor(dictionary=True)

            sql = """
                SELECT *
                FROM users
                WHERE email = %s
            """

            cursor.execute(sql, (email,))

            user = cursor.fetchone()
            if user and not int(user.get('is_active', 1)):
                flash(
                    'Your account has been deactivated. Please contact the administrator.',
                    'error'
                )

            elif user and check_password_hash(
                user['password'],
                password
            ):

                session.clear()

                session['user_id'] = user['user_id']
                session['full_name'] = user['full_name']
                session['role'] = user['role']

                return redirect(url_for('dashboard'))

            else:

                flash(
                    'Invalid email or password.',
                    'error'
                )

        except Exception as error:

            print("Login Error:", error)

            flash(
                'Something went wrong. Please try again.',
                'error'
            )

        finally:

            if cursor:
                cursor.close()

            connection.close()

    return render_template('login.html')


# =====================================
# ROLE-BASED DASHBOARD
# =====================================

@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:

        flash('Please login first.', 'error')

        return redirect(url_for('login'))

    role = session.get('role')

    if role == 'customer':

        return redirect(url_for('customer_dashboard'))

    elif role == 'laborer':

        return redirect(url_for('laborer_dashboard'))

    elif role == 'admin':

        return redirect(url_for('admin_dashboard'))

    session.clear()

    return redirect(url_for('login'))


# =====================================
# CUSTOMER DASHBOARD
# =====================================

@app.route('/customer/dashboard')
def customer_dashboard():
    """Customer workspace: search active services published by laborers."""

    if 'user_id' not in session or session.get('role') != 'customer':
        flash('Please login with a customer account.', 'error')
        return redirect(url_for('login'))

    search_text = request.args.get('q', '').strip()
    selected_category = request.args.get('category', '').strip()
    selected_location = request.args.get('location', '').strip()
    selected_district = request.args.get('district', '').strip()
    selected_availability = request.args.get('availability', 'available').strip()
    selected_min_rating = request.args.get('min_rating', '').strip()
    selected_max_wage = request.args.get('max_wage', '').strip()
    selected_experience = request.args.get('experience', '').strip()
    districts = [
        'Ampara', 'Anuradhapura', 'Badulla', 'Batticaloa', 'Colombo',
        'Galle', 'Gampaha', 'Hambantota', 'Jaffna', 'Kalutara',
        'Kandy', 'Kegalle', 'Kilinochchi', 'Kurunegala', 'Mannar',
        'Matale', 'Matara', 'Monaragala', 'Mullaitivu', 'Nuwara Eliya',
        'Polonnaruwa', 'Puttalam', 'Ratnapura', 'Trincomalee', 'Vavuniya'
    ]

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed. Please try again.', 'error')
        return render_template(
            'customer_dashboard.html',
            services=[],
            customer_bookings=[],
            categories=[],
            search_text=search_text,
            selected_category=selected_category,
            selected_location=selected_location,
            selected_district=selected_district,
            selected_availability=selected_availability,
            selected_min_rating=selected_min_rating,
            selected_max_wage=selected_max_wage,
            selected_experience=selected_experience,
            today_date=date.today().isoformat()
        )

    cursor = None
    services = []
    categories = []
    customer_bookings = []

    try:
        cursor = connection.cursor(dictionary=True)

        # Load this customer's booking history and current request statuses.
        cursor.execute(
            """
            SELECT
                b.booking_id,
                b.scheduled_date,
                b.scheduled_time,
                b.job_location,
                b.job_status,
                b.job_description,
                b.created_at,
                s.service_name,
                u.full_name AS laborer_name,
                r.review_id,
                r.rating AS customer_rating,
                r.review AS customer_review
            FROM bookings b
            LEFT JOIN services s ON s.service_id = b.service_id
            INNER JOIN users u ON u.user_id = b.laborer_id
            LEFT JOIN reviews r ON r.booking_id = b.booking_id
            WHERE b.customer_id = %s
            ORDER BY b.created_at DESC, b.booking_id DESC
            """,
            (session['user_id'],)
        )
        customer_bookings = cursor.fetchall()

        # Load available categories for the filter dropdown.
        cursor.execute(
            """
            SELECT DISTINCT category
            FROM services
            WHERE availability_status = 1
              AND category IS NOT NULL
              AND category <> ''
            ORDER BY category
            """
        )
        categories = [row['category'] for row in cursor.fetchall()]

        # Search the services table and display the laborer's public details.
        sql = """
            SELECT
                s.service_id,
                s.service_name,
                s.category,
                s.description AS service_description,
                s.price,
                s.availability_status,
                u.user_id AS laborer_id,
                u.full_name AS laborer_name,
                u.phone AS laborer_phone,
                u.location AS laborer_location,
                u.district AS laborer_district,
                lp.experience_years,
                lp.skills,
                lp.daily_wage,
                lp.description AS laborer_description,
                lp.availability_status AS profile_availability,
                COALESCE(rating_summary.average_rating, 0) AS average_rating,
                COALESCE(rating_summary.review_count, 0) AS review_count
            FROM services s
            INNER JOIN users u ON u.user_id = s.user_id
            LEFT JOIN laborer_profiles lp ON lp.user_id = u.user_id
            LEFT JOIN (
                SELECT laborer_id, AVG(rating) AS average_rating, COUNT(*) AS review_count
                FROM reviews
                GROUP BY laborer_id
            ) AS rating_summary ON rating_summary.laborer_id = u.user_id
            WHERE s.availability_status = 1
              AND u.role = 'laborer'
        """
        params = []

        if selected_category:
            sql += " AND s.category = %s"
            params.append(selected_category)

        if selected_location:
            sql += " AND u.location LIKE %s"
            params.append(f"%{selected_location}%")

        if selected_district:
            sql += " AND u.district = %s"
            params.append(selected_district)

        if selected_availability == 'available':
            sql += " AND (lp.availability_status = 1 OR lp.availability_status IS NULL)"
        elif selected_availability == 'unavailable':
            sql += " AND lp.availability_status = 0"

        if selected_min_rating:
            try:
                min_rating = float(selected_min_rating)
                if 0 <= min_rating <= 5:
                    sql += " AND COALESCE(rating_summary.average_rating, 0) >= %s"
                    params.append(min_rating)
            except ValueError:
                selected_min_rating = ''

        if selected_max_wage:
            try:
                max_wage = float(selected_max_wage)
                if max_wage >= 0:
                    sql += " AND lp.daily_wage <= %s"
                    params.append(max_wage)
            except ValueError:
                selected_max_wage = ''

        if selected_experience:
            try:
                min_experience = int(selected_experience)
                if 0 <= min_experience <= 50:
                    sql += " AND COALESCE(lp.experience_years, 0) >= %s"
                    params.append(min_experience)
            except ValueError:
                selected_experience = ''

        if search_text:
            sql += """
                AND (
                    s.service_name LIKE %s
                    OR s.category LIKE %s
                    OR COALESCE(s.description, '') LIKE %s
                    OR u.full_name LIKE %s
                    OR COALESCE(lp.skills, '') LIKE %s
                )
            """
            pattern = f"%{search_text}%"
            params.extend([pattern, pattern, pattern, pattern, pattern])

        sql += " ORDER BY s.created_at DESC, s.service_id DESC"
        cursor.execute(sql, tuple(params))
        services = cursor.fetchall()

        return render_template(
            'customer_dashboard.html',
            services=services,
            customer_bookings=customer_bookings,
            categories=categories,
            search_text=search_text,
            selected_category=selected_category,
            selected_location=selected_location,
            selected_district=selected_district,
            selected_availability=selected_availability,
            selected_min_rating=selected_min_rating,
            selected_max_wage=selected_max_wage,
            selected_experience=selected_experience,
            today_date=date.today().isoformat()
        )

    except Exception as error:
        print('Customer Dashboard Error:', error)
        flash('Unable to load worker services. Please check the database tables.', 'error')
        return render_template(
            'customer_dashboard.html',
            services=[],
            customer_bookings=customer_bookings,
            categories=categories,
            search_text=search_text,
            selected_category=selected_category,
            selected_location=selected_location,
            selected_district=selected_district,
            selected_availability=selected_availability,
            selected_min_rating=selected_min_rating,
            selected_max_wage=selected_max_wage,
            selected_experience=selected_experience,
            today_date=date.today().isoformat()
        )
    finally:
        if cursor:
            cursor.close()
        connection.close()


# =====================================
# CUSTOMER BOOKING
# =====================================

@app.route('/customer/book/<int:service_id>', methods=['POST'])
def create_booking(service_id):
    """Create a booking for an available laborer service."""

    if 'user_id' not in session or session.get('role') != 'customer':
        flash('Please login with a customer account to make a booking.', 'error')
        return redirect(url_for('login'))

    scheduled_date_text = request.form.get('scheduled_date', '').strip()
    scheduled_time_text = request.form.get('scheduled_time', '').strip()
    job_location = request.form.get('job_location', '').strip()
    job_description = request.form.get('job_description', '').strip()

    if not all([scheduled_date_text, scheduled_time_text, job_location]):
        flash('Please complete the booking date, time and location.', 'error')
        return redirect(url_for('customer_dashboard'))

    if len(job_location) > 255:
        flash('Job location must be 255 characters or less.', 'error')
        return redirect(url_for('customer_dashboard'))

    try:
        scheduled_date = datetime.strptime(
            scheduled_date_text, '%Y-%m-%d'
        ).date()
        scheduled_time = datetime.strptime(
            scheduled_time_text, '%H:%M'
        ).time()

        if scheduled_date < date.today():
            flash('Please select today or a future date.', 'error')
            return redirect(url_for('customer_dashboard'))
    except ValueError:
        flash('Please enter a valid booking date and time.', 'error')
        return redirect(url_for('customer_dashboard'))

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed. Please try again.', 'error')
        return redirect(url_for('customer_dashboard'))

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)

        # Confirm that the selected service exists and is still available.
        cursor.execute(
            """
            SELECT service_id, user_id, service_name
            FROM services
            WHERE service_id = %s AND availability_status = 1
            """,
            (service_id,)
        )
        service = cursor.fetchone()

        if not service:
            flash('This service is no longer available.', 'error')
            return redirect(url_for('customer_dashboard'))

        if int(service['user_id']) == int(session['user_id']):
            flash('You cannot book your own service.', 'error')
            return redirect(url_for('customer_dashboard'))

        cursor.execute(
            """
            INSERT INTO bookings
                (customer_id, laborer_id, service_id, job_description,
                 scheduled_date, scheduled_time, job_location, job_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending')
            """,
            (
                session['user_id'],
                service['user_id'],
                service['service_id'],
                job_description or None,
                scheduled_date,
                scheduled_time,
                job_location
            )
        )

        connection.commit()
        flash(
            f"Your booking request for {service['service_name']} was submitted successfully. Status: Pending.",
            'success'
        )

    except Exception as error:
        connection.rollback()
        print("Create Booking Error:", error)
        flash('Unable to submit your booking. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        connection.close()

    return redirect(url_for('customer_dashboard'))


# =====================================
# CUSTOMER BOOKING CANCELLATION
# =====================================

@app.route('/customer/booking/<int:booking_id>/cancel', methods=['POST'])
def cancel_customer_booking(booking_id):
    """Allow a customer to cancel only their own pending booking."""

    if 'user_id' not in session or session.get('role') != 'customer':
        flash('Please login with a customer account.', 'error')
        return redirect(url_for('login'))

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed. Please try again.', 'error')
        return redirect(url_for('customer_dashboard') + '#my-bookings')

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE bookings
            SET job_status = 'Cancelled'
            WHERE booking_id = %s
              AND customer_id = %s
              AND job_status = 'Pending'
            """,
            (booking_id, session['user_id'])
        )

        if cursor.rowcount == 1:
            connection.commit()
            flash(f'Booking #{booking_id} was cancelled successfully.', 'success')
        else:
            connection.rollback()
            flash(
                'This booking cannot be cancelled. It may already have been accepted, rejected, or cancelled.',
                'error'
            )
    except Exception as error:
        connection.rollback()
        print('Cancel Customer Booking Error:', error)
        flash('Unable to cancel this booking. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        connection.close()

    return redirect(url_for('customer_dashboard') + '#my-bookings')



# =====================================
# CUSTOMER REVIEWS & RATINGS
# =====================================

@app.route('/customer/booking/<int:booking_id>/review', methods=['POST'])
def submit_booking_review(booking_id):
    """Allow the customer who owns a completed booking to review it once."""

    if 'user_id' not in session or session.get('role') != 'customer':
        flash('Please login with a customer account to submit a review.', 'error')
        return redirect(url_for('login'))

    rating_text = request.form.get('rating', '').strip()
    review_text = request.form.get('review', '').strip()

    try:
        rating = int(rating_text)
        if rating < 1 or rating > 5:
            raise ValueError()
    except (TypeError, ValueError):
        flash('Please select a rating from 1 to 5 stars.', 'error')
        return redirect(url_for('customer_dashboard') + '#my-bookings')

    if len(review_text) > 1000:
        flash('Review must be 1000 characters or less.', 'error')
        return redirect(url_for('customer_dashboard') + '#my-bookings')

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed. Please try again.', 'error')
        return redirect(url_for('customer_dashboard') + '#my-bookings')

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT booking_id, customer_id, laborer_id, job_status
            FROM bookings
            WHERE booking_id = %s AND customer_id = %s
            """,
            (booking_id, session['user_id'])
        )
        booking = cursor.fetchone()

        if not booking:
            flash('Booking not found in your account.', 'error')
        elif booking['job_status'] != 'Completed':
            flash('You can review a booking only after the work is completed.', 'error')
        else:
            cursor.execute(
                """INSERT INTO reviews (booking_id, customer_id, laborer_id, rating, review)
                   VALUES (%s, %s, %s, %s, %s)""",
                (booking_id, session['user_id'], booking['laborer_id'], rating, review_text or None)
            )
            connection.commit()
            flash('Thank you! Your rating and review have been submitted.', 'success')

    except Exception as error:
        connection.rollback()
        if getattr(error, 'errno', None) == 1062:
            flash('You have already submitted a review for this booking.', 'error')
        else:
            print('Submit Review Error:', error)
            flash('Unable to submit your review. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        connection.close()

    return redirect(url_for('customer_dashboard') + '#my-bookings')


# =====================================
# LABORER DASHBOARD
# =====================================


def _get_laborer_dashboard_data(user_id):
    """Return dashboard values without assuming optional booking columns exist."""
    data = {
        'services_count': 0,
        'requests_count': 0,
        'active_bookings': 0,
        'earnings': 0,
        'rating': 0,
        'review_count': 0
    }

    connection = get_db_connection()
    if connection is None:
        return data

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT COUNT(*) AS total FROM services WHERE user_id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        data['services_count'] = int(row['total']) if row else 0

        cursor.execute(
            "SELECT COALESCE(AVG(rating), 0) AS average_rating, COUNT(*) AS review_count FROM reviews WHERE laborer_id = %s",
            (user_id,)
        )
        rating_row = cursor.fetchone() or {}
        data['rating'] = round(float(rating_row.get('average_rating') or 0), 1)
        data['review_count'] = int(rating_row.get('review_count') or 0)

        # Booking columns differ between project database versions.
        # Only run the optional query when the required relationship exists.
        cursor.execute("SHOW COLUMNS FROM bookings")
        booking_columns = {
            column['Field'] for column in cursor.fetchall()
        }

        if 'service_id' in booking_columns and 'job_status' in booking_columns:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS requests_total,
                    SUM(CASE
                        WHEN b.job_status IN ('Pending', 'Accepted', 'In Progress')
                        THEN 1 ELSE 0
                    END) AS active_total
                FROM bookings b
                INNER JOIN services s ON s.service_id = b.service_id
                WHERE s.user_id = %s
                """,
                (user_id,)
            )
            row = cursor.fetchone() or {}
            data['requests_count'] = int(row.get('requests_total') or 0)
            data['active_bookings'] = int(row.get('active_total') or 0)

            # The current bookings table has no payment/amount column.
            # Earnings therefore remain zero until a payment module is added.

    except Exception as error:
        # Keep the dashboard usable if an optional table/column is not present.
        print("Laborer Dashboard Data Error:", error)
    finally:
        if cursor:
            cursor.close()
        connection.close()

    return data


@app.route('/laborer/dashboard')
def laborer_dashboard():

    if 'user_id' not in session or session.get('role') != 'laborer':
        flash('Please login as a laborer.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    dashboard_data = _get_laborer_dashboard_data(user_id)
    job_requests = []
    completed_bookings = []
    laborer_reviews = []

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed. Please try again.', 'error')
    else:
        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)

            # Only load bookings assigned to the currently logged-in laborer.
            cursor.execute(
                """
                SELECT
                    b.booking_id,
                    b.customer_id,
                    b.laborer_id,
                    b.service_id,
                    b.job_description,
                    b.scheduled_date,
                    b.scheduled_time,
                    b.job_location,
                    b.job_status,
                    b.created_at,
                    s.service_name,
                    s.price AS service_price,
                    customer.full_name AS customer_name,
                    customer.phone AS customer_phone
                FROM bookings b
                LEFT JOIN services s ON s.service_id = b.service_id
                INNER JOIN users customer ON customer.user_id = b.customer_id
                WHERE b.laborer_id = %s
                ORDER BY
                    CASE WHEN b.job_status = 'Pending' THEN 0 ELSE 1 END,
                    b.created_at DESC,
                    b.booking_id DESC
                """,
                (user_id,)
            )
            job_requests = cursor.fetchall()

            # A laborer may mark an accepted booking complete only on or after
            # its scheduled service date.
            for booking in job_requests:
                scheduled_date = booking.get('scheduled_date')
                if isinstance(scheduled_date, datetime):
                    scheduled_date = scheduled_date.date()
                elif isinstance(scheduled_date, str):
                    try:
                        scheduled_date = datetime.strptime(
                            scheduled_date[:10], '%Y-%m-%d'
                        ).date()
                    except ValueError:
                        scheduled_date = None
                booking['can_complete'] = (
                    scheduled_date is not None and scheduled_date <= date.today()
                )

            # Estimate earnings from completed bookings using each service's listed price.
            # This is not a payment record; the current database has no payment amount/status.
            completed_bookings = [
                booking for booking in job_requests
                if booking.get('job_status') == 'Completed'
            ]
            dashboard_data['earnings'] = round(
                sum(float(booking.get('service_price') or 0) for booking in completed_bookings),
                2
            )

            # Load reviews submitted by customers for this laborer's completed work.
            cursor.execute(
                """
                SELECT
                    r.review_id,
                    r.booking_id,
                    r.rating,
                    r.review,
                    r.created_at,
                    customer.full_name AS customer_name,
                    s.service_name
                FROM reviews r
                INNER JOIN users customer ON customer.user_id = r.customer_id
                LEFT JOIN bookings b ON b.booking_id = r.booking_id
                LEFT JOIN services s ON s.service_id = b.service_id
                WHERE r.laborer_id = %s
                ORDER BY r.created_at DESC, r.review_id DESC
                """,
                (user_id,)
            )
            laborer_reviews = cursor.fetchall()

            # MySQL TIME columns may be returned as datetime.timedelta.
            # Convert them to display strings before passing them to Jinja.
            for booking in job_requests:
                scheduled_time = booking.get('scheduled_time')
                if scheduled_time is None:
                    booking['scheduled_time_display'] = '-'
                elif hasattr(scheduled_time, 'strftime'):
                    booking['scheduled_time_display'] = scheduled_time.strftime('%I:%M %p')
                elif hasattr(scheduled_time, 'total_seconds'):
                    total_minutes = int(scheduled_time.total_seconds() // 60)
                    hours, minutes = divmod(total_minutes, 60)
                    booking['scheduled_time_display'] = datetime.strptime(
                        f'{hours % 24:02d}:{minutes:02d}', '%H:%M'
                    ).strftime('%I:%M %p')
                else:
                    booking['scheduled_time_display'] = str(scheduled_time)

        except Exception as error:
            print('Load Laborer Bookings Error:', error)
            flash('Unable to load job requests. Please check the bookings table.', 'error')
        finally:
            if cursor:
                cursor.close()
            connection.close()

    return render_template(
        'laborer_dashboard.html',
        dashboard_data=dashboard_data,
        job_requests=job_requests,
        completed_bookings=completed_bookings,
        laborer_reviews=laborer_reviews,
        services=[],
        editing_service=None,
        show_services=False
    )


@app.route('/laborer/booking/<int:booking_id>/status', methods=['POST'])
def update_booking_status(booking_id):
    """Allow the assigned laborer to accept or reject a pending booking."""

    if 'user_id' not in session or session.get('role') != 'laborer':
        flash('Please login as a laborer.', 'error')
        return redirect(url_for('login'))

    new_status = request.form.get('job_status', '').strip()
    if new_status not in ('Accepted', 'Rejected'):
        flash('Invalid booking status.', 'error')
        return redirect(url_for('laborer_dashboard') + '#requests')

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed. Please try again.', 'error')
        return redirect(url_for('laborer_dashboard') + '#requests')

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)

        # Confirm that this pending booking belongs to the logged-in laborer.
        cursor.execute(
            """
            SELECT b.booking_id, b.job_status,
                   customer.full_name AS customer_name,
                   customer.email AS customer_email,
                   laborer.full_name AS laborer_name,
                   s.service_name
            FROM bookings b
            INNER JOIN users customer ON customer.user_id = b.customer_id
            INNER JOIN users laborer ON laborer.user_id = b.laborer_id
            LEFT JOIN services s ON s.service_id = b.service_id
            WHERE b.booking_id = %s AND b.laborer_id = %s
            """,
            (booking_id, session['user_id'])
        )
        booking = cursor.fetchone()

        if not booking or booking['job_status'] != 'Pending':
            connection.rollback()
            flash('Booking not found, already updated, or not assigned to your account.', 'error')
            return redirect(url_for('laborer_dashboard') + '#requests')

        cursor.execute(
            """
            UPDATE bookings
            SET job_status = %s
            WHERE booking_id = %s
              AND laborer_id = %s
              AND job_status = 'Pending'
            """,
            (new_status, booking_id, session['user_id'])
        )

        if cursor.rowcount != 1:
            connection.rollback()
            flash('This booking has already been updated.', 'error')
            return redirect(url_for('laborer_dashboard') + '#requests')

        connection.commit()
        if new_status == 'Accepted':
            email_body = (
                f"Hello {booking['customer_name']},\n\n"
                f"Your LaborConnect booking #{booking_id} has been accepted by "
                f"{booking['laborer_name']}.\n"
                f"Service: {booking.get('service_name') or 'Requested service'}\n\n"
                "Thank you for using LaborConnect."
            )
            email_sent = send_customer_email(
                booking.get('customer_email'),
                f'LaborConnect - Booking #{booking_id} Accepted',
                email_body
            )
            flash(f'Booking #{booking_id} accepted successfully.' + ('' if email_sent else ' Email notification could not be sent; check SMTP settings.'), 'success')
        else:
            flash(f'Booking #{booking_id} rejected.', 'success')

    except Exception as error:
        connection.rollback()
        print('Update Booking Status Error:', error)
        flash('Unable to update this booking. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        connection.close()

    return redirect(url_for('laborer_dashboard') + '#requests')


# =====================================
# LABORER MARK BOOKING AS COMPLETED
# =====================================

@app.route('/laborer/booking/<int:booking_id>/complete', methods=['POST'])
def complete_booking(booking_id):
    """Complete an accepted job, record its final amount, and notify the customer."""
    if 'user_id' not in session or session.get('role') != 'laborer':
        flash('Please login as a laborer.', 'error')
        return redirect(url_for('login'))

    amount_text = request.form.get('final_amount', '').strip()
    try:
        final_amount = Decimal(amount_text)
        if not final_amount.is_finite() or final_amount <= 0 or final_amount > Decimal('9999999999.99'):
            raise InvalidOperation
        final_amount = final_amount.quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        flash('Enter a valid final amount greater than zero.', 'error')
        return redirect(url_for('laborer_dashboard') + '#requests')

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed. Please try again.', 'error')
        return redirect(url_for('laborer_dashboard') + '#requests')

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT b.scheduled_date, b.job_status,
                      customer.full_name AS customer_name,
                      customer.email AS customer_email,
                      laborer.full_name AS laborer_name,
                      s.service_name
               FROM bookings b
               INNER JOIN users customer ON customer.user_id = b.customer_id
               INNER JOIN users laborer ON laborer.user_id = b.laborer_id
               LEFT JOIN services s ON s.service_id = b.service_id
               WHERE b.booking_id = %s AND b.laborer_id = %s""",
            (booking_id, session['user_id'])
        )
        booking = cursor.fetchone()
        if not booking:
            flash('This booking does not belong to your account.', 'error')
            return redirect(url_for('laborer_dashboard') + '#requests')
        if booking.get('job_status') != 'Accepted':
            flash('Only accepted bookings can be marked as completed.', 'error')
            return redirect(url_for('laborer_dashboard') + '#requests')

        scheduled_date = booking.get('scheduled_date')
        if isinstance(scheduled_date, datetime):
            scheduled_date = scheduled_date.date()
        elif isinstance(scheduled_date, str):
            try:
                scheduled_date = datetime.strptime(scheduled_date[:10], '%Y-%m-%d').date()
            except ValueError:
                scheduled_date = None
        if scheduled_date is None or date.today() < scheduled_date:
            flash('This work can only be completed on or after its scheduled date.', 'error')
            return redirect(url_for('laborer_dashboard') + '#requests')

        cursor.execute(
            """UPDATE bookings SET job_status = 'Completed'
               WHERE booking_id = %s AND laborer_id = %s
                 AND job_status = 'Accepted' AND scheduled_date <= CURDATE()""",
            (booking_id, session['user_id'])
        )
        if cursor.rowcount != 1:
            connection.rollback()
            flash('This booking could not be completed. Please refresh and try again.', 'error')
            return redirect(url_for('laborer_dashboard') + '#requests')

        cursor.execute(
            """INSERT INTO booking_payments (booking_id, final_amount, payment_status)
               VALUES (%s, %s, 'Pending')
               ON DUPLICATE KEY UPDATE final_amount = VALUES(final_amount),
                                       payment_status = 'Pending',
                                       payment_method = NULL, paid_at = NULL,
                                       confirmed_by_admin_id = NULL""",
            (booking_id, str(final_amount))
        )
        connection.commit()

        email_body = (
            f"Hello {booking['customer_name']},\n\n"
            f"Your work for booking #{booking_id} has been marked as completed.\n"
            f"Service: {booking.get('service_name') or 'Requested service'}\n"
            f"Laborer: {booking['laborer_name']}\n"
            f"Final amount: Rs. {final_amount:,.2f}\n"
            "Payment status: Pending admin confirmation.\n\n"
            "Please make the payment using the arrangement made with your laborer. "
            "The administrator will confirm the payment after verification.\n\n"
            "Thank you,\nLaborConnect"
        )
        sent = send_customer_email(
            booking.get('customer_email'),
            f'LaborConnect - Work Completed / Booking #{booking_id}',
            email_body
        )
        flash(f'Booking #{booking_id} completed. Final amount: Rs. {final_amount:,.2f}.' + ('' if sent else ' Email could not be sent; check SMTP settings.'), 'success')
    except Exception as error:
        connection.rollback()
        print('Complete Booking Error:', error)
        flash('Unable to complete this booking. Please check the payment table and try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        connection.close()
    return redirect(url_for('laborer_dashboard') + '#requests')


@app.route('/laborer/profile', methods=['GET', 'POST'])
def laborer_profile():

    if 'user_id' not in session or session.get('role') != 'laborer':
        flash('Please login as a laborer.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('laborer_dashboard'))

    cursor = None

    try:

        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':

            category = request.form.get('category', '').strip()
            skills = request.form.get('skills', '').strip()
            daily_wage = request.form.get('daily_wage', '').strip()
            availability_status = request.form.get(
                'availability_status', '1'
            )
            description = request.form.get('description', '').strip()
            district = request.form.get('district', '').strip()
            experience_text = request.form.get('experience_years', '0').strip()

            if not all([category, skills, daily_wage, description, district, experience_text]):
                flash('Please complete all required fields.', 'error')

            elif len(category) > 100:
                flash('Category name is too long.', 'error')

            elif availability_status not in ['0', '1']:
                flash('Invalid availability status.', 'error')

            else:

                try:
                    wage = float(daily_wage)
                    experience_years = int(experience_text)

                    if wage < 0 or experience_years < 0 or experience_years > 50:
                        raise ValueError()

                    cursor.execute(
                        "UPDATE users SET district = %s WHERE user_id = %s AND role = 'laborer'",
                        (district, user_id)
                    )

                    sql = """
                        INSERT INTO laborer_profiles
                        (
                            user_id,
                            category,
                            skills,
                            daily_wage,
                            availability_status,
                            description,
                            experience_years
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)

                        ON DUPLICATE KEY UPDATE
                            category = VALUES(category),
                            skills = VALUES(skills),
                            daily_wage = VALUES(daily_wage),
                            availability_status = VALUES(availability_status),
                            description = VALUES(description),
                            experience_years = VALUES(experience_years)
                    """

                    cursor.execute(sql, (
                        user_id,
                        category,
                        skills,
                        wage,
                        int(availability_status),
                        description,
                        experience_years
                    ))

                    connection.commit()

                    flash('Your profile has been saved successfully!', 'success')

                    return redirect(url_for('laborer_profile'))

                except ValueError:
                    flash('Enter a valid daily wage and experience (0-50 years).', 'error')

        # Retrieve existing profile

        cursor.execute(
            """
            SELECT *
            FROM laborer_profiles
            WHERE user_id = %s
            """,
            (user_id,)
        )

        profile = cursor.fetchone()

        cursor.execute(
            "SELECT district FROM users WHERE user_id = %s AND role = 'laborer'",
            (user_id,)
        )
        user_location = cursor.fetchone() or {}

        return render_template(
            'laborer_profile.html',
            profile=profile,
            district=user_location.get('district', '')
        )

    except Exception as error:

        connection.rollback()
        print("Laborer Profile Error:", error)

        flash('Unable to process your profile. Please try again.', 'error')

        return redirect(url_for('laborer_dashboard'))

    finally:

        if cursor:
            cursor.close()

        connection.close()




# =====================================
# LABORER SERVICES MANAGEMENT
# =====================================

def _laborer_only():
    """Check that the current session belongs to a laborer."""
    return (
        'user_id' in session
        and session.get('role') == 'laborer'
    )


def _load_laborer_services(cursor, user_id):
    cursor.execute(
        """
        SELECT service_id, service_name, category, description,
               price, availability_status, created_at
        FROM services
        WHERE user_id = %s
        ORDER BY created_at DESC, service_id DESC
        """,
        (user_id,)
    )
    return cursor.fetchall()


@app.route('/laborer/services', methods=['GET', 'POST'])
def my_services():

    if not _laborer_only():
        flash('Please login as a laborer.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('laborer_dashboard'))

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            service_name = request.form.get('service_name', '').strip()
            category = request.form.get('category', '').strip()
            description = request.form.get('description', '').strip()
            price_text = request.form.get('price', '').strip()
            availability_status = request.form.get(
                'availability_status', '1'
            )

            if not all([service_name, category, price_text]):
                flash('Please complete the service name, category and price.', 'error')
            elif len(service_name) > 150:
                flash('Service name must be 150 characters or less.', 'error')
            elif len(category) > 100:
                flash('Category must be 100 characters or less.', 'error')
            elif availability_status not in ('0', '1'):
                flash('Invalid availability option.', 'error')
            else:
                try:
                    price = float(price_text)
                    if price < 0:
                        raise ValueError
                    cursor.execute(
                        """
                        INSERT INTO services
                            (user_id, service_name, category, description,
                             price, availability_status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id, service_name, category, description,
                            price, int(availability_status)
                        )
                    )
                    connection.commit()
                    flash('Your service has been added successfully.', 'success')
                    return redirect(url_for('my_services') + '#services')
                except ValueError:
                    flash('Please enter a valid price (zero or greater).', 'error')

        services = _load_laborer_services(cursor, user_id)
        dashboard_data = _get_laborer_dashboard_data(user_id)

        return render_template(
            'laborer_dashboard.html',
            dashboard_data=dashboard_data,
            services=services,
            editing_service=None,
            show_services=True
        )

    except Exception as error:
        connection.rollback()
        print("My Services Error:", error)
        flash('Unable to load or save services. Please check the services table.', 'error')
        return redirect(url_for('laborer_dashboard'))
    finally:
        if cursor:
            cursor.close()
        connection.close()


@app.route('/laborer/services/edit/<int:service_id>', methods=['GET', 'POST'])
def edit_service(service_id):

    if not _laborer_only():
        flash('Please login as a laborer.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('laborer_dashboard'))

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            service_name = request.form.get('service_name', '').strip()
            category = request.form.get('category', '').strip()
            description = request.form.get('description', '').strip()
            price_text = request.form.get('price', '').strip()
            availability_status = request.form.get('availability_status', '1')

            if not all([service_name, category, price_text]):
                flash('Please complete the service name, category and price.', 'error')
            elif len(service_name) > 150 or len(category) > 100:
                flash('Please check the maximum length of the service name and category.', 'error')
            elif availability_status not in ('0', '1'):
                flash('Invalid availability option.', 'error')
            else:
                try:
                    price = float(price_text)
                    if price < 0:
                        raise ValueError
                    cursor.execute(
                        "SELECT service_id FROM services WHERE service_id = %s AND user_id = %s",
                        (service_id, user_id)
                    )
                    owned_service = cursor.fetchone()

                    if not owned_service:
                        flash('Service not found or you do not have permission to edit it.', 'error')
                    else:
                        cursor.execute(
                            """
                            UPDATE services
                            SET service_name = %s,
                                category = %s,
                                description = %s,
                                price = %s,
                                availability_status = %s
                            WHERE service_id = %s AND user_id = %s
                            """,
                            (
                                service_name, category, description, price,
                                int(availability_status), service_id, user_id
                            )
                        )
                        connection.commit()
                        flash('Service updated successfully.', 'success')
                        return redirect(url_for('my_services') + '#services')
                except ValueError:
                    flash('Please enter a valid price (zero or greater).', 'error')

        cursor.execute(
            """
            SELECT service_id, service_name, category, description,
                   price, availability_status
            FROM services
            WHERE service_id = %s AND user_id = %s
            """,
            (service_id, user_id)
        )
        editing_service = cursor.fetchone()

        if not editing_service:
            flash('Service not found.', 'error')
            return redirect(url_for('my_services'))

        services = _load_laborer_services(cursor, user_id)
        dashboard_data = _get_laborer_dashboard_data(user_id)

        return render_template(
            'laborer_dashboard.html',
            dashboard_data=dashboard_data,
            services=services,
            editing_service=editing_service,
            show_services=True
        )

    except Exception as error:
        connection.rollback()
        print("Edit Service Error:", error)
        flash('Unable to update this service. Please try again.', 'error')
        return redirect(url_for('my_services'))
    finally:
        if cursor:
            cursor.close()
        connection.close()


@app.route('/laborer/services/delete/<int:service_id>', methods=['POST'])
def delete_service(service_id):

    if not _laborer_only():
        flash('Please login as a laborer.', 'error')
        return redirect(url_for('login'))

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('laborer_dashboard'))

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM services WHERE service_id = %s AND user_id = %s",
            (service_id, session['user_id'])
        )

        if cursor.rowcount:
            connection.commit()
            flash('Service deleted successfully.', 'success')
        else:
            flash('Service not found or you do not have permission to delete it.', 'error')

    except Exception as error:
        connection.rollback()
        print("Delete Service Error:", error)
        flash('Unable to delete this service. It may be linked to an existing booking.', 'error')
    finally:
        if cursor:
            cursor.close()
        connection.close()

    return redirect(url_for('my_services') + '#services')


# =====================================
# ADMIN USER MANAGEMENT
# =====================================

@app.route('/admin/users')
def admin_users():

    # Allow administrators only
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an administrator.', 'error')
        return redirect(url_for('login'))

    search_text = request.args.get('q', '').strip()
    selected_role = request.args.get('role', '').strip()

    if selected_role not in ('', 'customer', 'laborer'):
        selected_role = ''

    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_dashboard'))

    cursor = None
    users = []

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                user_id,
                full_name,
                email,
                phone,
                role,
                location
            FROM users
            WHERE role IN ('customer', 'laborer')
        """

        params = []

        if selected_role:
            sql += " AND role = %s"
            params.append(selected_role)

        if search_text:
            sql += """
                AND (
                    full_name LIKE %s
                    OR email LIKE %s
                    OR phone LIKE %s
                    OR location LIKE %s
                )
            """
            pattern = f"%{search_text}%"
            params.extend([pattern, pattern, pattern, pattern])

        sql += " ORDER BY user_id DESC"

        cursor.execute(sql, tuple(params))
        users = cursor.fetchall()

    except Exception as error:
        print("Admin Users Error:", error)
        flash('Unable to load user accounts.', 'error')

    finally:
        if cursor:
            cursor.close()
        connection.close()

    return render_template(
        'admin_users.html',
        users=users,
        search_text=search_text,
        selected_role=selected_role
    )
    
    
# =====================================
# ADMIN SERVICES MANAGEMENT
# =====================================

@app.route('/admin/services')
def admin_services():

    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an administrator.', 'error')
        return redirect(url_for('login'))

    search_text = request.args.get('q', '').strip()
    selected_category = request.args.get('category', '').strip()

    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_dashboard'))

    cursor = None
    services = []
    categories = []

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT DISTINCT category
            FROM services
            WHERE category IS NOT NULL AND category <> ''
            ORDER BY category
        """)
        categories = [row['category'] for row in cursor.fetchall()]

        sql = """
            SELECT
                s.service_id,
                s.service_name,
                s.category,
                s.description,
                s.price,
                s.availability_status,
                s.created_at,
                u.user_id AS laborer_id,
                u.full_name AS laborer_name,
                u.email AS laborer_email,
                u.phone AS laborer_phone,
                u.location AS laborer_location
            FROM services s
            INNER JOIN users u ON u.user_id = s.user_id
            WHERE u.role = 'laborer'
        """

        params = []

        if search_text:
            sql += """
                AND (
                    s.service_name LIKE %s
                    OR s.category LIKE %s
                    OR u.full_name LIKE %s
                    OR u.location LIKE %s
                )
            """
            pattern = f"%{search_text}%"
            params.extend([pattern, pattern, pattern, pattern])

        if selected_category:
            sql += " AND s.category = %s"
            params.append(selected_category)

        sql += " ORDER BY s.service_id DESC"

        cursor.execute(sql, tuple(params))
        services = cursor.fetchall()

        return render_template(
            'admin_services.html',
            services=services,
            categories=categories,
            search_text=search_text,
            selected_category=selected_category
        )

    except Exception as error:
        print("Admin Services Error:", error)
        flash('Unable to load services.', 'error')
        return redirect(url_for('admin_dashboard'))

    finally:
        if cursor:
            cursor.close()
        connection.close()
        
        
        
# =====================================
# ADMIN BOOKINGS MANAGEMENT
# =====================================

@app.route('/admin/bookings')
def admin_bookings():

    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an administrator.', 'error')
        return redirect(url_for('login'))

    search_text = request.args.get('q', '').strip()
    selected_status = request.args.get('status', '').strip()

    allowed_statuses = [
        'Pending',
        'Accepted',
        'In Progress',
        'Completed',
        'Rejected',
        'Cancelled'
    ]

    if selected_status not in allowed_statuses:
        selected_status = ''

    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_dashboard'))

    cursor = None
    bookings = []

    try:
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                b.booking_id,
                b.customer_id,
                b.laborer_id,
                b.service_id,
                b.job_description,
                b.scheduled_date,
                b.scheduled_time,
                b.job_location,
                b.job_status,
                b.created_at,

                customer.full_name AS customer_name,
                customer.email AS customer_email,
                customer.phone AS customer_phone,

                laborer.full_name AS laborer_name,
                laborer.email AS laborer_email,
                laborer.phone AS laborer_phone,

                s.service_name,
                s.category,
                s.price

            FROM bookings b

            INNER JOIN users customer
                ON customer.user_id = b.customer_id

            INNER JOIN users laborer
                ON laborer.user_id = b.laborer_id

            LEFT JOIN services s
                ON s.service_id = b.service_id

            WHERE 1 = 1
        """

        params = []

        if search_text:
            sql += """
                AND (
                    CAST(b.booking_id AS CHAR) LIKE %s
                    OR customer.full_name LIKE %s
                    OR customer.email LIKE %s
                    OR laborer.full_name LIKE %s
                    OR laborer.email LIKE %s
                    OR s.service_name LIKE %s
                    OR b.job_location LIKE %s
                )
            """

            pattern = f"%{search_text}%"

            params.extend([
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern
            ])

        if selected_status:
            sql += " AND b.job_status = %s"
            params.append(selected_status)

        sql += " ORDER BY b.created_at DESC, b.booking_id DESC"

        cursor.execute(sql, tuple(params))
        bookings = cursor.fetchall()

    except Exception as error:
        print("Admin Bookings Error:", error)
        flash('Unable to load booking information.', 'error')

    finally:
        if cursor:
            cursor.close()

        connection.close()

    return render_template(
        'admin_bookings.html',
        bookings=bookings,
        search_text=search_text,
        selected_status=selected_status,
        allowed_statuses=allowed_statuses
    )



# =====================================
# ADMIN DELETE SERVICE
# =====================================

@app.route('/admin/services/delete/<int:service_id>', methods=['POST'])
def admin_delete_service(service_id):

    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an administrator.', 'error')
        return redirect(url_for('login'))

    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_services'))

    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM services WHERE service_id = %s",
            (service_id,)
        )

        if cursor.rowcount == 1:
            connection.commit()
            flash('Service deleted successfully.', 'success')
        else:
            connection.rollback()
            flash('Service not found.', 'error')

    except Exception as error:
        connection.rollback()
        print("Admin Delete Service Error:", error)
        flash(
            'Unable to delete this service. It may be linked to an existing booking.',
            'error'
        )

    finally:
        if cursor:
            cursor.close()
        connection.close()

    return redirect(url_for('admin_services'))




# =====================================
# ADMIN DASHBOARD
# =====================================


@app.route('/admin/payments')
def admin_payments():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an administrator.', 'error')
        return redirect(url_for('login'))
    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_dashboard'))
    cursor = None
    payments = []
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""SELECT bp.booking_id, bp.final_amount, bp.payment_status,
                                 bp.payment_method, bp.created_at, bp.paid_at,
                                 customer.full_name AS customer_name,
                                 customer.email AS customer_email,
                                 laborer.full_name AS laborer_name,
                                 s.service_name
                          FROM booking_payments bp
                          INNER JOIN bookings b ON b.booking_id = bp.booking_id
                          INNER JOIN users customer ON customer.user_id = b.customer_id
                          INNER JOIN users laborer ON laborer.user_id = b.laborer_id
                          LEFT JOIN services s ON s.service_id = b.service_id
                          ORDER BY CASE WHEN bp.payment_status = 'Pending' THEN 0 ELSE 1 END,
                                   bp.created_at DESC""")
        payments = cursor.fetchall()
    except Exception as error:
        print('Admin Payments Error:', error)
        flash('Unable to load payments. Check that booking_payments table exists.', 'error')
    finally:
        if cursor:
            cursor.close()
        connection.close()
    return render_template('admin_payments.html', payments=payments)


@app.route('/admin/payments/<int:booking_id>/confirm', methods=['POST'])
def confirm_payment(booking_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an administrator.', 'error')
        return redirect(url_for('login'))
    payment_method = request.form.get('payment_method', '').strip()
    if payment_method not in ('Cash', 'Bank Transfer'):
        flash('Select a valid payment method.', 'error')
        return redirect(url_for('admin_payments'))
    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_payments'))
    cursor = None
    payment = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""SELECT bp.payment_status, bp.final_amount,
                                 customer.full_name AS customer_name,
                                 customer.email AS customer_email,
                                 s.service_name
                          FROM booking_payments bp
                          INNER JOIN bookings b ON b.booking_id = bp.booking_id
                          INNER JOIN users customer ON customer.user_id = b.customer_id
                          LEFT JOIN services s ON s.service_id = b.service_id
                          WHERE bp.booking_id = %s FOR UPDATE""", (booking_id,))
        payment = cursor.fetchone()
        if not payment or payment['payment_status'] != 'Pending':
            connection.rollback()
            flash('Payment not found or already confirmed.', 'error')
            return redirect(url_for('admin_payments'))
        cursor.execute("""UPDATE booking_payments
                          SET payment_status = 'Paid', payment_method = %s,
                              paid_at = NOW(), confirmed_by_admin_id = %s
                          WHERE booking_id = %s AND payment_status = 'Pending'""",
                       (payment_method, session['user_id'], booking_id))
        if cursor.rowcount != 1:
            connection.rollback()
            flash('Payment status could not be updated.', 'error')
            return redirect(url_for('admin_payments'))
        connection.commit()
        body = (f"Hello {payment['customer_name']},\n\n"
                f"Your payment for LaborConnect booking #{booking_id} has been verified and confirmed.\n"
                f"Service: {payment.get('service_name') or 'Requested service'}\n"
                f"Amount received: Rs. {Decimal(str(payment['final_amount'])):,.2f}\n"
                f"Payment method: {payment_method}\n"
                "Payment status: Paid\n\nThank you for using LaborConnect.")
        sent = send_customer_email(payment.get('customer_email'),
                                   f'LaborConnect - Payment Confirmed / Booking #{booking_id}', body)
        flash(f'Payment for booking #{booking_id} confirmed as Paid.' + ('' if sent else ' Confirmation email could not be sent; check SMTP settings.'), 'success')
    except Exception as error:
        connection.rollback()
        print('Confirm Payment Error:', error)
        flash('Unable to confirm payment. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        connection.close()
    return redirect(url_for('admin_payments'))


@app.route('/admin/dashboard')
def admin_dashboard():

    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an administrator.', 'error')
        return redirect(url_for('login'))

    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('login'))

    cursor = None

    stats = {
        'customers': 0,
        'laborers': 0,
        'services': 0,
        'bookings': 0,
        'pending': 0,
        'completed': 0,
        'reviews': 0,
        'other_bookings': 0
    }

    recent_users = []
    recent_services = []
    recent_bookings = []
    recent_reviews = []

    try:
        cursor = connection.cursor(dictionary=True)

        # User statistics
        cursor.execute("""
            SELECT
                SUM(CASE WHEN role = 'customer' THEN 1 ELSE 0 END) AS customers,
                SUM(CASE WHEN role = 'laborer' THEN 1 ELSE 0 END) AS laborers
            FROM users
        """)

        row = cursor.fetchone() or {}

        stats['customers'] = int(row.get('customers') or 0)
        stats['laborers'] = int(row.get('laborers') or 0)

        # Service statistics
        cursor.execute("SELECT COUNT(*) AS total FROM services")
        stats['services'] = int(cursor.fetchone()['total'])

        # Booking statistics
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN job_status = 'Pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN job_status = 'Completed' THEN 1 ELSE 0 END) AS completed
            FROM bookings
        """)

        row = cursor.fetchone() or {}

        stats['bookings'] = int(row.get('total') or 0)
        stats['pending'] = int(row.get('pending') or 0)
        stats['completed'] = int(row.get('completed') or 0)

        stats['other_bookings'] = (
            stats['bookings']
            - stats['pending']
            - stats['completed']
        )

        # Review statistics
        cursor.execute("SELECT COUNT(*) AS total FROM reviews")
        stats['reviews'] = int(cursor.fetchone()['total'])

        # Recent users
        cursor.execute("""
            SELECT user_id, full_name, email, phone, role, location
            FROM users
            WHERE role IN ('customer', 'laborer')
            ORDER BY user_id DESC
            LIMIT 8
        """)

        recent_users = cursor.fetchall()

        # Recent services
        cursor.execute("""
            SELECT
                s.service_name,
                s.category,
                s.price,
                s.availability_status,
                u.full_name AS laborer_name
            FROM services s
            INNER JOIN users u ON u.user_id = s.user_id
            ORDER BY s.service_id DESC
            LIMIT 8
        """)

        recent_services = cursor.fetchall()

        # Recent bookings
        cursor.execute("""
            SELECT
                b.booking_id,
                b.scheduled_date,
                b.job_status,
                customer.full_name AS customer_name,
                laborer.full_name AS laborer_name,
                s.service_name
            FROM bookings b
            INNER JOIN users customer
                ON customer.user_id = b.customer_id
            INNER JOIN users laborer
                ON laborer.user_id = b.laborer_id
            LEFT JOIN services s
                ON s.service_id = b.service_id
            ORDER BY b.booking_id DESC
            LIMIT 8
        """)

        recent_bookings = cursor.fetchall()

        # Recent reviews
        cursor.execute("""
            SELECT
                r.booking_id,
                r.rating,
                r.review,
                r.created_at,
                customer.full_name AS customer_name,
                laborer.full_name AS laborer_name
            FROM reviews r
            INNER JOIN users customer
                ON customer.user_id = r.customer_id
            INNER JOIN users laborer
                ON laborer.user_id = r.laborer_id
            ORDER BY r.review_id DESC
            LIMIT 8
        """)

        recent_reviews = cursor.fetchall()

    except Exception as error:

        print("Admin Dashboard Error:", error)
        flash('Unable to load admin dashboard data.', 'error')

    finally:

        if cursor:
            cursor.close()

        connection.close()

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        recent_users=recent_users,
        recent_services=recent_services,
        recent_bookings=recent_bookings,
        recent_reviews=recent_reviews
    )
    
    # =====================================
# ADMIN REVIEWS MANAGEMENT
# =====================================

@app.route('/admin/reviews')
def admin_reviews():

    # Allow administrators only
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an administrator.', 'error')
        return redirect(url_for('login'))

    search_text = request.args.get('q', '').strip()
    selected_rating = request.args.get('rating', '').strip()

    if selected_rating not in ('1', '2', '3', '4', '5'):
        selected_rating = ''

    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed.', 'error')
        return redirect(url_for('admin_dashboard'))

    cursor = None
    reviews = []
    stats = {
        'total_reviews': 0,
        'average_rating': 0,
        'five_star': 0,
        'low_ratings': 0
    }

    try:
        cursor = connection.cursor(dictionary=True)

        # Review summary statistics
        cursor.execute("""
            SELECT
                COUNT(*) AS total_reviews,
                COALESCE(AVG(rating), 0) AS average_rating,
                SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) AS five_star,
                SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) AS low_ratings
            FROM reviews
        """)

        summary = cursor.fetchone() or {}

        stats['total_reviews'] = int(summary.get('total_reviews') or 0)
        stats['average_rating'] = round(
            float(summary.get('average_rating') or 0), 1
        )
        stats['five_star'] = int(summary.get('five_star') or 0)
        stats['low_ratings'] = int(summary.get('low_ratings') or 0)

        # Load all reviews with customer and laborer details
        sql = """
            SELECT
                r.review_id,
                r.booking_id,
                r.rating,
                r.review,
                r.created_at,
                customer.full_name AS customer_name,
                laborer.full_name AS laborer_name,
                s.service_name
            FROM reviews r
            INNER JOIN users customer
                ON customer.user_id = r.customer_id
            INNER JOIN users laborer
                ON laborer.user_id = r.laborer_id
            LEFT JOIN bookings b
                ON b.booking_id = r.booking_id
            LEFT JOIN services s
                ON s.service_id = b.service_id
            WHERE 1 = 1
        """

        params = []

        if search_text:
            sql += """
                AND (
                    customer.full_name LIKE %s
                    OR laborer.full_name LIKE %s
                    OR s.service_name LIKE %s
                    OR CAST(r.booking_id AS CHAR) LIKE %s
                    OR COALESCE(r.review, '') LIKE %s
                )
            """

            pattern = f"%{search_text}%"
            params.extend([
                pattern,
                pattern,
                pattern,
                pattern,
                pattern
            ])

        if selected_rating:
            sql += " AND r.rating = %s"
            params.append(int(selected_rating))

        sql += " ORDER BY r.created_at DESC, r.review_id DESC"

        cursor.execute(sql, tuple(params))
        reviews = cursor.fetchall()

    except Exception as error:
        print("Admin Reviews Error:", error)
        flash('Unable to load customer reviews.', 'error')

    finally:
        if cursor:
            cursor.close()

        connection.close()

    return render_template(
        'admin_reviews.html',
        reviews=reviews,
        stats=stats,
        search_text=search_text,
        selected_rating=selected_rating
    )



# =====================================
# LOGOUT
# =====================================


# =====================================
# LABORER ACCOUNT SETTINGS
# =====================================

@app.route('/laborer/settings', methods=['GET', 'POST'])
def laborer_settings():

    if 'user_id' not in session or session.get('role') != 'laborer':
        flash('Please login as a laborer.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    connection = get_db_connection()

    if connection is None:
        flash('Database connection failed. Please try again.', 'error')
        return redirect(url_for('laborer_dashboard'))

    cursor = None
    account = None

    try:
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            action = request.form.get('action', '').strip()

            if action == 'update_account':
                full_name = request.form.get('full_name', '').strip()
                phone = request.form.get('phone', '').strip()
                location = request.form.get('location', '').strip()

                if not full_name or not phone or not location:
                    flash('Please complete all account information fields.', 'error')
                elif len(full_name) < 3:
                    flash('Full name must contain at least 3 characters.', 'error')
                elif not phone.isdigit() or len(phone) != 10 or not phone.startswith('07'):
                    flash('Enter a valid Sri Lankan mobile number (07XXXXXXXX).', 'error')
                else:
                    cursor.execute(
                        """
                        UPDATE users
                        SET full_name = %s, phone = %s, location = %s
                        WHERE user_id = %s AND role = 'laborer'
                        """,
                        (full_name, phone, location, user_id)
                    )
                    connection.commit()
                    session['full_name'] = full_name
                    flash('Account information updated successfully.', 'success')
                    return redirect(url_for('laborer_settings'))

            elif action == 'change_password':
                current_password = request.form.get('current_password', '')
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')

                cursor.execute(
                    "SELECT password FROM users WHERE user_id = %s AND role = 'laborer'",
                    (user_id,)
                )
                password_row = cursor.fetchone()

                if not password_row or not check_password_hash(password_row['password'], current_password):
                    flash('Your current password is incorrect.', 'error')
                elif len(new_password) < 8:
                    flash('New password must contain at least 8 characters.', 'error')
                elif new_password != confirm_password:
                    flash('New password and confirmation do not match.', 'error')
                elif new_password == current_password:
                    flash('New password must be different from your current password.', 'error')
                else:
                    new_hash = generate_password_hash(new_password)
                    cursor.execute(
                        """
                        UPDATE users
                        SET password = %s
                        WHERE user_id = %s AND role = 'laborer'
                        """,
                        (new_hash, user_id)
                    )
                    connection.commit()
                    flash('Password changed successfully. Please keep it secure.', 'success')
                    return redirect(url_for('laborer_settings'))

            else:
                flash('Invalid settings action.', 'error')

        cursor.execute(
            """
            SELECT user_id, full_name, email, phone, location
            FROM users
            WHERE user_id = %s AND role = 'laborer'
            """,
            (user_id,)
        )
        account = cursor.fetchone()

        if not account:
            session.clear()
            flash('Laborer account could not be found. Please login again.', 'error')
            return redirect(url_for('login'))

        return render_template('laborer_settings.html', account=account)

    except Exception as error:
        connection.rollback()
        print('Laborer Settings Error:', error)
        flash('Unable to update settings. Please try again.', 'error')
        return redirect(url_for('laborer_dashboard'))

    finally:
        if cursor:
            cursor.close()
        connection.close()



@app.route('/logout')
def logout():

    session.clear()

    flash(
        'You have logged out successfully.',
        'success'
    )

    return redirect(url_for('home'))


# =====================================
# RUN APPLICATION
# =====================================

if __name__ == '__main__':

    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000
    )
