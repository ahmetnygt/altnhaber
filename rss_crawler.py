import feedparser
import time
from web_scraper import extract_news_with_newspaper4k
import db_manager

# Aynı haberleri tekrar tekrar çekip kotayı ve RAM'i ağlatmamak için geçici hafıza
islenmis_linkler = set()

# Kan emilecek hedeflerin RSS linkleri (Burası senin vizyonuna göre uzar gider)
RSS_KAYNAKLARI = [
    "https://www.trthaber.com/gundem_articles.rss",
    "https://www.ntv.com.tr/turkiye.rss",
    "https://www.sozcu.com.tr/rss/gundem.xml",
    "https://feeds.bbci.co.uk/turkce/rss.xml",
    "https://rss.dw.com/xml/rss-tur-all"
]
# GDH,BLOB

def orumcek_mesaisi():
    print("🕸️ [ÖRÜMCEK] RSS Tarayıcı sahaya indi, ağlar atılıyor...")
    
    while True:
        for rss_url in RSS_KAYNAKLARI:
            try:
                # Siteye sessizce gir ve RSS'i hortumla
                feed = feedparser.parse(rss_url)
                print(f"[TARANIYOR] {rss_url} ({len(feed.entries)} içerik bulundu)")
                
                # Sadece en tepedeki taze 5 habere bakıyoruz, geçmişi deşmeye gerek yok
                for entry in feed.entries[:5]:
                    link = entry.link
                    
                    if link not in islenmis_linkler:
                        print(f"   [+] YENİ AV: {entry.title}")
                        islenmis_linkler.add(link)
                        
                        # Newspaper4k'ya linki yolla, içini deşip bize JSON versin
                        haber_data = extract_news_with_newspaper4k(link)
                        
                        if haber_data:
                            # Gelen veriyi acımadan SQLite veritabanına bas
                            db_manager.havuza_firlat(haber_data)
                            
            except Exception as e:
                print(f"   [HATA] {rss_url} taranırken sistem sıçtı: {e}")
        
        print("\n⏳ [ÖRÜMCEK] Devriye bitti. Yeni haberler için 10 dakika uykuya geçiliyor...\n")
        # Botu 600 saniye (10 dakika) uyut ki siteler bizi DDoS atıyoruz sanıp banlamasın
        time.sleep(600) 

if __name__ == "__main__":
    # Tablo yoksa kursun, işi sağlama alalım
    db_manager.veritabanini_kur() 
    orumcek_mesaisi()