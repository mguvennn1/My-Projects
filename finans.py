import streamlit as st
import requests
import os
import yfinance as yf
import pandas as pd
import plotly.express as px
from pypdf import PdfReader
from auth import init_auth_db, auth_interface, logout_user
from api import generate_financial_response

# --- GARANTİ .ENV OKUMA YÖNTEMİ ---
api_key = os.getenv("GEMINI_API_KEY")

if not api_key and os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY"):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    os.environ["GEMINI_API_KEY"] = api_key
    except Exception as e:
        print(f".env dosyası okunurken hata oluştu: {e}")

# 1. Sayfa Yapılandırması
st.set_page_config(page_title="TG Finansal Asistan", page_icon="💰", layout="wide")

# Firebase URL Bilgisi
FIREBASE_URL = "https://planning-with-ai-17b8d-default-rtdb.firebaseio.com/"

# 2. Oturum Durumunu Başlatma
init_auth_db()

def load_all_chats_rest(username):
    """Kullanıcının Firebase'deki tüm geçmiş sohbet odalarını çeker."""
    try:
        url = f"{FIREBASE_URL}chat_histories/{username}.json"
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            chats = response.json()
            return chats if isinstance(chats, dict) else {}
    except Exception as e:
        print(f"Sohbet geçmişi yükleme hatası: {e}")
    return {}

def save_single_chat_rest(username, chat_id, messages):
    """Aktif olan sohbet odasını Firebase'e kaydeder."""
    try:
        url = f"{FIREBASE_URL}chat_histories/{username}/{chat_id}.json"
        requests.put(url, json=messages, timeout=4)
    except Exception as e:
        print(f"Sohbet kaydetme hatası: {e}")

def delete_all_chats_rest(username):
    """Kullanıcının tüm sohbet geçmişini Firebase'den siler."""
    try:
        url = f"{FIREBASE_URL}chat_histories/{username}.json"
        requests.delete(url, timeout=4)
    except Exception as e:
        print(f"Sohbet geçmişi silme hatası: {e}")

@st.cache_data(ttl=300)
def get_market_data():
    """Yahoo Finance kullanarak güncel piyasa verilerini çeker."""
    data_str = "GÜNCEL PİYASA VERİLERİ:\n"
    summary_dict = {}
    raw_prices = {"USD": 1.0, "EUR": 1.0, "GOLD": 1.0}
    try:
        usd = yf.Ticker("USDTRY=X").fast_info.last_price
        eur = yf.Ticker("EURTRY=X").fast_info.last_price
        gold_ons = yf.Ticker("GC=F").fast_info.last_price
        gold_gram = (gold_ons / 31.1034768) * usd
        
        raw_prices["USD"] = usd
        raw_prices["EUR"] = eur
        raw_prices["GOLD"] = gold_gram
        
        summary_dict = {
            "Dolar (USD/TRY)": f"{usd:.2f} TL",
            "Euro (EUR/TRY)": f"{eur:.2f} TL",
            "Gram Altın": f"{gold_gram:.2f} TL",
            "Ons Altın": f"${gold_ons:.2f}"
        }
        
        for k, v in summary_dict.items():
            data_str += f"- {k}: {v}\n"
    except Exception as e:
        data_str += "Piyasa verileri şu an çekilemedi.\n"
    return data_str, summary_dict, raw_prices

# 3. Oturum (Giriş) Kontrolü
if not st.session_state.get("logged_in", False):
    auth_interface()
    st.stop()

# --- BURADAN SONRASI SADECE GİRİŞ YAPILDIYSA ÇALIŞIR ---
username = st.session_state["username"]

# Kullanıcının tüm sohbet odalarını Firebase'den yükle
if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_all_chats_rest(username)

# Aktif bir sohbet odası seçili değilse, ekranda görünecek geçici bir boş hafıza aç
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None

# Canlı piyasa verilerini çekelim
market_context, market_ui, raw_prices = get_market_data()

