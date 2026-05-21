import tkinter as tk
import winsound

# Bağımsız Kilit Ekranı
root = tk.Tk()
root.attributes("-fullscreen", True) # Tüm ekranı kapla
root.attributes("-topmost", True)    # En üstte kal
root.configure(bg='black')
root.attributes("-alpha", 0.85)      # Arkaya %85 siyah cam efekti

frame = tk.Frame(root, bg='#e74c3c', bd=2) 
frame.place(relx=0.5, rely=0.5, anchor='center', width=500, height=250)

inner_frame = tk.Frame(frame, bg='#1e1e1e') 
inner_frame.pack(fill='both', expand=True, padx=2, pady=2)

tk.Label(inner_frame, text="🚨 SİSTEM KİLİTLENDİ", font=("Segoe UI", 20, "bold"), bg='#1e1e1e', fg='#e74c3c').pack(pady=(30, 10))
tk.Label(inner_frame, text="Duruşunuz tehlikeli seviyede bozuldu!\nKilit açmak için DİK OTURUN veya butona basın.", font=("Segoe UI", 12), bg='#1e1e1e', fg='white').pack(pady=10)

# Butona basılırsa bu bağımsız program kendini tamamen kapatır
tk.Button(inner_frame, text="ANLADIM, DÜZELTİYORUM", font=("Segoe UI", 11, "bold"), bg='#e74c3c', fg='white', command=root.destroy).pack(pady=20, ipadx=15, ipady=8)

winsound.PlaySound("SystemHand", winsound.SND_ASYNC)
root.mainloop()