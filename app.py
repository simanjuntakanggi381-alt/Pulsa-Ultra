from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from config import (
    SECRET_KEY,
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    NAMA_PRODUK,
    HARGA_JUAL,
    BATAS_SALDO_INGAT
)
from models import db, Transaksi, Pengguna, MutasiSaldo, JaringanRetail, ChatSession, ChatMessage
from transaksi import cek_saldo, proses_beli
from utils import format_uang
from sqlalchemy import func, or_, text, inspect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os
import uuid


app = Flask(__name__)
app.config.from_object("config")
app.secret_key = SECRET_KEY
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False

db.init_app(app)


# =========================================================
# GLOBAL TEMPLATE CONTEXT
# =========================================================
@app.context_processor
def konteks_global():
    pengguna_login = None

    if "sudah_login" in session and session.get("peran") != "admin":
        pengguna_login = Pengguna.query.filter_by(email=session.get("email")).first()

    return dict(
        datetime=datetime,
        sudah_login=("sudah_login" in session),
        nama_pengguna=session.get("nama", ""),
        email_pengguna=session.get("email", ""),
        peran_pengguna=session.get("peran", ""),
        pengguna_login=pengguna_login,
        format_uang=format_uang
    )


# =========================================================
# SETUP DATABASE + AKUN DEMO
# =========================================================
with app.app_context():
    db.create_all()

    # Migrasi ringan untuk database SQLite lama.
    kolom_pengguna = {kolom["name"] for kolom in inspect(db.engine).get_columns("pengguna")}
    if "saldo_retail" not in kolom_pengguna:
        db.session.execute(text("ALTER TABLE pengguna ADD COLUMN saldo_retail INTEGER DEFAULT 0"))
        db.session.commit()
    if "fee_retail" not in kolom_pengguna:
        db.session.execute(text("ALTER TABLE pengguna ADD COLUMN fee_retail INTEGER DEFAULT 0"))
        db.session.commit()

    cek_anggi = Pengguna.query.filter_by(email="anggi@gmail.com").first()

    if not cek_anggi:
        akun_anggi = Pengguna(
            nama_lengkap="Anggi",
            nomor_hp="081234567890",
            email="anggi@gmail.com",
            kata_sandi=generate_password_hash("anggi123", method="pbkdf2:sha256"),
            saldo=0
        )
        db.session.add(akun_anggi)
        db.session.commit()

    akun_master = Pengguna.query.filter_by(email="alex@master.local").first()
    if not akun_master:
        akun_master = Pengguna(
            nama_lengkap="Alex Master",
            nomor_hp="080811000001",
            email="alex@master.local",
            kata_sandi=AKUN_PANEL["alex"]["password_hash"] if "AKUN_PANEL" in globals() else generate_password_hash("alex080811", method="pbkdf2:sha256"),
            saldo=0,
            saldo_retail=0,
            fee_retail=0
        )
        db.session.add(akun_master)
        db.session.commit()

    print("\n✅ AKUN DEMO SIAP DIGUNAKAN:")
    print("📧 Email    : anggi@gmail.com")
    print("📱 Nomor HP : 081234567890")
    print("🔑 Sandi    : anggi123\n")


# =========================================================
# HELPER
# =========================================================
def user_sedang_login():
    return "sudah_login" in session


def user_admin():
    return session.get("peran") == "admin"


def user_master():
    return session.get("peran") == "master"


def ambil_pengguna_login():
    if not user_sedang_login():
        return None

    if user_admin():
        return None

    return Pengguna.query.filter_by(email=session.get("email")).first()


def wajib_login():
    if not user_sedang_login():
        flash("⚠️ Silakan masuk terlebih dahulu.", "warning")
        return redirect(url_for("login"))

    return None


