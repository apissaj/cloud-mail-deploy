# Rencana Migrasi: Cloud Mail → Solid Glass

> Status: **rancangan** · Dibuat: 2026-10-21
> Target: mengganti tampilan `mail-vue` (Vue 3 + Element Plus) agar memakai estetika **Solid Glass**.

---

## 0. TL;DR — Rekomendasi Utama

**JANGAN pindah framework.** Solid Glass adalah *stylesheet untuk React + Tailwind + shadcn/ui*, sedangkan `mail-vue` adalah *Vue 3 + SCSS + Element Plus*. Migrasi penuh = rewrite 12.700 baris UI.

**Yang disarankan: PORT MATERIALNYA, bukan frameworknya.**

Buat satu file `solid-glass-vue.css` (turunan dari `solid-glass.css` milik DeepLethe, lisensi MIT) yang meng-override variabel CSS Element Plus. Hasil: seluruh app langsung terlihat "Solid Glass" **tanpa mengubah satu pun komponen Vue**.

| Opsi | Usaha | Risiko | Hasil |
|---|---|---|---|
| **A. Port stylesheet ke EP** ⭐ | ~1–2 hari | Rendah | 90% estetika, 0 rewrite komponen |
| **B. Rewrite ke React + shadcn** | ~2–4 minggu | Sangat tinggi | 100% estetika + komponen agent-native |
| **C. Hybrid bertahap** | ~1 minggu | Sedang | Shell baru + halaman lama |

Rekomendasi: **mulai dari A**, evaluasi C kalau mau lebih jauh.

---

## 1. Apa itu Solid Glass (ringkas)

- **Sumber:** `github.com/deeplethe/solid-glass` (MIT, 2.1k ⭐)
- **Inti:** satu file `src/solid-glass.css` (1.409 baris) berisi seluruh "material"
- **Konsep:** kaca tebal berwarna asap — dari jauh tampak solid, dari dekat tampak kaca
- **4 aturan material:**
  1. **Finish di tepi** — rim + hairline + shadow, bukan gradien di muka
  2. **Berat, bukan transparan** — abu netral; blur melembutkan, bukan memperkuat warna
  3. **Kedalaman = ketebalan** — `panel` < `card` < `popover`, makin tebal makin opak
  4. **Satu state** — hover / terpilih / terbuka memakai kaca bening yang sama
- **Dark adalah desain aslinya** (oklch 0.16 background); light adalah versi siang.
- **Cara kerja:** menargetkan `data-slot="..."` + kelas Tailwind yang sudah ada di komponen shadcn → komponen tidak perlu diubah sama sekali.

### Variabel kunci yang mendefinisikan material

```
--glass-rim / --glass-inner / --glass-edge     → garis cahaya tepi atas, garis dalam, hairline luar
--glass-shade / --glass-lift / --glass-contact  → bayangan bawah, angkat, kontak
--glass-control / --glass-state                 → kaca bening untuk kontrol kecil & state
--field / --field-rim / --field-edge            → isian input
--well-shade / --well-rim                       → groove track switch/slider
--knob / --knob-shade                           → thumb switch/slider
--glass-blur                                    → blur(26px) [dark] / blur(26px) saturate(180%) [light]
--radius / --radius-control                     → 0.875rem / 0.7rem
--brand (hijau oklch 0.68 0.13 165)             → aksen
--chart-1..5                                    → grafik abu-abu, tanpa hue
```

Ini **bahasa desain yang bisa diterjemahkan ke CSS apa pun**, termasuk Element Plus.

---

## 2. Kondisi `mail-vue` saat ini (hasil audit)

**Stack:** Vue 3.5 `<script setup>` · Vite 7 · **Element Plus 2.13** · Pinia 3 · vue-router 4 · vue-i18n 11 · SCSS. Tanpa TypeScript. Tanpa Tailwind.

**Ukuran:** 72 file, **15.366 baris** di `src/` (12.829 baris non-blank).

