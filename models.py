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

    def __repr__(self):
        return f"<Pengguna {self.email}>"


class Transaksi(db.Model):
    __tablename__ = "data_transaksi"

    id = db.Column(db.Integer, primary_key=True)

    pengguna_id = db.Column(
        db.Integer,
        db.ForeignKey("pengguna.id"),
        nullable=False
    )

    jenis = db.Column(db.String(50), nullable=False)
    nomor_tujuan = db.Column(db.String(30), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)

    harga_modal = db.Column(db.Integer, default=0)
    laba = db.Column(db.Integer, default=0)

    status = db.Column(db.String(20), default="Berhasil")
    sn = db.Column(db.String(100))

    waktu = db.Column(db.DateTime, default=datetime.utcnow)

    pengguna = db.relationship(
        "Pengguna",
        backref=db.backref("transaksi", lazy=True)
    )

    def __repr__(self):
        return f"<Transaksi {self.jenis} - {self.nomor_tujuan} - {self.status}>"


class MutasiSaldo(db.Model):
    __tablename__ = "mutasi_saldo"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(100), nullable=False)
    jenis = db.Column(db.String(20), nullable=False)
    nominal = db.Column(db.Integer, nullable=False)
    keterangan = db.Column(db.String(200))

    waktu = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MutasiSaldo {self.email} - {self.jenis} - {self.nominal}>"


# =========================================================
# LIVE CHAT SENJADATA
# =========================================================

class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)

    kode_chat = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True
    )

    nama = db.Column(db.String(120), nullable=False)
    nomor_hp = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    status = db.Column(db.String(30), nullable=False, default="open")
    last_message = db.Column(db.Text, nullable=True)

    unread_admin = db.Column(db.Integer, nullable=False, default=0)
    unread_user = db.Column(db.Integer, nullable=False, default=0)

    dibuat_pada = db.Column(db.DateTime, default=datetime.utcnow)
    diperbarui_pada = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    pesan = db.relationship(
        "ChatMessage",
        backref="chat",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ChatSession {self.kode_chat} - {self.nama}>"


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)

    chat_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_sessions.id"),
        nullable=False,
        index=True
    )

    pengirim = db.Column(db.String(20), nullable=False)
    pesan = db.Column(db.Text, nullable=False)

    dibaca_admin = db.Column(db.Boolean, nullable=False, default=False)
    dibaca_user = db.Column(db.Boolean, nullable=False, default=False)

    waktu = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ChatMessage {self.pengirim} - {self.waktu}>"