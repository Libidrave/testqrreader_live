import streamlit as st
import pandas as pd
from camera_input_live import camera_input_live
from pyzbar.pyzbar import decode
from PIL import Image
import numpy as np
import cv2
import time

# --- 1. Inisialisasi Session State untuk Throttling ---
if 'last_process_time' not in st.session_state:
    st.session_state.last_process_time = 0

PROCESS_INTERVAL = 0.7

# --- Fungsi dan Logika Utama ---
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

st.title("Aplikasi QR Code Live")
st.write("Arahkan kamera ke QR code.")

image = camera_input_live(
    width=640,
    height=480
)

# Placeholder untuk menampilkan hasil
result_placeholder = st.empty()

# Proses gambar HANYA jika ada gambar yang diterima
if image is not None:
    current_time = time.time()
    
    # --- 2. Logika Throttling ---
    if current_time - st.session_state.last_process_time > PROCESS_INTERVAL:
        # Update waktu terakhir pemrosesan
        st.session_state.last_process_time = current_time
        
        # Konversi gambar ke format yang bisa dibaca OpenCV
        # pil_image = Image.open(image)
        # opencv_image = np.array(pil_image)
        # gray_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2GRAY)
        bytes_data = image.getvalue()        
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        gray_image = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
        
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

# --- 3. Tampilkan Hasil Terakhir ---
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





