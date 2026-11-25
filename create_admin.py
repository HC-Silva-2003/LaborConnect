
from werkzeug.security import generate_password_hash
from database import get_db_connection

admin_name = "System Administrator"
admin_email = "admin@laborconnect.com"
admin_phone = "0712345678"
admin_password = "Admin@12345"
admin_location = "Sri Lanka"

hashed_password = generate_password_hash(admin_password)

connection = get_db_connection()
cursor = connection.cursor()

try:
    cursor.execute(
        "SELECT user_id FROM users WHERE email = %s",
        (admin_email,)
    )

    existing_admin = cursor.fetchone()

    if existing_admin:
        print("Admin account already exists.")

    else:
        cursor.execute("""
            INSERT INTO users
                (full_name, email, phone, password, role, location)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            admin_name,
            admin_email,
            admin_phone,
            hashed_password,
            "admin",
            admin_location
        ))

        connection.commit()
        print("Admin account created successfully!")

except Exception as error:
    connection.rollback()
    print("Error:", error)

finally:
    cursor.close()
    connection.close()
