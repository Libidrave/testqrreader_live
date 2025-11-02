import streamlit as st
import pandas as pd
import cv2
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorFactory
from av import VideoFrame
import threading
import queue  # Import queue

# Gunakan cache_data untuk fungsi yang memuat data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('database.csv')
        # Pastikan kolom 'id' adalah string untuk perbandingan yang konsisten
        df['id'] = df['id'].astype(str)
        return df
    except FileNotFoundError:
        st.error("File 'database.csv' tidak ditemukan. Pastikan file tersebut ada di direktori yang sama.")
        return pd.DataFrame(columns=['id', 'nama_produk', 'harga', 'deskripsi'])

# Memuat data sekali saja
df = load_data()

# Buat sebuah queue untuk komunikasi thread-safe
result_queue = queue.Queue()

# Kelas prosesor video yang diperbarui
class QRCodeProcessor(VideoProcessorFactory):
    def __init__(self, result_queue):
        self.qr_detector = cv2.QRCodeDetector()
        self.result_queue = result_queue
        self.last_qr_code = None

    def create(self):
        # Ini adalah metode pabrik yang akan dipanggil oleh streamer
        return self

    def recv(self, frame: VideoFrame) -> VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        data, bbox, _ = self.qr_detector.detectAndDecode(img)
        
        if bbox is not None:
            # Gambar kotak di sekitar QR code untuk visualisasi
            pts = bbox[0].astype(int)
            cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=3)

        if data and data != self.last_qr_code:
            self.last_qr_code = data
            # Masukkan hasil ke dalam queue, bukan session_state
            self.result_queue.put(data)
        
        return VideoFrame.from_ndarray(img, format="bgr24")

# --- UI Streamlit ---
st.title("Aplikasi Pembaca QR Code (Versi Modern)")
st.write("Arahkan kamera ke QR code untuk mencari data produk.")

# Menjalankan WebRTC streamer
webrtc_ctx = webrtc_streamer(
    key="qr-scanner",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=lambda: QRCodeProcessor(result_queue),
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

st.subheader("Hasil Pencarian:")
result_placeholder = st.empty()

if not webrtc_ctx.state.playing:
    result_placeholder.info("Tekan 'START' untuk menyalakan kamera dan mulai memindai.")
else:
    result_placeholder.info("Kamera aktif. Arahkan ke QR Code...")
    
    # Inisialisasi session_state untuk menyimpan hasil terakhir
    if "last_scanned_id" not in st.session_state:
        st.session_state.last_scanned_id = None

    try:
        # Cek queue untuk hasil baru tanpa memblokir
        product_id = result_queue.get(timeout=1.0)
        st.session_state.last_scanned_id = product_id
    except queue.Empty:
        # Jika tidak ada hasil baru, gunakan hasil terakhir yang tersimpan
        product_id = st.session_state.last_scanned_id

    if product_id:
        with result_placeholder.container():
            st.write(f"QR Code Terakhir Dipindai: **{product_id}**")
            
            product = df[df['id'] == str(product_id)].iloc[0] if not df[df['id'] == str(product_id)].empty else None
            
            if product is not None:
                st.success("Produk ditemukan!")
                st.write(f"**Nama Produk:** {product['nama_produk']}")
                st.write(f"**Harga:** Rp {product['harga']:,}")
                st.write(f"**Deskripsi:** {product['deskripsi']}")
            else:
                st.error(f"Produk dengan ID '{product_id}' tidak ditemukan.")
    
    # Tambahkan trigger untuk rerun script agar selalu memeriksa queue
    st.rerun()
