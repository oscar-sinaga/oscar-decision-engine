# Bab 01 — Mulai, Navigasi, dan Siklus Hidup yang Berlaku di Mana-mana

## 1.1 Masuk ke aplikasi

Buka `http://localhost:3000`, masuk dengan salah satu akun demo, dan Anda mendarat di Dashboard. Menu di sisi kiri menyesuaikan izin akun. Akun `underwriter` misalnya tidak melihat tombol aktivasi strategy, bukan karena disembunyikan iseng, melainkan karena server memang tidak mengizinkannya. Tampilan hanyalah cermin dari izin yang ditegakkan di belakang.

## 1.2 Latar belakang, kenapa semuanya harus berversi

Sebelum masuk ke tombol-tombolnya, pahami dulu masalah yang mau dicegah. Di banyak perusahaan, kebijakan kredit hidup di file Excel yang ditimpa-timpa atau di kode program yang berubah tanpa arsip. Ketika auditor bertanya "aplikasi ini ditolak Maret lalu berdasarkan aturan apa", tidak ada yang bisa menjawab pasti, karena aturan bulan Maret sudah tak berbentuk. Ketika kebijakan baru ternyata merusak, tidak ada jalan pulang yang rapi. Dan ketika seseorang khilaf mengubah ambang, tidak ada yang tahu siapa dan kapan.

OSCAR menutup ketiga lubang itu dengan satu disiplin, yaitu **setiap kebijakan hidup sebagai versi**. Disiplin inilah yang membuat semua layar terasa "ribet satu langkah" dibanding mengedit Excel, dan keribetan itu disengaja.

## 1.3 Siklus hidup versi

Hampir semua objek kebijakan, baik rule, decision table, scorecard, maupun strategy, menjalani siklus yang sama. Pahami sekali di sini dan semua bab berikutnya terasa familiar.

```
DRAFT ──ajukan──▶ PENDING_APPROVAL ──setujui──▶ ACTIVE ──tergantikan──▶ RETIRED
  ▲                     │tolak                                             │
  └── buat draft baru ◀─┴──────── REJECTED                 rollback ◀──────┘  (khusus strategy)
```

Aturan mainnya empat, dan masing-masing punya alasan.

1. **Hanya draft yang bisa diedit.** Begitu diajukan atau aktif, isinya terkunci selamanya. Alasannya, keputusan kredit yang sudah terjadi harus bisa dijelaskan dengan aturan versi saat itu. Kalau versi aktif boleh diedit diam-diam, penjelasan itu runtuh. Ingin mengubah aturan yang aktif? Buat versi baru darinya, edit draftnya, lalu jalani siklusnya lagi.
2. **Pengaju dan penyetuju harus orang berbeda.** Prinsip ini bernama maker-checker, dan sistem menegakkannya, bukan sekadar menganjurkan. Kebijakan kredit terlalu berdampak untuk diputuskan sepasang tangan, sekaligus ini melindungi si pembuat sendiri karena keputusan tidak pernah dipikulnya sendirian.
3. **Khusus strategy, aktivasi menuntut lampiran simulasi.** Alasannya sederhana, penyetuju berhak melihat bukti dampak sebelum kebijakan hidup, bukan sekadar janji. Tanpa lampiran itu tombol aktivasi menolak bekerja.
4. **Versi lama tidak pernah dihapus,** hanya berganti status menjadi RETIRED. Karena itu pula tersedia rollback untuk strategy, yaitu menghidupkan kembali versi lama dengan alasan wajib. Sejarah tidak ditulis ulang, hanya diberi babak baru.

> **Analogi.** Anggap tiap versi seperti edisi buku resep yang sudah dicetak. Edisi yang beredar tidak dicoret-coret. Kalau resep berubah, terbitkan edisi baru lewat persetujuan kepala dapur, dan edisi lama tetap diarsip supaya semua orang tahu masakan tahun lalu mengikuti resep yang mana.

## 1.4 Siapa boleh apa

Tabel ini merangkum izin yang paling sering dibutuhkan. Sekali lagi, ini ditegakkan server, bukan sekadar diatur tampilannya.

| Aksi | riskanalyst | riskmanager | underwriter | compliance | datascientist | auditor | admin |
|---|---|---|---|---|---|---|---|
| Melihat keputusan dan trace | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Membuat draft rule, tabel, strategy | ✓ | ✓ | — | — | — | — | ✓ |
| Menyetujui dan mengaktifkan | — | ✓ | — | — | — | — | ✓ |
| Menjalankan simulasi | ✓ | ✓ | — | — | ✓ | — | ✓ |
| Memutus kasus manual review | — | ✓ | ✓ | — | — | — | ✓ |
| Membatalkan vonis fraud | — | ✓ | — | — | — | — | ✓ |
| Membaca audit log | — | ✓ | — | ✓ | — | ✓ | ✓ |
| Mengelola model registry | — | ✓ | — | — | ✓ | — | ✓ |
| Menulis rule expression | — | — | — | — | — | — | ✓ |
| Mengelola pengguna dan peran | — | — | — | — | — | — | ✓ |

Kenapa pembagiannya begini? Polanya konsisten, yaitu yang membuat tidak menyetujui, yang menyetujui tidak mengubah isi, yang memeriksa tidak bisa menghapus jejak, dan kekuatan paling berbahaya seperti expression dibatasi paling ketat dulu. Justru karena setiap peran terbatas, keseluruhan sistem jadi bisa dipercaya.

## 1.5 Irama kerja yang akan terus berulang

Hampir semua pekerjaan kebijakan mengikuti lima langkah yang sama. Buat atau ubah sesuatu sebagai draft. Uji, entah lewat tombol test pada rule maupun lewat menu Simulations. Ajukan, dengan lampiran simulasi kalau objeknya strategy. Minta orang lain menyetujui. Terakhir, pantau dampaknya di Dashboard dan bersiap untuk iterasi berikutnya. Kalau Anda hafal irama ini, tidak ada layar yang benar-benar baru.

## 1.6 Tiga jenis rekaman yang sering tertukar

OSCAR sengaja memisahkan tiga jenis catatan karena pembacanya berbeda dan kebutuhannya berbeda.

| Rekaman | Menjawab pertanyaan | Pembacanya | Letaknya |
|---|---|---|---|
| **Decision trace** | Kenapa aplikasi ini hasilnya begini | Risk, underwriter, auditor | Halaman detail keputusan |
| **Audit log** | Siapa mengubah apa, kapan, dan atas persetujuan siapa | Compliance dan audit | Menu Audit Log |
| **Log teknis** | Sistemnya sehat atau tidak | Engineering | Di luar workbench |

Kalau ketiganya dicampur jadi satu, yang terjadi adalah auditor tenggelam di log teknis dan engineer tersandung data sensitif. Pemisahan ini bukan kebetulan arsitektur, melainkan kebutuhan tata kelola.
