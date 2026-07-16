import sqlite3
import asyncio
import os
from config import Config

class DatabaseHandler:
    def __init__(self, db_path=Config.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Re-create tables with Speed and Timestamp columns to support dynamic reporting
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Motorcycles (
                Tracking_ID TEXT PRIMARY KEY,
                Read_Number_Plate TEXT,
                Helmet_Detected BOOLEAN,
                Violation_Detected BOOLEAN,
                Speed REAL,
                Timestamp TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Auto_Rickshaws (
                Tracking_ID TEXT PRIMARY KEY,
                Read_Number_Plate TEXT,
                Violation_Detected BOOLEAN,
                Speed REAL,
                Timestamp TEXT
            )
        ''')

        # Added Class_Name column to distinguish between Cars, Trucks, and Buses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Large_Vehicles (
                Tracking_ID TEXT PRIMARY KEY,
                Read_Number_Plate TEXT,
                Violation_Detected BOOLEAN,
                Speed REAL,
                Timestamp TEXT,
                Class_Name TEXT
            )
        ''')

        conn.commit()
        conn.close()

    async def log_motorcycle(self, track_id, plate, helmet, violation, speed, timestamp):
        def sync_log():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO Motorcycles (Tracking_ID, Read_Number_Plate, Helmet_Detected, Violation_Detected, Speed, Timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (track_id, plate, helmet, violation, speed, timestamp))
            conn.commit()
            conn.close()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_log)

    async def log_auto_rickshaw(self, track_id, plate, violation, speed, timestamp):
        def sync_log():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO Auto_Rickshaws (Tracking_ID, Read_Number_Plate, Violation_Detected, Speed, Timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (track_id, plate, violation, speed, timestamp))
            conn.commit()
            conn.close()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_log)

    async def log_large_vehicle(self, track_id, plate, violation, speed, timestamp, class_name):
        def sync_log():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO Large_Vehicles (Tracking_ID, Read_Number_Plate, Violation_Detected, Speed, Timestamp, Class_Name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (track_id, plate, violation, speed, timestamp, class_name))
            conn.commit()
            conn.close()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_log)
