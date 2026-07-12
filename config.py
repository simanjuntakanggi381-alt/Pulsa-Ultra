import os

# ======================================
# PENGATURAN DASAR PROYEK
# ======================================
# Lokasi direktori utama proyek
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Buat folder "database" jika belum ada
DB_FOLDER = os.path.join(BASE_DIR, "database")
os.makedirs(DB_FOLDER, exist_ok=True)

# Identitas Usaha
NAMA_USAHA = "Pulsa-Ultra"
SECRET_KEY = "pulsa_ultra_rahasia_2026_jakarta"  # Bisa diganti dengan yang lebih acak
MATA_UANG = "Rp"

# ======================================
# PENGATURAN DATABASE
# ======================================
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DB_FOLDER, 'pulsa_ultra.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ======================================
# PENGATURAN API PENYEDIA LAYANAN
# ======================================
SERVER_API_URL = "https://api-server-pulsa-anda.com/v1"
API_KEY = "MASUKAN_API_KEY_ANDA_DI_SINI"   # Ganti dengan API Key asli nanti
ID_AGEN = "AGEN12345678"                   # Ganti dengan ID Agen asli nanti
BATAS_SALDO_INGAT = 15000

# ======================================
# AKUN PENGGUNA
# ======================================
AKUN_ADMIN = {
    "email": "admin@pulsa-ultra.com",
    "password": "anggi123"
}

# ======================================
# DAFTAR PRODUK & HARGA
# ======================================

# Harga Modal (Harga beli dari penyedia)
HARGA_DASAR = {
    # --- PULSA ---
    "TLK_5K":   4750,
    "TLK_10K":  9500,
    "TLK_20K":  19000,
    "TLK_50K":  47200,
    "TLK_100K": 94000,

    "ISAT_5K":   4700,
    "ISAT_10K":  9400,
    "ISAT_20K":  18800,
    "ISAT_50K":  46800,

    "XL_5K":   4650,
    "XL_10K":  9300,
    "XL_20K":  18600,
    "XL_50K":  46200,

    "TRI_5K":   4600,
    "TRI_10K":  9200,
    "TRI_20K":  18400,
    "TRI_50K":  45800,

    # --- PAKET DATA ---
    "DATA_TLK_1GB": 8500,
    "DATA_TLK_2GB": 14500,
    "DATA_TLK_5GB": 28000,
    "DATA_ISAT_1GB": 8200,
    "DATA_ISAT_2GB": 14000,
    "DATA_ISAT_5GB": 27000,
    "DATA_XL_1GB": 8000,
    "DATA_XL_2GB": 13800,
    "DATA_XL_5GB": 26500,
    "DATA_TRI_1GB": 7800,
    "DATA_TRI_2GB": 13500,
    "DATA_TRI_5GB": 26000,

    # --- E-WALLET ---
    "DANA_10K":    9500,
    "DANA_20K":    19200,
    "DANA_50K":    48500,
    "DANA_100K":   97000,
    "GOPAY_10K":   9450,
    "GOPAY_20K":   19100,
    "GOPAY_50K":   48200,
    "GOPAY_100K":  96500,
    "OVO_10K":     9550,
    "OVO_20K":     19300,
    "OVO_50K":     48800,
    "LINKAJA_10K": 9600,
    "LINKAJA_20K": 19400,
    "SHOPEEPAY_10K": 9400,
    "SHOPEEPAY_50K": 48000,

    # --- TOKEN LISTRIK ---
    "PLN_20K":    19500,
    "PLN_50K":    48500,
    "PLN_100K":   97000,
    "PLN_200K":   193000,
    "PLN_500K":   480000,
    "PLN_1000K":  950000,

    # --- LAYANAN LAINNYA ---
    "VOUCHER_GOJEK_10K":  9500,
    "VOUCHER_GOJEK_25K":  24000,
    "VOUCHER_GRAB_20K":   19200,
    "VOUCHER_GRAB_50K":   47500,
    "VOUCHER_UNIPIN_10K": 9400,
    "VOUCHER_UNIPIN_25K": 23500,
    "EMONEY_FLAZZ_100K":  96000,
    "EMONEY_BRIZZI_100K": 95500,
    "EMONEY_ETOLL_100K":  95000
}

