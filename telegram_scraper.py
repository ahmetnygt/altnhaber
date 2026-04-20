import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
import db_manager

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

TARGET_CHANNELS = ['bpthaber', 'solcugazete']
MEDIA_DIR = "downloaded_media"

# Medyaları indireceğimiz klasör yoksa oluştursun
os.makedirs(MEDIA_DIR, exist_ok=True)

client = TelegramClient('altnhaber', API_ID, API_HASH)

@client.on(events.NewMessage(chats=TARGET_CHANNELS))
async def telegram_hose(event):
    message = event.message.message
    
    # Ne metin ne de medya yoksa siktir et
    if not message and not event.message.media:
        return

    media_path = ""
    # Aha burası sihrin olduğu yer. Video/Foto ayırmadan indirir!
    if event.message.media:
        print("   ⬇️ [DOWNLOAD] Fetching media (Photo/Video)...")
        media_path = await client.download_media(event.message, MEDIA_DIR)
        print(f"   ✅ [SAVED] {media_path}")

    news_data = {
        "source_type": "TELEGRAM",
        "source_name": event.chat.title if event.chat else "Unknown",
        "title": message.split('\n')[0][:50] + "..." if message else "No Title",
        "full_text": message or "",
        "media_url": media_path, # Artık link değil, dosyanın hard diskteki yeri!
        "fetched_at": event.message.date.strftime("%Y-%m-%d %H:%M:%S")
    }
 
    print(f"\n[BINGO] New Drop from {news_data['source_name']}")
    db_manager.toss_into_pool(news_data)

async def main():
    print("🕵️‍♂️ ALT+N Media Telegram Agent deployed... Monitoring targets.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())