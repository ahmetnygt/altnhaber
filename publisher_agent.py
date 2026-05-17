import os
import sqlite3
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
from instagrapi import Client
import time

load_dotenv()

# Telegram Ayarları
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
TARGET_CHAT = '@altnhaber' # Telegram kanalın

# Instagram Ayarları
INSTA_USERNAME = os.getenv("INSTA_USERNAME")
INSTA_PASSWORD = os.getenv("INSTA_PASSWORD")

DB_NAME = "altn_media.db"
INSTA_SESSION_FILE = "insta_session.json"

# Instagram Client
insta_client = Client()

def login_instagram():
    """Instagram'a giriş yapar, session dosyasının sahiden çalışıp çalışmadığını test eder."""
    try:
        if os.path.exists(INSTA_SESSION_FILE):
            insta_client.load_settings(INSTA_SESSION_FILE)
            # Session geçerli mi diye ufak bir istek atıp test edelim
            try:
                # Kendi profil bilgimizi çekmeyi deniyoruz, patlamazsa session sağlamdır
                insta_client.current_user() 
                print("🟢 [INSTA] Eski oturum (session) zımba gibi, giriş yapıldı.")
                return # Başarılıysa fonksiyonu bitir ve çık
            except Exception as e:
                print(f"⚠️ [INSTA] Eski oturum patlamış veya süresi dolmuş. Sıfırdan giriliyor... Detay: {e}")
        
        # Eğer dosya yoksa veya üstteki test patladıysa normal giriş yap
        insta_client.login(INSTA_USERNAME, INSTA_PASSWORD)
        insta_client.dump_settings(INSTA_SESSION_FILE)
        print("🟢 [INSTA] Yeni oturum oluşturuldu ve giriş yapıldı.")
    except Exception as e:
        print(f"❌ [INSTA ERROR] Giriş fena patladı: {e}")
        
def get_hashtags(category):
    """Kategoriye göre yapay zekanın seçtiği konuya uygun hashtagler üretir."""
    base_tags = "#sondakika #haber #altnhaber "
    cat_str = str(category).lower() if category else ""
    
    if "ekonomi" in cat_str:
        return base_tags + "#ekonomi #dolar #borsa #finans"
    elif "spor" in cat_str:
        return base_tags + "#spor #futbol #transfer #galatasaray #fenerbahçe #beşiktaş"
    elif "teknoloji" in cat_str:
        return base_tags + "#teknoloji #yapayzeka #bilim #yazılım"
    else:
        return base_tags + "#gündem #türkiye #haberler #gündemhaberleri"

async def run_single_publisher(n_id, title, caption_text):
    print(f"🚀 [PUBLISHER] {n_id} ID'li haber dağıtıma çıkıyor...")
    video_path = f"render_outputs/altn_reels_{n_id}.mp4"
    
    if not os.path.exists(video_path):
        print(f"⚠️ [UYARI] Video dosyası bulunamadı: {video_path}")
        return

    # Veritabanından kategoriyi çekelim (Hashtagler için lazım)
    conn = sqlite3.connect(DB_NAME, timeout=30)
    c = conn.cursor()
    c.execute("SELECT category FROM news_pool WHERE id=?", (n_id,))
    res = c.fetchone()
    category = res[0] if res else "Gündem"

    # --- 1. TELEGRAM YAYINI ---
    client = TelegramClient('altnhaber', API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        tg_caption = f"🎬 **{title}**\n\n{caption_text}\n\n🤖 *ALT+N Media*"
        try:
            await client.send_file(TARGET_CHAT, video_path, caption=tg_caption, supports_streaming=True)
            print("✅ [TELEGRAM] Video başarıyla fırlatıldı.")
        except Exception as e:
            print(f"❌ [TELEGRAM HATA] Gönderirken patladık: {e}")
    await client.disconnect()

    # --- 2. INSTAGRAM REELS YAYINI ---
    login_instagram()
    insta_caption = f"{title}\n\n{caption_text}\n\n{get_hashtags(category)}"
    
    try:
        print("⏳ [INSTA] Video Reels olarak yükleniyor, bu biraz sürebilir...")
        # clip_upload fonksiyonu videoyu Reels olarak Instagram'a basar
        insta_client.clip_upload(
            video_path,
            insta_caption,
            extra_data={
                "custom_accessibility_caption": title,
                "like_and_view_counts_disabled": False,
                "disable_comments": False
            }
        )
        print("✅ [INSTAGRAM] Reels başarıyla yayınlandı!")
    except Exception as e:
        print(f"❌ [INSTAGRAM HATA] Reels atılamadı: {e}")

    # Yayın bitince DB'yi güncelle
    c.execute("UPDATE news_pool SET status='posted_to_all' WHERE id=?", (n_id,))
    conn.commit()
    conn.close()
    print(f"🏆 [BİTTİ] {n_id} numaralı haber tüm platformlara dağıtıldı.")

def publish_single_item(n_id, title, caption_text):
    """Render.py'den çağrılacak asenkron tetikleyici"""
    asyncio.run(run_single_publisher(n_id, title, caption_text))
    
def start_publishing():
    print("🚀 [PUBLISHER] Yayın botu sahaya indi, renderlanmış videoları bekliyor...")
    while True:
        try:
            conn = sqlite3.connect(DB_NAME, timeout=30)
            c = conn.cursor()
            
            # Render motorunun işini bitirdiği (status='rendered') haberleri bul
            c.execute("SELECT id, title, caption FROM news_pool WHERE status='rendered'")
            ready_items = c.fetchall()
            
            for item in ready_items:
                n_id, title, caption_text = item
                # Asenkron dağıtım fonksiyonunu çalıştır (Hem Telegram Hem Insta)
                asyncio.run(run_single_publisher(n_id, title, caption_text))
                
            conn.close()
        except Exception as e:
            print(f"❌ [PUBLISHER HATA] Döngüde bir bokluk çıktı: {e}")
            
        time.sleep(30) # Her 30 saniyede bir yeni video çıkmış mı diye kontrol et

if __name__ == "__main__":
    # Test etmek istersen burayı kullanabilirsin
    pass