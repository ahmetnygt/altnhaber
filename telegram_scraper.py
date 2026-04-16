import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
import asyncio
import db_manager

# .env dosyasını sisteme yükle
load_dotenv()

# Şifreleri artık gizli kasadan (.env) çekiyoruz
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# Sızacağımız/Dinleyeceğimiz kanalların Telegram kullanıcı adları (Örn: bpt_haber)
HEDEF_KANALLAR = ['bpthaber', 'solcugazete'] 

# Oturum başlatıyoruz (ilk çalıştırdığında sana telefondan onay kodu sorar, sonra kaydeder)
client = TelegramClient('altnhaber', API_ID, API_HASH)

@client.on(events.NewMessage(chats=HEDEF_KANALLAR))
async def telegram_hortumu(event):
    """
    Hedef kanallara yeni mesaj düştüğü milisaniye tetiklenir.
    """
    mesaj = event.message.message
    
    # Eğer mesaj boşsa (adamlar sadece fotoğraf/reklam vs. atmışsa) pas geç
    if not mesaj:
        return

    # Ortak Havuz formatımızı oluşturuyoruz
    news_data = {
        "kaynak_tipi": "TELEGRAM",
        "kaynak_adi": event.chat.title if event.chat else "Bilinmiyor",
        "baslik": mesaj.split('\n')[0][:50] + "...",  # Mesajın ilk satırını başlık varsayıyoruz
        "tam_metin": mesaj,
        "medya_var_mi": True if event.message.media else False,
        "cekilen_zaman": event.message.date.strftime("%Y-%m-%d %H:%M:%S")
    }
 
    print("\n[ŞİPŞAK YAKALANDI] Yeni Haber Düştü!")
    print(f"Kaynak: {news_data['kaynak_adi']}")
    print(f"Özet: {news_data['tam_metin'][:100]}...\n") 
 
    db_manager.havuza_firlat(news_data)

async def main():
    print("ALT+N Medya Telegram Ajanı sahaya indi... Kanallar pür dikkat dinleniyor.")
    # Kodun kapanmadan sürekli dinlemede kalmasını sağlar
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())