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

        # Schema A: Motorcycles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Motorcycles (
                Tracking_ID TEXT PRIMARY KEY,
                Read_Number_Plate TEXT,
                Helmet_Detected BOOLEAN,
                Violation_Detected BOOLEAN
            )
        ''')

        # Schema B: Auto-Rickshaws
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Auto_Rickshaws (
                Tracking_ID TEXT PRIMARY KEY,
                Read_Number_Plate TEXT,
                Violation_Detected BOOLEAN
            )
        ''')

        # Schema C: Large Vehicles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Large_Vehicles (
                Tracking_ID TEXT PRIMARY KEY,
                Read_Number_Plate TEXT,
                Violation_Detected BOOLEAN
            )
        ''')

        conn.commit()
        conn.close()

    async def log_motorcycle(self, track_id, plate, helmet, violation):
        def sync_log():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO Motorcycles (Tracking_ID, Read_Number_Plate, Helmet_Detected, Violation_Detected)
                VALUES (?, ?, ?, ?)
            ''', (track_id, plate, helmet, violation))
            conn.commit()
            conn.close()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_log)

    async def log_auto_rickshaw(self, track_id, plate, violation):
        def sync_log():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO Auto_Rickshaws (Tracking_ID, Read_Number_Plate, Violation_Detected)
                VALUES (?, ?, ?)
            ''', (track_id, plate, violation))
            conn.commit()
            conn.close()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_log)

    async def log_large_vehicle(self, track_id, plate, violation):
        def sync_log():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO Large_Vehicles (Tracking_ID, Read_Number_Plate, Violation_Detected)
                VALUES (?, ?, ?)
            ''', (track_id, plate, violation))
            conn.commit()
            conn.close()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_log)
