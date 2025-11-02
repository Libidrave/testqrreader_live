import streamlit as st
import pandas as pd
import cv2
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase
from av import VideoFrame
import queue
import threading

# --- 1. Inisialisasi State di Awal ---
# Gunakan session_state untuk menyimpan queue. Ini membuatnya bisa diakses
# oleh semua bagian aplikasi secara thread-safe.
if "result_queue" not in st.session_state:
    st.session_state.result_queue = queue.Queue()

# Lock untuk mencegah beberapa update UI sekaligus (opsional, tapi bagus)
ui_lock = threading.Lock()

# --- 2. Kelas Processor yang Disederhanakan ---
# Tidak perlu lagi Factory yang rumit.
class QRCodeVideoProcessor(VideoProcessorBase):
    def __init__(self):
        # Tidak ada argumen yang dibutuhkan saat inisialisasi
        self.qr_detector = cv2.QRCodeDetector()
        self.last_qr_code = None

    def recv(self, frame: VideoFrame) -> VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        data, bbox, _ = self.qr_detector.detectAndDecode(img)
        
        if bbox is not None:
            pts = bbox[0].astype(int)
            cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

        if data and data != self.last_qr_code:
            self.last_qr_code = data
            # Akses queue dari session_state untuk memasukkan data
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

# --- 3. Pemanggilan webrtc_streamer yang Jauh Lebih Sederhana ---
webrtc_ctx = webrtc_streamer(
    key="qr-scanner",
    mode=WebRtcMode.SENDRECV,
    # Cukup berikan kelas Processor-nya langsung.
    # streamlit-webrtc akan membuat instance-nya sendiri tanpa argumen.
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
        
    with ui_lock:
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

# Tidak perlu st.rerun() karena interaksi dengan queue sudah cukup
# untuk menjaga aplikasi tetap hidup dan memeriksa update.
# Jika UI terasa lambat, Anda bisa menambahkannya kembali.
