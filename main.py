import time
import subprocess
from ai_brain import clean_and_group_pool
from ai_rewriter import ai_edit_desk
from render import start_production
import db_manager

def start_daemons():
    print("🚀 [SİSTEM] Ajanlar sahaya sürülüyor...")
    # Arka planda toplayıcıları çalıştır (Terminali kitlemezler, arkada takılırlar)
    # Not: Dosya adlarının senin sistemindekiyle tam eşleştiğine emin ol.
    rss_process = subprocess.Popen(["python", "rss_crawler.py"])
    tg_process = subprocess.Popen(["python", "telegram_scraper.py"]) # Yeni adıyla telegram_agent.py yaptıysan onu yaz
    return rss_process, tg_process

def brain_loop():
    print("🧠 [SİSTEM] Yapay Zeka Orkestrasyonu devrede. Uçuşa geçiyoruz...")
    while True:
        try:
            print("\n" + "="*40)
            print("🎬 YENİ PRODÜKSİYON DÖNGÜSÜ BAŞLIYOR")
            print("="*40)
            
            # 1. Havuzdaki haberleri vektörle ve benzerleri grupla
            clean_and_group_pool()
            
            # 2. Gruplanan haberleri birleştirip tekil, jilet gibi bir metin çıkar
            ai_edit_desk()
            
            # 3. Hazır olan metinlere ve fotoğraflara/videolara reels bas
            start_production()
            
            print("\n⏳ [SİSTEM] Döngü bitti. API'yi dinlendirmek için 5 dakika uyku moduna geçiliyor...")
            time.sleep(300) # 300 saniye (5 dakika) bekle. Gerekirse kısaltırsın.
            
        except Exception as e:
            print(f"💥 [KRİTİK HATA] Ana beyin döngüsünde sıçış yaşandı: {e}")
            print("🔄 60 saniye sonra tekrar denenecek...")
            time.sleep(60) 

if __name__ == "__main__":
    # Önce veritabanı tablolarının kurulu olduğundan emin olalım
    db_manager.setup_database()
    
    # Ajanları sal
    rss, tg = start_daemons()
    
    try:
        # Ana beyni çalıştır
        brain_loop()
    except KeyboardInterrupt:
        # Sen CTRL+C yapıp çıkmak istediğinde arkadaki ajanları da öldürsün, zombi gibi çalışmasınlar
        print("\n🛑 [SİSTEM] Şalter indirildi! Ajanların fişi çekiliyor...")
        rss.terminate()
        tg.terminate()
        print("✅ Fiş çekildi. Hadi eyvallah.")