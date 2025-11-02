import streamlit as st
import pandas as pd
from camera_input_live import camera_input_live
from pyzbar.pyzbar import decode
from PIL import Image
import numpy as np
import cv2
import time

# --- 1. Inisialisasi Session State untuk Throttling ---
# Kita akan menyimpan waktu terakhir kali kita memproses frame.
if 'last_process_time' not in st.session_state:
    st.session_state.last_process_time = 0

# Definisikan interval pemrosesan (dalam detik)
# Artinya, kita hanya akan memproses satu frame setiap 1.5 detik.
PROCESS_INTERVAL = 1.5 

# --- Fungsi dan Logika Utama Aplikasi ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('database.csv')
        df['id'] = df['id'].astype(str)
        return df
    except FileNotFoundError:
        st.error("File 'database.csv' tidak ditemukan.")
        return pd.DataFrame(columns=['id', 'nama_produk', 'harga', 'deskripsi'])

df = load_data()

st.title("Aplikasi Pembaca QR Code Live")
st.write("Arahkan kamera ke QR code. Pemindaian akan dilakukan secara berkala.")

# --- 2. Menggunakan camera_input_live dengan Resolusi Rendah ---
# Mengatur resolusi (width, height) akan sangat membantu performa.
image = camera_input_live(
    width=640,
    height=480
)

# Placeholder untuk menampilkan hasil
result_placeholder = st.empty()

# Proses gambar HANYA jika ada gambar yang diterima
if image is not None:
    current_time = time.time()
    
    # --- 3. Logika Throttling ---
    # Cek apakah sudah cukup waktu berlalu sejak pemrosesan terakhir.
    if current_time - st.session_state.last_process_time > PROCESS_INTERVAL:
        # Update waktu terakhir pemrosesan
        st.session_state.last_process_time = current_time
        
        # Konversi gambar ke format yang bisa dibaca OpenCV
        pil_image = Image.open(image)
        opencv_image = np.array(pil_image)
        gray_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2GRAY)
        
        # Lakukan decoding
        decoded_objects = decode(gray_image)
        
        # Update session state untuk menyimpan hasil terakhir
        if 'last_scanned_id' not in st.session_state:
            st.session_state.last_scanned_id = None
        
        product_id = None
        if decoded_objects:
            # Ambil hasil decode pertama
            product_id = decoded_objects[0].data.decode('utf-8')
            st.session_state.last_scanned_id = product_id

# --- 4. Tampilkan Hasil Terakhir (di luar blok throttling) ---
# Tampilan UI di-update setiap saat, tapi logika berat hanya berjalan sesekali.
with result_placeholder.container():
    last_id = st.session_state.get('last_scanned_id', None)
    
    st.subheader("Hasil Pemindaian:")
    if last_id:
        st.write(f"QR Code Terakhir Dipindai: **{last_id}**")
        
        product_df = df[df['id'] == str(last_id)]
        
        if not product_df.empty:
            product = product_df.iloc[0]
            st.success("Produk ditemukan!")
            st.write(f"**Nama Produk:** {product['nama_produk']}")
            st.write(f"**Harga:** Rp {product['harga']:,}")
            st.write(f"**Deskripsi:** {product['deskripsi']}")
        else:
            st.error(f"Produk dengan ID '{last_id}' tidak ditemukan di database.")
    else:
        st.info("Belum ada QR code yang dipindai. Arahkan kamera ke QR code.")

