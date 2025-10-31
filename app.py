import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

# HTML dan JavaScript untuk komponen pemindai QR
# Menggunakan library html5-qrcode untuk pemindaian di sisi klien (browser)
QR_CODE_SCANNER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>HTML5 QR Code Scanner</title>
    <script src="https://unpkg.com/html5-qrcode/minified/html5-qrcode.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/streamlit-component-lib@1.4.0/dist/streamlit-component-lib.js"></script>
    <style>
        body { margin: 0; padding: 0; }
        #reader {
            width: 100%;
            border: 2px solid #f0f2f6;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div id="reader"></div>
    <script type="text/javascript">
        // Fungsi ini dipanggil ketika QR code berhasil dipindai
        function onScanSuccess(decodedText, decodedResult) {
            // Mengirim teks yang didekode kembali ke Streamlit
            // Ini akan menyebabkan skrip Python berjalan kembali (rerun)
            Streamlit.setComponentValue(decodedText);
        }

        // Fungsi ini dipanggil jika pemindaian gagal (bisa diabaikan)
        function onScanFailure(error) {
            // console.warn(`Code scan error = ${error}`);
        }

        // Membuat instance pemindai baru
        let html5QrcodeScanner = new Html5QrcodeScanner(
            "reader", // ID dari elemen div tempat pemindai akan dirender
            { fps: 10, qrbox: {width: 250, height: 250} },
            /* verbose= */ false);
        
        // Merender pemindai. Ini akan meminta izin kamera.
        html5QrcodeScanner.render(onScanSuccess, onScanFailure);
    </script>
</body>
</html>
"""

# Fungsi untuk memuat database
@st.cache_data
def load_data():
    """Memuat data produk dari file CSV."""
    try:
        df = pd.read_csv('database.csv', dtype={'id': str})
        return df
    except FileNotFoundError:
        st.error("File 'database.csv' tidak ditemukan. Pastikan file tersebut ada.")
        return pd.DataFrame()

# Fungsi untuk mencari data berdasarkan ID dari QR code
def find_product_by_id(df, product_id):
    """Mencari produk dalam DataFrame berdasarkan ID."""
    if df.empty or product_id is None:
        return None
    product = df[df['id'].astype(str) == str(product_id)]
    if not product.empty:
        return product.iloc[0]
    return None

# --- Antarmuka Utama Aplikasi ---
st.set_page_config(page_title="QR Code Scanner", page_icon="📷")
st.title("📷 Aplikasi Pembaca QR Code")
st.write("Arahkan kamera ke QR code untuk mencari data produk secara instan.")

# Memuat data
df = load_data()

if not df.empty:
    st.subheader("Pindai QR Code di Sini")
    
    # Menampilkan komponen HTML/JS dan menangkap nilainya
    qr_code_result = components.html(QR_CODE_SCANNER_HTML, height=500)

    # Menampilkan hasil pencarian
    st.subheader("Hasil Pencarian:")
    
    # PERBAIKAN: Periksa apakah hasilnya adalah string yang valid sebelum diproses
    if qr_code_result and isinstance(qr_code_result, str):
        st.write(f"QR Code terdeteksi: **{qr_code_result}**")
        
        product_data = find_product_by_id(df, qr_code_result)
        
        if product_data is not None:
            st.success("Produk ditemukan!")
            st.write(f"**ID Produk:** {product_data['id']}")
            st.write(f"**Nama Produk:** {product_data['nama_produk']}")
            st.write(f"**Harga:** Rp {int(product_data['harga']):,}")
            st.write(f"**Deskripsi:** {product_data['deskripsi']}")
        else:
            st.error(f"Produk dengan ID '{qr_code_result}' tidak ditemukan di database.")
    else:
        st.info("Belum ada QR code yang dipindai. Arahkan kamera Anda ke QR code.")
