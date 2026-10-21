# AGENTS.md — Cloud Mail Deploy

Deployment mandiri dari **[maillab/cloud-mail](https://github.com/maillab/cloud-mail)** —
platform email lengkap di Cloudflare Workers: terima (Email Routing → Worker → D1),
kirim (Resend), UI web ala Gmail (Vue 3), admin panel, forward Telegram, dan ekstraksi
kode OTP otomatis lewat Workers AI.

Pemilik deployment: **Hafizh Muzani** (`admin@hafizhmuzani.my.id`).

> **Repo ini fork/deployment, bukan upstream.** Jangan menyamakan strukturnya dengan
> dokumentasi maillab/cloud-mail — ada penyesuaian lokal yang dijelaskan di bawah.

## Stack

| Bagian | Teknologi |
|---|---|
| Backend | Cloudflare Worker, **Hono 4.12.16**, ESM (JavaScript, **bukan TypeScript**) |
| Database | **D1** (SQLite) via **drizzle-orm** |
| Cache/settings | **KV** (settings cache + fallback attachment) |
| AI | **Workers AI** (`ai_model` di `[vars]`) — ekstraksi kode OTP dari email masuk |
| Attachment | Fallback berjenjang **S3 → R2 → KV** (`att-service`, `s3-service`, `r2-service`, `kv-obj-service`) |
| Email masuk | `postal-mime` (parsing), Email Routing catch-all |
| Email keluar | **Resend** (`resend` SDK, `resend-service`) |
| Frontend | Vue 3.5 + **Vite 7** + Element Plus + Pinia + vue-router + vue-i18n + ECharts + Dexie + PWA |
| CLI | `cloud-mail.py` — Python 3, **hanya standard library** (`urllib`, tanpa `requests`) |
| CI/CD | GitHub Actions → `wrangler deploy` |

## Struktur folder

```
cloud-mail.py                    # CLI automation: token, daftar, inbox, otp, poll
mail-worker/                     # ── BACKEND (Cloudflare Worker)
  src/index.js                   # entry: fetch() / email() / scheduled()
  src/hono/hono.js               # instance Hono app
  src/hono/webs.js               # Hono app + mendaftarkan SEMUA route /api/*
  src/api/*.js                   # 18 file route per-domain (email, user, login, role, ...)
  src/service/*.js               # 21 file logika bisnis
  src/entity/*.js                # skema drizzle + orm
  src/security/security.js       # middleware auth
  src/security/user-context.js   # konteks user per-request
  src/email/email.js             # handler email masuk
  src/const, dao, i18n, init,    # konstanta, akses data analitik, terjemahan,
  model, template, utils         # bootstrap, model, template email, util
  wrangler.toml                  # ⚠️ BERISI SECRET — di-ignore git
  wrangler.toml.example          # template aman untuk di-commit
  wrangler-dev.toml              # config dev (di-commit, tanpa secret)
  wrangler-action.toml           # template CI dengan placeholder ${VAR} (di-commit)
  test/index.spec.js             # ⚠️ masih boilerplate upstream — lihat "Jebakan"
mail-vue/                        # ── FRONTEND (Vue 3)
  src/views/*                    # 15 halaman (email, all-email, send, user, role, ...)
  src/layout/*                   # aside, header, main, write, account
  src/store, src/router, src/request, src/i18n, src/perm
  public/sounds/otp-notification.mp3   # aset notifikasi (fitur lokal)
  .env.dev / .env.release / .env.remote
.github/workflows/deploy-cloudflare.yml
doc/, README.md, README-en.md
```

## Perintah

### Backend (dari `mail-worker/`)

```bash
npm install --no-audit --no-fund        # sekali di awal
npm run dev                             # wrangler dev --config wrangler-dev.toml
                                        # → http://127.0.0.1:8787
npm run deploy                          # wrangler deploy (pakai wrangler.toml)
```

Butuh `mail-worker/wrangler.toml` ada di disk untuk `npm run deploy`.
Kalau file itu hilang (mis. habis clone baru), salin dari `wrangler.toml.example`
lalu isi D1 ID, KV ID, `jwt_secret`, `domain`, dan `admin`.

**`wrangler deploy` otomatis membangun frontend** — ada `[build]` di `wrangler.toml`:

```
npm --prefix ../mail-vue install --no-audit --no-fund --legacy-peer-deps
npm --prefix ../mail-vue run build
```

### Frontend (dari `mail-vue/`)

```bash
npm install --no-audit --no-fund --legacy-peer-deps   # ⚠️ flag legacy WAJIB
npm run dev        # vite --mode dev  → memanggil http://127.0.0.1:8787/api
npm run build      # vite build --mode release → output ke ../mail-worker/dist
```

`.env.release` mengarahkan `VITE_OUT_DIR=../mail-worker/dist`, jadi hasil build
langsung menjadi Assets milik Worker. **Build frontend harus dijalankan sebelum deploy**,
kalau tidak UI yang tersaji versi lama.

### CLI (`cloud-mail.py`, dari root repo)

```bash
python cloud-mail.py token '<password-admin>'   # simpan token ke .cloud-mail-token
python cloud-mail.py daftar email1@domain email2@domain
python cloud-mail.py inbox email@domain
python cloud-mail.py otp email@domain           # email + kode OTP hasil AI
python cloud-mail.py poll email@domain --wait 5
```

Variabel lingkungan: `CLOUD_MAIL_URL` (default `https://mail.hafizhmuzani.my.id`),
`CLOUD_MAIL_ADMIN`.

### Query database

```bash
cd mail-worker
npx wrangler d1 execute cloud-mail-db --remote \
  --command "SELECT to_email, subject, code FROM email ORDER BY email_id DESC LIMIT 5;"
```

## Verifikasi & jebakan (BACA SEBELUM MENGAKUI "SELESAI")

1. **Tidak ada test otomatis yang berjalan.** `vitest.config.js` menunjuk
   `./wrangler.jsonc` yang **tidak ada** di repo, dan `test/index.spec.js` masih
   boilerplate upstream ("Hello World!") yang tidak berhubungan dengan aplikasi ini.
   → **Jangan pernah bilang "tests pass".** Kalau perlu membuktikan perubahan,
   pakai cara manual di poin 4.

2. **`npm run test` bukan perintah tes.** Isinya `wrangler deploy --config wrangler-test.toml`
   — yaitu **deploy ke environment test**. Selain itu `wrangler-test.toml` sudah di-ignore
   dan **tidak ada di repo**, jadi perintah itu pasti gagal. Jangan dijalankan.

3. **`npm install` di `mail-vue` tanpa `--legacy-peer-deps` akan gagal** dengan ERESOLVE.
   Ini bukan bug yang perlu diperbaiki dengan mengubah dependency.

4. **Cara membuktikan perubahan dengan benar:**
   - Backend: `npm run dev`, lalu uji endpoint `/api/...` (mis. lewat `curl` atau UI).
   - Frontend: `npm run dev` di `mail-vue` dengan backend `npm run dev` tetap jalan.
   - UI web: bisa diuji dengan MCP **playwright** ke `http://127.0.0.1:8787`.
   - Syntax check cepat: `node --check src/<file>.js` (Worker memakai ESM).
   - Jangan menyatakan UI berubah tanpa benar-benar membukanya.

5. **`src/index.js` punya cabang cron yang tidak terpakai.** Kode menangani
   `*/30 * * * *`, tetapi `wrangler.toml` hanya mendaftarkan `0 16 * * *`.
   Jangan berasumsi refresh ECharts jalan tiap 30 menit.

6. **`views/test/index.vue` dan route `/test` masih ada** — sisa halaman debug.
   `src/api/test-api.js` sudah dikosongkan (tanpa route) dan **sengaja tidak**
   di-import di `webs.js`. Jangan mengimpor ulang tanpa alasan.

## Secret — JANGAN PERNAH DI-COMMIT

Repo ini di-push ke GitHub (`apissaj/cloud-mail-deploy`). Perlakukan sebagai publik.

| Berkas | Isi sensitif | Status |
|---|---|---|
| `mail-worker/wrangler.toml` | `jwt_secret`, D1/KV ID, daftar `domain`, `admin`, `ai_model` | di-ignore git |
| `.cloud-mail-token` (root) | token public API hasil `cloud-mail.py token` | di-ignore git |
| `mail-worker/.cloud-mail-token` | idem | di-ignore git |
| `*.bak`, `wrangler.toml.bak` | salinan config lama berisi secret | di-ignore git |
| `mail-worker/tmp/`, `ids.json`, `*.txt`, `[0-9]*` | artefak debug | di-ignore git |

- **Jangan** menyalin isi `wrangler.toml` ke `wrangler.toml.example`, README, commit message,
  atau keluarannya terminal yang di-paste ke chat.
- `wrangler-dev.toml` dan `wrangler-action.toml` **memang** di-commit dan aman (placeholder
  `${VAR}` / resource dev). Jangan menambahkan `jwt_secret` ke situ.
- Secret CI disimpan di GitHub Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`,
  `JWT_SECRET`, `D1_DATABASE_ID`, `KV_NAMESPACE_ID`, `R2_BUCKET_NAME`, `LINUXDO_CLIENT_SECRET`, dll.
- Kalau ada secret yang sudah terlanjur ter-commit, **tidak cukup** dengan commit penghapusan —
  harus di-rotate di Cloudflare/Resend/GitHub.

## Alur runtime

```
Email masuk  → MX Cloudflare → Email Routing → Worker email()
             → postal-mime parse → D1 (tabel email)
             → Workers AI ekstrak kode OTP → kolom code
             → forward Telegram (opsional)
             → notifikasi WebSocket ke UI

Request HTTP → /api/*        → Hono app (prefix /api dilepas) → route di src/api/
             → /static/*, /attachments/* → kv-obj-service (fallback S3/R2/KV)
             → selain itu    → env.assets (hasil build mail-vue)

Cron 0 16 * * * → hapus verify-record, reset kuota kirim harian,
                  selesaikan status terima, bersihkan user OAuth tanpa binding,
                  refresh cache ECharts
```

Bootstrap database (sekali per deployment): `GET /api/init/{jwt_secret}` → `success`.
Endpoint ini dilindungi nilai `jwt_secret`, jadi jangan dipanggil sembarangan dan
jangan pernah menempelkan URL lengkapnya ke tempat publik.

## Penyesuaian lokal di atas upstream

Bagian ini ditulis tangan dan **tidak ada di upstream** — perlakukan sebagai kode milik sendiri:

- **`cloud-mail.py`** — CLI automation (token, daftar batch, inbox, otp, poll).
- **Notifikasi email baru** — suara + toast:
  - `mail-vue/src/views/email/index.vue`, `mail-vue/src/views/all-email/index.vue`
  - Web Audio API, audio di-unlock setelah gesture pertama (patuh autoplay policy),
    fallback oscillator kalau MP3 gagal dimuat, kode OTP ikut tampil di judul toast
  - aset: `mail-vue/public/sounds/otp-notification.mp3`
  - memperbaiki perilaku polling: nilai auto-refresh `0` tidak lagi mematikan update otomatis
- **CI deploy** `.github/workflows/deploy-cloudflare.yml` — menulis `wrangler-action.toml`
  dari secret GitHub, deploy, lalu memanggil `/api/init/...`.

## Konvensi kode

- **Indentasi tab**, `end_of_line = lf`, UTF-8 (lihat `.editorconfig` & `.prettierrc` di `mail-worker/`).
- Prettier backend: `printWidth 140`, `singleQuote true`, `semi true`, `useTabs true`.
- Worker = ESM (`import`/`export`), tanpa TypeScript. Frontend = Vue SFC, alias `@/`.
- Komentar pada kode upstream berbahasa Mandarin/Inggris — **pertahankan apa adanya**.
  Komentar untuk kode tambahan lokal pakai Bahasa Indonesia.
- Tidak ada ESLint/Prettier yang dikonfigurasi untuk `mail-vue`; ikuti gaya file di sekitarnya.
- Jangan memformat ulang file besar yang tidak berubah — diff jadi tak terbaca.

## Aturan kerja

- **Baca dulu** file terkait sebelum mengubah. Banyak route bergantung pada service dan entity
  yang sama; perubahan di `service/` berdampak ke beberapa `api/`.
- Jangan mengubah `wrangler-action.toml` secara struktural tanpa mengecek
  `deploy-cloudflare.yml`, karena blok-bloknya dihapus/di-isi lewat `sed` berdasarkan
  ada-tidaknya secret (`[[r2_buckets]]`, `[[routes]]`, `linuxdo_*`, `[[send_email]]`).
- Setiap klaim perubahan harus punya bukti: perintah yang dijalankan dan hasilnya.
  Kalau belum dijalankan, katakan belum dijalankan.
- Kalau menemukan ketidakjelasan, sebutkan — jangan mengarang perilaku.
- Untuk perubahan yang menyentuh lebih dari ~3 berkas, pecah jadi langkah kecil dan
  jelaskan rencananya lebih dulu.

## MCP & alat yang relevan

- **context7** — dokumentasi Hono, Wrangler, drizzle-orm, Vue 3, Element Plus.
- **serena** — navigasi simbol & refactor (`find_symbol`, `find_referencing_symbols`,
  `rename_symbol`). Untuk proyek ini Serena mendeteksi language server **vue (Volar)**,
  dan indeks pertamanya sekitar 16 detik. Cache-nya di `.serena/` (di-ignore git).
- **playwright** — uji UI web lokal di `http://127.0.0.1:8787`.
- **dart** MCP — tidak relevan di proyek ini.
- Pencarian teks: `rg`. Contoh: `rg -n "resolve|send" mail-worker/src/api`.

## Rencana yang masih menggantung

`doc/solid-glass-migration.md` — rancangan (belum dikerjakan) untuk mengganti tampilan
`mail-vue` agar memakai estetika "Solid Glass". Rekomendasinya: **jangan rewrite ke React**,
cukup port material lewat satu file CSS yang meng-override variabel Element Plus.

Sebelum menyentuh tampilan `mail-vue` secara besar, **baca dokumen itu dulu** dan sebutkan
apakah pekerjaanmu sejalan atau bertentangan dengannya. Jangan memulai migrasi UI
tanpa persetujuan pemilik proyek.
