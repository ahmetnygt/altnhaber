import sqlite3

try:
    conn = sqlite3.connect("altnhaber.db")
    c = conn.cursor()
    c.execute("ALTER TABLE haber_havuzu ADD COLUMN grup_id TEXT")
    conn.commit()
    conn.close()
    print("✅ [BAŞARILI] Veritabanına 'grup_id' kolonu jilet gibi eklendi amk!")
except sqlite3.OperationalError:
    print("⚠️ [BİLGİ] Aga bu kolon zaten ekliymiş, telaşa gerek yok.")