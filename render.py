import os
import json
import sqlite3
import requests
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, CompositeVideoClip

load_dotenv()
# BAK BURAYI SİLMİŞSİN, API OLMADAN YZ ÇALIŞMAZ AMK
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_NAME = "altnhaber.db"

def gorsel_istihbarat_ajani(image_url):
    """Tek sorguda hem filigranı avlar hem de odak noktasını (X,Y) hesaplar."""
    print(f"   👁️ Vision Ajanı devrede, fotoğraf röntgenleniyor...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Sen acımasız bir fotoğraf editörüsün. SADECE şu formatta JSON dön: {\"logolu_mu\": true/false, \"odak_x\": 50, \"odak_y\": 30}. KURALLAR: 1) Resimde DHA, AA, İHA gibi ajans logosu veya şeffaf filigran varsa 'logolu_mu': true yap. 2) Bu fotoğraf 9:16 kırpılacak, en önemli objenin/yüzün yatay (x) ve dikey (y) konumunu yüzde olarak ver."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            response_format={ "type": "json_object" },
            max_tokens=80
        )
        cikti = json.loads(response.choices[0].message.content)
        logolu = cikti.get("logolu_mu", True)
        ox = cikti.get("odak_x", 50)
        oy = cikti.get("odak_y", 50)
        return logolu, ox, oy
    except Exception as e:
        print(f"   [HATA] Ajan kör oldu, risk almıyoruz: {e}")
        return True, 50, 50 # Hata verirse logolu say ve pas geç

def metni_satirlara_bol(metin, font, max_genislik):
    """Metni verilen font ve genişliğe göre akıllıca satırlara ayırır."""
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
    
    # AI'dan gelen Hedef pikseli buluyoruz
    odak_x = w * (odak_x_yuzde / 100)
    odak_y = h * (odak_y_yuzde / 100)

    oran = 9 / 16
    if w / h > oran:
        yeni_w = int(h * oran)
        sol = odak_x - (yeni_w / 2)
        sol = max(0, min(sol, w - yeni_w))
        arka_plan = arka_plan.crop((sol, 0, sol + yeni_w, h))
    else:
        yeni_h = int(w / oran)
        ust = odak_y - (yeni_h / 2)
        ust = max(0, min(ust, h - yeni_h))
        arka_plan = arka_plan.crop((0, ust, w, ust + yeni_h))
    
    arka_plan = arka_plan.resize((1080, 1920), Image.Resampling.LANCZOS)

    # Şablonu Bindir (Attığın dosyada adı template.png'ydi, onu kullanıyorum)
    if os.path.exists(sablon_yolu):
        sablon = Image.open(sablon_yolu).convert("RGBA")
        sablon = sablon.resize((1080, 1920), Image.Resampling.LANCZOS)
        arka_plan.paste(sablon, (0, 0), sablon)
    else:
        print("⚠️ Şablon bulunamadı! Transparan Canva şablonu eksik.")

    # Yazıları Ekle (Sola Yatık, Jilet Gibi)
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
    clip = ImageClip(resim_yolu).set_duration(5).set_fps(24)
    final_video = CompositeVideoClip([clip], size=(1080, 1920))
    final_video.write_videofile(video_cikti_yolu, codec="libx264", audio=False, logger=None)

def produksiyona_basla():
    print("🎥 [FAZ 4] Yönetmen Koltuğuna Geçildi. Zeka ve Prodüksiyon Aktif...")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT id, baslik, tam_metin, medya_url FROM haber_havuzu WHERE durum='Ultimate_Hazir'")
    haberler = c.fetchall()

    os.makedirs("render_ciktilari", exist_ok=True)

    for h in haberler:
        h_id, baslik, ozet_metni, medya_json = h
        print(f"\n🎬 İşleniyor: {baslik[:40]}...")
        
        try:
            gorseller = json.loads(medya_json)
            secilen_url = None
            o_x, o_y = 50, 50

            # Temiz fotoğrafı ve odağı bulana kadar AI'ı yoruyoruz
            for url in gorseller:
                if not isinstance(url, str) or not url.startswith("http"): continue 
                
                logolu_mu, ox, oy = gorsel_istihbarat_ajani(url)
                
                if not logolu_mu:
                    print(f"   ✅ Temiz görsel bulundu! Odak Kilitlendi -> X:%{ox} Y:%{oy}")
                    secilen_url = url
                    o_x, o_y = ox, oy
                    break
                else:
                    print("   ❌ Logolu çıktı, sıradakine geçiliyor...")

            if secilen_url:
                temp_raw = f"render_ciktilari/raw_{h_id}.jpg"
                hazir_frame = f"render_ciktilari/frame_{h_id}.jpg"
                video_out = f"render_ciktilari/altn_reels_{h_id}.mp4"

                r = requests.get(secilen_url)
                with open(temp_raw, 'wb') as f: f.write(r.content)

                # Şablonu giydirirken AI'ın verdiği koordinatları (o_x, o_y) basıyoruz!
                sablonu_uzerine_giydir(temp_raw, "template.png", hazir_frame, baslik, ozet_metni, o_x, o_y)

                statik_reels_yap(hazir_frame, video_out)
                
                c.execute("UPDATE haber_havuzu SET durum='Yayin_Bekliyor' WHERE id=?", (h_id,))
                print(f"✅ ŞAHESER HAZIR: {video_out}")
                
                os.remove(temp_raw)
                os.remove(hazir_frame)
            else:
                print("❌ İşe yarar temiz görsel bulunamadı, pas geçiliyor.")
        except Exception as e:
            print(f"💥 Hata: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    produksiyona_basla()