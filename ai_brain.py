import os
from dotenv import load_dotenv
import sqlite3
import numpy as np # (rewriter'da numpy yok, olanları yazarsın)
import uuid
from openai import OpenAI
from datetime import datetime, timedelta
 
# .env dosyasını sisteme yükle
load_dotenv()

# Key'i kasadan çekiyoruz
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

DB_NAME = "altnhaber.db"

def get_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def havuzu_temizle_ve_grupla():
    print("🧠 [YAPAY ZEKA] Frankenstein Faz 2: Bekleme Havuzu Analizi Başladı...")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    zaman_siniri = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT id, kaynak_adi, baslik, tam_metin FROM haber_havuzu WHERE durum='Havuzda' AND cekilen_zaman <= ?", (zaman_siniri,))
    bekleyen_haberler = c.fetchall()

    if not bekleyen_haberler:
        print("⏳ Havuzda demlenmiş yeterli haber yok. Bekliyoruz...")
        return

    islenmis_gruplar = [] 

    for haber in bekleyen_haberler:
        h_id, kaynak, baslik, metin = haber
        
        if not metin or len(metin) < 20:
            c.execute("UPDATE haber_havuzu SET durum='Çöp' WHERE id=?", (h_id,))
            continue

        vektor = get_embedding(metin)
        eslesti_mi = False

        for grup in islenmis_gruplar:
            lider_vektor = grup['vektor']
            benzerlik = cosine_similarity(vektor, lider_vektor)

            if benzerlik > 0.85: 
                print(f"   🚨 [EŞLEŞME YAKALANDI] %{int(benzerlik*100)} -> Gruba Eklendi: {baslik[:30]}...")
                grup['haberler'].append(haber)
                eslesti_mi = True
                break
        
        if not eslesti_mi:
            islenmis_gruplar.append({
                'grup_id': str(uuid.uuid4())[:8], # Rastgele jilet gibi bir 8 haneli ID
                'vektor': vektor,
                'haberler': [haber]
            })

    # DB Güncelleme: Hepsine grup ID basıp Harman_Bekliyor yapıyoruz
    for grup in islenmis_gruplar:
        g_id = grup['grup_id']
        for h in grup['haberler']:
            c.execute("UPDATE haber_havuzu SET durum='Harman_Bekliyor', grup_id=? WHERE id=?", (g_id, h[0]))

    conn.commit()
    conn.close()
    print("🧹 [ANALİZ BİTTİ] Benzer haberler aynı grup ID'si ile etiketlendi!")

if __name__ == "__main__":
    havuzu_temizle_ve_grupla()