| Area | File | Baris |
|---|---:|---:|
| `src/views/**` | 15 | 8.046 |
| `src/layout/**` | 6 | 2.428 |
| `src/components/**` | 7 | 2.032 |
| UI total (views+layout+components+style) | 30 | **12.733** |
| API (axios+request) | 13 | 362 |
| State (store+perm+db+enums) | 14 | 403 |
| Cross-cutting (utils+i18n+icons+router) | 15 | 1.996 |

**10 file terbesar = 10.127 baris ≈ 66% kode:**

| File | Baris |
|---|---:|
| `views/sys-setting/index.vue` | 2.001 |
| `components/email-scroll/index.vue` | 1.367 |
| `views/user/index.vue` | 1.294 |
| `views/analysis/index.vue` | 947 |
| `views/login/index.vue` | 842 |
| `layout/write/index.vue` | 788 |
| `layout/account/index.vue` | 677 |
| `views/all-email/index.vue` | 599 |
| `views/reg-key/index.vue` | 569 |
| `views/role/index.vue` | 551 |

### Permukaan Element Plus (biaya migrasi utama)

**465 instance `<el-*>` di 18 file, 46 komponen berbeda.** Terbanyak:

| Komponen | Jumlah | Catatan |
|---|---:|---|
| `el-button` | 71 | mudah dipetakan |
| `el-option` | 53 | ikut `el-select` |
| `el-input` | 45 | |
| `el-dropdown-item` | 31 | |
| `el-dialog` | 30 | **paling berat** — 16 di sys-setting |
| `el-select` | 26 | |
| `el-table-column` | 24 | |
| `el-tag` | 23 | |
| `el-switch` | 12 | |
| `el-input-number` | 11 | |
| `el-input-tag` | 10 | EP 2.9+, tidak umum di kit lain |
| `el-table` | 6 | |
| `el-tree` | 1 | dengan checkbox — non-trivial |
| `el-statistic` | 4 | |

**API terprogram (auto-import, tidak terlihat di grep import):**
`ElMessage` ×97, `ElMessageBox` ×20, `ElNotification` ×5.

**Container layout:** `el-container` / `el-aside` / `el-header` / `el-main` di `layout/index.vue`.

### Temuan penting untuk keputusan migrasi — **sudah diverifikasi langsung ke source**

1. **Theming EP murni CSS-variabel** — tidak ada override SCSS `$el-*`, tidak ada `element-plus/theme-chalk/src/index.scss`. Hanya `dark/css-vars.css`. **Ini kabar baik:** material bisa diganti lewat CSS vars.
2. **Hanya 5 variabel `--el-*` yang benar-benar dipakai langsung oleh app:**
   `--el-bg-color`, `--el-border-color`, `--el-border-color-lighter`, `--el-color-primary-light-8`, `--el-text-color-primary`.
   *(Variabel lain tetap terpakai — tapi dipakai oleh CSS internal EP sendiri, yang membaca var yang sama. Override di satu tempat tetap flows ke semua tempat.)*
3. **Hanya SATU selector `:deep()` yang menyentuh internal EP:**
   `style.css:20` → `:deep(.el-input__inner:focus)`.
   Audit awal memperkirakan ≥8 — **risiko ini jauh lebih rendah dari perkiraan.**
4. **Selector `.el-*` global di `style.css` (5 blok, manageable):**
   `.el-table thead th` (L25) · `.el-message` (L62) · `.el-icon` (L70) · `.el-input-group__append/.prepend` (L75) · `.el-input` (L170).
   Plus `layout/index.vue` memakai class container EP: `.el-aside` (L78) · `.el-main` (L99) · `.el-header` (L103) · `.el-aside-hide` (L53).
5. **⚠️ SPESIFIKASI — jebakan utama:**
   `element-plus/theme-chalk/dark/css-vars.css` (2.946 byte) memakai selektor **`html.dark { … }`**, yaitu spesifisitas **(0,1,1)**.
   Adapter kita akan menulis `.dark { … }` = **(0,1,0)** → **kalah**,EP wins.
   Bukti di kode sekarang: `style.css:167` memakai `--el-border-color: #414243 !important` — `!important` dipakai persis untuk menembus hal ini.
   → **Adapter WAJIB memakai `html.dark` (atau `!important`).**
