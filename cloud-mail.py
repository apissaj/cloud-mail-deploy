#!/usr/bin/env python3
"""
cloud-mail CLI — automation untuk platform email Cloudflare Workers (cloud-mail).

Fitur:
  daftar   <email1> [email2 ...]   Daftarkan akun email (batch, tanpa token)
  token    <password>              Dapatkan token akses public (login admin)
  inbox    <email> [--size N]      Lihat email masuk (butuh token)
  otp      <email> [--size N]      Lihat email + kode OTP hasil AI (butuh token)
  poll     <email> --wait S        Polling email masuk tiap S detik (butuh token)

Contoh:
  python cloud-mail.py daftar maulana.zikri1908@hafizhmuzani.my.id
  python cloud-mail.py token 'password-admin'
  python cloud-mail.py inbox maulana.zikri1908@hafizhmuzani.my.id
  python cloud-mail.py otp maulana.zikri1908@hafizhmuzani.my.id
  python cloud-mail.py poll maulana.zikri1908@hafizhmuzani.my.id --wait 5
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

# ============================================================
# KONFIGURASI — sesuaikan dengan deployment kamu
# ============================================================
BASE_URL = os.environ.get("CLOUD_MAIL_URL", "https://mail.hafizhmuzani.my.id")
ADMIN_EMAIL = os.environ.get("CLOUD_MAIL_ADMIN", "admin@hafizhmuzani.my.id")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cloud-mail-token")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


def api(method, path, body=None, token=None):
    """Panggil API cloud-mail. Return parsed JSON."""
    url = BASE_URL + path
    headers = {"User-Agent": UA, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"code": e.code, "message": str(e)}


def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    return None


def save_token(token):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)
    os.chmod(TOKEN_FILE, 0o600)


# ============================================================
# Perintah
# ============================================================

def _ok(res):
    """Cek apakah response sukses (code 200 / message success)."""
    return res.get("code") in (0, 200) or res.get("message") == "success"


def cmd_daftar(args):
    """Daftarkan satu atau banyak akun email (batch, butuh token)."""
    token = _get_token()
    if not args.emails:
        print("❌ Minimal 1 email. Contoh: python cloud-mail.py daftar a@domain.com b@domain.com")
        sys.exit(1)
    payload = {"list": [{"email": e} for e in args.emails]}
    res = api("POST", "/api/public/addUser", payload, token=token)
    if _ok(res):
        print(f"✅ {len(args.emails)} akun didaftarkan:")
        for e in args.emails:
            print(f"   • {e}")
    else:
        print(f"❌ Gagal: {res.get('message')}")
        sys.exit(1)


def cmd_token(args):
    """Dapatkan token akses public (login admin)."""
    res = api("POST", "/api/public/genToken", {"email": ADMIN_EMAIL, "password": args.password})
    if _ok(res):
        token = res["data"]["token"]
        save_token(token)
        print(f"✅ Token tersimpan di {TOKEN_FILE}")
    else:
        print(f"❌ Gagal: {res.get('message')}")
        sys.exit(1)


def _get_token():
    token = load_token()
    if not token:
        print("❌ Token belum ada. Jalankan dulu: python cloud-mail.py token '<password-admin>'")
        sys.exit(1)
    return token


def _email_list(email, size, token):
    res = api("POST", "/api/public/emailList", {"toEmail": email, "size": size}, token=token)
    if not _ok(res):
        print(f"❌ Gagal query: {res.get('message')}")
        sys.exit(1)
    return res.get("data") or []


def _print_email(row):
    print(f"  [{row.get('emailId')}] {row.get('createTime')}")
    print(f"      Dari   : {row.get('sendEmail')} ({row.get('sendName')})")
    print(f"      Subjek : {row.get('subject')}")
    code = row.get('code')
    if code:
        print(f"      🔑 KODE : {code}")
    text = (row.get('text') or row.get('content') or '')[:200]
    if text:
        print(f"      Isi    : {text.replace(chr(10), ' ')}")


def cmd_inbox(args):
    """Lihat email masuk (butuh token)."""
    token = _get_token()
    rows = _email_list(args.email, args.size, token)
    if not rows:
        print(f"📭 Tidak ada email untuk {args.email}")
        return
    print(f"📥 {len(rows)} email untuk {args.email}:")
    for row in rows:
        _print_email(row)


def cmd_otp(args):
    """Lihat email + kode OTP hasil AI (butuh token)."""
    token = _get_token()
    rows = _email_list(args.email, args.size, token)
    if not rows:
        print(f"📭 Tidak ada email untuk {args.email}")
        return
    print(f"🔑 {len(rows)} email untuk {args.email}:")
    found = False
    for row in rows:
        _print_email(row)
        if row.get('code'):
            found = True
    if not found:
        print("⚠️ Belum ada kode OTP di email terbaru (mungkin email bukan OTP atau AI belum memproses).")


def cmd_poll(args):
    """Polling email masuk tiap --wait detik (butuh token)."""
    token = _get_token()
    seen = set()
    print(f"👀 Polling email untuk {args.email} tiap {args.wait} detik... (Ctrl+C untuk stop)")
    try:
        while True:
            rows = _email_list(args.email, args.size, token)
            for row in rows:
                eid = row.get("emailId")
                if eid not in seen:
                    seen.add(eid)
                    print(f"\n📨 EMAIL BARU #{eid} — {row.get('createTime')}")
                    _print_email(row)
            time.sleep(args.wait)
    except KeyboardInterrupt:
        print("\n⏹️  Polling dihentikan.")


def main():
    parser = argparse.ArgumentParser(description="Cloud Mail CLI — automation email domain sendiri")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_daftar = sub.add_parser("daftar", help="Daftarkan akun email (batch)")
    p_daftar.add_argument("emails", nargs="+", help="Email yang didaftarkan")

    p_token = sub.add_parser("token", help="Dapatkan token akses public (login admin)")
    p_token.add_argument("password", help="Password akun admin")

    p_inbox = sub.add_parser("inbox", help="Lihat email masuk")
    p_inbox.add_argument("email", help="Alamat email yang dicek")
    p_inbox.add_argument("--size", type=int, default=10, help="Jumlah email (default 10)")

    p_otp = sub.add_parser("otp", help="Lihat email + kode OTP")
    p_otp.add_argument("email", help="Alamat email yang dicek")
    p_otp.add_argument("--size", type=int, default=10, help="Jumlah email (default 10)")

    p_poll = sub.add_parser("poll", help="Polling email masuk")
    p_poll.add_argument("email", help="Alamat email yang dicek")
    p_poll.add_argument("--wait", type=int, default=5, help="Interval detik (default 5)")
    p_poll.add_argument("--size", type=int, default=10, help="Jumlah email per query (default 10)")

    args = parser.parse_args()
    {
        "daftar": cmd_daftar,
        "token": cmd_token,
        "inbox": cmd_inbox,
        "otp": cmd_otp,
        "poll": cmd_poll,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
