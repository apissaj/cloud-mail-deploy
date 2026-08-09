# ☁️ Cloud Mail Deploy

Deployment siap-pakai dari **[maillab/cloud-mail](https://github.com/maillab/cloud-mail)** — platform email lengkap di Cloudflare Workers, dengan domain sendiri.

> **Apa bedanya dengan tempmail biasa?** Ini bukan sekadar API JSON — ada UI web ala Gmail (Vue 3), kirim & terima email dengan domain sendiri, admin panel, forward Telegram, dan **AI otomatis ekstrak kode OTP** dari email masuk.

## ✨ Fitur

| Fitur | Keterangan |
|---|---|
| 📬 **Terima email** | Catch-all Email Routing → worker → D1, langsung muncul di inbox |
| 📤 **Kirim email** | Via [Resend](https://resend.com) (free tier 3.000/bulan, tanpa kartu kredit) |
| 🧠 **AI ekstrak OTP** | Workers AI otomatis baca kode verifikasi dari email masuk, simpan di kolom `code` |
| 🖥️ **UI web** | Vue 3 ala Gmail — login, compose, inbox, settings (dark/light) |
| 👑 **Admin panel** | Kelola user, role, settings global (terpisah dari akun biasa) |
| 📎 **Attachment** | Storage fallback: S3 → R2 → KV (tanpa R2 tetap jalan) |
| 🤖 **Forward Telegram** | Email masuk bisa di-forward ke bot Telegram |
| 🔌 **Public API** | Batch generate user + query email (untuk automation) |

## 🏗️ Arsitektur

```
Internet ──► MX Cloudflare ──► Email Routing ──► Worker (cloud-mail)
                                                ├─► D1 (database: email, user, account, setting)
                                                ├─► KV (settings cache + attachment fallback)
                                                ├─► Workers AI (ekstraksi kode OTP)
                                                └─► Assets (frontend Vue 3, dist/)
        ──► mail.YOUR_DOMAIN.com ──► Worker route ──► UI web
```

- `mail-worker/` — backend Cloudflare Worker (Hono), email handler, service layer
- `mail-vue/` — frontend Vue 3 (build → `mail-worker/dist/` sebagai Assets)

## 🚀 Setup (10 menit)

### Prasyarat
- Akun [Cloudflare](https://dash.cloudflare.com) dengan domain (zone aktif, Email Routing enabled)
- Akun [Resend](https://resend.com) — **free tier, tanpa kartu kredit** (untuk kirim email)
- [Node.js 18+](https://nodejs.org) + [wrangler](https://developers.cloudflare.com/workers/wrangler/) (`npm i -g wrangler`)
- Login wrangler: `wrangler login` (atau `CLOUDFLARE_API_TOKEN`)

### 1. Clone & install

```bash
git clone https://github.com/<kamu>/cloud-mail-deploy
cd cloud-mail-deploy

# Backend
cd mail-worker && npm install --no-audit --no-fund
# Frontend (butuh --legacy-peer-deps karena ERESOLVE di dependency)
cd ../mail-vue && npm install --no-audit --no-fund --legacy-peer-deps
```

### 2. Buat resource Cloudflare

```bash
cd ../mail-worker
wrangler d1 create cloud-mail-db        # catat database_id
wrangler kv namespace create cloud-mail-kv   # catat namespace id
```

### 3. Konfigurasi

```bash
cp wrangler.toml.example wrangler.toml
```

Isi di `wrangler.toml`:
| Field | Isi dengan |
|---|---|
| `database_id` | ID dari `wrangler d1 create` |
| `kv id` | ID dari `wrangler kv namespace create` |
| `domain` | Domain kamu, e.g. `["hafizhmuzani.my.id"]` |
| `admin` | Email admin, e.g. `admin@hafizhmuzani.my.id` |
| `jwt_secret` | String acak panjang — **rahasia!** Dipakai `GET /api/init/{secret}` |

> ⚠️ `wrangler.toml` di-ignore oleh git (berisi secret). Selalu salin dari `.example`.

### 4. Deploy & init database

```bash
# Build frontend + deploy (build command di wrangler.toml otomatis jalan)
wrangler deploy

# Init database (bikin tabel) — GANTI {jwt_secret} dengan nilai kamu
curl "https://cloud-mail.<subdomain>.workers.dev/api/init/<JWT_SECRET>"
# → {"code":0,"data":"success"}
```

### 5. DNS & Email Routing (manual di dashboard Cloudflare)

1. **CNAME**: `mail` → `cloud-mail.<subdomain>.workers.dev` (proxied)
2. **Email Routing** → Rules → Catch-all → kirim ke worker `cloud-mail`
3. (Opsional) Verifikasi domain di **Resend** untuk kirim email: tambah DNS record TXT/DKIM/SPF yang diminta Resend

### 6. Aktifkan AI ekstraksi OTP

```sql
-- Di dashboard D1 (atau `wrangler d1 execute cloud-mail-db --remote --command "..."`)
UPDATE setting SET ai_code = 0;   -- 0 = OPEN (aktif), 1 = CLOSE (mati)
```

Lalu panggil lagi `/api/init/{jwt_secret}` untuk sync settings ke KV.

## 🔧 Perbaikan yang disertakan (vs upstream)

Proyek ini sudah dipakai di production dan mengandung fix penting:

1. **Model AI deprecated** — `@cf/meta/llama-3.1-8b-instruct` di-deprecate Cloudflare pada 2026-05-30 (error `5028`). Diganti ke `@cf/meta/llama-3.3-70b-instruct-fp8-fast` via var `ai_model` (bisa diubah tanpa patch kode).
2. **Format response model baru** — Model llama terbaru return `{ response: {...} }` (object) atau `{ choices: [{ message: { content } }] }`, bukan string JSON. `ai-service.js` sekarang handle ketiganya:
   - string JSON → `JSON.parse`
   - object langsung → pakai apa adanya
   - `choices[0].message.content` → fallback
3. **R2 opsional** — Tanpa aktivasi R2 (butuh kartu kredit), storage attachment fallback ke **KV** (gratis). Binding R2 cukup ditambahkan di `wrangler.toml` kalau sudah aktif.
4. **Public API `emailList` mengembalikan kolom `code`** — kode OTP hasil AI ekstraksi bisa diambil langsung dari API (tanpa query D1).

## 📦 Cloud Mail CLI (`cloud-mail.py`)

CLI Python untuk automation — daftar akun batch, polling email, ambil kode OTP tanpa buka UI.

### Setup pertama

```bash
# Dapatkan token akses (login admin)
python cloud-mail.py token '<password-admin>'
# Token disimpan otomatis di .cloud-mail-token (di-ignore git)
```

### Perintah

```bash
# Daftarkan banyak akun sekaligus
python cloud-mail.py daftar email1@domain.com email2@domain.com

# Lihat email masuk
python cloud-mail.py inbox email@domain.com

# Lihat email + kode OTP hasil AI ( langsung tampil 🔑 KODE : XXXXXX )
python cloud-mail.py otp email@domain.com

# Polling email masuk tiap 5 detik (Ctrl+C untuk stop)
python cloud-mail.py poll email@domain.com --wait 5
```

### Variabel environment (opsional)

| Variabel | Default | Keterangan |
|---|---|---|
| `CLOUD_MAIL_URL` | `https://mail.YOUR_DOMAIN.com` | Base URL worker |
| `CLOUD_MAIL_ADMIN` | `admin@YOUR_DOMAIN.com` | Email admin |

### Contoh workflow automation

```bash
# 1. Daftarkan 10 alamat
python cloud-mail.py daftar {1..10}@domain.com

# 2. Tunggu OTP masuk + ambil kodenya
python cloud-mail.py otp user1@domain.com --wait 3
```

## 🧪 Verifikasi

```bash
# Worker hidup
curl -H "User-Agent: Mozilla/5.0" https://mail.YOUR_DOMAIN.com/login   # HTTP 200

# Email masuk + kode OTP (via CLI)
python cloud-mail.py otp email@domain.com
# → 🔑 KODE : 765610  (otomatis dari AI!)

# Atau query D1 langsung
wrangler d1 execute cloud-mail-db --remote --command "SELECT to_email, subject, code FROM email ORDER BY email_id DESC LIMIT 5;"
```

## 📄 Lisensi

[MIT](LICENSE) — upstream [maillab/cloud-mail](https://github.com/maillab/cloud-mail) © eoao. Deployment config & fix tambahan oleh Hafizh.

---

_Dibuat dengan ☕ + Cloudflare Workers._
