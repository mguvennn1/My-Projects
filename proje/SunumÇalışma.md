"""# 🛡️ Akıllı Ergonomi Asistanı - Teknik Sunum ve Çalışma Notları

Bu belge, **Bulanık Mantık** dersi kapsamında geliştirilen "Yapay Zeka Destekli Ergonomi Asistanı" projesinin tüm teknik detaylarını, matematiksel modellerini ve yazılım mimarisini içermektedir.

---

## 1. Projenin Vizyonu ve Amacı
Proje, masa başında çalışan bireylerin duruş bozukluklarını (kamburluk, ekrana yakınlık) herhangi bir ek donanım gerektirmeden, sadece standart bir web kamerası kullanarak takip eder. Sistemin en büyük inovasyonu; **Bulanık Mantık (Fuzzy Logic)** kullanarak kullanıcıya göre esneyebilen, kişiselleştirilmiş bir uyarı mekanizması sunmasıdır.

---

## 2. Görüntü İşleme (Image Processing) Mimarisi
Sistemin "Gözü" **Google MediaPipe Pose** kütüphanesidir. Görüntü işleme süreci şu adımlardan oluşur:

### A. Nokta Tespiti (Landmarks)
Yapay zeka modeli, insan vücudunu 33 farklı koordinat noktası olarak haritalandırır. Bizim algoritmamız özellikle şu 5 noktayı izler:
* **0 (Burun)**
* **1 - 4 (Göz Pınarları):** Derinlik algısı için.
* **11 - 12 (Omuzlar):** Gövde referansı ve duruş skoru için.

### B. Derinlik Algılama (Göz Mesafesi)
Ekrana yakınlığı ölçmek için göz pınarları arasındaki piksel farkı kullanılır:
> **Formül:** `abs(sol_göz_x - sağ_göz_x) * görüntü_genişliği`
* **Mantık:** Kullanıcı kameraya yaklaştıkça gözler arası mesafe artar. Kalibrasyon sırasında "İdeal Mesafe" öğrenilir ve bu mesafeden sapmalar risk olarak kaydedilir.

### C. Kamburluk Ölçümü (Duruş Skoru)
Kamburluk, omuz genişliği ile burun-boyun mesafesi arasındaki orana bakılarak hesaplanır. Sadece yüksekliğe bakmamamızın sebebi, kullanıcının kameradan uzaklaşsa bile sistemin yanılmamasını sağlamaktır.
1.  **Boyun Merkezi:** Sol ve sağ omzun Y koordinatlarının ortalaması.
2.  **Omuz Genişliği:** İki omuz arasındaki X koordinat farkı.
3.  **Nihai Skor:** `((Boyun_Y - Burun_Y) / Omuz_Genişliği) * 100`
* **Yorum:** Burun, boyun hizasına yaklaştıkça (kamburluk arttıkça) pay küçülür ve skor düşer.

---

## 3. Bulanık Mantık (Fuzzy Logic) Yapısı
Projenin "Beyni" bu bölümdür. Keskin (0 veya 1) kurallar yerine, insan mantığına yakın esnek kurallar kullanılır.

### A. Giriş Değişkenleri (Antecedents)
1.  **Duruş Skoru (0-100):** Kambur, Normal, Dik.
2.  **Süre (0-60 sn):** Kısa, Orta, Uzun.
3.  **Mesafe (0-150 px):** Uzak, İdeal, Yakın.

### B. Üyelik Fonksiyonları (Membership Functions)
* **Üçgen (Trimf) ve Yamuk (Trapmf)** fonksiyonları kullanılmıştır.
* **Dinamik Yapı:** Üyelik fonksiyonlarının sınırları sabit değildir. Kalibrasyon sırasında kullanıcının "Dik" duruş skoru alınır ve bulanık kümeler (Kambur, Normal, Dik) bu skora göre otomatik olarak yeniden çizilir.

### C. Kural Tabanı (Rule Base)
Sistemde 8 adet ana kural tanımlıdır. Örnek kurallar:
* *EĞER* duruş **kambur** VE süre **orta** *İSE* uyarı **yüksek**.
* *EĞER* mesafe **yakın** *İSE* uyarı **yüksek**.
* *EĞER* duruş **dik** *İSE* uyarı **düşük**.

### D. Durulaştırma (Defuzzification)
Sistem, bulanık sonuçları **Centroid (Ağırlık Merkezi)** yöntemini kullanarak %0-100 arası tek bir "Uyarı Şiddeti" değerine dönüştürür.

---

## 4. Yazılım Mimarisi ve Veritabanı

### A. SQLite Veritabanı
Veriler JSON yerine daha güvenli ve hızlı olan **SQLite** ilişkisel veritabanında tutulur.
* **Kullanicilar Tablosu:** İsim, Dik Skor, Kambur Skor ve İdeal Mesafe verilerini tutar.
* **Oturumlar Tablosu:** Her oturumun tarihini, duruş sürelerini ve saniye saniye trend verisini saklar.

### B. Çoklu İş Parçacığı ve Kilit Sistemi (Subprocess)
Sistem kilitlendiğinde (`kilit.py`), ana dashboard donmasın diye bu ekran bağımsız bir **Subprocess (Alt İşlem)** olarak çalıştırılır.
* **İllüzyon:** Ekran %85 siyah saydam bir katmanla kaplanır ve "Topmost" özelliğiyle en üstte tutulur. Kullanıcı arkadaki uygulamalara tıklayamaz.
* **Oto-Kapanma:** Dashboard, kullanıcının dikleştiğini algıladığı an kilit sürecine "Terminate" sinyali göndererek ekranı otomatik olarak açar.

---

## 5. Veri Analizi ve Dashboard
* **Pandas & Matplotlib:** Geçmiş veriler analiz edilerek **Time-Series (Zaman Serisi)** grafikleri oluşturulur.
* **Oyunlaştırma:** Kullanıcının sağlıklı duruş yüzdesine göre bir "Ergonomi Başarı Puanı" hesaplanır.
* **Dışa Aktarma:** Veriler, tıbbi analizlerde kullanılabilmesi için Excel (CSV) formatında indirilebilir.

---
**Ders:** Bulanık Mantık (Fuzzy Logic)
