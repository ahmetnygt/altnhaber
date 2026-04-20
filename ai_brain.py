import os
import json
import sqlite3
import numpy as np
import uuid
from openai import OpenAI
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

DB_NAME = "altn_media.db"

def get_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def clean_and_group_pool():
    print("🧠 [AI] Frankenstein Phase 2: Pending Pool Analysis Started...")
    
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()

    time_limit = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Sadece bekleyenleri çekiyoruz, embedding'i de alıyoruz
    c.execute("SELECT id, source_name, title, full_text, embedding FROM news_pool WHERE status='pending' AND fetched_at <= ?", (time_limit,))
    pending_news = c.fetchall()

    if not pending_news:
        print("⏳ Not enough marinated news in the pool. Waiting...")
        conn.close()
        return

    processed_groups = []

    for news in pending_news:
        n_id, source, title, text, embedding_json = news
        
        if not text or len(text) < 20:
            c.execute("UPDATE news_pool SET status='trash' WHERE id=?", (n_id,))
            continue

        # Kilit Nokta: Embedding DB'de varsa API'ye gitme, yoksa hesapla ve hemen kaydet!
        if embedding_json:
            vector = np.array(json.loads(embedding_json))
        else:
            print(f"   [API CALL] Generating vector for: {title[:30]}...")
            try:
                vector_list = get_embedding(text)
                vector = np.array(vector_list)
                # Save immediately so we don't pay for it again if script crashes
                c.execute("UPDATE news_pool SET embedding=? WHERE id=?", (json.dumps(vector_list), n_id))
                conn.commit() 
            except Exception as e:
                print(f"   [ERROR] Embedding API failed for {n_id}: {e}")
                continue

        matched = False

        for group in processed_groups:
            leader_vector = group['vector']
            similarity = cosine_similarity(vector, leader_vector)

            if similarity > 0.85: 
                print(f"   🚨 [MATCH CAUGHT] %{int(similarity*100)} -> Added to Group: {title[:30]}...")
                group['news_ids'].append(n_id)
                matched = True
                break
        
        if not matched:
            processed_groups.append({
                'group_id': str(uuid.uuid4())[:8], 
                'vector': vector,
                'news_ids': [n_id]
            })

    # DB Update: Group everything and set status to 'awaiting_merge'
    for group in processed_groups:
        g_id = group['group_id']
        for news_id in group['news_ids']:
            c.execute("UPDATE news_pool SET status='awaiting_merge', group_id=? WHERE id=?", (g_id, news_id))

    conn.commit()
    conn.close()
    print("🧹 [ANALYSIS FINISHED] Similar news tagged with the same group ID!")

if __name__ == "__main__":
    clean_and_group_pool()