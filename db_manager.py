import sqlite3
import json
from datetime import datetime

# Yeni, temiz veritabanımız
DB_NAME = "altn_media.db"

def setup_database():
    """Sets up the heart of ALT+N Media."""
    # timeout=10 is crucial for avoiding 'database is locked' errors during concurrent writes
    conn = sqlite3.connect(DB_NAME, timeout=10)
    
    # Enable WAL mode for better concurrency
    conn.execute('PRAGMA journal_mode=WAL;')
    
    c = conn.cursor()
    
    # Main table for the news pool
    c.execute('''
        CREATE TABLE IF NOT EXISTS news_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT,
            source_type TEXT,
            source_name TEXT,
            original_link TEXT,
            title TEXT,
            full_text TEXT,
            caption TEXT, -- YENİ EKLENEN SÜTUN (Açıklama paragrafı için)
            media_url TEXT,
            category TEXT DEFAULT 'pending',
            status TEXT DEFAULT 'pending',
            embedding TEXT, -- VECTOR STORAGE: Saves us money and time
            fetched_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[SYSTEM] Database and Pending Pool are set up like a razor.")

def toss_into_pool(news_data):
    """Throws incoming JSON/Dictionary data into the database mercilessly."""
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        c = conn.cursor()
        c.execute('''
            INSERT INTO news_pool 
            (source_type, source_name, original_link, title, full_text, media_url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            news_data.get('source_type'),
            news_data.get('source_name'),
            news_data.get('original_link', ''),
            news_data.get('title'),
            news_data.get('full_text'),
            news_data.get('media_url', ''), 
            news_data.get('fetched_at')
        ))
        conn.commit()
        conn.close()
        print(f"[POOL] Data locked in the vault! Source: {news_data.get('source_name')}")
    except Exception as e:
        print(f"[ERROR] Shit happened while writing to DB: {e}")

if __name__ == "__main__":
    setup_database()