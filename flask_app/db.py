import psycopg2

from flask_app.config import Config

def get_db_connection():
    conn = psycopg2.connect(Config.DATABASE_URL)

    return conn