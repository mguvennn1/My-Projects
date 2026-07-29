import streamlit as st
import requests
import hashlib

def init_auth_db():
    """Oturum durumunu başlatır."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = None

def hash_password(password):
    """Şifreyi SHA-256 algoritması ile güvenli bir şekilde hash'ler."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def login_user(username, password):
    """Giriş kontrolünü şifreyi hash'leyerek veri tabanından doğrular."""
    try:
        url = f"https://planning-with-ai-17b8d-default-rtdb.firebaseio.com/users/{username}.json"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            user_data = response.json()
            if user_data:
                hashed_input = hash_password(password)
                if user_data.get("password") == hashed_input:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    return True
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
    return False

def register_user(username, password):
    """Yeni kullanıcıyı şifresini hash'leyerek güvenli şekilde kaydeder."""
    try:
        url = f"https://planning-with-ai-17b8d-default-rtdb.firebaseio.com/users/{username}.json"
        check_res = requests.get(url, timeout=5)
        if check_res.status_code == 200 and check_res.json() is not None:
            return "exists"
        
        hashed_password = hash_password(password)
        response = requests.put(url, json={"password": hashed_password}, timeout=5)
        if response.status_code == 200:
            return "success"
    except Exception as e:
        st.error(f"Kayıt Hatası: {e}")
    return "error"

def reset_password(username, new_password):
    """Kullanıcının şifresini yeni hash'lenmiş şifre ile günceller."""
    try:
        url = f"https://planning-with-ai-17b8d-default-rtdb.firebaseio.com/users/{username}.json"
        check_res = requests.get(url, timeout=5)
        
        if check_res.status_code != 200 or check_res.json() is None:
            return "not_found"
        
        hashed_password = hash_password(new_password)
        response = requests.put(url, json={"password": hashed_password}, timeout=5)
        if response.status_code == 200:
            return "success"
    except Exception as e:
        st.error(f"Şifre Sıfırlama Hatası: {e}")
    return "error"

def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["username"] = None

def auth_interface():
    st.title("🔒 TG Finansal Asistan - Giriş Paneli")
    tab1, tab2, tab3 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol", "🔄 Şifremi Unuttum"])
    
    with tab1:
        st.subheader("Hesabınıza Giriş Yapın")
        
        login_username = st.text_input("Kullanıcı Adı", key="login_user_input")
        login_password = st.text_input("Şifre", type="password", key="login_pass_input")
        submit_button = st.button("Giriş Yap", use_container_width=True, key="login_submit_btn")
        
        if submit_button:
            if not login_username or not login_password:
                st.warning("Lütfen kullanıcı adı ve şifre girin.")
            elif login_user(login_username, login_password):
                st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
                
    with tab2:
        st.subheader("Yeni Hesap Oluştur")
        with st.form(key="register_form"):
            reg_username = st.text_input("Yeni Kullanıcı Adı")
            reg_password = st.text_input("Yeni Şifre", type="password")
            reg_password_confirm = st.text_input("Şifre Tekrar", type="password")
            register_button = st.form_submit_button("Kayıt Ol", use_container_width=True)
            
            if register_button:
                if not reg_username or not reg_password:
                    st.warning("Alanlar boş bırakılamaz.")
                elif reg_password != reg_password_confirm:
                    st.error("Şifreler uyuşmuyor!")
                else:
                    result = register_user(reg_username, reg_password)
                    if result == "exists":
                        st.error("Bu kullanıcı adı zaten alınmış!")
                    elif result == "success":
                        st.success(f"'{reg_username}' başarıyla oluşturuldu! Giriş yapabilirsiniz.")

    with tab3:
        st.subheader("Şifrenizi Sıfırlayın")
        with st.form(key="forgot_password_form"):
            forgot_username = st.text_input("Kullanıcı Adınız")
            new_password = st.text_input("Yeni Şifre", type="password")
            new_password_confirm = st.text_input("Yeni Şifre Tekrar", type="password")
            reset_button = st.form_submit_button("Şifreyi Güncelle", use_container_width=True)
            
            if reset_button:
                if not forgot_username or not new_password or not new_password_confirm:
                    st.warning("Lütfen tüm alanları doldurun.")
                elif new_password != new_password_confirm:
                    st.error("Girdiğiniz yeni şifreler birbiriyle uyuşmuyor!")
                else:
                    status = reset_password(forgot_username, new_password)
                    if status == "not_found":
                        st.error("Sistemde böyle bir kullanıcı adı bulunamadı!")
                    elif status == "success":
                        st.success("Şifreniz başarıyla güncellendi! 'Giriş Yap' sekmesinden yeni şifrenizle oturum açabilirsiniz.")
                    else:
                        st.error("Şifre güncellenirken bir hata oluştu.")