6. **`--el-color-primary: #1890ff`** (biru) di `style.css:109`. Solid Glass pakai brand hijau (`oklch(0.68 0.13 165)`) — perlu keputusan (§6).
7. **Dark mode = class `.dark` di `<html>`** (di-toggle lewat `root.setAttribute('class', …)` di `layout/header/index.vue:228`).
   Mekanisme identik dengan Solid Glass → **kompatibel 100%.**
8. **`backdrop-filter` belum dipakai sama sekali** di app — jadi kita menambahkannya bersih, tanpa bentrok.
9. **Iconify runtime API** untuk ~100 ikon (hanya 3 koleksi lokal: `hugeicons`, `cil`, `ep`). Dependency network saat runtime.
10. **Dep mati:** `date-time-format-timezone` (tak pernah diimpor), `compressorjs` (`compressImage` tak pernah dipanggil), `less`, `path`.
11. **Blok `<style>` global (tidak scoped)** — perlu diaudit: `analysis`, `all-email`, `draft`, `email`, `login`, `sys-setting`, `user`, `layout/account`, `layout/header`, `layout/write`, `components/shadow-html`.

---

## 3. Kenapa bukan rewrite ke React/shadcn

| Hambatan | Dampak |
|---|---|
| 12.733 baris UI harus ditulis ulang | berbulan-bulan |
| 46 komponen EP → perlu padanan shadcn atau bikin sendiri | `el-table`, `el-tree`, `el-statistic`, `el-input-tag` tak ada di shadcn |
| TinyMCE (self-hosted, GPL key, `blobCache` image) | integrasi React perlu ditulis ulang |
| ECharts ×4 + theming | perlu wrapper React |
| Dexie draft + autosave compose | perlu ditulis ulang |
| Sistem `v-perm` (hapus elemen dari DOM) + `permsToRouter` | perlu reimplementasi |
| PINIA → state baru | ~400 baris + coupling |
| Deploy: Vue→`dist/` di worker | build pipeline berubah |

Kesimpulan: **rewrite total tidak rasional** untuk tujuan yang murni visual.

---

## 4. Strategi yang disarankan — "Port Material"

### Ide inti

Element Plus **sudah** sepenuhnya digerakkan CSS custom property (`--el-*`). Solid Glass **juga** CSS custom property (`--glass-*`, `--background`, `--card` …). Jadi:

> Buat `solid-glass-ep.css` yang memetakan material Solid Glass **ke** variabel Element Plus.

⚠️ **Aturan #1 (dari §2.5): semua override untuk dark mode harus memakai selektor `html.dark`, bukan `.dark`** — kalau tidak, `element-plus/theme-chalk/dark/css-vars.css` akan menang dan material kita tidak terpakai di dark mode.

Contoh pemetaan (light = `:root`, dark = `html.dark`):

