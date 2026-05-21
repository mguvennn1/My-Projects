import subprocess
import sys
from plyer import notification
import streamlit as st
import cv2
import mediapipe as mp
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import time
import json 
import os
import winsound
from datetime import datetime
import pandas as pd
import sqlite3

# ==========================================
# 0. SQLITE VERİTABANI YARDIMCI FONKSİYONLARI
# ==========================================
DB_DOSYASI = "ergonomi.db"

def init_db():
    conn = sqlite3.connect(DB_DOSYASI)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Kullanicilar
                 (isim TEXT PRIMARY KEY, dik_skor INTEGER, kambur_skor INTEGER, ideal_mesafe INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Oturumlar
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  isim TEXT,
                  tarih TEXT,
                  iyi_sure INTEGER,
                  uyari_sure INTEGER,
                  tehlike_sure INTEGER,
                  trend TEXT)''')
    conn.commit()
    conn.close()

def profilleri_yukle():
    init_db()
    conn = sqlite3.connect(DB_DOSYASI)
    c = conn.cursor()
    c.execute("SELECT * FROM Kullanicilar")
    satirlar = c.fetchall()
    
    profiller = {}
    if len(satirlar) == 0:
        varsayilanlar = [
            ("Enes", 80, 24, 42),
            ("Memduh", 82, 25, 45),
            ("Talha", 75, 20, 40)
        ]
        c.executemany("INSERT INTO Kullanicilar VALUES (?,?,?,?)", varsayilanlar)
        conn.commit()
        for v in varsayilanlar:
            profiller[v[0]] = {"dik_skor": v[1], "kambur_skor": v[2], "ideal_mesafe": v[3]}
    else:
        for satir in satirlar:
            profiller[satir[0]] = {"dik_skor": satir[1], "kambur_skor": satir[2], "ideal_mesafe": satir[3]}
    conn.close()
    return profiller

def profil_kaydet_sql(isim, dik, kambur, mesafe):
    conn = sqlite3.connect(DB_DOSYASI)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO Kullanicilar VALUES (?,?,?,?)", (isim, dik, kambur, mesafe))
    conn.commit()
    conn.close()

def profil_sil_sql(isim):
    conn = sqlite3.connect(DB_DOSYASI)
    c = conn.cursor()
    c.execute("DELETE FROM Kullanicilar WHERE isim=?", (isim,))
    c.execute("DELETE FROM Oturumlar WHERE isim=?", (isim,))
    conn.commit()
    conn.close()

def oturum_kaydet_sql(isim, tarih, iyi, uyari, tehlike, trend_listesi):
    trend_str = json.dumps(trend_listesi) 
    conn = sqlite3.connect(DB_DOSYASI)
    c = conn.cursor()
    c.execute("INSERT INTO Oturumlar (isim, tarih, iyi_sure, uyari_sure, tehlike_sure, trend) VALUES (?,?,?,?,?,?)", 
              (isim, tarih, iyi, uyari, tehlike, trend_str))
    conn.commit()
    conn.close()

def oturumlari_getir_sql(isim):
    conn = sqlite3.connect(DB_DOSYASI)
    c = conn.cursor()
    c.execute("SELECT tarih, iyi_sure, uyari_sure, tehlike_sure, trend FROM Oturumlar WHERE isim=?", (isim,))
    satirlar = c.fetchall()
    conn.close()
    
    oturumlar = []
    for s in satirlar:
        oturumlar.append({
            "Tarih": s[0],
            "Sağlıklı Duruş (sn)": s[1],
            "Uyarı Durumu (sn)": s[2],
            "Tehlikeli Duruş (sn)": s[3],
            "Trend": json.loads(s[4]) if s[4] else []
        })
    return oturumlar

def oturum_sil_sql(isim, tarih):
    """Sadece kullanıcının seçtiği spesifik bir oturumu (tarihe göre) siler."""
    conn = sqlite3.connect(DB_DOSYASI)
    c = conn.cursor()
    # 🌟 YENİ: Hem isim hem de tarih eşleşiyorsa sil!
    c.execute("DELETE FROM Oturumlar WHERE isim=? AND tarih=?", (isim, tarih))
    conn.commit()
    conn.close()

# ==========================================
# 1. STREAMLIT SAYFA AYARLARI VE HAFIZA
# ==========================================
st.set_page_config(page_title="Ergonomi Asistanı", page_icon="🛡️", layout="wide")

if 'oturum_kaydedilecek' not in st.session_state: st.session_state.oturum_kaydedilecek = False
if 'gecici_sure_iyi' not in st.session_state: st.session_state.gecici_sure_iyi = 0
if 'gecici_sure_uyari' not in st.session_state: st.session_state.gecici_sure_uyari = 0
if 'gecici_sure_tehlike' not in st.session_state: st.session_state.gecici_sure_tehlike = 0
if 'oturum_baslangic' not in st.session_state: st.session_state.oturum_baslangic = None
if 'gecici_trend' not in st.session_state: st.session_state.gecici_trend = []
if 'yeni_kullanici_adi' not in st.session_state: st.session_state.yeni_kullanici_adi = None # 🌟 YENİ: İsim hafızası

st.sidebar.title("👤 Kullanıcı Girişi")
profiller = profilleri_yukle()
secenekler = ["Yeni Kullanıcı (Kalibrasyon)"] + list(profiller.keys())

if 'gecici_hedef_profil' in st.session_state and st.session_state.gecici_hedef_profil:
    st.session_state.profil_secici = st.session_state.gecici_hedef_profil
    st.session_state.gecici_hedef_profil = None

secili_kullanici = st.sidebar.selectbox("Profilinizi Seçin:", secenekler, key="profil_secici")

if 'aktif_profil' not in st.session_state: st.session_state.aktif_profil = None
if 'kalibrasyon_modu' not in st.session_state: st.session_state.kalibrasyon_modu = False
if 'onceki_secim' not in st.session_state: st.session_state.onceki_secim = secili_kullanici

if st.session_state.onceki_secim != secili_kullanici:
    st.session_state.kalibrasyon_modu = False
    st.session_state.onceki_secim = secili_kullanici

# --- KAYITLI KULLANICI MANTIĞI ---
if secili_kullanici != "Yeni Kullanıcı (Kalibrasyon)":
    st.session_state.aktif_profil = profiller[secili_kullanici]
    if not st.session_state.kalibrasyon_modu:
        st.sidebar.success(f"Hoş geldin, {secili_kullanici}! Kişisel ayarların yüklendi.")
        col1, col2 = st.sidebar.columns(2)
        if col1.button("🔄 Kalibre Et"):
            st.session_state.kalibrasyon_modu = True
            st.session_state.yeni_kullanici_adi = secili_kullanici 
            st.rerun()
        if col2.button("🗑️ Sil"):
            profil_sil_sql(secili_kullanici) 
            st.session_state.gecici_hedef_profil = "Yeni Kullanıcı (Kalibrasyon)" 
            st.rerun()
    else:
        st.sidebar.warning(f"{secili_kullanici} profili güncelleniyor...")
        st.sidebar.info("Lütfen sağ taraftan 'Sistemi Başlat' kutusunu işaretleyip kameraya dik bakın.")

# --- 🌟 YENİ: KUSURSUZ YENİ KULLANICI AKIŞI ---
else:
    st.session_state.aktif_profil = None
    st.session_state.yeni_kullanici_adi = None # Önce sıfırla
    yeni_isim = st.sidebar.text_input("Adınızı Girin:")
    
    if yeni_isim:
        if yeni_isim in profiller:
            st.sidebar.error("Bu isim zaten var! Lütfen menüden profili seçin.")
        else:
            st.session_state.yeni_kullanici_adi = yeni_isim
            st.sidebar.info("👉 Adınız onaylandı! Sağ taraftan 'Sistemi Başlat' kutusunu işaretlediğiniz an kalibrasyon otomatik başlayacaktır.")
    else:
        st.sidebar.warning("Sistemi başlatmadan önce bir ad girmeniz zorunludur.")

st.title("🛡️ Akıllı Ergonomi Asistanı")
st.markdown("Gerçek zamanlı duruş analizi, bulanık mantık uyarıları ve istatistik raporları.")

# ==========================================
# 2. DİNAMİK BULANIK MANTIK MOTORU
# ==========================================
def setup_fuzzy_logic(profil):
    if profil is None:
        dik_merkez, kambur_merkez, mesafe_merkez = 80, 24, 42
    else:
        dik_merkez, kambur_merkez, mesafe_merkez = profil["dik_skor"], profil["kambur_skor"], profil["ideal_mesafe"]

    durus = ctrl.Antecedent(np.arange(0, 101, 1), 'durus')
    sure = ctrl.Antecedent(np.arange(0, 61, 1), 'sure') 
    mesafe = ctrl.Antecedent(np.arange(0, 151, 1), 'mesafe')
    uyari = ctrl.Consequent(np.arange(0, 101, 1), 'uyari')

    durus['kambur'] = fuzz.trapmf(durus.universe, [0, 0, kambur_merkez, kambur_merkez + 15])
    orta_nokta = int((dik_merkez + kambur_merkez) / 2)
    durus['normal'] = fuzz.trimf(durus.universe, [kambur_merkez + 5, orta_nokta, dik_merkez - 10])
    durus['dik'] = fuzz.trapmf(durus.universe, [dik_merkez - 15, dik_merkez, 100, 100])

    sure['kisa'] = fuzz.trimf(sure.universe, [0, 0, 15])
    sure['orta'] = fuzz.trimf(sure.universe, [10, 20, 30])
    sure['uzun'] = fuzz.trimf(sure.universe, [25, 60, 60])

    mesafe['uzak'] = fuzz.trapmf(mesafe.universe, [0, 0, mesafe_merkez - 15, mesafe_merkez - 5])
    mesafe['ideal'] = fuzz.trimf(mesafe.universe, [mesafe_merkez - 10, mesafe_merkez, mesafe_merkez + 15])
    mesafe['yakin'] = fuzz.trapmf(mesafe.universe, [mesafe_merkez + 10, mesafe_merkez + 30, 150, 150])

    uyari['dusuk'] = fuzz.trimf(uyari.universe, [0, 0, 40])
    uyari['orta'] = fuzz.trimf(uyari.universe, [30, 50, 70])
    uyari['yuksek'] = fuzz.trimf(uyari.universe, [60, 100, 100])

    kural1 = ctrl.Rule(durus['dik'], uyari['dusuk'])
    kural2 = ctrl.Rule(durus['normal'] & sure['kisa'], uyari['dusuk'])
    kural3 = ctrl.Rule(durus['normal'] & sure['orta'], uyari['orta'])
    kural4 = ctrl.Rule(durus['normal'] & sure['uzun'], uyari['orta'])
    kural5 = ctrl.Rule(durus['kambur'] & sure['kisa'], uyari['orta'])
    kural6 = ctrl.Rule(durus['kambur'] & sure['orta'], uyari['yuksek'])
    kural7 = ctrl.Rule(durus['kambur'] & sure['uzun'], uyari['yuksek'])
    kural8 = ctrl.Rule(mesafe['yakin'], uyari['yuksek'])

    uyari_kontrol = ctrl.ControlSystem([kural1, kural2, kural3, kural4, kural5, kural6, kural7, kural8])
    return ctrl.ControlSystemSimulation(uyari_kontrol)

uyari_motoru = setup_fuzzy_logic(st.session_state.aktif_profil)

# ==========================================
# 3. SEKME (TAB) YAPISI VE KAMERA DÖNGÜSÜ
# ==========================================
tab_canli, tab_rapor = st.tabs(["📷 Canlı Analiz Ekranı", "📊 İstatistik ve Günlük Raporlar"])

with tab_canli:
    col1, col2 = st.columns([3, 1])

    with col1:
        run = st.checkbox("Sistemi Başlat / Durdur (Kapatınca Kaydeder)")
        
        # 🌟 GÜVENLİK DUVARI: İsim girmeden kamerayı açmasını engelle!
        if run and secili_kullanici == "Yeni Kullanıcı (Kalibrasyon)" and not st.session_state.yeni_kullanici_adi:
            st.error("🚨 Kamerayı açabilmek için lütfen sol menüden geçerli bir ad girin!")
            run = False # Döngüye girmesini engelle, kamerayı kapalı tut
            
        FRAME_WINDOW = st.image([]) 

    with col2:
        st.subheader("Anlık Metrikler")
        metric_durus = st.empty()
        metric_sure = st.empty()
        metric_mesafe = st.empty()
        st.divider()
        metric_uyari = st.empty()
        uyari_mesaji = st.empty()

    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5)
    mp_drawing = mp.solutions.drawing_utils

    if run:
        # 🌟 OTOMATİK KALİBRASYON TETİĞİ
        if secili_kullanici == "Yeni Kullanıcı (Kalibrasyon)" and st.session_state.yeni_kullanici_adi:
            st.session_state.kalibrasyon_modu = True
            
        if not st.session_state.oturum_kaydedilecek:
            st.session_state.oturum_baslangic = datetime.now()
            st.session_state.oturum_kaydedilecek = True
            st.session_state.gecici_sure_iyi = 0
            st.session_state.gecici_sure_uyari = 0
            st.session_state.gecici_sure_tehlike = 0
            st.session_state.gecici_trend = [] 
            
        sure_iyi = st.session_state.gecici_sure_iyi
        sure_uyari = st.session_state.gecici_sure_uyari
        sure_tehlike = st.session_state.gecici_sure_tehlike

        cap = cv2.VideoCapture(0)
        bozuk_durus_suresi = 0
        son_kare_zamani, son_veri_zamani, son_trend_zamani = time.time(), time.time(), time.time()
        son_toast_zamani, son_ses_zamani, son_kilit_zamani = 0, 0, 0
        kilit_process = None 

        if 'kalib_dik_havuz' not in st.session_state:
            st.session_state.kalib_dik_havuz = []
            st.session_state.kalib_mesafe_havuz = []

        try:  
            while run:
                success, image = cap.read()
                if not success: break

                su_an = time.time()
                gecen_zaman = su_an - son_kare_zamani
                son_kare_zamani = su_an
                delta_t = su_an - son_veri_zamani
                son_veri_zamani = su_an

                image = cv2.flip(image, 1)
                image = cv2.medianBlur(image, 3)
                img_lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                img_lab[:,:,0] = clahe.apply(img_lab[:,:,0])
                image = cv2.cvtColor(img_lab, cv2.COLOR_LAB2BGR)
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = pose.process(image_rgb)

                posture_score, goz_mesafesi, gecerli_sure, cikis_degeri = 80, 40, 0, 0
                h, w, _ = image.shape

                if results.pose_landmarks:
                    mp_drawing.draw_landmarks(image_rgb, results.pose_landmarks, mp_pose.POSE_CONNECTIONS) 
                    lm = results.pose_landmarks.landmark
                    nose, left_shoulder, right_shoulder = lm[0], lm[11], lm[12]
                    left_eye_inner, right_eye_inner = lm[1], lm[4]
                    
                    goz_mesafesi = max(0, min(150, int(abs(left_eye_inner.x - right_eye_inner.x) * w)))
                    neck_y = (left_shoulder.y + right_shoulder.y) / 2
                    shoulder_width = abs(left_shoulder.x - right_shoulder.x)
                    
                    if shoulder_width > 0:
                        posture_score = max(0, min(100, int(((neck_y - nose.y) / shoulder_width) * 100)))
                        
                        if st.session_state.kalibrasyon_modu:
                            cv2.putText(image_rgb, "KALIBRASYON YAPILIYOR...", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)
                            st.session_state.kalib_dik_havuz.append(posture_score)
                            st.session_state.kalib_mesafe_havuz.append(goz_mesafesi)
                            kare_sayisi = len(st.session_state.kalib_dik_havuz)
                            
                            cv2.rectangle(image_rgb, (30, 120), (30 + kare_sayisi * 4, 150), (0, 255, 0), -1)
                            cv2.putText(image_rgb, f"%{kare_sayisi}", (35 + kare_sayisi * 4, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                            
                            if kare_sayisi >= 100:
                                hedef_dik = int(np.median(st.session_state.kalib_dik_havuz))
                                hedef_mesafe = int(np.median(st.session_state.kalib_mesafe_havuz))
                                hedef_kambur = max(0, hedef_dik - 50)
                                
                                profil_kaydet_sql(st.session_state.yeni_kullanici_adi, hedef_dik, hedef_kambur, hedef_mesafe) 
                                
                                st.session_state.kalibrasyon_modu = False
                                st.session_state.gecici_hedef_profil = st.session_state.yeni_kullanici_adi # 🌟 Widget'a değil, not kağıdına yaz!
                                st.rerun()
                        else:
                            # 🌟 GÖRÜNMEZ KAMERA BUG'I ÇÖZÜMÜ: continue sildik!
                            if st.session_state.aktif_profil is None: 
                                cv2.putText(image_rgb, "LUTFEN GECERLI BIR PROFIL SECIN", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            else:
                                if posture_score < (st.session_state.aktif_profil["dik_skor"] - 15) or goz_mesafesi > (st.session_state.aktif_profil["ideal_mesafe"] + 15):
                                    bozuk_durus_suresi += gecen_zaman
                                else:
                                    bozuk_durus_suresi = 0
                                    
                                gecerli_sure = min(60, int(bozuk_durus_suresi))

                                uyari_motoru = setup_fuzzy_logic(st.session_state.aktif_profil)
                                uyari_motoru.input['durus'] = posture_score
                                uyari_motoru.input['sure'] = gecerli_sure
                                uyari_motoru.input['mesafe'] = goz_mesafesi
                                uyari_motoru.compute()
                                cikis_degeri = int(uyari_motoru.output['uyari'])

                if not st.session_state.kalibrasyon_modu and st.session_state.aktif_profil is not None:
                    
                    if su_an - son_trend_zamani >= 1.0:
                        st.session_state.gecici_trend.append(cikis_degeri)
                        son_trend_zamani = su_an
                    
                    if cikis_degeri < 65 and kilit_process is not None:
                        try: kilit_process.terminate() 
                        except: pass
                        kilit_process = None
                    
                    if cikis_degeri < 35:
                        uyari_mesaji.success("DURUM: İYİ 🟢")
                        sure_iyi += delta_t 
                        
                    elif 35 <= cikis_degeri < 55:
                        uyari_mesaji.warning("DURUM: UYARI 🟡 - Aşama 1: Sessiz Bildirim")
                        cv2.rectangle(image_rgb, (0, 0), (w, h), (0, 255, 255), 15) 
                        sure_uyari += delta_t 
                        if su_an - son_toast_zamani > 30:
                            notification.notify(title="Ergonomi Asistanı", message="Duruşunuz yavaş yavaş bozuluyor, lütfen dikleşin.", timeout=5)
                            son_toast_zamani = su_an
                            
                    elif 55 <= cikis_degeri < 65:
                        uyari_mesaji.warning("DURUM: UYARI 🟠 - Aşama 2: Sesli İkaz")
                        sure_uyari += delta_t
                        if su_an - son_toast_zamani > 20:
                            notification.notify(title="Ergonomi Asistanı", message="Lütfen duruşunuzu düzeltin!", timeout=5)
                            son_toast_zamani = su_an
                        if su_an - son_ses_zamani > 5:
                            winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
                            son_ses_zamani = su_an
                            
                    else: 
                        uyari_mesaji.error("DURUM: TEHLİKE 🔴 - KİLİT DEVREDE!")
                        sure_tehlike += delta_t 
                        image_rgb = cv2.GaussianBlur(image_rgb, (99, 99), 0)
                        cv2.putText(image_rgb, "SISTEM KILITLENDI!", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 4)
                            
                        if su_an - son_kilit_zamani > 8 and kilit_process is None:
                            kilit_process = subprocess.Popen([sys.executable, "kilit.py"])
                            son_kilit_zamani = time.time()
                        elif kilit_process is not None:
                            if kilit_process.poll() is not None: 
                                kilit_process = None 
                            elif su_an - son_ses_zamani > 3:
                                winsound.PlaySound("SystemHand", winsound.SND_ASYNC)
                                son_ses_zamani = su_an

                st.session_state.gecici_sure_iyi = sure_iyi
                st.session_state.gecici_sure_uyari = sure_uyari
                st.session_state.gecici_sure_tehlike = sure_tehlike

                FRAME_WINDOW.image(image_rgb)
                metric_durus.metric("Anlık Duruş Skoru", f"{posture_score}")
                metric_sure.metric("Bozuk Duruş Süresi", f"{gecerli_sure} sn")
                metric_mesafe.metric("Anlık Göz Mesafesi", f"{goz_mesafesi}")
                if not st.session_state.kalibrasyon_modu: metric_uyari.metric("Bulanık Çıktı (Uyarı Şiddeti)", f"%{cikis_degeri}")

        finally:
            if 'cap' in locals() and cap.isOpened(): cap.release()
            if kilit_process is not None:
                try: kilit_process.terminate()
                except: pass

    else:
        if st.session_state.oturum_kaydedilecek:
            toplam_sure = st.session_state.gecici_sure_iyi + st.session_state.gecici_sure_uyari + st.session_state.gecici_sure_tehlike
            
            if toplam_sure > 5 and st.session_state.aktif_profil is not None and not st.session_state.kalibrasyon_modu:
                tarih_str = st.session_state.oturum_baslangic.strftime("%Y-%m-%d %H:%M:%S")
                iyi_sn = round(st.session_state.gecici_sure_iyi)
                uyari_sn = round(st.session_state.gecici_sure_uyari)
                tehlike_sn = round(st.session_state.gecici_sure_tehlike)
                
                oturum_kaydet_sql(secili_kullanici, tarih_str, iyi_sn, uyari_sn, tehlike_sn, st.session_state.gecici_trend)
                st.success("✅ Oturum verileriniz başarıyla SQL Veritabanına kaydedildi!")
            
            st.session_state.oturum_kaydedilecek = False
            st.session_state.gecici_sure_iyi = 0
            st.session_state.gecici_sure_uyari = 0
            st.session_state.gecici_sure_tehlike = 0
            st.session_state.gecici_trend = []
            
        st.info("Kamerayı açmak için 'Sistemi Başlat / Durdur' kutucuğunu işaretleyin. Kamera kapatıldığında verileriniz Raporlara kaydedilecektir.")

# ------------------------------------------
# SEKME 2: İSTATİSTİKLER VE GRAFİKLER (MÜKEMMEL UX)
# ------------------------------------------
with tab_rapor:
    st.header("📊 Oturum Geçmişi ve Duruş Analizi")
    if st.session_state.aktif_profil is not None:
        oturumlar = oturumlari_getir_sql(secili_kullanici)
        
        if len(oturumlar) > 0:
            
            oturum_tarihleri = [o.get("Tarih") for o in oturumlar]
            secilen_tarih = st.selectbox("📅 İncelemek İstediğiniz Oturumu Seçin:", oturum_tarihleri[::-1])
            
            secilen_oturum = next((o for o in oturumlar if o.get("Tarih") == secilen_tarih), oturumlar[-1])
            
            st.markdown(f"### 📈 {secilen_tarih} Tarihli Duruş Trendi")
            if "Trend" in secilen_oturum and len(secilen_oturum["Trend"]) > 0:
                trend_df = pd.DataFrame(secilen_oturum["Trend"], columns=["Duruş Bozukluğu (Tehlike %)"])
                st.line_chart(trend_df, color="#e74c3c", height=350)
            else:
                st.info("Bu oturumda detaylı trend verisi bulunamadı.")
                
            st.markdown("### ⏱️ Seçilen Oturumun Karnesi")
            
            iyi_sn = secilen_oturum.get('Sağlıklı Duruş (sn)', 0)
            uyari_sn = secilen_oturum.get('Uyarı Durumu (sn)', 0)
            tehlike_sn = secilen_oturum.get('Tehlikeli Duruş (sn)', 0)
            toplam_sn = iyi_sn + uyari_sn + tehlike_sn
            basari_puani = int((iyi_sn / toplam_sn) * 100) if toplam_sn > 0 else 0
            
            # 🌟 YENİ UX: GÖRSEL İLERLEME ÇUBUĞU (Oyunlaştırma)
            st.progress(basari_puani / 100.0, text=f"Genel Ergonomi Başarı Oranı: %{basari_puani}")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🏆 Puan", f"%{basari_puani}")
            col2.metric("🟢 Sağlıklı", f"{iyi_sn} sn")
            col3.metric("🟡 Uyarı", f"{uyari_sn} sn")
            col4.metric("🔴 Tehlike", f"{tehlike_sn} sn")
            
            st.divider()
            
            # 🌟 YENİ UX: AKORDEON MENÜ (Arayüzü temiz tutmak için tabloyu gizledik)
            with st.expander("📋 Tabloyu Göster / Excel Çıktısı Al"):
                gosterilecek_veri = []
                for o in oturumlar:
                    gosterilecek_veri.append({
                        "Tarih": o.get("Tarih"),
                        "Sağlıklı (sn)": o.get("Sağlıklı Duruş (sn)"),
                        "Uyarı (sn)": o.get("Uyarı Durumu (sn)"),
                        "Tehlike (sn)": o.get("Tehlikeli Duruş (sn)")
                    })
                df_gecmis = pd.DataFrame(gosterilecek_veri).set_index("Tarih")
                st.dataframe(df_gecmis, use_container_width=True)
                
                # İndirme Butonu Artık Tablonun Altında (Mantıksal Bütünlük)
                csv_veri = df_gecmis.to_csv(sep=';').encode('utf-8-sig')
                st.download_button(
                    label="📥 Verileri Excel (CSV) Olarak İndir",
                    data=csv_veri,
                    file_name=f"{secili_kullanici}_ergonomi_gecmisi.csv",
                    mime='text/csv'
                )
                
            st.write("") 
            
            # 🌟 YENİ UX: SADECE SEÇİLİ OTURUMU SİLEN BUTON
            # Butonu sağa yaslamak için boşluk (columns) kullandık
            _, col_sil = st.columns([3, 1]) 
            with col_sil:
                if st.button(f"🗑️ Seçili Oturumu ({secilen_tarih}) Sil", type="primary"):
                    oturum_sil_sql(secili_kullanici, secilen_tarih)
                    st.success("Seçili oturum başarıyla silindi!")
                    time.sleep(1) 
                    st.rerun() 
            
        else:
            st.info("Henüz kaydedilmiş bir oturumunuz yok. Canlı Analiz ekranında kamerayı başlatıp biraz zaman geçirin, ardından kamerayı durdurun.")
    else:
        st.warning("Raporları görebilmek için soldan bir profil seçin.")