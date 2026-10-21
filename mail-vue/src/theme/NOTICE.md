# Tema Solid Glass — catatan

Folder ini memuat tema **Solid Glass** yang di-adaptasi ke Element Plus.

## Isi

| Berkas | Keterangan |
|---|---|
| `solid-glass-ep.css` | **Adapter** — material Solid Glass dipetakan ke variabel `--el-*` dan kelas `.glass-*`. Ini satu-satunya berkas yang di-`import` app. |
| `LICENSE.solid-glass` | Lisensi MIT upstream (DeepLethe). |
| `NOTICE.solid-glass.md` | Notis upstream (komponen dari shadcn/ui). |
| `NOTICE.md` | Notis ini. |

## Sumber upstream

- Repo: https://github.com/deeplethe/solid-glass
- Commit: `6e8903e494a15491ceda38fafea5056c95a74d44` (2026-10-16)
- Lisensi: MIT © 2026 DeepLethe

Adapter **tidak** menyalin `solid-glass.css` upstream apa adanya, karena upstream
memakai at-rule Tailwind (`@theme`, `@apply`) dan menargetkan `data-slot` komponen
shadcn/ui — keduanya tidak ada di app Vue + Element Plus ini. Yang disalin adalah
**nilai token materialnya** (warna `oklch`, token `--glass-*`, aturan box-shadow
kaca), lalu diarahkan ke `--el-*`.

## Aturan saat meng-update dari upstream

1. Ambil `src/solid-glass.css` dari upstream, baca blok `:root` dan `.dark`.
2. Bandingkan nilai token material (`--glass-rim`, `--glass-shade`, `--glass-blur`,
   warna `oklch`, `--chart-*`, `--sg-brand`) dengan `solid-glass-ep.css`.
3. Salin perubahannya — **jangan** bawa `@theme`/`@apply`/`data-slot`.
4. Perbarui commit hash di atas.

## Jebakan yang harus diingat

- **Spesifisitas dark mode.** `element-plus/theme-chalk/dark/css-vars.css` memakai
  selektor `html.dark` (spesifisitas 0,1,1). Adapter **wajib** memakai `html.dark`
  juga — `.dark` (0,1,0) akan kalah dan material tidak terpakai di mode gelap.
- **Urutan impor.** `solid-glass-ep.css` harus di-import **setelah**
  `element-plus/theme-chalk/dark/css-vars.css` di `main.js`.
- **Primary = pane solid.** Solid Glass tidak memakai gradien di muka
  (aturan "finish is at the edge"). Tombol/judul utama memakai `--sg-solid`
  (pane solid ber-rim) dan brand hijau hanya sebagai aksen.