```css
/* ===== LIGHT ===== */
:root {
  /* Permukaan halaman & pane (Solid Glass: background < panel < card < popover) */
  --el-bg-color-page:      oklch(0.925 0.007 265);   /* = --background */
  --el-bg-color:           oklch(0.98 0.004 265 / 60%);   /* = --card (tebal sedang) */
  --el-bg-color-overlay:   oklch(0.985 0.003 265 / 96%);  /* = --popover (paling tebal) */
  --el-fill-color-blank:   oklch(0.925 0.007 265);

  /* Teks */
  --el-text-color-primary:   oklch(0.16 0 0);        /* = --foreground */
  --el-text-color-regular:   oklch(0.30 0 0);
  --el-text-color-secondary: oklch(0.47 0 0);        /* = --muted-foreground */
  --el-text-color-placeholder: oklch(0.60 0 0);

  /* Garis (hairline Solid Glass, bukan solid gelap) */
  --el-border-color:         oklch(0.3 0.02 265 / 13%);   /* = --border */
  --el-border-color-light:   oklch(0.3 0.02 265 / 10%);
  --el-border-color-lighter: oklch(0.3 0.02 265 / 7%);
  --el-border-color-extra-light: oklch(0.3 0.02 265 / 5%);

  /* Isian kontrol */
  --el-fill-color:         oklch(0.3 0.02 265 / 9%);   /* = --accent */
  --el-fill-color-light:   oklch(0.3 0.02 265 / 7%);   /* = --muted */
  --el-fill-color-lighter: oklch(0.3 0.02 265 / 5%);

  /* Brand (lihat §6 — atau biarkan #1890ff) */
  --el-color-primary:         oklch(0.68 0.13 165);
  --el-color-primary-light-3: oklch(0.76 0.10 165);
  --el-color-primary-light-5: oklch(0.82 0.07 165);
  --el-color-primary-light-7: oklch(0.88 0.05 165);
  --el-color-primary-light-8: oklch(0.91 0.04 165);
  --el-color-primary-light-9: oklch(0.94 0.03 165);
  --el-color-primary-dark-2:  oklch(0.58 0.14 165);

  /* Geometri material */
  --el-border-radius-base:  0.7rem;    /* = --radius-control */
  --el-border-radius-small: 0.45rem;
  --el-border-radius-round: 9999px;

  /* Material tokens (dipakai class .glass-* di bawah) */
  --radius: 0.875rem;
  --glass-blur: blur(26px) saturate(180%);
  --glass-rim:   oklch(1 0 0 / 90%);
  --glass-inner: oklch(1 0 0 / 35%);
  --glass-edge:  oklch(0.38 0.03 265 / 10%);
  --glass-shade: oklch(0.3 0.06 265 / 28%);
  /* … salin lengkap dari upstream solid-glass.css :root … */
}

/* ===== DARK — WAJIB html.dark ===== */
html.dark {
  --el-bg-color-page:      oklch(0.16 0 0);
  --el-bg-color:           oklch(0.31 0 0 / 46%);
  --el-bg-color-overlay:   oklch(0.22 0 0 / 96%);
  --el-fill-color-blank:   oklch(0.16 0 0);

  --el-text-color-primary:   oklch(0.985 0 0);
  --el-text-color-regular:   oklch(0.85 0 0);
  --el-text-color-secondary: oklch(0.72 0 0);
  --el-text-color-placeholder: oklch(0.55 0 0);

  --el-border-color:         oklch(1 0 0 / 11%);
  --el-border-color-light:   oklch(1 0 0 / 9%);
  --el-border-color-lighter: oklch(1 0 0 / 7%);
  --el-border-color-extra-light: oklch(1 0 0 / 5%);

  --el-fill-color:         oklch(1 0 0 / 8%);
  --el-fill-color-light:   oklch(1 0 0 / 7%);
  --el-fill-color-lighter: oklch(1 0 0 / 5%);

  --glass-blur:  blur(26px);            /* dark: tanpa saturate */
  --glass-rim:   oklch(1 0 0 / 16%);
  --glass-inner: oklch(1 0 0 / 4%);
  --glass-edge:  oklch(1 0 0 / 6%);
  --glass-shade: oklch(0 0 0 / 60%);
  /* … salin lengkap dari upstream solid-glass.css .dark … */
}
```

Lalu **kaca (glass) ditambahkan sebagai utility class** untuk permukaan besar:

```css
/* Finish di tepi — bukan gradien di muka (aturan #1 Solid Glass) */
.glass-panel,
.el-aside,
.el-header {
  background: var(--el-bg-color);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  box-shadow:
    inset 0 1px 0 var(--glass-rim),        /* cahaya tepi atas */
    inset 0 0 0 1px var(--glass-inner),    /* garis dalam */
    0 0 0 1px var(--glass-edge),           /* hairline luar */
    0 8px 24px var(--glass-shade);         /* bayangan bawah */
  border: none;
}

.el-overlay-dialog .el-dialog,
.el-dropdown__popper,
.el-select__popper,
.el-popper.is-pure {
  background: var(--el-bg-color-overlay);          /* = popover: paling tebal */
  backdrop-filter: var(--glass-blur);
  box-shadow:
    inset 0 1px 0 var(--glass-rim),
    0 0 0 1px var(--glass-edge),
    0 16px 40px var(--glass-shade);
}

/* Field: kaca bening untuk mengetik */
.el-input__wrapper,
.el-textarea__inner,
.el-select__wrapper {
  background: var(--el-fill-color);
  box-shadow:
    inset 0 1px 0 var(--glass-rim),
    0 0 0 1px var(--el-border-color);
}
```

