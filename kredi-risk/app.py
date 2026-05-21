import streamlit as st
import pandas as pd
import numpy as np
import joblib
from tensorflow.keras.models import load_model

st.set_page_config(page_title="Kredi Risk Tahmin Sistemi", page_icon="🏦", layout="wide")

# Modeli ve Scaler'ı hafızaya alıyoruz
@st.cache_resource
def load_assets():
    model = load_model('kredi_modeli.keras')
    scaler = joblib.load('scaler.pkl')
    return model, scaler

model, scaler = load_assets()

# Başlık ve Açıklama
st.title("🏦 Yapay Zeka Tabanlı Kredi Risk Tahmin Sistemi")
st.markdown("Lütfen müşteri profilini ve talep edilen kredi detaylarını giriniz. Sistem, **Çok Katmanlı Algılayıcı (MLP)** mimarisiyle arka planda risk olasılığını anlık olarak hesaplayacaktır.")
st.divider()

# ANA EKRANI İKİYE BÖLÜYORUZ: Sol Taraf (Form) | Sağ Taraf (Sonuçlar)
sol_kolon, sag_kolon = st.columns([1, 1], gap="large")

with sol_kolon:
    # Formu sadece sol kolona yerleştiriyoruz
    with st.form("kredi_basvuru_formu"):
        st.subheader("📝 Müşteri ve Kredi Bilgileri")
        
        # Sol kolonun içini de ikiye bölüyoruz ki çok aşağı sarkmasın, derli toplu dursun
        ic_kolon1, ic_kolon2 = st.columns(2)
        
        with ic_kolon1:
            age = st.slider("Yaş", min_value=18, max_value=100, value=30)
            income = st.number_input("Yıllık Gelir (TL)", min_value=1000, max_value=10000000, value=60000, step=5000)
            emp_length = st.slider("Çalışma Süresi (Yıl)", min_value=0, max_value=50, value=5)
            home_ownership = st.selectbox("Ev Durumu", ["KİRA (RENT)", "EV SAHİBİ (OWN)", "İPOTEKLİ (MORTGAGE)", "DİĞER (OTHER)"], help="Müşterinin mevcut barınma durumu.")
            cb_person_default_on_file = st.radio("Daha Önce Temerrüde (Batağa) Düştü mü?", ["Hayır (N)", "Evet (Y)"], help="Geçmişte kredisini ödeyemeyip yasal takibe düşme durumu.")
            cred_hist_length = st.slider("Kredi Geçmişi Uzunluğu (Yıl)", min_value=0, max_value=30, value=3, help="Müşterinin bankalarla olan ilk kredi ilişkisinden bu yana geçen süre.")

        with ic_kolon2:
            loan_amnt = st.number_input("Talep Edilen Kredi Tutarı (TL)", min_value=500, max_value=500000, value=15000, step=1000)
            loan_int_rate = st.number_input("Uygulanacak Faiz Oranı (%)", min_value=1.0, max_value=30.0, value=10.0, step=0.1)
            loan_intent = st.selectbox("Kredi Amacı", ["EĞİTİM (EDUCATION)", "SAĞLIK (MEDICAL)", "KİŞİSEL (PERSONAL)", "EV GELİŞTİRME (HOMEIMPROVEMENT)", "GİRİŞİM (VENTURE)", "BORÇ KAPATMA (DEBTCONSOLIDATION)"])
            loan_grade = st.selectbox("Banka Kredi Notu Sınıfı", ["A", "B", "C", "D", "E", "F", "G"], help="A en risksiz, G en riskli banka içi değerlendirme notudur.")

        st.markdown("<br>", unsafe_allow_html=True) 
        submit_button = st.form_submit_button("🚀 Kredi Riskini Hesapla", use_container_width=True)

