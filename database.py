
import mysql.connector
from mysql.connector import Error
from config import Config


def get_db_connection():

    try:

        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            port=Config.DB_PORT
        )

        if connection.is_connected():
            print("MySQL Database Connected Successfully!")
            return connection

    except Error as error:

        print("Database Connection Error:", error)

    return None
