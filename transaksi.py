import requests
from config import SERVER_API_URL, API_KEY, ID_AGEN, HARGA_DASAR, HARGA_JUAL, NAMA_PRODUK
from utils import validasi_nomor_hp, validasi_nomor_pln, hitung_laba
from models import Transaksi, Pengguna, db

def cek_saldo():
    """Ambil data saldo dari server penyedia layanan"""
    data = {
        "id_agen": ID_AGEN,
        "api_key": API_KEY,
        "aksi": "cek_saldo"
    }
    try:
        res = requests.post(SERVER_API_URL, json=data, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"status": "gagal", "pesan": f"Koneksi bermasalah: {str(e)}"}


def proses_beli(kode_produk, nomor_tujuan, email_pengguna):
    """Proses pembelian & simpan ke database"""
    # Cek apakah kode produk terdaftar
    if kode_produk not in HARGA_DASAR:
        return {"status": "gagal", "pesan": "Kode produk tidak ditemukan"}

    # Validasi nomor tujuan
    if "PLN" in kode_produk:
        if not validasi_nomor_pln(nomor_tujuan):
            return {"status": "gagal", "pesan": "Nomor meter PLN tidak valid"}
    else:
        if not validasi_nomor_hp(nomor_tujuan):
            return {"status": "gagal", "pesan": "Nomor HP tidak valid"}

    # Ambil data pengguna untuk cek saldo
    pengguna = Pengguna.query.filter_by(email=email_pengguna).first()
    if not pengguna:
        return {"status": "gagal", "pesan": "Akun pengguna tidak ditemukan"}

    # Cek saldo cukup untuk beli
    if pengguna.saldo < HARGA_JUAL[kode_produk]:
        return {"status": "gagal", "pesan": "Saldo tidak cukup untuk transaksi ini"}

    # Data yang dikirim ke server API
    data_kirim = {
        "id_agen": ID_AGEN,
        "api_key": API_KEY,
        "aksi": "beli",
        "kode": kode_produk,
        "tujuan": nomor_tujuan,
        "harga_modal": HARGA_DASAR[kode_produk]
    }

    try:
        res = requests.post(SERVER_API_URL, json=data_kirim, timeout=15)
        res.raise_for_status()
        hasil = res.json()

        if hasil.get("status") in ["sukses", "berhasil"]:
            # Kurangi saldo pengguna
            pengguna.saldo -= HARGA_JUAL[kode_produk]
            laba = hitung_laba(HARGA_DASAR[kode_produk], HARGA_JUAL[kode_produk])

            # Simpan transaksi berhasil
            transaksi = Transaksi(
                pengguna_id=pengguna.id,
                jenis=NAMA_PRODUK[kode_produk],
                nomor_tujuan=nomor_tujuan,
                jumlah=HARGA_JUAL[kode_produk],
                harga_modal=HARGA_DASAR[kode_produk],
                laba=laba,
                status="Berhasil",
                sn=hasil.get("sn", "-")
            )
            db.session.add(transaksi)
            db.session.commit()
            return {"status": "berhasil", "sn": hasil.get("sn", "-"), "pesan": "Transaksi berhasil"}

        else:
            # Simpan transaksi gagal dari respon API
            transaksi = Transaksi(
                pengguna_id=pengguna.id,
                jenis=NAMA_PRODUK[kode_produk],
                nomor_tujuan=nomor_tujuan,
                jumlah=HARGA_JUAL[kode_produk],
                harga_modal=HARGA_DASAR[kode_produk],
                laba=0,
                status="Gagal",
                sn="-"
            )
            db.session.add(transaksi)
            db.session.commit()
            return {"status": "gagal", "pesan": hasil.get("pesan", "Transaksi ditolak server")}

    except Exception as e:
        # Simpan transaksi gagal karena kesalahan sistem
        transaksi = Transaksi(
            pengguna_id=pengguna.id,
            jenis=NAMA_PRODUK.get(kode_produk, "Tidak diketahui"),
            nomor_tujuan=nomor_tujuan,
            jumlah=HARGA_JUAL.get(kode_produk, 0),
            harga_modal=HARGA_DASAR.get(kode_produk, 0),
            laba=0,
            status="Gagal",
            sn="-"
        )
        db.session.add(transaksi)
        db.session.commit()
        return {"status": "gagal", "pesan": f"Kesalahan sistem: {str(e)}"}