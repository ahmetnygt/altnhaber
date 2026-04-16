import newspaper
from newspaper import Article
from datetime import datetime

def extract_news_with_newspaper4k(url):
    """
    Verilen URL'deki haberin başlığını, metnini ve ana görselini çeker.
    Veritabanına yazılmaya hazır standart sözlük formatında döndürür.
    """
    try:
        # Haberin büyük ihtimalle Türkçe olacağını belirtiyoruz ki parser rahat etsin
        article = Article(url, language='tr') 
        
        # Sayfayı indir ve parçala
        article.download()
        article.parse()
        
        # Ortak Havuz formatımızı oluşturuyoruz
        news_data = {
            "kaynak_tipi": "WEB",
            "kaynak_adi": article.meta_site_name if article.meta_site_name else "Bilinmiyor",
            "orijinal_link": url,
            "baslik": article.title,
            "tam_metin": article.text,
            "medya_url": article.top_image,  # Orijinal haber görseli
            "yayin_tarihi": str(article.publish_date) if article.publish_date else None,
            "cekilen_zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Eğer haberin metni çok kısaysa (mesela galeri falan çekmişse) pas geçmek mantıklı
        if len(news_data["tam_metin"]) < 50:
            print(f"[UYARI] Yetersiz içerik, pas geçiliyor: {url}")
            return None
            
        return news_data

    except Exception as e:
        # Site çökmüş olabilir, ban atmış olabilir. Bot patlamasın diye yakalıyoruz.
        print(f"[HATA] {url} cekilirken sorun olustu: {e}")
        return None

# ------------- TEST KISMI -------------
if __name__ == "__main__":
    # Gidip Webtekno veya benzeri bir siteden taze bir haber linki bul ve buraya yapıştır
    test_url = "https://www.aa.com.tr/tr/gundem/cumhurbaskani-erdogan-hicbir-guc-turkiyeye-ve-turkiye-cumhurbaskanina-parmak-sallayamaz/3906095" 
    
    print("Haber çekiliyor, bekle...")
    sonuc = extract_news_with_newspaper4k(test_url)
    
    if sonuc:
        print("\n--- ÇEKİLEN VERİ ---")
        for anahtar, deger in sonuc.items():
            print(f"{anahtar.upper()}: {deger}")
    else:
        print("Haber çekilemedi.")