def wajib_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not user_sedang_login() or not user_admin():
            flash("⚠️ Silakan masuk sebagai admin terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def wajib_master(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not user_sedang_login() or not user_master():
            flash("Akses khusus akun Master.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def format_flash_nominal(nominal):
    try:
        return format_uang(int(nominal))
    except Exception:
        return f"Rp {nominal}"


def ambil_daftar_produk(prefix):
    return {
        kode: nama
        for kode, nama in NAMA_PRODUK.items()
        if kode.startswith(prefix)
    }


# =========================================================
# MIDDLEWARE
# =========================================================
@app.before_request
def cek_akses():
    halaman_bebas = [
        "login",
        "daftar",
        "logout",
        "static",
        "dashboard",
        "pulsa",
        "data",
        "ewallet",
        "listrik",
        "lainnya",
        "riwayat",
        "produk",
        "profil",
        "topup_saldo",
        "mutasi_saldo",
        "tv",
        "game",
        "pdam",
        "bpjs",
        "internet",
        "masa_aktif",
        "paket_telp",
        "aktivasi",
        "gas",
        "angsuran",
        "pbb",
        "asuransi",
        "voucher",
        "zakat",
        "pln_pasca",
        "tiket",
        "admin_index",
        "admin_login",
        "admin_dashboard",
        "admin_logout",
        "admin_transaksi",
        "admin_pengguna",
        "admin_produk",
        "admin_cek_sistem",
        "cs_index",
        "cs_login",
        "cs_live_chat",
        "cs_live_chat_detail",
        "cs_live_chat_balas",
        "cs_live_chat_tutup",
        "cs_live_chat_buka",
        "cs_live_chat_catatan",
        "cs_member_detail",
        "cs_member_list",
        "cs_transaksi",
        "cs_transaksi_provider",
        "cs_dashboard",
        "cs_logout",
        "api_chat_start",
        "api_chat_send",
        "api_chat_messages",
        "api_chat_reset",
        "api_chat_ping",
        "api_cs_chats"
    ]

    if request.endpoint in halaman_bebas:
        return

    if "sudah_login" not in session:
        flash("⚠️ Silakan masuk terlebih dahulu untuk bertransaksi.", "warning")
        return redirect(url_for("login"))


# =========================================================
# HALAMAN UTAMA
# =========================================================
@app.route("/")
def index():
    return redirect(url_for("dashboard"))


# =========================================================
# ADMIN PANEL SENJADATA V2
# =========================================================
AKUN_PANEL = {
    "alex": {
        "nama": "Master Alex",
        "level": "master",
        "password_hash": "pbkdf2:sha256:600000$1NK75eS6LfPmpBBz$cd625c01e6f9a76d4c6e1cd4b3b41e6aa8c0bceac8f59bded4bd2e92a8e36037"
    },
    "anggi": {
        "nama": "Admin Anggi",
        "level": "admin",
        "password_hash": "pbkdf2:sha256:600000$ffakAmRDs25dioIj$6d43d9627163edae8e3743a82ee80c5275187d9022f7b417c93c5e2778203e3e"
    }
}


def validasi_login_admin(username, password):
    username = (username or "").strip()
    password = (password or "").strip()
    username_lower = username.lower()

    akun = AKUN_PANEL.get(username_lower)
    if akun and check_password_hash(akun["password_hash"], password):
        return {"username": username_lower, **akun}

    return None


def masuk_sebagai_admin(akun):
    session.clear()
    session["sudah_login"] = True
    session["email"] = akun["username"]
    session["nama"] = akun["nama"]
    session["peran"] = "admin"
    session["level_admin"] = akun["level"]


def masuk_sebagai_master(akun):
    pengguna = Pengguna.query.filter_by(email="alex@master.local").first()
    if not pengguna:
        return False

    session.clear()
    session["sudah_login"] = True
    session["email"] = pengguna.email
    session["nama"] = pengguna.nama_lengkap
    session["peran"] = "master"
    session["level_akun"] = "master"
    return True


def hitung_statistik_admin():
    total_pengguna = Pengguna.query.count()
    total_produk = len(NAMA_PRODUK)
    total_transaksi = Transaksi.query.count()
    total_mutasi = MutasiSaldo.query.count()

    transaksi_sukses = Transaksi.query.filter_by(status="Berhasil").count()
    transaksi_pending = Transaksi.query.filter_by(status="Pending").count()
    transaksi_gagal = Transaksi.query.filter_by(status="Gagal").count()

    total_laba = db.session.query(
        func.sum(Transaksi.laba)
    ).filter_by(status="Berhasil").scalar() or 0

    return {
        "total_pengguna": total_pengguna,
        "total_produk": total_produk,
        "total_transaksi": total_transaksi,
        "total_mutasi": total_mutasi,
        "transaksi_sukses": transaksi_sukses,
        "transaksi_pending": transaksi_pending,
        "transaksi_gagal": transaksi_gagal,
        "total_laba": total_laba
    }


def cek_kesehatan_sistem():
    hasil = {
        "database": {
            "status": "ok",
            "label": "Database Aktif",
            "detail": "Koneksi database berhasil."
        },
        "produk": {
            "status": "ok" if len(NAMA_PRODUK) > 0 else "warning",
            "label": "Produk",
            "detail": f"{len(NAMA_PRODUK)} produk tersedia."
        },
        "harga": {
            "status": "ok" if len(HARGA_JUAL) > 0 else "warning",
            "label": "Harga Jual",
            "detail": f"{len(HARGA_JUAL)} harga jual tersedia."
        },
        "transaksi": {
            "status": "ok",
            "label": "Tabel Transaksi",
            "detail": f"{Transaksi.query.count()} transaksi tercatat."
        },
        "pengguna": {
            "status": "ok",
            "label": "Tabel Pengguna",
            "detail": f"{Pengguna.query.count()} pengguna terdaftar."
        },
        "mutasi": {
            "status": "ok",
            "label": "Mutasi Saldo",
            "detail": f"{MutasiSaldo.query.count()} mutasi saldo tercatat."
        },
        "admin": {
            "status": "ok",
            "label": "Admin Panel",
            "detail": "Akun admin panel aktif dan route admin tersedia."
        }
    }

    try:
        db.session.execute(text("SELECT 1"))
        hasil["database"]["status"] = "ok"
        hasil["database"]["label"] = "Database Aktif"
        hasil["database"]["detail"] = "Koneksi database berhasil dicek."
    except Exception as e:
        hasil["database"]["status"] = "danger"
        hasil["database"]["label"] = "Database Bermasalah"
        hasil["database"]["detail"] = str(e)

    return hasil


@app.route("/admin")
@app.route("/panel")
@app.route("/admin-panel")
def admin_index():
    if user_master():
        return redirect(url_for("dashboard"))
    if user_sedang_login() and user_admin():
        return redirect(url_for("admin_dashboard"))

    return redirect(url_for("login"))


@app.route("/admin/login", methods=["GET", "POST"])
@app.route("/admin-login", methods=["GET", "POST"])
@app.route("/panel/login", methods=["GET", "POST"])
def admin_login():
    flash("Login panel sekarang melalui halaman login aplikasi.", "info")
    return redirect(url_for("login"))


@app.route("/master")
@app.route("/master/dashboard")
@wajib_master
def master_dashboard():
    return redirect(url_for("dashboard"))


@app.route("/admin/dashboard")
@app.route("/panel/dashboard")
@wajib_admin
def admin_dashboard():
    statistik = hitung_statistik_admin()
    cek_sistem = cek_kesehatan_sistem()

    transaksi_terbaru = Transaksi.query.order_by(
        Transaksi.waktu.desc()
    ).limit(8).all()

    pengguna_terbaru = Pengguna.query.order_by(
        Pengguna.id.desc()
    ).limit(6).all()

    mutasi_terbaru = MutasiSaldo.query.order_by(
        MutasiSaldo.waktu.desc()
    ).limit(6).all()

    return render_template(
        "admin_dashboard.html",
        statistik=statistik,
        cek_sistem=cek_sistem,
        transaksi_terbaru=transaksi_terbaru,
        pengguna_terbaru=pengguna_terbaru,
        mutasi_terbaru=mutasi_terbaru,
        admin_username=session.get("nama", "Admin"),
        format_uang=format_uang
    )


@app.route("/admin/transaksi")
@wajib_admin
def admin_transaksi():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    query = Transaksi.query

    if q:
        kondisi = []

        if hasattr(Transaksi, "email"):
            kondisi.append(Transaksi.email.ilike(f"%{q}%"))

        if hasattr(Transaksi, "tujuan"):
            kondisi.append(Transaksi.tujuan.ilike(f"%{q}%"))

        if hasattr(Transaksi, "kode_produk"):
            kondisi.append(Transaksi.kode_produk.ilike(f"%{q}%"))

        if hasattr(Transaksi, "nama_produk"):
            kondisi.append(Transaksi.nama_produk.ilike(f"%{q}%"))

        if kondisi:
            query = query.filter(or_(*kondisi))

    if status:
        query = query.filter_by(status=status)

    daftar = query.order_by(Transaksi.waktu.desc()).limit(300).all()

    ringkasan = {
        "total": len(daftar),
        "berhasil": len([x for x in daftar if x.status == "Berhasil"]),
        "pending": len([x for x in daftar if x.status == "Pending"]),
        "gagal": len([x for x in daftar if x.status == "Gagal"])
    }

    return render_template(
        "admin_transaksi.html",
        daftar=daftar,
        q=q,
        status=status,
        ringkasan=ringkasan,
        format_uang=format_uang
    )


@app.route("/admin/pengguna")
@wajib_admin
def admin_pengguna():
    q = request.args.get("q", "").strip()

    query = Pengguna.query

    if q:
        query = query.filter(
            or_(
                Pengguna.nama_lengkap.ilike(f"%{q}%"),
                Pengguna.email.ilike(f"%{q}%"),
                Pengguna.nomor_hp.ilike(f"%{q}%")
            )
        )

    daftar = query.order_by(Pengguna.id.desc()).all()

    total_saldo = sum([int(user.saldo or 0) for user in daftar])

    ringkasan = {
        "total": len(daftar),
        "total_saldo": total_saldo
    }

    return render_template(
        "admin_pengguna.html",
        daftar=daftar,
        q=q,
        ringkasan=ringkasan,
        format_uang=format_uang
    )


@app.route("/admin/produk")
@wajib_admin
def admin_produk():
    q = request.args.get("q", "").strip().lower()
    kategori = request.args.get("kategori", "").strip()

    def kategori_produk(kode):
        if kode.startswith("DATA_"):
            return "Paket Data"
        if kode.startswith(("DANA_", "GOPAY_", "OVO_", "LINKAJA_", "SHOPEEPAY_")):
            return "E-Wallet"
        if kode.startswith("PLN_"):
            return "Token Listrik"
        if kode.startswith(("VOUCHER_", "EMONEY_")):
            return "Voucher & E-Money"
        return "Pulsa"

    daftar = [
        {
            "kode": kode,
            "nama": nama,
            "harga": HARGA_JUAL.get(kode, 0),
            "kategori": kategori_produk(kode)
        }
        for kode, nama in NAMA_PRODUK.items()
    ]

    if q:
        daftar = [
            item for item in daftar
            if q in item["kode"].lower() or q in item["nama"].lower()
        ]

    if kategori:
        daftar = [item for item in daftar if item["kategori"] == kategori]

    ringkasan = {
        "total": len(daftar),
        "harga_terendah": min([x["harga"] for x in daftar], default=0),
        "harga_tertinggi": max([x["harga"] for x in daftar], default=0),
        "kategori": len({x["kategori"] for x in daftar})
    }

    return render_template(
        "admin_produk.html",
        daftar=daftar,
        q=q,
        kategori=kategori,
        ringkasan=ringkasan,
        format_uang=format_uang
    )


@app.route("/admin/cek-sistem")
@app.route("/admin/system")
@wajib_admin
def admin_cek_sistem():
    statistik = hitung_statistik_admin()
    cek_sistem = cek_kesehatan_sistem()

    return render_template(
        "admin_cek_sistem.html",
        statistik=statistik,
        cek_sistem=cek_sistem,
        format_uang=format_uang
    )


@app.route("/admin/logout")
@app.route("/panel/logout")
@wajib_admin
def admin_logout():
    session.clear()
    flash("Berhasil keluar dari panel. Silakan login kembali.", "success")
    return redirect(url_for("login"))


# =========================================================
# LIVE CHAT PANEL TERPISAH - CS SENJADATA PRO
# =========================================================
CS_PANEL_USERNAME = os.getenv("CS_PANEL_USERNAME", "cs")
CS_PANEL_PASSWORD = os.getenv("CS_PANEL_PASSWORD", "cs12345")


def buat_kode_chat():
    return "CHAT-" + uuid.uuid4().hex[:12].upper()


def format_waktu_chat(waktu):
    if not waktu:
        return "-"

    try:
        waktu_wib = waktu + timedelta(hours=7)
        return waktu_wib.strftime("%d/%m/%Y, %H:%M:%S")
    except Exception:
        return "-"


def serialize_chat_message(item):
    return {
        "id": item.id,
        "pengirim": item.pengirim,
        "pesan": item.pesan,
        "waktu": format_waktu_chat(item.waktu),
        "dibaca_admin": bool(item.dibaca_admin),
        "dibaca_user": bool(item.dibaca_user)
    }


BOT_NAMA = "CS SenjaData"
BOT_WELCOME_MESSAGES = [
    "Selamat datang di SenjaData 👋",
    "Ada yang bisa kami bantu hari ini?"
]


def tambah_bot_welcome(chat):
    """
    Membuat pesan sambutan otomatis sekali saja untuk setiap sesi chat.
    Pesan bot dibuat pendek dan rapi, tidak panjang.
    """
    if not chat:
        return []

    pesan_sudah_ada = ChatMessage.query.filter(
        ChatMessage.chat_id == chat.id,
        ChatMessage.pengirim == "admin",
        ChatMessage.pesan.ilike("%Selamat datang di SenjaData%")
    ).first()

    if pesan_sudah_ada:
        return []

    pesan_bot_list = []

    for isi_pesan in BOT_WELCOME_MESSAGES:
        pesan_bot = ChatMessage(
            chat_id=chat.id,
            pengirim="admin",
            pesan=isi_pesan,
            dibaca_admin=True,
            dibaca_user=False
        )
        db.session.add(pesan_bot)
        pesan_bot_list.append(pesan_bot)

    chat.last_message = BOT_WELCOME_MESSAGES[-1]
    chat.unread_user = int(chat.unread_user or 0) + len(pesan_bot_list)
    chat.diperbarui_pada = datetime.utcnow()

    db.session.commit()

    return pesan_bot_list


def cs_sedang_login():
    return session.get("cs_login") is True


def cs_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not cs_sedang_login():
            flash("⚠️ Silakan masuk ke panel live chat terlebih dahulu.", "warning")
            return redirect(url_for("cs_login"))
        return f(*args, **kwargs)
    return wrapper


def parse_tanggal(nilai, akhir_hari=False):
    if not nilai:
        return None

    try:
        tanggal = datetime.strptime(nilai, "%Y-%m-%d")

        if akhir_hari:
            tanggal = tanggal.replace(hour=23, minute=59, second=59)

        return tanggal
    except Exception:
        return None


def rentang_dari_request():
    range_key = request.args.get("range", "").strip()
    tanggal_awal = request.args.get("tanggal_awal", "").strip()
    tanggal_akhir = request.args.get("tanggal_akhir", "").strip()

    hari_ini = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    if range_key == "hari_ini":
        awal = hari_ini
        akhir = hari_ini + timedelta(days=1) - timedelta(seconds=1)
        return awal, akhir, "Hari Ini"

    if range_key == "kemarin":
        awal = hari_ini - timedelta(days=1)
        akhir = hari_ini - timedelta(seconds=1)
        return awal, akhir, "Kemarin"

    if range_key == "7_hari":
        awal = hari_ini - timedelta(days=7)
        akhir = datetime.utcnow()
        return awal, akhir, "7 Hari"

    if range_key == "30_hari":
        awal = hari_ini - timedelta(days=30)
        akhir = datetime.utcnow()
        return awal, akhir, "30 Hari"

    if range_key == "bulan_ini":
        awal = hari_ini.replace(day=1)
        akhir = datetime.utcnow()
        return awal, akhir, "Bulan Ini"

    awal = parse_tanggal(tanggal_awal)
    akhir = parse_tanggal(tanggal_akhir, akhir_hari=True)

    if awal or akhir:
        return awal, akhir, "Custom"

    return None, None, "Semua"


def filter_transaksi_query(query, q="", status="", tanggal_awal_obj=None, tanggal_akhir_obj=None):
    q = (q or "").strip()
    status = (status or "").strip()

    if status:
        query = query.filter(Transaksi.status == status)

    if tanggal_awal_obj is not None and hasattr(Transaksi, "waktu"):
        query = query.filter(Transaksi.waktu >= tanggal_awal_obj)

    if tanggal_akhir_obj is not None and hasattr(Transaksi, "waktu"):
        query = query.filter(Transaksi.waktu <= tanggal_akhir_obj)

    if q:
        kondisi = []

        if hasattr(Transaksi, "jenis"):
            kondisi.append(Transaksi.jenis.ilike(f"%{q}%"))

        if hasattr(Transaksi, "nomor_tujuan"):
            kondisi.append(Transaksi.nomor_tujuan.ilike(f"%{q}%"))

        if hasattr(Transaksi, "sn"):
            kondisi.append(Transaksi.sn.ilike(f"%{q}%"))

        if hasattr(Transaksi, "email"):
            kondisi.append(Transaksi.email.ilike(f"%{q}%"))

        if hasattr(Transaksi, "tujuan"):
            kondisi.append(Transaksi.tujuan.ilike(f"%{q}%"))

        if hasattr(Transaksi, "kode_produk"):
            kondisi.append(Transaksi.kode_produk.ilike(f"%{q}%"))

        if hasattr(Transaksi, "nama_produk"):
            kondisi.append(Transaksi.nama_produk.ilike(f"%{q}%"))

        if hasattr(Transaksi, "pengguna_id"):
            query = query.outerjoin(Pengguna, Transaksi.pengguna_id == Pengguna.id)

            kondisi.extend([
                Pengguna.nama_lengkap.ilike(f"%{q}%"),
                Pengguna.email.ilike(f"%{q}%"),
                Pengguna.nomor_hp.ilike(f"%{q}%")
            ])

        if kondisi:
            query = query.filter(or_(*kondisi))

    return query


def ringkasan_transaksi(daftar):
    total_nominal = 0

    for trx in daftar:
        if hasattr(trx, "jumlah"):
            total_nominal += int(trx.jumlah or 0)
        elif hasattr(trx, "harga_jual"):
            total_nominal += int(trx.harga_jual or 0)

    return {
        "total": len(daftar),
        "total_transaksi": len(daftar),
        "berhasil": len([x for x in daftar if x.status == "Berhasil"]),
        "pending": len([x for x in daftar if x.status == "Pending"]),
        "gagal": len([x for x in daftar if x.status == "Gagal"]),
        "total_nominal": total_nominal
    }


def provider_dari_produk(nama_produk):
    nama = (nama_produk or "").lower()
    provider_map = [
        ("telkomsel", "Telkomsel"),
        ("indosat", "Indosat"),
        ("xl", "XL / Axis"),
        ("axis", "XL / Axis"),
        ("tri", "Tri"),
        ("dana", "DANA"),
        ("gopay", "GoPay"),
        ("ovo", "OVO"),
        ("linkaja", "LinkAja"),
        ("shopeepay", "ShopeePay"),
        ("listrik", "PLN"),
        ("pln", "PLN"),
        ("gojek", "Gojek"),
        ("grab", "Grab"),
        ("unipin", "UniPin"),
        ("flazz", "Flazz"),
        ("brizzi", "Brizzi"),
        ("e-toll", "E-Toll")
    ]

    for kata, provider in provider_map:
        if kata in nama:
            return provider

    return "Lainnya"


def cari_member_dari_chat(chat):
    member = None

    if chat.email:
        member = Pengguna.query.filter_by(email=chat.email).first()

    if not member and chat.nomor_hp:
        member = Pengguna.query.filter_by(nomor_hp=chat.nomor_hp).first()

    if not member and chat.nama:
        member = Pengguna.query.filter(
            Pengguna.nama_lengkap.ilike(f"%{chat.nama}%")
        ).first()

    return member


def ambil_transaksi_member(member, q="", status="", tanggal_awal_obj=None, tanggal_akhir_obj=None, limit=20):
    if not member:
        return []

    query = Transaksi.query

    if hasattr(Transaksi, "pengguna_id"):
        query = query.filter(Transaksi.pengguna_id == member.id)
    elif hasattr(Transaksi, "email"):
        query = query.filter(Transaksi.email == member.email)
    else:
        return []

    query = filter_transaksi_query(
        query=query,
        q=q,
        status=status,
        tanggal_awal_obj=tanggal_awal_obj,
        tanggal_akhir_obj=tanggal_akhir_obj
    )

    return query.order_by(Transaksi.waktu.desc()).limit(limit).all()


def ambil_mutasi_member(member, limit=20):
    if not member:
        return []

    return MutasiSaldo.query.filter_by(
        email=member.email
    ).order_by(MutasiSaldo.waktu.desc()).limit(limit).all()


@app.route("/cs")
@app.route("/cs-panel")
@app.route("/live-chat-panel")
def cs_index():
    if cs_sedang_login():
        return redirect(url_for("cs_dashboard"))

    return redirect(url_for("cs_login"))


@app.route("/cs/login", methods=["GET", "POST"])
@app.route("/cs-panel/login", methods=["GET", "POST"])
@app.route("/live-chat-panel/login", methods=["GET", "POST"])
def cs_login():
    if cs_sedang_login():
        return redirect(url_for("cs_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username.lower() == str(CS_PANEL_USERNAME).lower() and password == str(CS_PANEL_PASSWORD):
            session["cs_login"] = True
            session["cs_username"] = username or "CS SenjaData"

            flash("✅ Berhasil masuk ke Live Chat Panel.", "success")
            return redirect(url_for("cs_dashboard"))

        flash("❌ Username atau password CS salah.", "danger")
        return redirect(url_for("cs_login"))

    return render_template("cs_login.html")


@app.route("/cs/dashboard")
@app.route("/cs-panel/dashboard")
@app.route("/live-chat-panel/dashboard")
@cs_required
def cs_dashboard():
    hari_ini = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_chat = ChatSession.query.count()
    chat_open = ChatSession.query.filter_by(status="open").count()
    unread_chat = db.session.query(func.sum(ChatSession.unread_admin)).scalar() or 0

    transaksi_hari_ini = Transaksi.query.filter(Transaksi.waktu >= hari_ini).count()
    transaksi_berhasil = Transaksi.query.filter_by(status="Berhasil").count()
    transaksi_pending = Transaksi.query.filter_by(status="Pending").count()
    transaksi_gagal = Transaksi.query.filter_by(status="Gagal").count()

    statistik = {
        "total_chat": total_chat,
        "chat_open": chat_open,
        "unread_chat": int(unread_chat or 0),
        "total_member": Pengguna.query.count(),
        "transaksi_hari_ini": transaksi_hari_ini,
        "transaksi_berhasil": transaksi_berhasil,
        "transaksi_pending": transaksi_pending,
        "transaksi_gagal": transaksi_gagal
    }

    chat_terbaru = ChatSession.query.order_by(
        ChatSession.diperbarui_pada.desc()
    ).limit(8).all()

    transaksi_terbaru = Transaksi.query.order_by(
        Transaksi.waktu.desc()
    ).limit(10).all()

    member_terbaru = Pengguna.query.order_by(
        Pengguna.id.desc()
    ).limit(8).all()

    return render_template(
        "cs_dashboard.html",
        statistik=statistik,
        chat_terbaru=chat_terbaru,
        transaksi_terbaru=transaksi_terbaru,
        member_terbaru=member_terbaru,
        format_waktu_chat=format_waktu_chat,
        format_uang=format_uang
    )


@app.route("/cs/live-chat")
@app.route("/live-chat-panel/chat")
@cs_required
def cs_live_chat():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    query = ChatSession.query

    if q:
        query = query.filter(
            or_(
                ChatSession.kode_chat.ilike(f"%{q}%"),
                ChatSession.nama.ilike(f"%{q}%"),
                ChatSession.nomor_hp.ilike(f"%{q}%"),
                ChatSession.email.ilike(f"%{q}%"),
                ChatSession.last_message.ilike(f"%{q}%")
            )
        )

    if status:
        query = query.filter_by(status=status)

    daftar_chat = query.order_by(
        ChatSession.diperbarui_pada.desc()
    ).limit(200).all()

    semua_chat = ChatSession.query.all()

    ringkasan = {
        "total": len(daftar_chat),
        "open": len([x for x in semua_chat if x.status == "open"]),
        "closed": len([x for x in semua_chat if x.status == "closed"]),
        "unread": sum([int(x.unread_admin or 0) for x in semua_chat])
    }

    return render_template(
        "cs_live_chat.html",
        daftar_chat=daftar_chat,
        ringkasan=ringkasan,
        q=q,
        status=status,
        format_waktu_chat=format_waktu_chat,
        format_uang=format_uang
    )


@app.route("/cs/live-chat/<int:chat_id>")
@app.route("/live-chat-panel/chat/<int:chat_id>")
@cs_required
def cs_live_chat_detail(chat_id):
    chat = ChatSession.query.get_or_404(chat_id)

    ChatMessage.query.filter_by(
        chat_id=chat.id,
        pengirim="user",
        dibaca_admin=False
    ).update({"dibaca_admin": True})

    chat.unread_admin = 0
    db.session.commit()

    pesan_chat = ChatMessage.query.filter_by(
        chat_id=chat.id
    ).order_by(ChatMessage.waktu.asc()).all()

    daftar_chat = ChatSession.query.order_by(
        ChatSession.diperbarui_pada.desc()
    ).limit(25).all()

    member = cari_member_dari_chat(chat)

    q_trx = request.args.get("q_trx", "").strip()
    status_trx = request.args.get("status_trx", "").strip()
    tanggal_awal = request.args.get("tanggal_awal", "").strip()
    tanggal_akhir = request.args.get("tanggal_akhir", "").strip()
    tanggal_awal_obj, tanggal_akhir_obj, mode_filter = rentang_dari_request()

    transaksi_member = ambil_transaksi_member(
        member=member,
        q=q_trx,
        status=status_trx,
        tanggal_awal_obj=tanggal_awal_obj,
        tanggal_akhir_obj=tanggal_akhir_obj,
        limit=20
    )

    mutasi_member = ambil_mutasi_member(member, limit=10)

    setattr(chat, "catatan_internal", session.get(f"catatan_chat_{chat.id}", ""))

    return render_template(
        "cs_live_chat_detail.html",
        chat=chat,
        pesan_chat=pesan_chat,
        daftar_chat=daftar_chat,
        member=member,
        transaksi_member=transaksi_member,
        mutasi_member=mutasi_member,
        q_trx=q_trx,
        status_trx=status_trx,
        tanggal_awal=tanggal_awal,
        tanggal_akhir=tanggal_akhir,
        mode_filter=mode_filter,
        format_waktu_chat=format_waktu_chat,
        format_uang=format_uang
    )


@app.route("/cs/live-chat/<int:chat_id>/balas", methods=["POST"])
@app.route("/live-chat-panel/chat/<int:chat_id>/balas", methods=["POST"])
@cs_required
def cs_live_chat_balas(chat_id):
    chat = ChatSession.query.get_or_404(chat_id)

    if chat.status != "open":
        flash("⚠️ Chat ini sudah ditutup. Buka lagi chat jika ingin membalas.", "warning")
        return redirect(url_for("cs_live_chat_detail", chat_id=chat.id))

    pesan = request.form.get("pesan", "").strip()

    if not pesan:
        flash("⚠️ Pesan balasan tidak boleh kosong.", "warning")
        return redirect(url_for("cs_live_chat_detail", chat_id=chat.id))

    pesan_baru = ChatMessage(
        chat_id=chat.id,
        pengirim="admin",
        pesan=pesan,
        dibaca_admin=True,
        dibaca_user=False
    )

    chat.last_message = pesan
    chat.unread_user = int(chat.unread_user or 0) + 1
    chat.unread_admin = 0
    chat.diperbarui_pada = datetime.utcnow()

    db.session.add(pesan_baru)
    db.session.commit()

    flash("✅ Balasan berhasil dikirim.", "success")
    return redirect(url_for("cs_live_chat_detail", chat_id=chat.id))


@app.route("/cs/live-chat/<int:chat_id>/tutup", methods=["POST"])
@app.route("/live-chat-panel/chat/<int:chat_id>/tutup", methods=["POST"])
@cs_required
def cs_live_chat_tutup(chat_id):
    chat = ChatSession.query.get_or_404(chat_id)

    chat.status = "closed"
    chat.diperbarui_pada = datetime.utcnow()

    db.session.commit()

    flash("✅ Chat berhasil ditutup.", "success")
    return redirect(url_for("cs_live_chat_detail", chat_id=chat.id))


@app.route("/cs/live-chat/<int:chat_id>/buka", methods=["POST"])
@cs_required
def cs_live_chat_buka(chat_id):
    chat = ChatSession.query.get_or_404(chat_id)

    chat.status = "open"
    chat.diperbarui_pada = datetime.utcnow()

    db.session.commit()

    flash("✅ Chat berhasil dibuka kembali.", "success")
    return redirect(url_for("cs_live_chat_detail", chat_id=chat.id))


@app.route("/cs/live-chat/<int:chat_id>/catatan", methods=["POST"])
@cs_required
def cs_live_chat_catatan(chat_id):
    chat = ChatSession.query.get_or_404(chat_id)
    catatan = request.form.get("catatan", "").strip()

    if hasattr(ChatSession, "catatan_internal"):
        chat.catatan_internal = catatan
        db.session.commit()
    else:
        session[f"catatan_chat_{chat.id}"] = catatan

    flash("✅ Catatan internal berhasil disimpan.", "success")
    return redirect(url_for("cs_live_chat_detail", chat_id=chat.id))


@app.route("/cs/member/<int:user_id>")
@cs_required
def cs_member_detail(user_id):
    member = Pengguna.query.get_or_404(user_id)

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    tanggal_awal = request.args.get("tanggal_awal", "").strip()
    tanggal_akhir = request.args.get("tanggal_akhir", "").strip()
    tanggal_awal_obj, tanggal_akhir_obj, mode_filter = rentang_dari_request()

    daftar_transaksi = ambil_transaksi_member(
        member=member,
        q=q,
        status=status,
        tanggal_awal_obj=tanggal_awal_obj,
        tanggal_akhir_obj=tanggal_akhir_obj,
        limit=300
    )

    daftar_mutasi = ambil_mutasi_member(member, limit=100)

    ringkasan = ringkasan_transaksi(daftar_transaksi)
    ringkasan["total_mutasi"] = len(daftar_mutasi)

    return render_template(
        "cs_member_detail.html",
        member=member,
        daftar_transaksi=daftar_transaksi,
        daftar_mutasi=daftar_mutasi,
        ringkasan=ringkasan,
        q=q,
        status=status,
        tanggal_awal=tanggal_awal,
        tanggal_akhir=tanggal_akhir,
        mode_filter=mode_filter,
        format_uang=format_uang
    )


@app.route("/cs/transaksi")
@cs_required
def cs_transaksi():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    tanggal_awal = request.args.get("tanggal_awal", "").strip()
    tanggal_akhir = request.args.get("tanggal_akhir", "").strip()
    tanggal_awal_obj, tanggal_akhir_obj, mode_filter = rentang_dari_request()

    query = Transaksi.query

    query = filter_transaksi_query(
        query=query,
        q=q,
        status=status,
        tanggal_awal_obj=tanggal_awal_obj,
        tanggal_akhir_obj=tanggal_akhir_obj
    )

    daftar_transaksi = query.order_by(
        Transaksi.waktu.desc()
    ).limit(500).all()

    ringkasan = ringkasan_transaksi(daftar_transaksi)

    return render_template(
        "cs_transaksi.html",
        daftar_transaksi=daftar_transaksi,
        ringkasan=ringkasan,
        q=q,
        status=status,
        tanggal_awal=tanggal_awal,
        tanggal_akhir=tanggal_akhir,
        mode_filter=mode_filter,
        view_mode="member",
        format_uang=format_uang
    )


@app.route("/cs/transaksi-provider")
@cs_required
def cs_transaksi_provider():
    provider = request.args.get("provider", "").strip()
    status = request.args.get("status", "").strip()
    member = request.args.get("member", "").strip()
    kode_produk = request.args.get("kode_produk", "").strip()
    ref_id = request.args.get("ref_id", "").strip()
    tujuan = request.args.get("tujuan", "").strip()
    tanggal_awal = request.args.get("tanggal_awal", "").strip()
    tanggal_akhir = request.args.get("tanggal_akhir", "").strip()
    tanggal_awal_obj, tanggal_akhir_obj, mode_filter = rentang_dari_request()

    query = Transaksi.query
    if status:
        query = query.filter(Transaksi.status == status)
    if tanggal_awal_obj:
        query = query.filter(Transaksi.waktu >= tanggal_awal_obj)
    if tanggal_akhir_obj:
        query = query.filter(Transaksi.waktu <= tanggal_akhir_obj)
    if kode_produk:
        query = query.filter(Transaksi.jenis.ilike(f"%{kode_produk}%"))
    if tujuan:
        query = query.filter(Transaksi.nomor_tujuan.ilike(f"%{tujuan}%"))
    if ref_id:
        ref_key = ref_id.lower().replace("trx-", "")
        conditions = [Transaksi.sn.ilike(f"%{ref_id}%")]
        if ref_key.isdigit():
            conditions.append(Transaksi.id == int(ref_key))
        query = query.filter(or_(*conditions))
    if member:
        query = query.join(Pengguna, Transaksi.pengguna_id == Pengguna.id).filter(or_(
            Pengguna.nama_lengkap.ilike(f"%{member}%"),
            Pengguna.email.ilike(f"%{member}%"),
            Pengguna.nomor_hp.ilike(f"%{member}%")
        ))

    daftar_transaksi = query.order_by(Transaksi.waktu.desc()).limit(500).all()
    for transaksi in daftar_transaksi:
        transaksi.provider_label = provider_dari_produk(transaksi.jenis)

    daftar_provider = sorted({
        transaksi.provider_label for transaksi in daftar_transaksi
    })

    if provider:
        daftar_transaksi = [
            transaksi for transaksi in daftar_transaksi
            if transaksi.provider_label.lower() == provider.lower()
        ]

    return render_template(
        "cs_transaksi_provider.html",
        daftar_transaksi=daftar_transaksi,
        daftar_provider=daftar_provider,
        provider=provider,
        status=status,
        member=member,
        kode_produk=kode_produk,
        ref_id=ref_id,
        tujuan=tujuan,
        tanggal_awal=tanggal_awal,
        tanggal_akhir=tanggal_akhir,
        mode_filter=mode_filter,
        format_uang=format_uang
    )


@app.route("/cs/member")
@cs_required
def cs_member_list():
    q = request.args.get("q", "").strip()
    query = Pengguna.query

    if q:
        query = query.filter(or_(
            Pengguna.nama_lengkap.ilike(f"%{q}%"),
            Pengguna.email.ilike(f"%{q}%"),
            Pengguna.nomor_hp.ilike(f"%{q}%")
        ))

    daftar_member = query.order_by(Pengguna.id.desc()).limit(500).all()
    return render_template(
        "cs_member.html",
        daftar_member=daftar_member,
        q=q,
        total_saldo=sum(int(member.saldo or 0) for member in daftar_member),
        format_uang=format_uang
    )


@app.route("/cs/logout")
@app.route("/cs-panel/logout")
@app.route("/live-chat-panel/logout")
@cs_required
def cs_logout():
    session.pop("cs_login", None)
    session.pop("cs_username", None)

    flash("✅ Berhasil keluar dari Live Chat Panel.", "success")
    return redirect(url_for("cs_login"))


# =========================================================
# API LIVE CHAT UNTUK USER / APK
# =========================================================

@app.route("/api/chat/start", methods=["POST"])
def api_chat_start():
    data_json = request.get_json(silent=True) or {}

    nama = (
        data_json.get("nama")
        or request.form.get("nama")
        or session.get("nama")
        or "Pengguna SenjaData"
    ).strip()

    nomor_hp = (
        data_json.get("nomor_hp")
        or request.form.get("nomor_hp")
        or ""
    ).strip()

    email = (
        data_json.get("email")
        or request.form.get("email")
        or session.get("email")
        or ""
    ).strip().lower()

    pesan_awal = (
        data_json.get("pesan")
        or request.form.get("pesan")
        or ""
    ).strip()

    kode_chat = (
        data_json.get("kode_chat")
        or request.form.get("kode_chat")
        or ""
    ).strip()

    chat = None
    chat_baru = False

    if kode_chat:
        chat = ChatSession.query.filter_by(kode_chat=kode_chat).first()

    if chat and chat.status == "closed":
        chat = None

    if not chat:
        chat_baru = True

        chat = ChatSession(
            kode_chat=buat_kode_chat(),
            nama=nama or "Pengguna SenjaData",
            nomor_hp=nomor_hp,
            email=email,
            status="open",
            last_message="Selamat datang di SenjaData 👋",
            unread_admin=0,
            unread_user=0,
            diperbarui_pada=datetime.utcnow()
        )

        db.session.add(chat)
        db.session.commit()

        tambah_bot_welcome(chat)

    else:
        if nama and nama != "Pengguna SenjaData":
            chat.nama = nama

        if nomor_hp:
            chat.nomor_hp = nomor_hp

        if email:
            chat.email = email

        chat.status = "open"
        chat.diperbarui_pada = datetime.utcnow()
        db.session.commit()

        tambah_bot_welcome(chat)

    if pesan_awal:
        pesan_member = ChatMessage(
            chat_id=chat.id,
            pengirim="user",
            pesan=pesan_awal,
            dibaca_admin=False,
            dibaca_user=True
        )

        chat.last_message = pesan_awal
        chat.unread_admin = int(chat.unread_admin or 0) + 1
        chat.status = "open"
        chat.diperbarui_pada = datetime.utcnow()

        db.session.add(pesan_member)
        db.session.commit()

    pesan_chat = ChatMessage.query.filter_by(
        chat_id=chat.id
    ).order_by(ChatMessage.waktu.asc()).all()

    return jsonify({
        "success": True,
        "message": "Chat berhasil dimulai.",
        "kode_chat": chat.kode_chat,
        "chat_id": chat.id,
        "nama": chat.nama,
        "status": chat.status,
        "chat_baru": chat_baru,
        "messages": [serialize_chat_message(item) for item in pesan_chat]
    })


@app.route("/api/chat/send", methods=["POST"])
def api_chat_send():
    data_json = request.get_json(silent=True) or {}

    kode_chat = (
        data_json.get("kode_chat")
        or request.form.get("kode_chat")
        or ""
    ).strip()

    pesan = (
        data_json.get("pesan")
        or request.form.get("pesan")
        or ""
    ).strip()

    pengirim = (
        data_json.get("pengirim")
        or request.form.get("pengirim")
        or "user"
    ).strip().lower()

    if pengirim not in ["user", "admin"]:
        pengirim = "user"

    # Balasan admin dari API hanya boleh saat CS sedang login.
    # User widget tetap aman karena selalu mengirim pengirim=user.
    if pengirim == "admin" and not cs_sedang_login():
        return jsonify({
            "success": False,
            "message": "Akses admin tidak valid."
        }), 403

    if not kode_chat:
        return jsonify({
            "success": False,
            "message": "Kode chat tidak ditemukan."
        }), 400

    if not pesan:
        return jsonify({
            "success": False,
            "message": "Pesan tidak boleh kosong."
        }), 400

    chat = ChatSession.query.filter_by(kode_chat=kode_chat).first()

    if not chat:
        return jsonify({
            "success": False,
            "message": "Sesi chat tidak ditemukan."
        }), 404

    if chat.status != "open":
        return jsonify({
            "success": False,
            "message": "Chat sudah ditutup. Silakan mulai chat baru."
        }), 403

    if pengirim == "user":
        dibaca_admin = False
        dibaca_user = True
        chat.unread_admin = int(chat.unread_admin or 0) + 1
    else:
        dibaca_admin = True
        dibaca_user = False
        chat.unread_user = int(chat.unread_user or 0) + 1
        chat.unread_admin = 0

    pesan_baru = ChatMessage(
        chat_id=chat.id,
        pengirim=pengirim,
        pesan=pesan,
        dibaca_admin=dibaca_admin,
        dibaca_user=dibaca_user
    )

    chat.last_message = pesan
    chat.status = "open"
    chat.diperbarui_pada = datetime.utcnow()

    db.session.add(pesan_baru)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Pesan berhasil dikirim.",
        "kode_chat": chat.kode_chat,
        "chat_id": chat.id,
        "data": serialize_chat_message(pesan_baru)
    })


@app.route("/api/chat/messages/<kode_chat>")
def api_chat_messages(kode_chat):
    mode = request.args.get("mode", "user").strip().lower()

    chat = ChatSession.query.filter_by(kode_chat=kode_chat).first()

    if not chat:
        return jsonify({
            "success": False,
            "message": "Sesi chat tidak ditemukan.",
            "messages": []
        }), 404

    tambah_bot_welcome(chat)

    if mode == "admin":
        ChatMessage.query.filter_by(
            chat_id=chat.id,
            pengirim="user",
            dibaca_admin=False
        ).update({"dibaca_admin": True})
        chat.unread_admin = 0
    else:
        ChatMessage.query.filter_by(
            chat_id=chat.id,
            pengirim="admin",
            dibaca_user=False
        ).update({"dibaca_user": True})
        chat.unread_user = 0

    db.session.commit()

    pesan_chat = ChatMessage.query.filter_by(
        chat_id=chat.id
    ).order_by(ChatMessage.waktu.asc()).all()

    return jsonify({
        "success": True,
        "kode_chat": chat.kode_chat,
        "chat_id": chat.id,
        "nama": chat.nama,
        "status": chat.status,
        "unread_admin": int(chat.unread_admin or 0),
        "unread_user": int(chat.unread_user or 0),
        "messages": [serialize_chat_message(item) for item in pesan_chat]
    })


@app.route("/api/chat/ping/<kode_chat>")
def api_chat_ping(kode_chat):
    chat = ChatSession.query.filter_by(kode_chat=kode_chat).first()

    if not chat:
        return jsonify({
            "success": False,
            "message": "Sesi chat tidak ditemukan."
        }), 404

    return jsonify({
        "success": True,
        "kode_chat": chat.kode_chat,
        "chat_id": chat.id,
        "status": chat.status,
        "unread_user": int(chat.unread_user or 0),
        "unread_admin": int(chat.unread_admin or 0),
        "last_message": chat.last_message or ""
    })


@app.route("/api/chat/reset", methods=["POST"])
def api_chat_reset():
    return jsonify({
        "success": True,
        "message": "Reset chat diizinkan."
    })


@app.route("/api/cs/chats")
@cs_required
def api_cs_chats():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    query = ChatSession.query

    if q:
        query = query.filter(
            or_(
                ChatSession.kode_chat.ilike(f"%{q}%"),
                ChatSession.nama.ilike(f"%{q}%"),
                ChatSession.nomor_hp.ilike(f"%{q}%"),
                ChatSession.email.ilike(f"%{q}%"),
                ChatSession.last_message.ilike(f"%{q}%")
            )
        )

    if status:
        query = query.filter_by(status=status)

    daftar_chat = query.order_by(
        ChatSession.diperbarui_pada.desc()
    ).limit(200).all()

    semua_chat = ChatSession.query.all()

    return jsonify({
        "success": True,
        "ringkasan": {
            "total": len(daftar_chat),
            "open": len([x for x in semua_chat if x.status == "open"]),
            "closed": len([x for x in semua_chat if x.status == "closed"]),
            "unread": sum([int(x.unread_admin or 0) for x in semua_chat])
        },
        "chats": [
            {
                "id": item.id,
                "kode_chat": item.kode_chat,
                "nama": item.nama or "Pengguna SenjaData",
                "nomor_hp": item.nomor_hp or "",
                "email": item.email or "",
                "status": item.status or "open",
                "last_message": item.last_message or "Belum ada pesan terakhir.",
                "unread_admin": int(item.unread_admin or 0),
                "diperbarui_pada": format_waktu_chat(item.diperbarui_pada)
            }
            for item in daftar_chat
        ]
    })


# =========================================================
# DAFTAR
# =========================================================
@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    if "sudah_login" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nama_lengkap = request.form.get("nama_lengkap", "").strip()
        nomor_hp = request.form.get("nomor_hp", "").strip()
        email = request.form.get("email", "").strip().lower()
        kata_sandi = request.form.get("kata_sandi", "").strip()
        ulangi_sandi = request.form.get("ulangi_sandi", "").strip()

        if not nama_lengkap or not nomor_hp or not email or not kata_sandi or not ulangi_sandi:
            flash("⚠️ Semua kolom wajib diisi.", "danger")
            return redirect(url_for("daftar"))

        if kata_sandi != ulangi_sandi:
            flash("❌ Sandi tidak cocok.", "danger")
            return redirect(url_for("daftar"))

        if len(kata_sandi) < 6:
            flash("❌ Sandi minimal 6 karakter.", "danger")
            return redirect(url_for("daftar"))

        if Pengguna.query.filter_by(email=email).first():
            flash("❌ Email sudah terdaftar.", "danger")
            return redirect(url_for("daftar"))

        if Pengguna.query.filter_by(nomor_hp=nomor_hp).first():
            flash("❌ Nomor HP sudah terdaftar.", "danger")
            return redirect(url_for("daftar"))

        pengguna_baru = Pengguna(
            nama_lengkap=nama_lengkap,
            nomor_hp=nomor_hp,
            email=email,
            kata_sandi=generate_password_hash(kata_sandi, method="pbkdf2:sha256"),
            saldo=0
        )

        db.session.add(pengguna_baru)
        db.session.commit()

        flash("✅ Akun berhasil dibuat, silakan masuk.", "success")
        return redirect(url_for("login"))

    return render_template("daftar.html")


# =========================================================
# LOGIN
# =========================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if "sudah_login" in session:
        if user_master():
            return redirect(url_for("dashboard"))
        if user_admin():
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identitas = request.form.get("identitas", "").strip().lower()
        kata_sandi = request.form.get("kata_sandi", "").strip()

        akun_admin = validasi_login_admin(identitas, kata_sandi)
        if akun_admin:
            if akun_admin["level"] == "master":
                if masuk_sebagai_master(akun_admin):
                    flash("Berhasil masuk ke akun Master.", "success")
                    return redirect(url_for("dashboard"))
                flash("Data akun Master belum tersedia.", "danger")
                return redirect(url_for("login"))
            masuk_sebagai_admin(akun_admin)
            flash("Berhasil masuk sebagai Admin.", "success")
            return redirect(url_for("admin_dashboard"))

        pengguna = Pengguna.query.filter(
            (Pengguna.email == identitas) | (Pengguna.nomor_hp == identitas)
        ).first()

        if pengguna and check_password_hash(pengguna.kata_sandi, kata_sandi):
            session["sudah_login"] = True
            session["email"] = pengguna.email
            session["nama"] = pengguna.nama_lengkap
            session["peran"] = "pengguna"
            flash(f"✅ Selamat datang, {pengguna.nama_lengkap}.", "success")
            return redirect(url_for("dashboard"))

        flash("❌ Nomor HP/Email atau kata sandi salah.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================
@app.route("/logout")
def logout():
    session.clear()
    flash("ℹ️ Anda telah keluar dari akun.", "info")
    return redirect(url_for("login"))


# =========================================================
# PROFIL
# =========================================================
@app.route("/profil")
def profil():
    login_check = wajib_login()
    if login_check:
        return login_check

    if user_admin():
        flash("ℹ️ Admin tidak memiliki profil saldo pengguna.", "info")
        return redirect(url_for("admin_dashboard"))

    pengguna = ambil_pengguna_login()

    if not pengguna:
        session.clear()
        flash("❌ Data akun tidak ditemukan, silakan masuk ulang.", "danger")
        return redirect(url_for("login"))

    ringkasan_master = None
    if user_master():
        transaksi_master = Transaksi.query.filter_by(pengguna_id=pengguna.id)
        ringkasan_master = {
            "total_transaksi": transaksi_master.count(),
            "transaksi_berhasil": transaksi_master.filter_by(status="Berhasil").count(),
            "total_mutasi": MutasiSaldo.query.filter_by(email=pengguna.email).count(),
            "saldo_retail": int(pengguna.saldo_retail or 0),
            "fee_retail": int(pengguna.fee_retail or 0),
            "total_jaringan": JaringanRetail.query.filter_by(master_id=pengguna.id).count()
        }

    return render_template(
        "profil.html",
        pengguna=pengguna,
        is_master=user_master(),
        ringkasan_master=ringkasan_master,
        mutasi_master=(MutasiSaldo.query.filter_by(email=pengguna.email).order_by(MutasiSaldo.waktu.desc()).limit(5).all() if user_master() else []),
        jaringan_master=(JaringanRetail.query.filter_by(master_id=pengguna.id).order_by(JaringanRetail.id.desc()).limit(6).all() if user_master() else []),
        format_uang=format_uang
    )


@app.route("/master/saldo-retail", methods=["POST"])
def master_saldo_retail():
    if not user_sedang_login() or not user_master():
        flash("Fitur ini khusus akun Master.", "warning")
        return redirect(url_for("login"))

    pengguna = ambil_pengguna_login()
    nominal = request.form.get("nominal", type=int)

    if not pengguna or not nominal or nominal < 10000:
        flash("Minimal pemindahan saldo retail Rp 10.000.", "warning")
        return redirect(url_for("profil"))

    if int(pengguna.saldo or 0) < nominal:
        flash("Saldo utama tidak cukup untuk dipindahkan ke saldo retail.", "danger")
        return redirect(url_for("profil"))

    pengguna.saldo = int(pengguna.saldo or 0) - nominal
    pengguna.saldo_retail = int(pengguna.saldo_retail or 0) + nominal
    db.session.add(MutasiSaldo(
        email=pengguna.email,
        jenis="Keluar",
        nominal=nominal,
        keterangan="Pemindahan saldo utama ke saldo retail"
    ))
    db.session.commit()

    flash(f"Berhasil memindahkan {format_flash_nominal(nominal)} ke saldo retail.", "success")
    return redirect(url_for("profil"))


@app.route("/master/withdraw-fee", methods=["POST"])
def master_withdraw_fee():
    if not user_sedang_login() or not user_master():
        flash("Fitur ini khusus akun Master.", "warning")
        return redirect(url_for("login"))

    pengguna = ambil_pengguna_login()
    nominal = request.form.get("nominal", type=int)
    if not pengguna or not nominal or nominal < 10000:
        flash("Minimal withdraw fee Rp 10.000.", "warning")
        return redirect(url_for("profil"))
    if int(pengguna.fee_retail or 0) < nominal:
        flash("Fee retail belum cukup untuk ditarik.", "danger")
        return redirect(url_for("profil"))

    pengguna.fee_retail = int(pengguna.fee_retail or 0) - nominal
    pengguna.saldo = int(pengguna.saldo or 0) + nominal
    db.session.add(MutasiSaldo(email=pengguna.email, jenis="Masuk", nominal=nominal, keterangan="Withdraw fee retail ke saldo utama"))
    db.session.commit()
    flash(f"Withdraw fee {format_flash_nominal(nominal)} berhasil masuk ke saldo utama.", "success")
    return redirect(url_for("profil"))


@app.route("/master/jaringan-retail", methods=["POST"])
def master_tambah_jaringan():
    if not user_sedang_login() or not user_master():
        flash("Fitur ini khusus akun Master.", "warning")
        return redirect(url_for("login"))

    pengguna = ambil_pengguna_login()
    nama = request.form.get("nama", "").strip()
    nomor_hp = request.form.get("nomor_hp", "").strip()
    if not pengguna or len(nama) < 2 or len(nomor_hp) < 8:
        flash("Lengkapi nama dan nomor HP jaringan retail.", "warning")
        return redirect(url_for("profil"))

    db.session.add(JaringanRetail(master_id=pengguna.id, nama=nama, nomor_hp=nomor_hp, status="Aktif"))
    db.session.commit()
    flash(f"Jaringan retail {nama} berhasil ditambahkan.", "success")
    return redirect(url_for("profil"))


# =========================================================
# TOP UP SALDO
# =========================================================
@app.route("/topup-saldo", methods=["GET", "POST"])
@app.route("/topup_saldo", methods=["GET", "POST"])
def topup_saldo():
    login_check = wajib_login()
    if login_check:
        return login_check

    if user_admin():
        flash("⚠️ Admin tidak bisa melakukan top up saldo pengguna.", "warning")
        return redirect(url_for("admin_dashboard"))

    pengguna = ambil_pengguna_login()

    if not pengguna:
        session.clear()
        flash("❌ Data akun tidak ditemukan, silakan masuk ulang.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        nominal = request.form.get("nominal", type=int)
        metode = request.form.get("metode", "").strip()

        if not nominal or nominal < 10000:
            flash("❌ Minimal isi saldo Rp 10.000.", "danger")
            return redirect(url_for("topup_saldo"))

        if not metode:
            flash("⚠️ Pilih metode pembayaran terlebih dahulu.", "warning")
            return redirect(url_for("topup_saldo"))

        pengguna.saldo = int(pengguna.saldo or 0) + int(nominal)

        mutasi = MutasiSaldo(
            email=pengguna.email,
            jenis="Masuk",
            nominal=nominal,
            keterangan=f"Top Up Saldo via {metode}"
        )

        db.session.add(mutasi)
        db.session.commit()

        flash(f"✅ Berhasil menambah saldo sebesar {format_flash_nominal(nominal)}.", "success")
        return redirect(url_for("profil"))

    return render_template("topup_saldo.html", pengguna=pengguna, format_uang=format_uang)


# =========================================================
# MUTASI SALDO
# =========================================================
@app.route("/mutasi-saldo")
@app.route("/mutasi_saldo")
def mutasi_saldo():
    login_check = wajib_login()
    if login_check:
        return login_check

    if user_admin():
        daftar_mutasi = MutasiSaldo.query.order_by(MutasiSaldo.waktu.desc()).all()
    else:
        daftar_mutasi = MutasiSaldo.query.filter_by(email=session.get("email")).order_by(MutasiSaldo.waktu.desc()).all()

    return render_template("mutasi_saldo.html", daftar=daftar_mutasi, format_uang=format_uang)


# =========================================================
# DASHBOARD
# =========================================================
@app.route("/dashboard")
def dashboard():
    if "sudah_login" not in session:
        saldo = "Rp 0"
        total_laba = "Rp 0"
        transaksi_terakhir = Transaksi.query.filter_by(status="Berhasil").order_by(Transaksi.waktu.desc()).limit(5).all()
    else:
        pengguna = ambil_pengguna_login()

        if pengguna:
            saldo = format_uang(pengguna.saldo or 0)
        else:
            saldo = "Admin"

        total_laba = format_uang(
            db.session.query(func.sum(Transaksi.laba)).filter_by(status="Berhasil").scalar() or 0
        )

        transaksi_terakhir = Transaksi.query.order_by(Transaksi.waktu.desc()).limit(5).all()

    jumlah_transaksi = Transaksi.query.filter_by(status="Berhasil").count()

    return render_template(
        "dashboard.html",
        saldo=saldo,
        total_laba=total_laba,
        jumlah_transaksi=jumlah_transaksi,
        transaksi_terakhir=transaksi_terakhir,
        format_uang=format_uang
    )


# =========================================================
# PROSES BELI UMUM
# =========================================================
def proses_pembelian_umum(kode, tujuan, endpoint_redirect):
    if "sudah_login" not in session:
        flash("⚠️ Masuk dulu untuk bertransaksi.", "warning")
        return redirect(url_for("login"))

    if user_admin():
        flash("⚠️ Admin tidak bisa melakukan transaksi pembelian.", "warning")
        return redirect(url_for(endpoint_redirect))

    if not kode or not tujuan:
        flash("⚠️ Lengkapi semua data.", "danger")
        return redirect(url_for(endpoint_redirect))

    hasil = proses_beli(kode, tujuan, session.get("email"))

    if hasil.get("status") in ["sukses", "berhasil"]:
        flash(f"✅ Berhasil! Ref/SN: {hasil.get('sn', '-')}", "success")
    else:
        flash(f"❌ Gagal: {hasil.get('pesan', 'Terjadi kesalahan')}", "danger")

    return redirect(url_for(endpoint_redirect))


# =========================================================
# PULSA
# =========================================================
@app.route("/pulsa", methods=["GET", "POST"])
def pulsa():
    if request.method == "POST":
        kode = request.form.get("kode_produk", "").strip()
        tujuan = request.form.get("nomor_tujuan", "").strip()
        return proses_pembelian_umum(kode, tujuan, "pulsa")

    daftar = ambil_daftar_produk(("TLK_", "ISAT_", "XL_", "TRI_", "AXIS_", "SMART_"))
    return render_template("pulsa.html", daftar_produk=daftar, harga=HARGA_JUAL, format_uang=format_uang)


# =========================================================
# DATA
# =========================================================
@app.route("/data", methods=["GET", "POST"])
def data():
    if request.method == "POST":
        kode = request.form.get("kode_produk", "").strip()
        tujuan = request.form.get("nomor_tujuan", "").strip()
        return proses_pembelian_umum(kode, tujuan, "data")

    daftar = ambil_daftar_produk(("DATA_",))
    return render_template("data.html", daftar_produk=daftar, harga=HARGA_JUAL, format_uang=format_uang)


# =========================================================
# EWALLET
# =========================================================
@app.route("/ewallet", methods=["GET", "POST"])
def ewallet():
    if request.method == "POST":
        kode = request.form.get("kode_produk", "").strip()
        tujuan = request.form.get("nomor_tujuan", "").strip()
        return proses_pembelian_umum(kode, tujuan, "ewallet")

    daftar = ambil_daftar_produk(("DANA_", "GOPAY_", "OVO_", "LINKAJA_", "SHOPEEPAY_"))
    return render_template("ewallet.html", daftar_produk=daftar, harga=HARGA_JUAL, format_uang=format_uang)


# =========================================================
# LISTRIK
# =========================================================
@app.route("/listrik", methods=["GET", "POST"])
def listrik():
    if request.method == "POST":
        kode = request.form.get("kode_produk", "").strip()
        tujuan = request.form.get("nomor_tujuan", "").strip()
        return proses_pembelian_umum(kode, tujuan, "listrik")

    daftar = ambil_daftar_produk(("PLN_",))
    return render_template("listrik.html", daftar_produk=daftar, harga=HARGA_JUAL, format_uang=format_uang)


# =========================================================
# KATEGORI LAINNYA
# =========================================================
KATEGORI_LAINNYA = {
    "tv": {
        "endpoint": "tv",
        "template": "tv.html",
        "prefix": ("TV_",),
        "nama": "TV Kabel"
    },
    "game": {
        "endpoint": "game",
        "template": "game.html",
        "prefix": ("GAME_",),
        "nama": "Game"
    },
    "pdam": {
        "endpoint": "pdam",
        "template": "pdam.html",
        "prefix": ("PDAM_",),
        "nama": "PDAM"
    },
    "bpjs": {
        "endpoint": "bpjs",
        "template": "bpjs.html",
        "prefix": ("BPJS_",),
        "nama": "BPJS"
    },
    "internet_pasca": {
        "endpoint": "internet",
        "template": "internet.html",
        "prefix": ("INTERNET_", "INET_"),
        "nama": "Internet"
    },
    "masa_aktif": {
        "endpoint": "masa_aktif",
        "template": "masa_aktif.html",
        "prefix": ("MASA_AKTIF_", "AKTIF_"),
        "nama": "Masa Aktif"
    },
    "paket_telp": {
        "endpoint": "paket_telp",
        "template": "paket_telp.html",
        "prefix": ("PAKET_TELP_", "TELP_"),
        "nama": "Paket Telp"
    },
    "aktivasi": {
        "endpoint": "aktivasi",
        "template": "aktivasi.html",
        "prefix": ("AKTIVASI_",),
        "nama": "Aktivasi"
    },
    "gas": {
        "endpoint": "gas",
        "template": "gas.html",
        "prefix": ("GAS_",),
        "nama": "Gas Negara"
    },
    "angsuran": {
        "endpoint": "angsuran",
        "template": "angsuran.html",
        "prefix": ("ANGSURAN_", "FIN_"),
        "nama": "Angsuran"
    },
    "pbb": {
        "endpoint": "pbb",
        "template": "pbb.html",
        "prefix": ("PBB_",),
        "nama": "Pajak PBB"
    },
    "asuransi": {
        "endpoint": "asuransi",
        "template": "asuransi.html",
        "prefix": ("ASURANSI_", "ASR_"),
        "nama": "Asuransi"
    },
    "voucher": {
        "endpoint": "voucher",
        "template": "voucher.html",
        "prefix": ("VOUCHER_", "VCR_"),
        "nama": "Voucher"
    },
    "zakat": {
        "endpoint": "zakat",
        "template": "zakat.html",
        "prefix": ("ZAKAT_",),
        "nama": "Zakat & Infaq"
    },
    "pln_pasca": {
        "endpoint": "pln_pasca",
        "template": "pln_pasca.html",
        "prefix": ("PLN_PASCA_", "PLN_NON_TAGLIS", "PLN_INSTALLASI", "PLN_TAMBAH_DAYA"),
        "nama": "PLN Pasca"
    },
    "tiket": {
        "endpoint": "tiket",
        "template": "tiket.html",
        "prefix": ("TIKET_",),
        "nama": "Tiket"
    }
}


def ambil_produk_lainnya(jenis):
    data = KATEGORI_LAINNYA.get(jenis)

    if not data:
        return {}

    return {
        kode: nama
        for kode, nama in NAMA_PRODUK.items()
        if kode.startswith(data["prefix"])
    }


def deteksi_jenis_dari_kode(kode_produk):
    if not kode_produk:
        return ""

    for jenis, data in KATEGORI_LAINNYA.items():
        if kode_produk.startswith(data["prefix"]):
            return jenis

    return ""


def proses_post_layanan(jenis, endpoint_redirect):
    kode = request.form.get("kode_produk", "").strip()
    tujuan = request.form.get("nomor_tujuan", "").strip()

    if not jenis:
        jenis = request.form.get("jenis", "").strip()

    if not jenis:
        jenis = deteksi_jenis_dari_kode(kode)

    return proses_pembelian_umum(kode, tujuan, endpoint_redirect)


def tampilkan_halaman_layanan(jenis):
    data = KATEGORI_LAINNYA.get(jenis)

    if not data:
        flash("⚠️ Kategori layanan tidak ditemukan.", "warning")
        return redirect(url_for("lainnya"))

    if request.method == "POST":
        return proses_post_layanan(jenis, data["endpoint"])

    daftar = ambil_produk_lainnya(jenis)

    return render_template(
        data["template"],
        daftar_produk=daftar,
        harga=HARGA_JUAL,
        format_uang=format_uang
    )


# =========================================================
# LAINNYA
# =========================================================
@app.route("/lainnya", methods=["GET", "POST"])
def lainnya():
    if request.method == "POST":
        jenis = request.form.get("jenis", "").strip()
        kode = request.form.get("kode_produk", "").strip()

        if not jenis:
            jenis = deteksi_jenis_dari_kode(kode)

        data = KATEGORI_LAINNYA.get(jenis)

        if data:
            return proses_post_layanan(jenis, data["endpoint"])

        flash("⚠️ Pilih kategori layanan terlebih dahulu.", "danger")
        return redirect(url_for("lainnya"))

    jenis = request.args.get("jenis", "").strip()

    if jenis in KATEGORI_LAINNYA:
        return redirect(url_for(KATEGORI_LAINNYA[jenis]["endpoint"]))

    return render_template("lainnya.html", format_uang=format_uang)


# =========================================================
# ROUTE KATEGORI SENDIRI
# =========================================================
@app.route("/tv", methods=["GET", "POST"])
@app.route("/tv/", methods=["GET", "POST"])
def tv():
    return tampilkan_halaman_layanan("tv")


@app.route("/game", methods=["GET", "POST"])
@app.route("/game/", methods=["GET", "POST"])
def game():
    return tampilkan_halaman_layanan("game")


@app.route("/pdam", methods=["GET", "POST"])
@app.route("/pdam/", methods=["GET", "POST"])
def pdam():
    return tampilkan_halaman_layanan("pdam")


@app.route("/bpjs", methods=["GET", "POST"])
@app.route("/bpjs/", methods=["GET", "POST"])
def bpjs():
    return tampilkan_halaman_layanan("bpjs")


@app.route("/internet", methods=["GET", "POST"])
@app.route("/internet/", methods=["GET", "POST"])
def internet():
    return tampilkan_halaman_layanan("internet_pasca")


@app.route("/masa-aktif", methods=["GET", "POST"])
@app.route("/masa-aktif/", methods=["GET", "POST"])
def masa_aktif():
    return tampilkan_halaman_layanan("masa_aktif")


@app.route("/paket-telp", methods=["GET", "POST"])
@app.route("/paket-telp/", methods=["GET", "POST"])
def paket_telp():
    return tampilkan_halaman_layanan("paket_telp")


@app.route("/aktivasi", methods=["GET", "POST"])
@app.route("/aktivasi/", methods=["GET", "POST"])
def aktivasi():
    return tampilkan_halaman_layanan("aktivasi")


@app.route("/gas", methods=["GET", "POST"])
@app.route("/gas/", methods=["GET", "POST"])
def gas():
    return tampilkan_halaman_layanan("gas")


@app.route("/angsuran", methods=["GET", "POST"])
@app.route("/angsuran/", methods=["GET", "POST"])
def angsuran():
    return tampilkan_halaman_layanan("angsuran")


@app.route("/pbb", methods=["GET", "POST"])
@app.route("/pbb/", methods=["GET", "POST"])
def pbb():
    return tampilkan_halaman_layanan("pbb")


@app.route("/asuransi", methods=["GET", "POST"])
@app.route("/asuransi/", methods=["GET", "POST"])
def asuransi():
    return tampilkan_halaman_layanan("asuransi")


@app.route("/voucher", methods=["GET", "POST"])
@app.route("/voucher/", methods=["GET", "POST"])
def voucher():
    return tampilkan_halaman_layanan("voucher")


@app.route("/zakat", methods=["GET", "POST"])
@app.route("/zakat/", methods=["GET", "POST"])
def zakat():
    return tampilkan_halaman_layanan("zakat")


@app.route("/pln-pasca", methods=["GET", "POST"])
@app.route("/pln-pasca/", methods=["GET", "POST"])
def pln_pasca():
    return tampilkan_halaman_layanan("pln_pasca")


@app.route("/tiket", methods=["GET", "POST"])
@app.route("/tiket/", methods=["GET", "POST"])
def tiket():
    return tampilkan_halaman_layanan("tiket")


# =========================================================
# RIWAYAT TRANSAKSI
# =========================================================
@app.route("/riwayat")
def riwayat():
    if "sudah_login" in session and not user_admin():
        pengguna = ambil_pengguna_login()

        if pengguna and hasattr(Transaksi, "pengguna_id"):
            daftar = Transaksi.query.filter_by(pengguna_id=pengguna.id).order_by(Transaksi.waktu.desc()).all()
        elif hasattr(Transaksi, "email"):
            daftar = Transaksi.query.filter_by(email=session.get("email")).order_by(Transaksi.waktu.desc()).all()
        else:
            daftar = Transaksi.query.order_by(Transaksi.waktu.desc()).limit(50).all()
    else:
        daftar = Transaksi.query.order_by(Transaksi.waktu.desc()).limit(100).all()

    return render_template("riwayat.html", daftar=daftar, format_uang=format_uang)


# =========================================================
# DAFTAR PRODUK
# =========================================================
@app.route("/produk")
def produk():
    daftar = [
        {
            "kode": kode,
            "nama": nama,
            "harga": HARGA_JUAL.get(kode, 0)
        }
        for kode, nama in NAMA_PRODUK.items()
    ]

    return render_template("produk.html", daftar=daftar, format_uang=format_uang)


# =========================================================
# RUN APP
# =========================================================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