# Harga Jual ke Pelanggan
HARGA_JUAL = {
    # --- PULSA ---
    "TLK_5K":   5200,
    "TLK_10K":  10200,
    "TLK_20K":  20300,
    "TLK_50K":  50500,
    "TLK_100K": 99000,

    "ISAT_5K":   5100,
    "ISAT_10K":  10100,
    "ISAT_20K":  20200,
    "ISAT_50K":  49800,

    "XL_5K":   5000,
    "XL_10K":  10000,
    "XL_20K":  20000,
    "XL_50K":  49200,

    "TRI_5K":   4900,
    "TRI_10K":  9800,
    "TRI_20K":  19600,
    "TRI_50K":  48500,

    # --- PAKET DATA ---
    "DATA_TLK_1GB": 9500,
    "DATA_TLK_2GB": 16000,
    "DATA_TLK_5GB": 31000,
    "DATA_ISAT_1GB": 9200,
    "DATA_ISAT_2GB": 15500,
    "DATA_ISAT_5GB": 30000,
    "DATA_XL_1GB": 9000,
    "DATA_XL_2GB": 15200,
    "DATA_XL_5GB": 29500,
    "DATA_TRI_1GB": 8800,
    "DATA_TRI_2GB": 15000,
    "DATA_TRI_5GB": 29000,

    # --- E-WALLET ---
    "DANA_10K":     10500,
    "DANA_20K":     20800,
    "DANA_50K":     51500,
    "DANA_100K":    102000,
    "GOPAY_10K":    10450,
    "GOPAY_20K":    20700,
    "GOPAY_50K":    51200,
    "GOPAY_100K":   101500,
    "OVO_10K":      10550,
    "OVO_20K":      20900,
    "OVO_50K":      51800,
    "LINKAJA_10K":  10600,
    "LINKAJA_20K":  21000,
    "SHOPEEPAY_10K": 10400,
    "SHOPEEPAY_50K": 51000,

    # --- TOKEN LISTRIK ---
    "PLN_20K":    21000,
    "PLN_50K":    51000,
    "PLN_100K":   101000,
    "PLN_200K":   200000,
    "PLN_500K":   495000,
    "PLN_1000K":  975000,

    # --- LAYANAN LAINNYA ---
    "VOUCHER_GOJEK_10K":  10500,
    "VOUCHER_GOJEK_25K":  26000,
    "VOUCHER_GRAB_20K":   20500,
    "VOUCHER_GRAB_50K":   50500,
    "VOUCHER_UNIPIN_10K": 10300,
    "VOUCHER_UNIPIN_25K": 25500,
    "EMONEY_FLAZZ_100K":  100000,
    "EMONEY_BRIZZI_100K": 99500,
    "EMONEY_ETOLL_100K":  99000
}

