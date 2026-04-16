import sqlite3
from datetime import datetime

DB_NAME = "altnhaber.db"

def veritabanini_kur():
    """ALT+N Medya'nın kalbini oluşturur."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Haberleri tutacağımız ana tablo
    c.execute('''
        CREATE TABLE IF NOT EXISTS haber_havuzu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kaynak_tipi TEXT,
            kaynak_adi TEXT,
            orijinal_link TEXT,
            baslik TEXT,
            tam_metin TEXT,
            medya_url TEXT,
            kategori TEXT DEFAULT 'Bekliyor', 
            durum TEXT DEFAULT 'Havuzda',
            cekilen_zaman TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("[SİSTEM] Veritabanı ve Bekleme Havuzu jilet gibi hazır.")

def havuza_firlat(haber_data):
    """Gelen JSON/Dictionary verisini acımadan veritabanına basar."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            INSERT INTO haber_havuzu 
            (kaynak_tipi, kaynak_adi, orijinal_link, baslik, tam_metin, medya_url, cekilen_zaman)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            haber_data.get('kaynak_tipi'),
            haber_data.get('kaynak_adi'),
            haber_data.get('orijinal_link', ''),
            haber_data.get('baslik'),
            haber_data.get('tam_metin'),
            haber_data.get('medya_var_mi', ''), 
            haber_data.get('cekilen_zaman')
        ))
        conn.commit()
        conn.close()
        print(f"[HAVUZ] Veri depoya kilitlendi! Kaynak: {haber_data.get('kaynak_adi')}")
    except Exception as e:
        print(f"[HATA] Veritabanına yazarken sıçtık: {e}")

if __name__ == "__main__":
    # Sadece bu dosyayı ilk çalıştırdığında tabloyu kursun diye
    veritabanini_kur()