import os
from dotenv import load_dotenv
import sqlite3
import json
from openai import OpenAI
 
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

DB_NAME = "altn_media.db" # Yeni DB adımız

def ultimate_edit_desk():
    print("🎬 [PHASE 3] Ultimate AI Edit Desk Opened...")
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()

    c.execute("SELECT DISTINCT group_id FROM news_pool WHERE status='awaiting_merge'")
    groups = c.fetchall()

    if not groups:
        print("🤷‍♂️ No new news groups to merge.")
        return

    for (g_id,) in groups:
        print(f"\n⚙️ Processing GROUP ID [{g_id}]...")
        
        c.execute("SELECT id, source_name, title, full_text, media_url FROM news_pool WHERE group_id=?", (g_id,))
        news_items = c.fetchall()
        
        merge_text = ""
        media_pool = [] 
        
        for i, item in enumerate(news_items):
            n_id, src, title, txt, media = item
            merge_text += f"--- SOURCE {i+1} ({src}) ---\nTITLE: {title}\nTEXT: {txt}\n\n"
            if media: media_pool.append(media) 
            
        print(f"   📚 Merging {len(news_items)} different sources...")

        prompt = f"""
        Sen "ALT+N Medya" adında profesyonel, hızlı ve tarafsız bir Instagram haber sayfasının baş editörüsün.
        Aşağıda aynı olayı anlatan {len(news_items)} farklı haber kaynağından gelen metinler var. 
        Senden istediğim bu metinleri HARMANLAYIP, eksik detayları birleştirerek kusursuz, tek bir haber çıkarman.
        
        Bana SADECE şu JSON formatını dön:
        1. "category": Bu haber hangi sayfaya uyar? (Gündem, Ekonomi, Spor, Teknoloji veya Çöp).
        2. "title": Videonun üstüne yazılacak, 4-6 kelimelik çok vurucu başlık.
        3. "reels_text": Harmanlanmış, eksiksiz, akıcı, en fazla 3-4 cümlelik özet metin.

        {merge_text}
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
            
            ai_output = json.loads(response.choices[0].message.content)
            category = ai_output.get("category", "Gündem")
            new_title = ai_output.get("title", "No Title")
            new_text = ai_output.get("reels_text", "")

            if category == "Çöp":
                c.execute("UPDATE news_pool SET status='trash' WHERE group_id=?", (g_id,))
                print("   🗑️ Trash detected, group destroyed.")
            else:
                leader_id = news_items[0][0]
                media_json = json.dumps(media_pool)

                c.execute('''
                    UPDATE news_pool 
                    SET category=?, title=?, full_text=?, media_url=?, status='ultimate_ready' 
                    WHERE id=?
                ''', (category, new_title, new_text, media_json, leader_id))
                
                for item in news_items[1:]:
                    c.execute("UPDATE news_pool SET status='merged' WHERE id=?", (item[0],))
                
                print(f"   ✅ MERGED! Category: {category} | Title: {new_title}")

        except Exception as e:
            print(f"   [ERROR] OpenAI API fucked up: {e}")

    conn.commit()
    conn.close()
    print("🏆 [PHASE 3 DONE] Ultimate news are ready for render!")

if __name__ == "__main__":
    ultimate_edit_desk()