# --- ARABİRİM DÜZENİ ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.write(f"Hoş Geldiniz, **{username}**!")
    st.divider()

    # --- YAPAY ZEKA PERSONA SEÇİMİ ---
    st.subheader("🤖 Asistan Karakteri")
    persona_choice = st.selectbox(
        "Finansal Danışman Tipi:",
        ["⚖️ Dengeli Danışman", "🛡️ Muhafazakar (Garanti)", "🚀 Agresif (Yatırımcı)", "📉 Bütçe Koçu"]
    )
    
    persona_prompts = {
        "⚖️ Dengeli Danışman": "Uzman bir finansal danışman olarak dengeli, riskleri ve kazançları objektif değerlendiren bir üslup kullan.",
        "🛡️ Muhafazakar (Garanti)": "Aşırı riskten kaçınan, kullanıcının birikimlerini korumaya odaklanan bir finansal danışmansın. Vadeli hesap, altın ve devlet tahvili gibi risksiz enstrümanları önceliklendir.",
        "🚀 Agresif (Yatırımcı)": "Yüksek getiri hedefleyen, borsa, hisse senetleri, riskli fonlar ve büyüme odaklı enstrümanları iyi bilen dinamik bir yatırım danışmanısın. Risk-getiri dengesini vurgula.",
        "📉 Bütçe Koçu": "Kullanıcının harcamalarını kısmaya, tasarruf yapmaya and bütçe planlamasına odaklanan samimi bir finans koçusun. Gereksiz masrafları azaltmaya yönelik stratejiler ver."
    }
    current_persona_instruction = persona_prompts[persona_choice]
    st.divider()

    st.subheader("📁 Sohbet Geçmişi")
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
        st.session_state.active_chat_id = None
        st.rerun()
    
    if st.session_state.all_chats:
        for c_id, msgs in st.session_state.all_chats.items():
            preview_title = "Boş Sohbet"
            
            if msgs:
                first_msg = None
                if isinstance(msgs, list) and len(msgs) > 0:
                    first_msg = msgs[0]
                elif isinstance(msgs, dict) and len(msgs) > 0:
                    sorted_keys = sorted(list(msgs.keys()))
                    first_msg = msgs[sorted_keys[0]]
                
                if first_msg and isinstance(first_msg, dict) and "content" in first_msg:
                    preview_title = first_msg["content"][:20] + "..."
            
            button_label = f"📌 {preview_title}" if st.session_state.active_chat_id == c_id else f"💬 {preview_title}"
            
            if st.button(button_label, key=f"btn_{c_id}", use_container_width=True):
                st.session_state.active_chat_id = c_id
                st.rerun()
    else:
        st.caption("Henüz geçmiş bir sohbet yok.")
    
    st.divider()
    
    st.subheader("📈 Canlı Finans Paneli")
    if market_ui:
        col1, col2 = st.columns(2)
        col1.metric("💵 USD/TRY", market_ui["Dolar (USD/TRY)"])
        col2.metric("💶 EUR/TRY", market_ui["Euro (EUR/TRY)"])
        col1.metric("🟡 Gram Altın", market_ui["Gram Altın"])
        col2.metric("🔱 Ons Altın", market_ui["Ons Altın"])
    else:
        st.caption("Piyasa verileri yüklenemedi.")
        
    # --- CANLI DÖVİZ ÇEVİRİCİ HESAP MAKİNESİ ---
    with st.expander("💱 Canlı Döviz Çevirici", expanded=False):
        calc_amount = st.number_input("Miktar", min_value=0.0, value=1.0, step=1.0)
        from_curr = st.selectbox("Kaynak Birim", ["USD", "EUR", "GA (Gram Altın)", "TRY"])
        to_curr = st.selectbox("Hedef Birim", ["TRY", "USD", "EUR", "GA (Gram Altın)"])
        
        prices_in_try = {
            "TRY": 1.0,
            "USD": raw_prices["USD"],
            "EUR": raw_prices["EUR"],
            "GA (Gram Altın)": raw_prices["GOLD"]
        }
        
        if from_curr != to_curr:
            amount_in_try = calc_amount * prices_in_try[from_curr]
            result_val = amount_in_try / prices_in_try[to_curr]
            st.success(f"**{calc_amount:} {from_curr} = {result_val:,.2f} {to_curr}**")
        else:
            st.caption("Kaynak ve hedef birim aynı seçilemez.")
            
    st.divider()

    st.subheader("📁 Akıllı Rapor / PDF Analizi")
    uploaded_file = st.file_uploader("Finansal rapor veya ekstre yükleyin (PDF)", type=["pdf"])
    pdf_text_content = ""
    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                pdf_text_content += page.extract_text() + "\n"
            st.success("PDF başarıyla analiz edildi! Artık chat üzerinden bu dökümanla ilgili soru sorabilirsiniz.")
        except Exception as e:
            st.error(f"PDF okunurken hata oluştu: {e}")
    st.divider()
    
    if st.button("🗑️ Sohbet Geçmişini Temizle", use_container_width=True):
        delete_all_chats_rest(username)
        st.session_state.all_chats = {}
        st.session_state.active_chat_id = None
        st.success("Tüm geçmiş başarıyla temizlendi!")
        st.rerun()
        
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        if "all_chats" in st.session_state:
            del st.session_state.all_chats
        if "active_chat_id" in st.session_state:
            del st.session_state.active_chat_id
        logout_user()
        st.rerun()

