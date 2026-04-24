import os
import sqlite3
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
DB_NAME = "altn_media.db"
TARGET_CHAT = '@altnhaber' # Buraya kendi username'ini veya test grubunu yazabilirsin

async def run_publisher():
    print("📤 [PUBLISHER] Yayına hazır içerikler taranıyor...")
    
    # 'altnhaber' session ismini kullanıyoruz, oturumun zaten açık olduğunu varsayıyorum
    client = TelegramClient('altnhaber', API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ [ERROR] Telegram oturumu açık değil! Önce scraper'ı çalıştırıp giriş yap.")
        await client.disconnect()
        return

    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    
    # Sadece renderlanmış ama henüz test edilmemiş videoları çek
    c.execute("SELECT id, title, caption FROM news_pool WHERE status='published'")
    items = c.fetchall()

    if not items:
        print("🤷‍♂️ [PUBLISHER] Paylaşılacak taze mal yok.")
    else:
        for n_id, title, caption_text in items: # summary yerine caption_text oldu
            video_path = f"render_outputs/altn_reels_{n_id}.mp4"

            if os.path.exists(video_path):
                print(f"🚀 [Ateşleniyor] {title[:30]}...")
                # Telegram'a giden uzun metin
                caption = f"🎬 **{title}**\n\n{caption_text}\n\n🤖 *ALT+N Media Production Pipeline Test*"
                
                try:
                    await client.send_file(TARGET_CHAT, video_path, caption=caption, supports_streaming=True)
                    c.execute("UPDATE news_pool SET status='posted_to_test' WHERE id=?", (n_id,))
                    print(f"✅ [BAŞARILI] {n_id} ID'li video Telegram'a fırlatıldı.")
                except Exception as e:
                    print(f"❌ [HATA] Gönderirken patladık: {e}")
            else:
                print(f"⚠️ [UYARI] Video dosyası bulunamadı: {video_path}")

    conn.commit()
    conn.close()
    await client.disconnect()
    
# Argümanları caption_text olarak değiştirdik
async def run_single_publisher(n_id, title, caption_text):
    client = TelegramClient('altnhaber', API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        await client.disconnect()
        return

    video_path = f"render_outputs/altn_reels_{n_id}.mp4"
    if os.path.exists(video_path):
        caption = f"🎬 **{title}**\n\n{caption_text}\n\n🤖 *ALT+N Media Pipeline*"
        try:
            await client.send_file(TARGET_CHAT, video_path, caption=caption, supports_streaming=True)
            # Yayın bittiği an DB'yi kilitlemeden güncelle
            conn = sqlite3.connect(DB_NAME, timeout=30)
            conn.execute("UPDATE news_pool SET status='posted_to_test' WHERE id=?", (n_id,))
            conn.commit()
            conn.close()
            print(f"✅ [SUCCESS] {n_id} Telegram'a fırlatıldı.")
        except Exception as e:
            print(f"❌ [HATA] Gönderirken patladık: {e}")
    
    await client.disconnect()

def publish_single_item(n_id, title, caption_text):
    asyncio.run(run_single_publisher(n_id, title, caption_text))

def start_publishing():
    """Main döngüsünden çağrılacak olan senkron wrapper."""
    asyncio.run(run_publisher())