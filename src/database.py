import sqlite3
import pandas as pd
import os

DB_PATH = "data/agriculture_ops.db"
CSV_PATH = "agri_12.csv"

def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_sample_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Create procurement and operational tables if they don't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collection_centers (
        center_id TEXT PRIMARY KEY,
        center_name TEXT,
        region TEXT,
        capacity_tons REAL
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farmers (
        farmer_id TEXT PRIMARY KEY,
        farmer_name TEXT,
        group_name TEXT,
        center_id TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS procurement (
        procurement_id TEXT PRIMARY KEY,
        farmer_id TEXT,
        center_id TEXT,
        crop_type TEXT,
        quantity_kg REAL,
        quality_grade TEXT,
        date TEXT,
        payment_status TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        farmer_id TEXT,
        amount REAL,
        status TEXT,
        due_date TEXT
    )""")
    
    conn.commit()
    
    # 2. Seed sample operational data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM collection_centers;")
    if cursor.fetchone()[0] == 0:
        print("🌱 Seeding sample operational data into SQLite...")
        
        # Collection Centers
        centers = [
            ("C001", "North Hub Center", "North Region", 500.0),
            ("C002", "South Agri Depot", "South Region", 750.0),
            ("C003", "East Valley Silos", "East Region", 600.0),
            ("C004", "West Plains Terminal", "West Region", 1000.0)
        ]
        cursor.executemany("INSERT OR IGNORE INTO collection_centers VALUES (?, ?, ?, ?)", centers)
        
        # Farmers
        farmers = [
            ("F101", "Ramesh Kumar", "Green Valley Group", "C001"),
            ("F102", "Suresh Patel", "Sunrise Farmers", "C002"),
            ("F103", "Amit Singh", "Delta Growers", "C003"),
            ("F104", "Priya Sharma", "Highland Union", "C004")
        ]
        cursor.executemany("INSERT OR IGNORE INTO farmers VALUES (?, ?, ?, ?)", farmers)
        
        # Procurement
        procurements = [
            ("P001", "F101", "C001", "Wheat", 2500.0, "Grade A", "2026-01-10", "Paid"),
            ("P002", "F102", "C002", "Paddy", 4000.0, "Grade B", "2026-01-12", "Pending"),
            ("P003", "F103", "C003", "Cotton", 1500.0, "Grade A", "2026-01-15", "Pending"),
            ("P004", "F104", "C004", "Maize", 3200.0, "Grade C", "2026-01-18", "Paid")
        ]
        cursor.executemany("INSERT OR IGNORE INTO procurement VALUES (?, ?, ?, ?, ?, ?, ?, ?)", procurements)
        
        # Payments
        payments = [
            ("PAY01", "F101", 45000.0, "Completed", "2026-01-15"),
            ("PAY02", "F102", 72000.0, "Pending", "2026-02-01"),
            ("PAY03", "F103", 30000.0, "Pending", "2026-02-05"),
            ("PAY04", "F104", 55000.0, "Completed", "2026-01-20")
        ]
        cursor.executemany("INSERT OR IGNORE INTO payments VALUES (?, ?, ?, ?, ?)", payments)
        conn.commit()

    # 3. Automatically ingest agri_12.csv into SQLite if not already loaded
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='field_surveys';")
    if not cursor.fetchone():
        print("📥 Ingesting agri_12.csv into SQLite (this runs once)...")
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
            df.to_sql("field_surveys", conn, if_exists="replace", index=False)
            print("✅ CSV Ingestion complete!")
        else:
            print(f"⚠️ Warning: {CSV_PATH} not found in root folder.")

    # 4. Create high-performance indexes across all tables
    print("⚡ Building performance indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_survey_state ON field_surveys(state);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_survey_crop ON field_surveys(primary_crop);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_survey_season ON field_surveys(crop_season);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_procurement_crop ON procurement(crop_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);")
    conn.commit()
            
    conn.close()

def run_sql_query(query: str) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df