# Nama Tampilan Produk
NAMA_PRODUK = {
    # --- PULSA ---
    "TLK_5K":   "Pulsa Telkomsel Rp 5.000",
    "TLK_10K":  "Pulsa Telkomsel Rp 10.000",
    "TLK_20K":  "Pulsa Telkomsel Rp 20.000",
    "TLK_50K":  "Pulsa Telkomsel Rp 50.000",
    "TLK_100K": "Pulsa Telkomsel Rp 100.000",

    "ISAT_5K":   "Pulsa Indosat IM3 Rp 5.000",
    "ISAT_10K":  "Pulsa Indosat IM3 Rp 10.000",
    "ISAT_20K":  "Pulsa Indosat IM3 Rp 20.000",
    "ISAT_50K":  "Pulsa Indosat IM3 Rp 50.000",

    "XL_5K":   "Pulsa XL / Axis Rp 5.000",
    "XL_10K":  "Pulsa XL / Axis Rp 10.000",
    "XL_20K":  "Pulsa XL / Axis Rp 20.000",
    "XL_50K":  "Pulsa XL / Axis Rp 50.000",

    "TRI_5K":   "Pulsa Tri Rp 5.000",
    "TRI_10K":  "Pulsa Tri Rp 10.000",
    "TRI_20K":  "Pulsa Tri Rp 20.000",
    "TRI_50K":  "Pulsa Tri Rp 50.000",

    # --- PAKET DATA ---
    "DATA_TLK_1GB": "Paket Data Telkomsel 1GB",
    "DATA_TLK_2GB": "Paket Data Telkomsel 2GB",
    "DATA_TLK_5GB": "Paket Data Telkomsel 5GB",
    "DATA_ISAT_1GB": "Paket Data Indosat 1GB",
    "DATA_ISAT_2GB": "Paket Data Indosat 2GB",
    "DATA_ISAT_5GB": "Paket Data Indosat 5GB",
    "DATA_XL_1GB": "Paket Data XL / Axis 1GB",
    "DATA_XL_2GB": "Paket Data XL / Axis 2GB",
    "DATA_XL_5GB": "Paket Data XL / Axis 5GB",
    "DATA_TRI_1GB": "Paket Data Tri 1GB",
    "DATA_TRI_2GB": "Paket Data Tri 2GB",
    "DATA_TRI_5GB": "Paket Data Tri 5GB",

    # --- E-WALLET ---
    "DANA_10K":    "Isi Saldo DANA Rp 10.000",
    "DANA_20K":    "Isi Saldo DANA Rp 20.000",
    "DANA_50K":    "Isi Saldo DANA Rp 50.000",
    "DANA_100K":   "Isi Saldo DANA Rp 100.000",
    "GOPAY_10K":   "Isi Saldo GoPay Rp 10.000",
    "GOPAY_20K":   "Isi Saldo GoPay Rp 20.000",
    "GOPAY_50K":   "Isi Saldo GoPay Rp 50.000",
    "GOPAY_100K":  "Isi Saldo GoPay Rp 100.000",
    "OVO_10K":     "Isi Saldo OVO Rp 10.000",
    "OVO_20K":     "Isi Saldo OVO Rp 20.000",
    "OVO_50K":     "Isi Saldo OVO Rp 50.000",
    "LINKAJA_10K": "Isi Saldo LinkAja Rp 10.000",
    "LINKAJA_20K": "Isi Saldo LinkAja Rp 20.000",
    "SHOPEEPAY_10K": "Isi Saldo ShopeePay Rp 10.000",
    "SHOPEEPAY_50K": "Isi Saldo ShopeePay Rp 50.000",

    # --- TOKEN LISTRIK ---
    "PLN_20K":    "Token Listrik PLN Rp 20.000",
    "PLN_50K":    "Token Listrik PLN Rp 50.000",
    "PLN_100K":   "Token Listrik PLN Rp 100.000",
    "PLN_200K":   "Token Listrik PLN Rp 200.000",
    "PLN_500K":   "Token Listrik PLN Rp 500.000",
    "PLN_1000K":  "Token Listrik PLN Rp 1.000.000",

    # --- LAYANAN LAINNYA ---
    "VOUCHER_GOJEK_10K":  "Voucher Gojek Rp 10.000",
    "VOUCHER_GOJEK_25K":  "Voucher Gojek Rp 25.000",
    "VOUCHER_GRAB_20K":   "Voucher Grab Rp 20.000",
    "VOUCHER_GRAB_50K":   "Voucher Grab Rp 50.000",
    "VOUCHER_UNIPIN_10K": "Voucher Unipin Rp 10.000",
    "VOUCHER_UNIPIN_25K": "Voucher Unipin Rp 25.000",
    "EMONEY_FLAZZ_100K":  "Isi Saldo Flazz Rp 100.000",
    "EMONEY_BRIZZI_100K": "Isi Saldo Brizzi Rp 100.000",
    "EMONEY_ETOLL_100K":  "Isi Saldo E-Toll Rp 100.000"
}