import feedparser
import time
import sqlite3
from calendar import timegm
from web_scraper import extract_news_with_newspaper4k # Bunu da sonra refactor ederiz
import db_manager

RSS_SOURCES = [
    "https://www.trthaber.com/gundem_articles.rss",
    "https://www.ntv.com.tr/turkiye.rss",
    "https://www.sozcu.com.tr/rss/gundem.xml",
    "https://feeds.bbci.co.uk/turkce/rss.xml",
    "https://rss.dw.com/xml/rss-tur-all"
]

def is_link_processed(url):
    """Checks the database directly instead of volatile RAM memory."""
    conn = sqlite3.connect(db_manager.DB_NAME, timeout=10)
    c = conn.cursor()
    c.execute("SELECT 1 FROM news_pool WHERE original_link = ?", (url,))
    result = c.fetchone()
    conn.close()
    return bool(result)

def spider_shift():
    print("🕸️ [SPIDER] RSS Crawler hit the field, casting webs...")
    
    while True:
        # Son 5 dakika (300 saniye). Ancak RSS'lerin bazen geç güncellenme 
        # ihtimaline karşı 2 dakika da "güvenlik payı" (buffer) bırakıp son 7 dakikayı tarıyoruz.
        # Merak etme, is_link_processed sayesinde aynı haberi 2 kez DB'ye kaydetmez.
        time_limit = time.time() - (7 * 60) 
        
        for rss_url in RSS_SOURCES:
            try:
                feed = feedparser.parse(rss_url)
                print(f"[SCANNING] {rss_url} ({len(feed.entries)} items found)")
                
                # Artık [:5] yok, tüm listeyi tarıyor ama SADECE son 7 dakikada yayınlananları alıyor!
                for entry in feed.entries:
                    
                    # Haber yayınlanma saatini kontrol et
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        entry_time = timegm(entry.published_parsed)
                        if entry_time < time_limit:
                            continue # Haber eski, direkt atla ve zaman kazan
                            
                    link = entry.link
                    
                    # RAM'e değil, DB'ye soruyoruz!
                    if not is_link_processed(link):
                        print(f"   [+] NEW PREY: {entry.title}")
                        
                        # Newspaper4k ile içeriği deş
                        news_data = extract_news_with_newspaper4k(link)
                        
                        if news_data:
                            db_manager.toss_into_pool(news_data)
                        else:
                            print("   [-] Could not extract meaningful data. Skipping.")
                            
            except Exception as e:
                print(f"   [ERROR] System shit the bed while scanning {rss_url}: {e}")
        
        print("\n⏳ [SPIDER] Patrol finished. Sleeping for 5 minutes...\n")
        time.sleep(300) # Eskiden 600 saniyeydi, 300'e (5 dakika) indirdik.

if __name__ == "__main__":
    spider_shift()