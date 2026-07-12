from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Pengguna(db.Model):
    __tablename__ = "pengguna"
    id = db.Column(db.Integer, primary_key=True)
    nama_lengkap = db.Column(db.String(100), nullable=False)
    nomor_hp = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    kata_sandi = db.Column(db.String(255), nullable=False)
    saldo = db.Column(db.Integer, default=0)

class Transaksi(db.Model):
    __tablename__ = "data_transaksi"
    id = db.Column(db.Integer, primary_key=True)
    # ✅ Tambahkan baris ini (wajib ada)
    pengguna_id = db.Column(db.Integer, db.ForeignKey("pengguna.id"), nullable=False)
    jenis = db.Column(db.String(50), nullable=False)
    nomor_tujuan = db.Column(db.String(30), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    harga_modal = db.Column(db.Integer, default=0)
    laba = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="Berhasil")
    sn = db.Column(db.String(100))
    waktu = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ Relasi ke tabel pengguna
    pengguna = db.relationship("Pengguna", backref=db.backref("transaksi", lazy=True))

class MutasiSaldo(db.Model):
    __tablename__ = "mutasi_saldo"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    jenis = db.Column(db.String(20), nullable=False)
    nominal = db.Column(db.Integer, nullable=False)
    keterangan = db.Column(db.String(200))
    waktu = db.Column(db.DateTime, default=datetime.utcnow)