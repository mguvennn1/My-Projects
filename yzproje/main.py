import os
from ultralytics import YOLO
import cv2

# 1. Windows'ta OMP hatası almamak için bu ayarı ekliyoruz (Garanti olsun)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

print("Model yükleniyor... Lütfen bekleyin.")

# 2. Eğittiğimiz modeli yüklüyoruz
# best.pt dosyasının bu kodla yan yana olduğundan emin ol!
try:
    model = YOLO("best.pt")
except Exception as e:
    print("HATA: best.pt dosyası bulunamadı! Lütfen dosyayı bu kodun yanına koy.")
    exit()

print("Kamera açılıyor... (Kapatmak için 'q' tuşuna basabilirsin)")

# 3. Webcam'i açıp tahmin yapıyoruz
# source="0" -> Bilgisayarın kendi kamerası
# show=True -> Ekrana pencere açar
# conf=0.50 -> Sadece %50'den emin olduklarını göster (Hatalı çizimleri engeller)
results = model.predict(source="0", show=True, conf=0.50)

