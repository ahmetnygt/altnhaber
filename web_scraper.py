import newspaper
from newspaper import Article
from datetime import datetime
from urllib.parse import quote, urlparse

def extract_news_with_newspaper4k(url):
    try:
        # Türkçe karakterli URL'leri tarayıcıların anlayacağı formata çeviriyoruz
        p = urlparse(url)
        safe_url = p.scheme + "://" + p.netloc + quote(p.path)
        if p.query: safe_url += "?" + p.query

        article = Article(safe_url, language='tr') 
        article.download()
        article.parse()
        
        news_data = {
            "source_type": "WEB",
            "source_name": article.meta_site_name if article.meta_site_name else "Unknown",
            "original_link": url,
            "title": article.title,
            "full_text": article.text,
            "media_url": article.top_image,  
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if len(news_data["full_text"]) < 50: return None
        return news_data
    except Exception as e:
        print(f"[ERROR] {url} çekilirken sorun oluştu: {e}")
        return None

if __name__ == "__main__":
    test_url = "https://www.aa.com.tr/tr/gundem/cumhurbaskani-erdogan-hicbir-guc-turkiyeye-ve-turkiye-cumhurbaskanina-parmak-sallayamaz/3906095" 
    
    print("Haber çekiliyor, bekle...")
    sonuc = extract_news_with_newspaper4k(test_url)
    
    if sonuc:
        print("\n--- ÇEKİLEN VERİ ---")
        for anahtar, deger in sonuc.items():
            print(f"{anahtar.upper()}: {deger}")
    else:
        print("Haber çekilemedi.")