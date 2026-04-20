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

def vision_agent(media_source):
    """Hem URL hem yerel dosya destekler. Videoları es geçer."""
    if str(media_source).lower().endswith(('.mp4', '.avi', '.mov')):
        print("   🎥 Video detected. Bypassing Vision API, defaulting to center focus.")
        return False, 50, 50

    print(f"   👁️ Vision Agent deployed, analyzing: {media_source[:30]}...")
    
    try:
        # Link mi yoksa Telegram'dan inen yerel dosya mı?
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
                        {"type": "text", "text": "Sen acımasız bir fotoğraf editörüsün. SADECE JSON dön: {\"has_logo\": true/false, \"focus_x\": 50, \"focus_y\": 30}. Resimde ajans logosu varsa 'has_logo': true yap. Fotoğraf 9:16 kırpılacak, odak x/y yüzdesini ver."},
                        {"type": "image_url", "image_url": image_content}
                    ]
                }
            ],
            response_format={ "type": "json_object" },
            max_tokens=80
        )
        output = json.loads(response.choices[0].message.content)
        return output.get("has_logo", True), output.get("focus_x", 50), output.get("focus_y", 50)
    except Exception as e:
        print(f"   [ERROR] Vision agent went blind: {e}")
        return True, 50, 50 

def create_reels_clip(media_path, video_out_path):
    """Memory leak önleyici try-finally bloğu ile video basımı."""
    clip = None
    final_video = None
    try:
        if media_path.lower().endswith(('.mp4', '.avi', '.mov')):
            clip = VideoFileClip(media_path)
            # Video çok uzunsa Instagram için 15 saniyeye kırp
            if clip.duration > 15:
                clip = clip.subclip(0, 15)
            # Videoyu 9:16 merkeze oturt (Basit yaklaşım)
            # İstersen cropx/y mantığını moviepy fx.crop ile buraya da yedirirsin
            clip = clip.resize(height=1920) 
            clip = clip.set_position(("center", "center"))
        else:
            clip = ImageClip(media_path).set_duration(5).set_fps(24)
            
        final_video = CompositeVideoClip([clip], size=(1080, 1920))
        final_video.write_videofile(video_out_path, codec="libx264", audio=False, logger=None)
    finally:
        # Memory leak'i engelleyen ve sunucuyu çökertmeyen o altın vuruş
        if clip: clip.close()
        if final_video: final_video.close()

def start_production():
    print("🎥 [PHASE 4] Director's Chair. AI and Production Active...")
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()

    c.execute("SELECT id, title, full_text, media_url FROM news_pool WHERE status='ultimate_ready'")
    news_items = c.fetchall()

    os.makedirs("render_outputs", exist_ok=True)

    for item in news_items:
        n_id, title, summary, media_json = item
        print(f"\n🎬 Processing: {title[:40]}...")
        
        try:
            media_list = json.loads(media_json)
            selected_media = None
            o_x, o_y = 50, 50

            for media in media_list:
                if not media: continue
                
                has_logo, ox, oy = vision_agent(media)
                
                if not has_logo:
                    print(f"   ✅ Clean media found! Focus Locked -> X:%{ox} Y:%{oy}")
                    selected_media = media
                    o_x, o_y = ox, oy
                    break
                else:
                    print("   ❌ Logo detected, skipping to next media...")

            if selected_media:
                temp_raw = f"render_outputs/raw_{n_id}.jpg" # Eğer fotoğrafa template giydireceksen
                video_out = f"render_outputs/altn_reels_{n_id}.mp4"

                try:
                    # Medya URL ise indir, yerel dosya ise direkt yolu kullan
                    if selected_media.startswith("http"):
                        r = requests.get(selected_media)
                        with open(temp_raw, 'wb') as f: f.write(r.content)
                        active_media_path = temp_raw
                    else:
                        active_media_path = selected_media # Telegram'dan inen yerel dosya

                    # BURADA: Eski sablonu_uzerine_giydir fonksiyonunu çağırabilirsin (Sola yatık jilet yazılar vs.)
                    # Sadece resimler için çalıştır
                    if not active_media_path.lower().endswith(('.mp4', '.avi', '.mov')):
                         # sablonu_uzerine_giydir(active_media_path, "template.png", temp_raw, title, summary, o_x, o_y)
                         active_media_path = temp_raw

                    create_reels_clip(active_media_path, video_out)
                    
                    c.execute("UPDATE news_pool SET status='published' WHERE id=?", (n_id,))
                    print(f"✅ MASTERPIECE READY: {video_out}")
                
                finally:
                    # İşlem bittikten sonra ortalığı bok götürmesin, temp dosyaları sil
                    if os.path.exists(temp_raw) and temp_raw == active_media_path:
                        os.remove(temp_raw)
            else:
                print("❌ No clean media found. Skipping.")
        except Exception as e:
            print(f"💥 Error: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    start_production()