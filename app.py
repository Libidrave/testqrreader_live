import streamlit as st
import pandas as pd
import cv2
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import threading

# Lock untuk thread-safe access ke session state
lock = threading.Lock()

# Kelas untuk memproses frame video dan mendeteksi QR
class QRCodeTransformer(VideoTransformerBase):
    def __init__(self):
        self.qr_detector = cv2.QRCodeDetector()
        self.last_qr_code = None

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # Deteksi dan decode QR code
        data, bbox, _ = self.qr_detector.detectAndDecode(img)
        
        if data:
            # Jika QR code baru terdeteksi
            if data != self.last_qr_code:
                self.last_qr_code = data
                with lock:
                    st.session_state['qr_code_result'] = data
        
        return img

# Fungsi untuk memuat database
@st.cache_data
def load_data():
    df = pd.read_csv('database.csv')
    return df

# Memuat data
df = load_data()

st.title("Aplikasi Pembaca QR Code")
st.write("Arahkan kamera ke QR code untuk mencari data produk.")

# Inisialisasi session state jika belum ada
if 'qr_code_result' not in st.session_state:
    st.session_state['qr_code_result'] = None

# Menjalankan WebRTC streamer
webrtc_ctx = webrtc_streamer(
    key="qr-scanner",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=QRCodeTransformer,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

# Fungsi untuk mencari data berdasarkan ID dari QR code
def find_product_by_id(product_id):
    product = df[df['id'] == product_id]
    if not product.empty:
        return product.iloc[0]
    return None

# Menampilkan hasil pencarian
st.subheader("Hasil Pencarian:")
if st.session_state['qr_code_result']:
    product_id = st.session_state['qr_code_result']
    st.write(f"QR Code terdeteksi: **{product_id}**")
    
    product_data = find_product_by_id(product_id)
    
    if product_data is not None:
        st.success("Produk ditemukan!")
        st.write(f"**Nama Produk:** {product_data['nama_produk']}")
        st.write(f"**Harga:** Rp {product_data['harga']:,}")
        st.write(f"**Deskripsi:** {product_data['deskripsi']}")
    else:
        st.error(f"Produk dengan ID '{product_id}' tidak ditemukan di database.")
else:
    st.info("Belum ada QR code yang dipindai.")
