import streamlit as st
import pandas as pd
import cv2
import numpy as np  # Pastikan numpy di-import
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase
from av import VideoFrame
import queue
from pyzbar.pyzbar import decode

# --- 1. Inisialisasi State di Awal ---
# Gunakan session_state untuk menyimpan queue. Ini membuatnya bisa diakses
# oleh semua bagian aplikasi secara thread-safe.
if "result_queue" not in st.session_state:
    st.session_state.result_queue = queue.Queue()

# --- 2. Kelas Processor yang Benar dan Sederhana ---
#    - Mewarisi dari VideoProcessorBase
#    - __init__ tidak memiliki argumen
#    - Mengakses queue dari st.session_state
class QRCodeVideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.last_qr_code = None

    def recv(self, frame: VideoFrame) -> VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        # Gunakan pyzbar.decode yang lebih andal
        decoded_objects = decode(img)
        
        data = None
        for obj in decoded_objects:
            # Ambil data dari QR code pertama yang ditemukan
            if not data:
                data = obj.data.decode('utf-8')
            
            # Gambar kotak di sekitar QR code
            points = obj.polygon
            if len(points) > 3:
                pts = np.array([(p.x, p.y) for p in points], dtype=np.int32)
                cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=3)

        # Cek jika ada data BARU yang ditemukan
        if data and data != self.last_qr_code:
            self.last_qr_code = data
            # Masukkan data ke queue yang ada di session_state
            st.session_state.result_queue.put(data)
        
        return VideoFrame.from_ndarray(img, format="bgr24")

# --- Fungsi dan Logika Utama Aplikasi Streamlit ---

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

st.title("Aplikasi Pembaca QR Code")
st.write("Arahkan kamera ke QR code untuk mencari data produk.")

# --- 3. Pemanggilan webrtc_streamer yang Benar ---
webrtc_ctx = webrtc_streamer(
    key="qr-scanner",
    mode=WebRtcMode.SENDRECV,
    # Cukup berikan NAMA KELASNYA. Streamlit-webrtc akan membuat instance-nya
    # secara internal tanpa argumen, yang sekarang sudah benar.
    video_processor_factory=QRCodeVideoProcessor,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

# --- Logika untuk menampilkan hasil ---
result_placeholder = st.empty()

if not webrtc_ctx.state.playing:
    result_placeholder.info("Tekan 'START' untuk menyalakan kamera.")
else:
    if "last_scanned_id" not in st.session_state:
        st.session_state.last_scanned_id = None
        
    try:
        # Ambil hasil dari queue yang ada di session_state
        product_id = st.session_state.result_queue.get(timeout=1.0)
        st.session_state.last_scanned_id = product_id
    except queue.Empty:
        product_id = st.session_state.last_scanned_id

    with result_placeholder.container():
        st.subheader("Hasil Pencarian:")
        if product_id:
            st.write(f"QR Code Terakhir Dipindai: **{product_id}**")
            
            product_df = df[df['id'] == str(product_id)]
            
            if not product_df.empty:
                product = product_df.iloc[0]
                st.success("Produk ditemukan!")
                st.write(f"**Nama Produk:** {product['nama_produk']}")
                st.write(f"**Harga:** Rp {product['harga']:,}")
                st.write(f"**Deskripsi:** {product['deskripsi']}")
            else:
                st.error(f"Produk dengan ID '{product_id}' tidak ditemukan.")
        else:
            st.info("Kamera aktif. Arahkan ke QR Code...")
