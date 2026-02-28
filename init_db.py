import psycopg2

from flask_app.config import Config

def init_db():
    try:
        conn = psycopg2.connect(Config.DATABASE_URL)

        cur = conn.cursor()

        # Create `telemetry` table
        cur.execute("DROP TABLE IF EXISTS telemetries;")
        cur.execute("CREATE TABLE telemetries (id SERIAL PRIMARY KEY," \
                                            "sensor_id VARCHAR(50) NOT NULL," \
                                            "temperature DOUBLE PRECISION NOT NULL," \
                                            "recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);"
                                            )
        
        # Add an example rcord
        cur.execute("INSERT INTO telemetries (sensor_id, temperature) VALUES (%s, %s)", ("room_24", 22.5))
        
        conn.commit()
        
    except Exception as ex:
        print(f"An error occured while running `init_db()`: {ex}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    init_db()