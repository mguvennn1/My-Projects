import requests

def generate_financial_response(api_key, current_user_input, chat_history=None, context_data=None, *args, **kwargs):
    """
    Gemini API'sine tüm sohbet geçmişini (hafızayı) ve güncel bağlamı göndererek
    akıllı bir finansal danışman yanıtı döner.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # Gemini'ın beklediği contents yapısını kuruyoruz
    contents = []
    
    # 1. Eğer geçmiş mesajlar varsa hafıza olarak contents listesine ekle
    if chat_history and isinstance(chat_history, list):
        for msg in chat_history:
            # Streamlit rol isimlerini Gemini rol isimlerine eşle (assistant -> model)
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
    # 2. En son (aktif) kullanıcı sorusunu bağlamla birleştirerek son eleman olarak ekle
    full_prompt = current_user_input
    if context_data:
        full_prompt = f"--- SİSTEM TARAFINDAN SAĞLANAN EK BİLGİ/BAĞLAM ---\n{context_data}\n---------------------------------------------\nKullanıcı Sorusu: {current_user_input}"
    
    contents.append({
        "role": "user",
        "parts": [{"text": full_prompt}]
    })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{
                "text": "Uzman bir finansal danışman olarak kullanıcıların birikim, yatırım, bütçe ve yükledikleri doküman sorularına "
                        "anlaşılır, mantıklı ve verilere dayalı yanıtlar ver. Kesin yatırım tavsiyesi vermeden "
                        "alternatifleri ve riskleri maddeler halinde Türkçe sun. Yanıtlarında Markdown formatını "
                        "(kalın yazılar, listeler) efektif kullanarak okunabilirliği artır. Eğer sana bir piyasa verisi "
                        "veya doküman içeriği sağlandıysa, yanıtlarında doğrudan o verileri referans alarak konuş. "
                        "Sana gönderilen sohbet geçmişini dikkate alarak, kullanıcının önceki sorularıyla bağlantılı cevaplar ver."
            }]
        },
        "generationConfig": {"temperature": 0.3}
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            response_json = response.json()
            return response_json["candidates"][0]["content"]["parts"][0]["text"], None
        else:
            try:
                error_msg = response.json().get('error', {}).get('message', 'Bilinmeyen Hata')
            except:
                error_msg = "Sunucu hatası oluştu."
            return None, f"API Hatası ({response.status_code}): {error_msg}"
    except Exception as e:
        return None, f"İstek Hatası: {e}"