with sag_kolon:
    st.subheader("📊 Yapay Zeka Analiz Sonucu")
    
    if submit_button:
        # Eğer butona basıldıysa burası çalışır ve matrisleri çarpar
        loan_percent_income = loan_amnt / income if income > 0 else 0

        with st.spinner('Yapay Sinir Ağı matrisleri çarpıyor...'):
            cols = ['person_age', 'person_income', 'person_emp_length', 'loan_amnt',
                    'loan_int_rate', 'loan_percent_income', 'cb_person_cred_hist_length',
                    'person_home_ownership_OTHER', 'person_home_ownership_OWN',
                    'person_home_ownership_RENT', 'loan_intent_EDUCATION',
                    'loan_intent_HOMEIMPROVEMENT', 'loan_intent_MEDICAL',
                    'loan_intent_PERSONAL', 'loan_intent_VENTURE', 'loan_grade_B',
                    'loan_grade_C', 'loan_grade_D', 'loan_grade_E', 'loan_grade_F',
                    'loan_grade_G', 'cb_person_default_on_file_Y']
            
            input_data = {col: 0 for col in cols}
            
            input_data['person_age'] = age
            input_data['person_income'] = income
            input_data['person_emp_length'] = emp_length
            input_data['loan_amnt'] = loan_amnt
            input_data['loan_int_rate'] = loan_int_rate
            input_data['loan_percent_income'] = loan_percent_income
            input_data['cb_person_cred_hist_length'] = cred_hist_length
            
            if "OTHER" in home_ownership: input_data['person_home_ownership_OTHER'] = 1
            elif "OWN" in home_ownership: input_data['person_home_ownership_OWN'] = 1
            elif "RENT" in home_ownership: input_data['person_home_ownership_RENT'] = 1
            
            if "EDUCATION" in loan_intent: input_data['loan_intent_EDUCATION'] = 1
            elif "HOMEIMPROVEMENT" in loan_intent: input_data['loan_intent_HOMEIMPROVEMENT'] = 1
            elif "MEDICAL" in loan_intent: input_data['loan_intent_MEDICAL'] = 1
            elif "PERSONAL" in loan_intent: input_data['loan_intent_PERSONAL'] = 1
            elif "VENTURE" in loan_intent: input_data['loan_intent_VENTURE'] = 1
            
            if loan_grade == "B": input_data['loan_grade_B'] = 1
            elif loan_grade == "C": input_data['loan_grade_C'] = 1
            elif loan_grade == "D": input_data['loan_grade_D'] = 1
            elif loan_grade == "E": input_data['loan_grade_E'] = 1
            elif loan_grade == "F": input_data['loan_grade_F'] = 1
            elif loan_grade == "G": input_data['loan_grade_G'] = 1
            
            if cb_person_default_on_file == "Evet (Y)": input_data['cb_person_default_on_file_Y'] = 1
            
            input_df = pd.DataFrame([input_data])
            scaled_data = scaler.transform(input_df)
            prediction_prob = model.predict(scaled_data)[0][0]
            
            risk_percentage = int(prediction_prob * 100)
            
            if prediction_prob > 0.5:
                st.error(f"🚨 **RİSKLİ MÜŞTERİ!** Krediyi ödeyememe ihtimali: **% {risk_percentage}**")
                st.progress(risk_percentage, text="Risk Seviyesi")
                st.warning("Model Yorumu: Bu müşterinin finansal profili geçmişteki batık kredilerle yüksek oranda eşleşiyor. Veri dengesizliği (Imbalanced Data) analizi göz önüne alındığında bu uyarı dikkate alınmalıdır.")
            else:
                st.success(f"✅ **GÜVENİLİR MÜŞTERİ.** Krediyi ödeyememe ihtimali: **% {risk_percentage}**")
                st.progress(risk_percentage, text="Risk Seviyesi")
                st.info("Model Yorumu: Müşteri düşük risk profiline sahiptir. Ancak %96'lık model kesinliğine (Precision) rağmen son karar kredi komitesine aittir.")
    else:
        # Site ilk açıldığında boş durmasın diye kullanıcıyı yönlendiren şık bir uyarı
        st.info("👈 Lütfen sol taraftaki panelden müşteri bilgilerini girip **'🚀 Kredi Riskini Hesapla'** butonuna tıklayın. Yapay zeka analiz sonuçları anında burada görüntülenecektir.")
    
    st.divider()
    with st.expander("⚙️ Sistemin Arka Planı (Mühendislik Detayları)"):
        st.write("""
        **Model Mimarisi:**
        * 22 özellikli Girdi Katmanı -> 64 Nöronlu (ReLU) Gizli Katman -> %20 Dropout -> 32 Nöronlu (ReLU) Gizli Katman -> %20 Dropout -> Çıktı Katmanı (Sigmoid).
        * Model toplam **3.585 eğitilebilir parametre** ile 50 Epoch boyunca eğitilmiştir.
        * Ön işleme aşamasında veriler `StandardScaler` ile normalize edilmiş ve kategorik veriler `One-Hot Encoding` ile matrise çevrilmiştir.
        """)