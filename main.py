import time
import subprocess
import asyncio
from ai_brain import clean_and_group_pool
from ai_rewriter import ai_edit_desk
from render import start_production
from publisher_agent import start_publishing # Yeni yayıncıyı ekledik
import db_manager

def start_daemons():
    print("🚀 [SİSTEM] Toplayıcı ajanlar (RSS & Telegram) sahaya sürülüyor...")
    # Dosya isimlerinin tam eşleştiğinden emin ol amk
    rss_process = subprocess.Popen(["python", "rss_crawler.py"])
    tg_process = subprocess.Popen(["python", "telegram_scraper.py"])
    return rss_process, tg_process

def brain_loop():
    while True:
        try:
            clean_and_group_pool() #
            ai_edit_desk()         #
            start_production()    # Render + Publish artık tek elden!
            
            print("\n⏳ [SİSTEM] Döngü tamam. 5 dakika uyku...")
            time.sleep(300)
        except Exception as e:
            print(f"💥 [KRİTİK HATA]: {e}")
            time.sleep(60)

if __name__ == "__main__":
    db_manager.setup_database()
    rss, tg = start_daemons()
    
    try:
        brain_loop()
    except KeyboardInterrupt:
        print("\n🛑 [SİSTEM] Kapatılıyor... Ajanları da yanımda götürüyorum.")
        rss.terminate()
        tg.terminate()