Ini meniru **persis** 4 aturan Solid Glass (finish di tepi, berat, kedalaman=ketebalan, satu state) dengan sintaks CSS apa pun.

### Kenapa ini bekerja

- `el-card`, `el-dialog`, `el-dropdown-menu`, `el-table` semuanya mengambil warna dari `--el-bg-color*`, `--el-fill-color*` dan `--el-border-color*` → cukup override variabel.
- Class `.dark` sudah ada di `<html>` → mekanisme tema Solid Glass langsung nyambung (dengan catatan spesifisitas §2.5).
- `backdrop-filter` didukung semua browser target (Chrome/Safari/Firefox modern) dan **belum dipakai app** → aman ditambahkan.
- Tidak ada komponen Vue yang diubah → risiko regresi minimal; hanya **1 `:deep()`** yang perlu disentuh.

### Hasil yang diharapkan

- Latar halaman bergeser ke abu cool-grey (light) / hitam (dark)
- Semua panel/kartu/dialog jadi kaca ber-asap dengan rim cahaya & hairline
- Primary jadi hijau brand Solid Glass (atau tetap biru — lihat §6)
- State hover/terpilih memakai satu kaca bening
- Grafik abu-abu (chart-1..5) alih-alih warna-warni
- ~90% "rasa" Solid Glass, tanpa menyentuh 1 baris template Vue

---

## 5. Rencana Kerja (fase)

