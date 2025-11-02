import streamlit as st
import pandas as pd
import cv2
from streamlit_webrtc import (
    webrtc_streamer, 
    WebRtcMode, 
    VideoProcessorBase, 
    VideoProcessorFactory
)
from av import VideoFrame
import queue

# --- 1. KELAS PROCESSOR: Melakukan deteksi QR ---
# Kelas ini melakukan pekerjaan utama pada setiap frame video.
class QRCodeVideoProcessor(VideoProcessorBase):
    def __init__(self, result_queue: queue.Queue):
        self.qr_detector = cv2.QRCodeDetector()
        self.result_queue = result_queue
        self.last_qr_code = None

    def recv(self, frame: VideoFrame) -> VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        data, bbox, _ = self.qr_detector.detectAndDecode(img)
        
        if bbox is not None:
            pts = bbox[0].astype(int)
            cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

        if data and data != self.last_qr_code:
            self.last_qr_code = data
            # Masukkan hasil ke dalam queue yang diterima saat inisialisasi
            self.result_queue.put(data)
        
        return VideoFrame.from_ndarray(img, format="bgr24")


# --- 2. KELAS FACTORY: Membuat instance dari Processor ---
# Tugas kelas ini HANYA untuk membuat objek QRCodeVideoProcessor.
class QRCodeProcessorFactory(VideoProcessorFactory):
    def __init__(self, result_queue: queue.Queue):
        # Simpan queue di factory
        self.result_queue = result_queue

    def create(self) -> VideoProcessorBase:
        # Buat instance QRCodeVideoProcessor dan berikan queue padanya.
        return QRCodeVideoProcessor(self.result_queue)


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

# Buat queue di scope utama
result_queue = queue.Queue()

# --- 3. PEMANGGILAN WEBRTC_STREAMER YANG DIPERBAIKI ---
# Kita sekarang memberikan instance dari FACTORY kita.
webrtc_ctx = webrtc_streamer(
    key="qr-scanner",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=QRCodeProcessorFactory(result_queue), # INI PERUBAHANNYA
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

# --- Logika untuk menampilkan hasil ---
if not webrtc_ctx.state.playing:
    st.info("Tekan 'START' untuk menyalakan kamera.")
else:
    st.info("Kamera aktif. Arahkan ke QR Code...")
    
    if "last_scanned_id" not in st.session_state:
        st.session_state.last_scanned_id = None

    try:
        product_id = result_queue.get(timeout=1.0)
        st.session_state.last_scanned_id = product_id
        # Hapus placeholder setelah scan pertama berhasil
        # st.empty() 
    except queue.Empty:
        product_id = st.session_state.last_scanned_id

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
        st.write("Belum ada QR code yang dipindai.")
    
    # Trigger rerun untuk menjaga UI tetap responsif
    st.rerun()
