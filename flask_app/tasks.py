from celery import Celery

from flask_app.config import Config
from flask_app.db import get_db_connection

celery_app = Celery("tasks", broker=Config.BROKER_URL)

@celery_app.task
def save_to_db_async(sensor_id, temperature):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("INSERT INTO telemetries (sensor_id, temperature) VALUES (%s, %s)", (sensor_id, temperature))
        conn.commit()

        print(f"[WORKER] {sensor_id} has been written to the DB: {temperature}")
    except Exception as ex:
        print(f"[ERROR] An error occured while writing telemetry datas: {ex}")
    finally:
        cur.close()
        conn.close()