### Fase 0 — Persiapan (½ hari)
- [ ] Copy `solid-glass.css` dari upstream ke `mail-vue/src/theme/solid-glass.css` (simpan lisensi MIT + NOTICE + catat commit hash upstream).
- [ ] Audit 11 blok `<style>` global (tidak scoped) — tandai mana yang perlu di-`scoped`.
- [ ] Konfirmasi 5 var `--el-*` yang dipakai app + **19 var permukaan EP** dari `dark/css-vars.css` (bg-color-page/bg-color/bg-color-overlay, text-color ×4, border-color ×5, fill-color ×5) →，这就是 peta pemetaan.
- [ ] Petakan 26 var app-lokal (`--aside-backgound`, `--email-hover-background`, `--base-fill`, `--choose-account-background`, …) ke padanan Solid Glass. Perhatikan: `--aside-backgound: #001529` (biru tua) → jadi abu netral.
- [ ] Putuskan: primary **biru (#1890ff) tetap** atau **hijau brand Solid Glass**? (lihat §6)

### Fase 1 — Material dasar (1 hari)
- [ ] Tulis `src/theme/solid-glass-ep.css` dengan blok `:root` (light) + **`html.dark`** (dark) —法的 kunci: `html.dark`, bukan `.dark`.
- [ ] Tambah kelas `.glass-panel` / `.glass-card` / `.glass-popover` / `.glass-control` / `.glass-state`.
- [ ] Terapkan `.glass-panel` ke: `layout/aside`, `layout/header`, `layout/main`, `layout/account` (mailbox card), `email-scroll` (baris), `el-card` di account.
- [ ] Ganti `--el-color-primary` + `--el-color-primary-{light-3,5,7,8,9}` + `--el-color-primary-dark-2`.
- [ ] Ganti `--el-border-radius-*` → `0.7rem` / `0.45rem` (material Solid Glass).
- [ ] Perbarui `src/style.css`: hapus 34 var `:root` + 24 var `.dark` lama, delegasikan ke file tema baru. **Hapus blok `--el-color-primary` yang bentrok.**
- [ ] Ganti `--aside-backgound` #001529 → abu netral; sesuaikan `--email-hover-background` → pakai `--glass-state`.

### Fase 2 — Permukaan kompleks (1 hari)
- [ ] `el-dialog` ×30 → gaya popover Solid Glass (rim + edge + under-shadow) + isi opak di dalam pane.
- [ ] `el-table` ×6 → header muted, baris hover kaca, hairline pemisah. Perbaiki `.el-table thead th` (`style.css:25`).
- [ ] `el-dropdown-menu` / `el-dropdown-item` ×31 → pane kaca + state seragam (hover = `--glass-state`).
- [ ] `el-select` / `el-option` → dropdown kaca; `el-select-dropdown__loading` (internal `components/loading`).
- [ ] `el-switch` / `el-slider` / `el-checkbox` / `el-radio` → knob terang (`--knob`) + well groove (`--well-shade`).
- [ ] `el-input` ×45 → field kaca (`--field` + `--field-rim` + `--field-edge`); perbaiki `:deep(.el-input__inner:focus)` (`style.css:20`).
- [ ] `el-skeleton` / `el-skeleton-item` → shimmer senada.
- [ ] `el-menu` / `el-menu-item` ×11 (aside) → sesuai aturan "satu state".

### Fase 3 — Chart, ikon, font (½ hari)
- [ ] ECharts `analysis`: ganti palet ke `--chart-1..5` (abu Solid Glass) atau brand untuk seri utama.
- [ ] Perbaiki `topic` computed di `analysis/index.vue` agar menarik dari var CSS (bukan hardcode hex).
- [ ] Font: pasang `@fontsource-variable/geist` + `geist-mono` (pilihan §6).
- [ ] (Opsional) kurangi ketergantungan Iconify runtime API.

### Fase 4 — Verifikasi (½ hari)
- [ ] Uji light + dark di semua 15 halaman (buka lewat browser, bukan asumsi).
- [ ] Uji responsif (`window.innerWidth < 1025` collapse aside).
- [ ] Cek kontras WCAG AA (Solid Glass dark `--muted-foreground` oklch 0.72 ≈ ~7:1; light oklch 0.47 ≈ ~5.7:1).
- [ ] Uji `backdrop-filter` di Firefox & Safari (fallback: `@supports not (backdrop-filter: blur(1px))` → pakai warna opak).
- [ ] `npm run build` → `wrangler deploy` → cek `https://mail.hafizhmuzani.my.id`.

**Total: 3–4 hari kerja** untuk versi A penuh.

---

## 6. Keputusan yang perlu diambil

| # | Pertanyaan | Opsi | Rekomendasi |
|---|---|---|---|
| 1 | Primary color | Biru `#1890ff` (sekarang) vs Hijau brand Solid Glass | **Hijau** — biar konsisten dengan material; kalau mau netral, pakai `--primary` Solid Glass yang justru hitam/putih |
| 2 | Cakupan kaca | Semua permukaan vs hanya panel besar | **Mulai dari panel besar**, tambah bertahap |
| 3 | `backdrop-filter` | Aktif vs mati | **Aktif** — tanpa blur, "glass" hilang |
| 4 | Font | Inter (sekarang?) vs Geist (Solid Glass) | **Geist** via `@fontsource-variable/geist` |
| 5 | Radius | Sekarang vs `0.875rem` | **0.875rem** (mengikuti material) |
| 6 | Grafik | Warna-warni vs abu-abu | **Abu-abu** (chart-1..5) atau brand untuk seri utama |
| 7 | Nama file | `solid-glass-vue.css` vs `solid-glass-ep.css` | **`solid-glass-ep.css`** (eksplisit: EP adapter) |

---

## 7. Risiko & mitigasi — **setelah diverifikasi ke source**

| Risiko | Tingkat | Mitigasi |
|---|---|---|
| **Spesifisitas `html.dark`** — adapter `.dark` kalah dari EP | **TINGGI** | Adapter **wajib** pakai `html.dark` atau `!important`. Sudah terbukti dari `dark/css-vars.css` + `style.css:167` |
| Blok `<style>` global bocor → regresi | **Sedang** | Audit 11 blok global sebelum mulai; ubah ke `scoped` bila perlu |
| `backdrop-filter` berat di mobile (blur 26px × banyak pane) | **Sedang** | Batasi ke pane besar; `@supports not (backdrop-filter)` → warna opak; matikan blur saat `prefers-reduced-motion` |
| Kontras teks turun (light `--muted-foreground` 0.47) | **Sedang** | Uji WCAG AA; light ≈ 5.7:1, dark ≈ 7:1 — keduanya lolos tapi cek placeholder 0.60 |
| `el-table` / `el-tree` / `el-statistic` susah di-glass-kan | **Sedang** | Beri latar opak di dalam pane; hanya container yang kaca |
| `el-dialog` + `backdrop-filter` + `position:fixed` | **Rendah** | Isi dialog opak, tepi kaca |
| TinyMCE iframe tak senada | **Rendah** | Override `.tox-*` sudah ada di `style.css:79-106`; sesuaikan warnanya |
| `--aside-backgound: #001529` (biru tua) → netral | **Rendah** | Ganti ke `--el-bg-color` / abu netral; visual aside berubah signifikan |
| `:deep()` ke internal EP | **RENDAH** ✅ | **Hanya 1** (`input__inner:focus`) — audit awal salah perkirakan |
| Sebenarnya rewrite besar perlu | **Tidak** ✅ | Hanya 5 var `--el-*` + 5 selector `.el-*` global yang disentuh app |
| Perbedaan nuansa upstream di masa depan | Rendah | Vendor file + catat commit hash upstream |

---

## 8. Fase Lanjutan (opsional, bila mau lebih dari A)

### 8a. Komponen "agent-native" Solid Glass
Solid Glass punya komponen khusus AI: `status-glyph`, `turn-status`, `composer`, `tool-steps`, `diff-view`, `context-ring`, `task-notice`, `reasoning`.
**Semuanya React.** Kalau mau, tulis ulang versi Vue-nya satu per satu (masing-masing ~50–150 baris) dan pakai di cloud-mail (mis. `status-glyph` untuk indikator kirim, `dot-loader` untuk loading).

### 8b. Adopsi Tailwind
Ganti SCSS bertahap dengan Tailwind 4 + `@theme` Solid Glass. Ini pintu masuk ke ekosistem shadcn **tanpa** pindah framework (ada `shadcn-vue`).
- Usaha: besar. Untung: komponen shadcn-vue bisa dipakai langsung dengan `data-slot` Solid Glass.
- Baru layak kalau mau **serius** mengadopsi ekosistem ini jangka panjang.

### 8c. Micro-frontend / rewrite bertahap
Halaman baru (mis. dashboard agent) dibangun di React + shadcn + Solid Glass, di-mount di route Vue. Kompleks, tapi memungkinkan eksperimen tanpa rewrite penuh.

---

## 9. Struktur file akhir (target Fase A)

```
mail-vue/src/
  theme/
    solid-glass.css          ← vendor dari upstream (MIT, jangan diedit)
    solid-glass-ep.css       ← ADAPTER: map --glass-* → --el-*  (file buatan kita)
    README.md                ← catatan versi upstream + lisensi
  style.css                  ← tetap, tapi delegasi warna ke theme/
  main.js                    ← import 'element-plus/theme-chalk/dark/css-vars.css'
                                + import './theme/solid-glass-ep.css'
```

---

## 10. Checklist hari-1 (bisa mulai sekarang)

1. [ ] Salin `solid-glass.css` upstream + catat commit hash-nya.
2. [ ] `grep -rn "\-\-el-" mail-vue/src` → daftar var EP yang dipakai.
3. [ ] Buat `solid-glass-ep.css` dengan blok `:root` + `.dark` yang memetakan warna inti saja (background, text, border, primary).
4. [ ] Import di `main.js` setelah `dark/css-vars.css`.
5. [ ] `npm run dev` → lihat sekilas apakah latar & teks sudah bergeser.
6. [ ] Iterasi: tambah `.glass-panel` ke aside/header, evaluasi.

---

## 11. Referensi

- Upstream: `github.com/deeplethe/solid-glass` (MIT) — `src/solid-glass.css` (1.409 baris)
- Live: `deeplethe.github.io/solid-glass`
- Registry: `npx shadcn add deeplethe/solid-glass/solid-glass` (untuk konteks React)
- Adapter Element Plus: variabel `--el-*` (lihat `element-plus/theme-chalk/src/common/var.scss`)
- Catatan lisensi: komponen & dokumen dari shadcn/ui di repo upstream adalah lisensi shadcn (MIT) — lihat `NOTICE.md` upstream. **Saat vendor, sertakan LICENSE + NOTICE.**
