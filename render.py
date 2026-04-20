import os
import json
import sqlite3
import requests
import base64
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, VideoFileClip, CompositeVideoClip

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_NAME = "altn_media.db"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def split_text_into_lines(text, font, max_width):
    """Metni verilen font ve genişliğe göre akıllıca satırlara ayırır."""
    # Eski getbbox/getsize hatalarını engellemek için getlength kullanıyoruz
    words = text.split()
    lines = []
    temp_line = ""
    for word in words:
        test_line = f"{temp_line} {word}".strip()
        # draw.textlength kullanımı daha güvenlidir
        if font.getlength(test_line) <= max_width:
            temp_line = test_line
        else:
            lines.append(temp_line)
            temp_line = word
    if temp_line:
        lines.append(temp_line)
    return lines

def create_transparent_overlay(title, summary, overlay_out_path):
    """
    Arkası transparan 1080x1920 bir PNG oluşturur.
    Üzerine template.png'yi ve metinleri çakar.
    Bunu videonun veya fotoğrafın üstüne sticker gibi yapıştıracağız.
    """
    # Tamamen transparan bir tuval aç
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    
    # Şablonu Bindir
    template_path = "template.png"
    if os.path.exists(template_path):
        template = Image.open(template_path).convert("RGBA")
        template = template.resize((1080, 1920), Image.Resampling.LANCZOS)
        overlay.paste(template, (0, 0), template)
    else:
        print("   ⚠️ [WARNING] template.png bulunamadı! Yazılar şablonsuz basılacak.")

    # Yazıları Ekle (Sola Yatık)
    draw = ImageDraw.Draw(overlay)
    try:
        font_title = ImageFont.truetype("Antonio-Bold.ttf", 75) 
        font_summary = ImageFont.truetype("Antonio-Regular.ttf", 38)
    except:
        print("   ⚠️ [WARNING] Antonio fontları bulunamadı, default font kullanılıyor.")
        font_title = ImageFont.load_default()
        font_summary = ImageFont.load_default()

    max_text_width = 920 
    x_left_margin = 80 
    
    title_lines = split_text_into_lines(title.upper(), font_title, max_text_width)
    summary_lines = split_text_into_lines(summary, font_summary, max_text_width)

    line_spacing_title = 10
    line_spacing_summary = 8
    
    # Yazıların toplam yüksekliğini hesapla ki aşağıdan yukarı hizalayabilelim
    # Font metriklerini güvenli şekilde alalım
    ascent_t, descent_t = font_title.getmetrics()
    h_title = ascent_t + descent_t
    
    ascent_s, descent_s = font_summary.getmetrics()
    h_summary = ascent_s + descent_s

    total_title_h = len(title_lines) * h_title + (len(title_lines)-1) * line_spacing_title
    total_summary_h = len(summary_lines) * h_summary + (len(summary_lines)-1) * line_spacing_summary
    total_text_height = total_title_h + 35 + total_summary_h 

    start_y = 1480 - total_text_height
    current_y = start_y

    for line in title_lines:
        draw.text((x_left_margin, current_y), line, font=font_title, fill=(214, 40, 40, 255))
        current_y += h_title + line_spacing_title

    current_y += 35 # Başlık ile özet arası ekstra boşluk

    for line in summary_lines:
        draw.text((x_left_margin, current_y), line, font=font_summary, fill=(255, 255, 255, 255))
        current_y += h_summary + line_spacing_summary

    overlay.save(overlay_out_path, "PNG")
    return overlay_out_path

def vision_agent(media_source):
    """Video gelirse 1. saniyesinden frame alıp logoyu tarar, API parasını sömürmez."""
    print(f"   👁️ Vision Agent deployed, analyzing: {media_source[:30]}...")
    
    try:
        if str(media_source).lower().endswith(('.mp4', '.avi', '.mov')):
            print("   🎥 Video detected. Extracting a test frame for the Vision API...")
            temp_frame = "temp_vision_frame.jpg"
            
            try:
                with VideoFileClip(media_source) as clip:
                    t = 1.0 if clip.duration > 1.0 else clip.duration / 2.0
                    frame = clip.get_frame(t)
                    Image.fromarray(frame).save(temp_frame)
                
                base64_image = encode_image(temp_frame)
                image_content = {"url": f"data:image/jpeg;base64,{base64_image}"}
                
                if os.path.exists(temp_frame): os.remove(temp_frame)
            except Exception as e:
                print(f"   [ERROR] Frame extraction failed: {e}")
                return True, 50, 50 
        else:
            if media_source.startswith("http"):
                image_content = {"url": media_source}
            else:
                base64_image = encode_image(media_source)
                image_content = {"url": f"data:image/jpeg;base64,{base64_image}"}

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Sen acımasız bir fotoğraf editörüsün. SADECE JSON dön: {\"has_logo\": true/false, \"focus_x\": 50, \"focus_y\": 30}. Resimde ajans logosu veya filigran varsa 'has_logo': true yap. Fotoğraf 9:16 kırpılacak, odak x/y yüzdesini ver."},
                        {"type": "image_url", "image_url": image_content}
                    ]
                }
            ],
            response_format={ "type": "json_object" },
            max_tokens=80
        )
        output = json.loads(response.choices[0].message.content)
        is_contaminated = output.get("has_logo", True)
        if is_contaminated and str(media_source).lower().endswith(('.mp4', '.avi', '.mov')):
             print("   ⚠️ [WARNING] Logo detected in the video frame! Trashing it.")
        return is_contaminated, output.get("focus_x", 50), output.get("focus_y", 50)

    except Exception as e:
        print(f"   [ERROR] Vision agent went blind: {e}")
        return True, 50, 50 