# --- ANA EKRAN DÜZENİ ---
st.title("💰 TG Finansal Asistan")
st.caption(f"Generative AI & LLM Destekli Akıllı Finansal Özetleyici | Aktif Mod: **{persona_choice}**")

# --- PORTFÖY GÖRSELLEŞTİRME VE GRAFİK MODÜLÜ ---
with st.expander("📊 Benim Portföyüm / Varlık Dağılımım (Grafiksel Gösterim)", expanded=False):
    st.subheader("Varlık Miktarlarınızı Girin")
    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    
    amt_tl = p_col1.number_input("Nakit TL", min_value=0.0, value=0.0, step=100.0)
    amt_usd = p_col2.number_input("Dolar ($)", min_value=0.0, value=0.0, step=50.0)
    amt_eur = p_col3.number_input("Euro (€)", min_value=0.0, value=0.0, step=50.0)
    amt_gold = p_col4.number_input("Gram Altın", min_value=0.0, value=0.0, step=1.0)
    
    val_tl = amt_tl
    val_usd = amt_usd * raw_prices["USD"]
    val_eur = amt_eur * raw_prices["EUR"]
    val_gold = amt_gold * raw_prices["GOLD"]
    total_portfolio = val_tl + val_usd + val_eur + val_gold
    
    if total_portfolio > 0:
        st.markdown(f"#### 💵 Toplam Portföy Değeriniz: **{total_portfolio:,.2f} TL**")
        
        portfolio_data = pd.DataFrame({
            "Varlık Türü": ["Türk Lirası (TL)", "Amerikan Doları (USD)", "Euro (EUR)", "Gram Altın"],
            "TL Karşılığı": [val_tl, val_usd, val_eur, val_gold],
            "Miktar": [amt_tl, amt_usd, amt_eur, amt_gold]
        })
        
        portfolio_data = portfolio_data[portfolio_data["TL Karşılığı"] > 0]
        
        fig = px.pie(
            portfolio_data, 
            values="TL Karşılığı", 
            names="Varlık Türü",
            hover_data=["Miktar"],
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.YlOrBr[::-1]
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Portföy grafiğinizi görebilmek için lütfen yukarıdaki alanlara sahip olduğunuz varlık miktarlarınızı girin.")

st.divider()

# --- SOHBET ALANI ---
active_id = st.session_state.active_chat_id
current_messages = st.session_state.all_chats.get(active_id, []) if active_id else []

if isinstance(current_messages, dict):
    sorted_keys = sorted(list(current_messages.keys()))
    current_messages = [current_messages[k] for k in sorted_keys]

for message in current_messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input := st.chat_input("Birikiminiz veya yüklediğiniz rapor hakkında soru sorun..."):
    if not api_key:
        st.error("Sistemde Gemini API Key bulunamadı! Lütfen kök dizine .env dosyası ekleyin veya ortam değişkenini tanımlayın.")
    else:
        if st.session_state.active_chat_id is None:
            import time
            new_id = f"chat_{int(time.time())}"
            st.session_state.active_chat_id = new_id
            st.session_state.all_chats[new_id] = []
            current_messages = st.session_state.all_chats[new_id]

        with st.chat_message("user"):
            st.write(user_input)
            
        portfolio_context = ""
        if total_portfolio > 0:
            portfolio_context = f"\nKULLANICININ MEVCUT PORTFÖYÜ:\n- Nakit TL: {amt_tl} TL\n- Dolar: {amt_usd} USD\n- Euro: {amt_eur} EUR\n- Gram Altın: {amt_gold} Gr\n- Toplam Portföy Değeri: {total_portfolio:.2f} TL\n"
        
        combined_context = f"AKTİF ROL TALİMATI: {current_persona_instruction}\n\n{market_context}{portfolio_context}"
        if pdf_text_content:
            combined_context += f"\n\nKULLANICININ YÜKLEDİĞİ PDF DOKÜMANI İÇERİĞİ:\n{pdf_text_content}"

        with st.chat_message("assistant"):
            try:
                answer, error = generate_financial_response(
                    api_key=api_key, 
                    current_user_input=user_input, 
                    chat_history=current_messages, 
                    context_data=combined_context
                )
                
                if error:
                    st.error(error)
                else:
                    st.write(answer)
                    current_messages.append({"role": "user", "content": user_input})
                    current_messages.append({"role": "assistant", "content": answer})
                    
                    st.session_state.all_chats[st.session_state.active_chat_id] = current_messages
                    save_single_chat_rest(username, st.session_state.active_chat_id, current_messages)
                    st.rerun()
            except Exception as e:
                st.error(f"Sistem Hatası: {e}")