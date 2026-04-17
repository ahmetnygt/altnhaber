import os
import json
import sqlite3
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, CompositeVideoClip

load_dotenv()
DB_NAME = "altnhaber.db"

def metni_satirlara_bol(metin, font, max_genislik):
    """Metni verilen font ve genişliğe göre akıllıca satırlara ayırır (Word Wrap)."""
    kelimeler = metin.split()
    satirlar = []
    gecici_satir = ""
    for kelime in kelimeler:
        test_satiri = f"{gecici_satir} {kelime}".strip()
        if font.getlength(test_satiri) <= max_genislik:
            gecici_satir = test_satiri
        else:
            satirlar.append(gecici_satir)
            gecici_satir = kelime
    if gecici_satir:
        satirlar.append(gecici_satir)
    return satirlar

def sablonu_uzerine_giydir(haber_resim_yolu, sablon_yolu, cikti_yolu, baslik, ozet_metni, odak_x_yuzde=50, odak_y_yuzde=50):
    """Odak noktasına göre kaydırarak kırpar, şablonu ve sola yatık yazıları çakar."""
    arka_plan = Image.open(haber_resim_yolu).convert("RGBA")
    w, h = arka_plan.size
    
    # Hedef pikseli buluyoruz
    odak_x = w * (odak_x_yuzde / 100)
    odak_y = h * (odak_y_yuzde / 100)

    oran = 9 / 16
    if w / h > oran:
        yeni_w = int(h * oran)
        # SİHİR BURADA: Makası odak noktasına göre sağa/sola kaydır
        sol = odak_x - (yeni_w / 2)
        # Ama resmin dışına taşmasını engelle sike sike sınırlar içinde tut
        sol = max(0, min(sol, w - yeni_w))
        arka_plan = arka_plan.crop((sol, 0, sol + yeni_w, h))
    else:
        yeni_h = int(w / oran)
        # SİHİR BURADA: Makası odak noktasına göre aşağı/yukarı kaydır
        ust = odak_y - (yeni_h / 2)
        ust = max(0, min(ust, h - yeni_h))
        arka_plan = arka_plan.crop((0, ust, w, ust + yeni_h))
    
    arka_plan = arka_plan.resize((1080, 1920), Image.Resampling.LANCZOS)

    # 2. Şablonu Bindir
    if os.path.exists(sablon_yolu):
        sablon = Image.open(sablon_yolu).convert("RGBA")
        sablon = sablon.resize((1080, 1920), Image.Resampling.LANCZOS)
        arka_plan.paste(sablon, (0, 0), sablon)

    # 3. Yazıları Ekle (Bir önceki sola yatık, gölgesiz Jilet kodun aynısı)
    draw = ImageDraw.Draw(arka_plan)
    try:
        font_manset = ImageFont.truetype("Antonio-Bold.ttf", 75) 
        font_ozet = ImageFont.truetype("Antonio-Regular.ttf", 38)
    except:
        font_manset = ImageFont.load_default()
        font_ozet = ImageFont.load_default()

    max_yazi_genisligi = 920 
    x_sol_marjin = 80 
    
    manset_satirlari = metni_satirlara_bol(baslik.upper(), font_manset, max_yazi_genisligi)
    ozet_satirlari = metni_satirlara_bol(ozet_metni, font_ozet, max_yazi_genisligi)

    satir_boslugu_manset = 10
    satir_boslugu_ozet = 8
    
    manset_h = sum([font_manset.getbbox(s)[3] - font_manset.getbbox(s)[1] for s in manset_satirlari]) + (len(manset_satirlari)-1)*satir_boslugu_manset
    ozet_h = sum([font_ozet.getbbox(s)[3] - font_ozet.getbbox(s)[1] for s in ozet_satirlari]) + (len(ozet_satirlari)-1)*satir_boslugu_ozet
    toplam_yazi_yuksekligi = manset_h + 35 + ozet_h 

    baslangic_y = 1480 - toplam_yazi_yuksekligi
    mevcut_y = baslangic_y

    for satir in manset_satirlari:
        draw.text((x_sol_marjin, mevcut_y), satir, font=font_manset, fill=(214, 40, 40, 255))
        mevcut_y += (font_manset.getbbox(satir)[3] - font_manset.getbbox(satir)[1]) + satir_boslugu_manset

    mevcut_y += 35 

    for satir in ozet_satirlari:
        draw.text((x_sol_marjin, mevcut_y), satir, font=font_ozet, fill=(255, 255, 255, 255))
        mevcut_y += (font_ozet.getbbox(satir)[3] - font_ozet.getbbox(satir)[1]) + satir_boslugu_ozet

    final_img = arka_plan.convert("RGB")
    final_img.save(cikti_yolu)

def statik_reels_yap(resim_yolu, video_cikti_yolu):
    """Hareketsiz ama jilet gibi 5 saniyelik MP4 video."""
    clip = ImageClip(resim_yolu).set_duration(5).set_fps(24)
    final_video = CompositeVideoClip([clip], size=(1080, 1920))
    final_video.write_videofile(video_cikti_yolu, codec="libx264", audio=False, logger=None)

def produksiyona_basla():
    print("🎥 [FAZ 4] Kurgu Masası: Tipografi ve Şablon Modu Aktif...")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # DİKKAT: tam_metin kolonunu da çektik ki 1-2 cümlelik özeti yazdırabilelim
    c.execute("SELECT id, baslik, tam_metin, medya_url FROM haber_havuzu WHERE durum='Ultimate_Hazir'")
    haberler = c.fetchall()

    os.makedirs("render_ciktilari", exist_ok=True)

    for h in haberler:
        h_id, baslik, ozet_metni, medya_json = h
        print(f"\n🎬 İşleniyor: {baslik[:40]}...")
        
        try:
            gorseller = json.loads(medya_json)
            secilen_url = next((url for url in gorseller if isinstance(url, str) and url.startswith("http")), None)
            
            if secilen_url:
                temp_raw = f"render_ciktilari/raw_{h_id}.jpg"
                hazir_frame = f"render_ciktilari/frame_{h_id}.jpg"
                video_out = f"render_ciktilari/altn_reels_{h_id}.mp4"

                # 1. Fotoğrafı indir
                r = requests.get(secilen_url)
                with open(temp_raw, 'wb') as f: f.write(r.content)

                # Odak noktasını AI'dan çek
                o_x, o_y = akilli_odak_bul(secilen_url)

                # Yeni akıllı parametrelerle şablonu giydir
                sablonu_uzerine_giydir(temp_raw, "template.png", hazir_frame, baslik, ozet_metni, o_x, o_y)

                # 3. Videoya (MP4) çevir
                statik_reels_yap(hazir_frame, video_out)
                
                c.execute("UPDATE haber_havuzu SET durum='Yayin_Bekliyor' WHERE id=?", (h_id,))
                print(f"✅ ŞAHESER HAZIR: {video_out}")
                
                # Çöpleri sil
                os.remove(temp_raw)
                os.remove(hazir_frame)
            else:
                print("❌ Görsel bulunamadı, pas geçiliyor.")
        except Exception as e:
            print(f"💥 Hata: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    produksiyona_basla()