def create_reels_clip(media_path, overlay_path, video_out_path):
    """Base medyayı (Video/Resim) alta koyar, Transparan Şablonu üstüne yapıştırır."""
    base_clip = None
    overlay_clip = None
    final_video = None
    try:
        # 1. Base Medyayı Ayarla (Alt Katman)
        if media_path.lower().endswith(('.mp4', '.avi', '.mov')):
            base_clip = VideoFileClip(media_path)
            if base_clip.duration > 15:
                base_clip = base_clip.subclip(0, 15)
            # Videoyu dik boyuta oturt ve ortala
            base_clip = base_clip.resize(height=1920) 
            base_clip = base_clip.set_position(("center", "center"))
        else:
            # Resimse 5 saniyelik statik video yap
            base_clip = ImageClip(media_path).set_duration(5).set_fps(24)
            # Burada AI'dan gelen focus_x, focus_y ile crop yapabilirsin, şimdilik merkeze oturtuyoruz
            base_clip = base_clip.resize(height=1920)
            base_clip = base_clip.set_position(("center", "center"))
            
        # 2. Transparan Şablonu Ayarla (Üst Katman)
        overlay_clip = ImageClip(overlay_path).set_duration(base_clip.duration)
        overlay_clip = overlay_clip.set_position(("center", "center"))
            
        # 3. İkisini Üst Üste Bindir!
        final_video = CompositeVideoClip([base_clip, overlay_clip], size=(1080, 1920))
        final_video.write_videofile(video_out_path, codec="libx264", audio=False, logger=None)
    finally:
        if base_clip: base_clip.close()
        if overlay_clip: overlay_clip.close()
        if final_video: final_video.close()

def start_production():
    print("🎥 [PHASE 4] Director's Chair. AI and Production Active...")
    
    # 1. Önce listeyi alıyoruz ve veritabanı kilitlenmesin diye BAĞLANTIYI HEMEN KAPATIYORUZ
    conn = sqlite3.connect(DB_NAME, timeout=30)
    c = conn.cursor()
    c.execute("SELECT id, title, full_text, media_url FROM news_pool WHERE status='render_ready'")
    news_items = c.fetchall()
    conn.close() 

    if not news_items:
        print("🤷‍♂️ No news ready for rendering. Sleeping...")
        return

    os.makedirs("render_outputs", exist_ok=True)

    for item in news_items:
        n_id, title, summary, media_json = item
        print(f"\n🎬 Processing: {title[:40]}...")
        
        try:
            media_list = json.loads(media_json)
            selected_media = None
            o_x, o_y = 50, 50

            # 2. Temiz medya bulana kadar havuzu deşiyoruz
            for media in media_list:
                if not media: continue
                
                has_logo, ox, oy = vision_agent(media) #
                
                if not has_logo:
                    print(f"   ✅ Clean media found! Focus Locked -> X:%{ox} Y:%{oy}")
                    selected_media = media
                    o_x, o_y = ox, oy
                    break
                else:
                    print("   ❌ Logo detected, skipping to next media...")

            if selected_media:
                temp_raw = f"render_outputs/raw_{n_id}.jpg" 
                temp_overlay = f"render_outputs/overlay_{n_id}.png"
                video_out = f"render_outputs/altn_reels_{n_id}.mp4"
                masterpiece_ready = False

                try:
                    # Medya URL (RSS) ise indir, yerel yol (Telegram) ise direkt kullan
                    if selected_media.startswith("http"):
                        r = requests.get(selected_media)
                        with open(temp_raw, 'wb') as f: f.write(r.content)
                        active_media_path = temp_raw
                    else:
                        active_media_path = selected_media 

                    # 3. Transparan şablonu ve yazıları üret
                    create_transparent_overlay(title, summary, temp_overlay)

                    # 4. Render motorunu ateşle
                    create_reels_clip(active_media_path, temp_overlay, video_out)
                    masterpiece_ready = True
                    
                    # 5. Render bittiği an durumunu güncelle (Granüler bağlantı)
                    conn = sqlite3.connect(DB_NAME, timeout=30)
                    conn.execute("UPDATE news_pool SET status='published' WHERE id=?", (n_id,))
                    conn.commit()
                    conn.close()
                    
                    print(f"✅ MASTERPIECE READY: {video_out}")

                    # 6. BEKLEME YAPMA, HEMEN TELEGRAM'A FIRLAT!
                    print(f"📤 Render bitti, {n_id} hemen yayına gidiyor...")
                    publish_single_item(n_id, title, summary)
                
                finally:
                    # Arkada çöp bırakmıyoruz, try-finally ile her durumda temizlik
                    if os.path.exists(temp_raw) and temp_raw == active_media_path:
                        os.remove(temp_raw)
                    if os.path.exists(temp_overlay):
                        os.remove(temp_overlay)
            else:
                print("❌ No clean media found. Skipping.")
        except Exception as e:
            print(f"💥 Error in production for ID {n_id}: {e}")

    print("🏆 [PHASE 4 DONE] Production cycle finished.")
    
if __name__ == "__main__":
    start_production()