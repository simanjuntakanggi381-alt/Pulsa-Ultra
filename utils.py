import re
from config import MATA_UANG

def validasi_nomor_hp(nomor):
    """Cek format nomor HP Indonesia"""
    nomor = nomor.strip().replace(" ", "").replace("-", "")
    return bool(re.match(r"^(08|628)[0-9]{8,12}$", nomor))

def validasi_nomor_pln(nomor):
    """Cek format nomor meter PLN"""
    nomor = nomor.strip()
    return nomor.isdigit() and 11 <= len(nomor) <= 13

def format_uang(nilai):
    """Format angka menjadi mata uang Indonesia"""
    try:
        nilai = int(nilai)
        return f"{MATA_UANG} {nilai:,.0f}".replace(",", ".")
    except:
        return f"{MATA_UANG} 0"

def hitung_laba(harga_beli, harga_jual):
    """Hitung keuntungan bersih"""
    return harga_jual - harga_beli