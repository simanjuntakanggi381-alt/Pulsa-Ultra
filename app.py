from flask import Flask, render_template, request, redirect, url_for, flash, session
from config import (
    SECRET_KEY,
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    NAMA_PRODUK,
    HARGA_JUAL,
    BATAS_SALDO_INGAT,
    AKUN_ADMIN
)
from models import db, Transaksi, Pengguna, MutasiSaldo
from transaksi import cek_saldo, proses_beli
from utils import format_uang
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import os


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
            return redirect(url_for("admin_login"))
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
        "admin_produk"
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
# ADMIN PANEL SENJADATA - FIX + MODERN
# =========================================================
# Login default admin panel:
# Username : admin
# Password : admin12345
#
# Bisa juga login pakai AKUN_ADMIN dari config.py:
# AKUN_ADMIN["email"] / AKUN_ADMIN["password"]
# =========================================================

ADMIN_PANEL_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin12345")


def validasi_login_admin(username, password):
    """
    Validasi login admin dibuat fleksibel:
    1. admin / admin12345
    2. ENV ADMIN_USERNAME / ADMIN_PASSWORD
    3. config.py AKUN_ADMIN["email"] / AKUN_ADMIN["password"]
    """

    username = (username or "").strip()
    password = (password or "").strip()

    username_lower = username.lower()
    env_username = str(ADMIN_PANEL_USERNAME or "admin").strip().lower()
    env_password = str(ADMIN_PANEL_PASSWORD or "admin12345").strip()

    # Login default supaya pasti bisa masuk
    if username_lower == "admin" and password == "admin12345":
        return True

    # Login dari environment variable
    if username_lower == env_username and password == env_password:
        return True

    # Login dari config.py
    try:
        admin_email_config = str(AKUN_ADMIN.get("email", "")).strip().lower()
        admin_password_config = str(AKUN_ADMIN.get("password", "")).strip()

        if username_lower == admin_email_config and password == admin_password_config:
            return True
    except Exception:
        pass

    return False


@app.route("/admin")
@app.route("/panel")
@app.route("/admin-panel")
def admin_index():
    if user_sedang_login() and user_admin():
        return redirect(url_for("admin_dashboard"))

    return redirect(url_for("admin_login"))


@app.route("/admin/login", methods=["GET", "POST"])
@app.route("/admin-login", methods=["GET", "POST"])
@app.route("/panel/login", methods=["GET", "POST"])
def admin_login():
    # Kalau sudah login sebagai admin, langsung masuk dashboard admin
    if user_sedang_login() and user_admin():
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        # Dibuat fleksibel supaya cocok dengan berbagai nama input form
        username = (
            request.form.get("username")
            or request.form.get("identitas")
            or request.form.get("email")
            or request.form.get("admin_username")
            or ""
        ).strip()

        password = (
            request.form.get("password")
            or request.form.get("kata_sandi")
            or request.form.get("admin_password")
            or ""
        ).strip()

        if validasi_login_admin(username, password):
            session.clear()
            session["sudah_login"] = True
            session["email"] = username
            session["nama"] = "Admin"
            session["peran"] = "admin"

            flash("✅ Berhasil masuk ke panel admin.", "success")
            return redirect(url_for("admin_dashboard"))

        flash("❌ Username atau password admin salah. Coba pakai admin / admin12345.", "danger")
        return redirect(url_for("admin_login"))

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
@app.route("/panel/dashboard")
@wajib_admin
def admin_dashboard():
    total_pengguna = Pengguna.query.count()
    total_produk = len(NAMA_PRODUK)
    total_transaksi = Transaksi.query.count()

    transaksi_sukses = Transaksi.query.filter_by(status="Berhasil").count()
    transaksi_pending = Transaksi.query.filter_by(status="Pending").count()
    transaksi_gagal = Transaksi.query.filter_by(status="Gagal").count()

    total_laba = db.session.query(func.sum(Transaksi.laba)).filter_by(status="Berhasil").scalar() or 0

    transaksi_terbaru = Transaksi.query.order_by(Transaksi.waktu.desc()).limit(8).all()
    pengguna_terbaru = Pengguna.query.order_by(Pengguna.id.desc()).limit(6).all()

    statistik = {
        "total_pengguna": total_pengguna,
        "total_produk": total_produk,
        "total_transaksi": total_transaksi,
        "transaksi_sukses": transaksi_sukses,
        "transaksi_pending": transaksi_pending,
        "transaksi_gagal": transaksi_gagal,
        "total_laba": total_laba
    }

    return render_template(
        "admin_dashboard.html",
        statistik=statistik,
        transaksi_terbaru=transaksi_terbaru,
        pengguna_terbaru=pengguna_terbaru,
        admin_username=session.get("nama", "Admin"),
        format_uang=format_uang
    )


@app.route("/admin/transaksi")
@app.route("/panel/transaksi")
@wajib_admin
def admin_transaksi():
    daftar = Transaksi.query.order_by(Transaksi.waktu.desc()).limit(200).all()

    return render_template(
        "admin_transaksi.html",
        daftar=daftar,
        format_uang=format_uang
    )


@app.route("/admin/pengguna")
@app.route("/panel/pengguna")
@wajib_admin
def admin_pengguna():
    daftar = Pengguna.query.order_by(Pengguna.id.desc()).all()

    return render_template(
        "admin_pengguna.html",
        daftar=daftar,
        format_uang=format_uang
    )


@app.route("/admin/produk")
@app.route("/panel/produk")
@wajib_admin
def admin_produk():
    daftar = [
        {
            "kode": kode,
            "nama": nama,
            "harga": HARGA_JUAL.get(kode, 0)
        }
        for kode, nama in NAMA_PRODUK.items()
    ]

    return render_template(
        "admin_produk.html",
        daftar=daftar,
        format_uang=format_uang
    )


@app.route("/admin/logout")
@app.route("/admin/keluar")
@app.route("/panel/logout")
def admin_logout():
    session.clear()
    flash("✅ Berhasil keluar dari panel admin.", "success")
    return redirect(url_for("admin_login"))


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
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identitas = request.form.get("identitas", "").strip().lower()
        kata_sandi = request.form.get("kata_sandi", "").strip()

        if identitas == AKUN_ADMIN["email"] and kata_sandi == AKUN_ADMIN["password"]:
            session["sudah_login"] = True
            session["email"] = identitas
            session["nama"] = "Admin"
            session["peran"] = "admin"
            flash("✅ Berhasil masuk sebagai Admin.", "success")
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

    return render_template("profil.html", pengguna=pengguna, format_uang=format_uang)


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