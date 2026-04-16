import os
from dotenv import load_dotenv
import sqlite3
import json
from openai import OpenAI
 
# .env dosyasını sisteme yükle
load_dotenv()

# Key'i kasadan çekiyoruz
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

DB_NAME = "altnhaber.db"

def ultimate_kurgu_masasi():
    print("🎬 [FAZ 3] Ultimate Yapay Zeka Kurgu Masası Açıldı...")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Önce işlem bekleyen benzersiz grup ID'lerini bulalım
    c.execute("SELECT DISTINCT grup_id FROM haber_havuzu WHERE durum='Harman_Bekliyor'")
    gruplar = c.fetchall()

    if not gruplar:
        print("🤷‍♂️ Harmanlanacak yeni haber grubu yok.")
        return

    for (g_id,) in gruplar:
        print(f"\n⚙️ GRUP ID [{g_id}] İşleme Alınıyor...")
        
        # O gruba ait TÜM haberleri çekiyoruz (1 tane de olabilir, 5 tane de)
        c.execute("SELECT id, kaynak_adi, baslik, tam_metin, medya_url FROM haber_havuzu WHERE grup_id=?", (g_id,))
        haberler = c.fetchall()
        
        harmanlanacak_metin = ""
        gorsel_havuzu = [] # Bu diziyi Faz 4'te (Vision kontrolünde) kullanacağız
        
        for i, h in enumerate(haberler):
            harmanlanacak_metin += f"--- {i+1}. KAYNAK ({h[1]}) ---\nBAŞLIK: {h[2]}\nMETİN: {h[3]}\n\n"
            if h[4]: gorsel_havuzu.append(h[4]) # Resim linklerini cebe atıyoruz
            
        print(f"   📚 {len(haberler)} farklı kaynak birleştiriliyor...")

        prompt = f"""
        Sen "ALT+N Medya" adında profesyonel, hızlı ve tarafsız bir Instagram haber sayfasının baş editörüsün.
        Aşağıda aynı olayı anlatan {len(haberler)} farklı haber kaynağından gelen metinler var. 
        Senden istediğim bu metinleri HARMANLAYIP, eksik detayları birleştirerek kusursuz, tek bir haber çıkarman.
        
        Bana SADECE şu JSON formatını dön:
        1. "kategori": Bu haber hangi sayfaya uyar? (Gündem, Ekonomi, Spor, Teknoloji veya Çöp).
        2. "baslik": Videonun üstüne yazılacak, 4-6 kelimelik çok vurucu başlık.
        3. "reels_metni": Harmanlanmış, eksiksiz, akıcı, en fazla 3-4 cümlelik özet metin.

        {harmanlanacak_metin}
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen sadece istenilen formatta JSON üreten bir yapay zeka editörüsün."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" } 
            )
            
            ai_cikti = json.loads(response.choices[0].message.content)
            kategori = ai_cikti.get("kategori", "Gündem")
            yeni_baslik = ai_cikti.get("baslik", "Başlık Bulunamadı")
            yeni_metin = ai_cikti.get("reels_metni", "")

            if kategori == "Çöp":
                c.execute("UPDATE haber_havuzu SET durum='Çöpe_Gitti' WHERE grup_id=?", (g_id,))
                print("   🗑️ Çöp bulundu, tüm grup imha edildi.")
            else:
                # O gruptaki sadece ilk haberi "Ultimate_Hazir" yapıyoruz, diğerlerini "Harmanlandi" yapıp gizliyoruz ki Faz 4 şaşırmasın.
                lider_id = haberler[0][0]
                
                # Bütün görsel havuzunu JSON formatında ilk habere kaydedelim ki Faz 4 oradan alsın
                gorseller_json = json.dumps(gorsel_havuzu)

                c.execute('''
                    UPDATE haber_havuzu 
                    SET kategori=?, baslik=?, tam_metin=?, medya_url=?, durum='Ultimate_Hazir' 
                    WHERE id=?
                ''', (kategori, yeni_baslik, yeni_metin, gorseller_json, lider_id))
                
                # Geri kalanları kapat
                for h in haberler[1:]:
                    c.execute("UPDATE haber_havuzu SET durum='Harmana_Katildi' WHERE id=?", (h[0],))
                
                print(f"   ✅ HARMANLANDI! Kategori: {kategori} | Başlık: {yeni_baslik}")

        except Exception as e:
            print(f"   [HATA] OpenAI API sıçtı: {e}")

    conn.commit()
    conn.close()
    print("🏆 [FAZ 3 BİTTİ] Harmanlanmış Ultimate Haberler render için hazır!")

if __name__ == "__main__":
    ultimate_kurgu_masasi()