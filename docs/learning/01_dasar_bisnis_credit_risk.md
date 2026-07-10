# Bab 1 — Dasar Bisnis Credit Risk: Kenapa Ada yang Mau Meminjamkan Uang?

## 1.1 Mulai dari warung: analogi paling dasar

Bayangkan **warung Bu Tejo**. Pelanggan tetap boleh **ngebon** (kasbon): ambil barang sekarang, bayar akhir bulan. Kenapa Bu Tejo mau?

1. **Penjualan naik** — orang yang lagi bokek tetap belanja.
2. **Pelanggan jadi setia** — yang dikasih bon jarang pindah warung.
3. Bu Tejo **kenal** pelanggannya — dia tahu Pak RT pasti bayar, dan tahu si Anu suka ngemplang.

Tapi ada risikonya: sebagian bon **tidak pernah dibayar**. Maka diam-diam Bu Tejo melakukan tiga hal yang — percaya atau tidak — adalah inti seluruh industri kredit:

1. **Menyeleksi** siapa yang boleh ngebon (tidak semua orang!).
2. **Membatasi** berapa besar bon per orang (Pak RT boleh 500 ribu, orang baru cuma 50 ribu).
3. **Menaikkan harga sedikit** untuk menutup bon yang hangus.

Bank dan multifinance adalah **warung Bu Tejo dalam skala jutaan pelanggan**. Masalahnya: Bu Tejo kenal 50 pelanggannya secara pribadi; multifinance harus menilai **ribuan orang asing per hari**. Seluruh disiplin *credit risk management* lahir dari satu pertanyaan: **bagaimana menilai orang asing secepat dan seakurat Bu Tejo menilai tetangganya?**

## 1.2 Dari mana untungnya, dan ke mana perginya

Mesin uang bisnis pembiayaan (disederhanakan) untuk 1 kontrak motor:

```
Pendapatan bunga & biaya      : + Rp 3.000.000   (selama tenor)
Biaya dana (cost of fund)     : - Rp 1.200.000   (uang yang dipinjamkan pun "disewa" dari bank/obligasi)
Biaya operasional & akuisisi  : - Rp   700.000   (sales, survey, sistem, gaji)
Kerugian kredit (credit loss) : - Rp   ???       ← INI YANG DIKELOLA CREDIT RISK
─────────────────────────────
Laba                          : sisanya
```

Perhatikan: tiga baris pertama relatif tetap. **Satu-satunya angka yang bisa meledak adalah credit loss.** Kalau dari 100 kontrak ada 3 yang gagal bayar total (loss 3%), bisnis untung. Kalau 8 yang gagal (loss 8%), seluruh laba — dan sebagian modal — hangus. Margin lending itu tipis; **beda beberapa persen bad rate = beda hidup-mati perusahaan.**

> **Analogi:** pedagang buah memperhitungkan bahwa dari 100 kg mangga, 5 kg pasti busuk sebelum laku. Ia tetap untung *karena busuknya terprediksi dan sudah dihargai*. Bisnisnya hancur bukan karena ada buah busuk, tapi kalau tiba-tiba yang busuk 20 kg. Credit risk management = memastikan "tingkat busuk" tetap di angka yang sudah diperhitungkan.

## 1.3 Rumus mental yang dipakai orang risk: Expected Loss

Orang risk memandang setiap pinjaman dengan tiga pertanyaan (ini juga fondasi matematis yang nanti dekat dengan dunia Anda sebagai DS):

| Komponen | Pertanyaan | Contoh |
|---|---|---|
| **PD** (Probability of Default) | Berapa peluang orang ini gagal bayar? | 4% |
| **LGD** (Loss Given Default) | Kalau gagal, berapa % uang yang benar-benar hilang? (setelah motor ditarik & dilelang) | 40% |
| **EAD** (Exposure at Default) | Saat gagal, sisa utangnya berapa? | Rp 10 juta |

**Expected Loss = PD × LGD × EAD** = 4% × 40% × 10 juta = **Rp 160.000**. Kalau margin bersih dari kontrak itu Rp 900.000, kontrak ini layak. Kalau PD-nya 15%, EL = Rp 600.000 — hampir memakan seluruh margin → tolak, atau kecilkan pinjaman (EAD turun), atau minta uang muka lebih besar (LGD turun), atau naikkan bunga (margin naik). **Lihat: "keputusan kredit" bukan cuma ya/tidak — ia bisa berupa limit, tenor, DP, dan harga.** Ini alasan kenapa decision engine nanti outputnya bukan cuma APPROVE/REJECT tapi juga limit/tenor/pricing.

## 1.4 Trade-off abadi: gas vs rem

Setiap perusahaan pembiayaan punya dua pedal:

- **Gas (bisnis/sales):** approve lebih banyak → volume naik, market share naik, komisi naik.
- **Rem (risk):** approve lebih selektif → kerugian turun, tapi volume turun.

> **Analogi jaring ikan:** kebijakan kredit itu seperti memilih ukuran mata jaring. Jaring rapat = ikan kecil (nasabah berisiko) tersaring, tapi banyak ikan bagus ikut lolos tak tertangkap (kehilangan bisnis). Jaring longgar = tangkapan banyak, tapi penuh ikan buruk. **Tidak ada jaring yang "benar" — yang ada adalah pilihan sadar di mana perusahaan mau berdiri**, dan pilihan itu bernama *credit policy* (risk appetite).

Dua kesalahan yang selalu ditimbang:
- **Salah tolak (false reject):** menolak orang yang sebenarnya akan lancar → kehilangan margin + orang itu jadi nasabah kompetitor.
- **Salah terima (false approve):** menerima orang yang gagal bayar → rugi pokok.

Karena rugi pokok jauh lebih besar dari kehilangan margin, dunia kredit "default-nya konservatif" — tapi terlalu konservatif juga mati (tidak ada pendapatan). Menyeimbangkan inilah pekerjaan harian orang-orang yang akan Anda temui di bab 2.

## 1.5 Bagaimana orang asing dinilai: 5C

Kerangka klasik penilaian kredit — cara berpikir yang nanti Anda lihat menjelma jadi *rules* dan *fitur model*:

| C | Arti | Analogi menilai calon penyewa kos | Wujudnya di data |
|---|---|---|---|
| **Character** | Niat & rekam jejak bayar | "Dulu di kos lama bayarnya lancar nggak?" | Riwayat SLIK/bureau, kolektibilitas, DPD historis, blacklist |
| **Capacity** | Kemampuan bayar dari penghasilan | "Gajinya cukup nggak buat bayar kos tiap bulan?" | Penghasilan, DTI/FOIR, jumlah cicilan berjalan |
| **Capital** | Modal/kekayaan sendiri | "Punya tabungan nggak kalau kepepet?" | Uang muka (DP), saldo tabungan, aset |
| **Collateral** | Jaminan yang bisa diambil kalau gagal | "Ada deposit yang bisa dipotong?" | Nilai & usia kendaraan, LTV |
| **Condition** | Kondisi eksternal | "Kerjanya di industri yang lagi PHK massal?" | Jenis pekerjaan, industri, wilayah, kondisi ekonomi |

Multifinance menerjemahkan 5C ini menjadi hal-hal yang **terukur**: umur, penghasilan, DTI (rasio cicilan/penghasilan), LTV (pinjaman/nilai kendaraan), riwayat DPD (hari keterlambatan), skor kredit. Angka-angka inilah **bahan baku** rule dan model — dan di OSCAR mereka hidup sebagai *feature catalog* (`applicant.monthly_income`, `loan.ltv`, `affordability.dti`, `bureau.max_dpd_12m`, ...).

## 1.6 Contoh kasus mini: dua pemohon, satu kebijakan

Produk: lease-back motor (pemilik motor "menjual" motornya ke perusahaan lalu mengangsurnya kembali — motor jadi jaminan, uang tunai cair ke pemilik).

| | Pak Budi | Mas Roni |
|---|---|---|
| Pengajuan | 15 juta, 24 bulan | 18 juta, 36 bulan |
| Penghasilan | 8,5 juta/bln | 4 juta/bln (tidak tetap) |
| Cicilan berjalan | 2,5 jt/bln | 1,8 jt/bln |
| **DTI (capacity)** | (2,5jt + ±0,8jt cicilan baru) / 8,5jt ≈ **39%** | (1,8jt + ±0,9jt) / 4jt ≈ **67%** |
| Motor (collateral) | Vario 2020, taksiran 18 jt → **LTV 83%** | Beat 2013, taksiran 9 jt → **LTV 200%** ⚠️ |
| Riwayat SLIK (character) | Lancar, DPD 0 | Pernah DPD 45 hari tahun lalu |

Tanpa alat apa pun, intuisi Anda sudah bilang: Pak Budi layak (mungkin dengan syarat), Mas Roni sangat berisiko (minta 2× nilai motornya!). **Credit policy adalah menuliskan intuisi itu menjadi aturan eksplisit** — "DTI maksimal 45%", "LTV maksimal 85%", "DPD 12 bulan terakhir maksimal 30 hari" — supaya ribuan kasus per hari dinilai **konsisten**, oleh siapa pun (atau oleh mesin), dan bisa dipertanggungjawabkan. Bagaimana aturan-aturan itu dijalankan secara otomatis? Itulah cerita bab 3 & 4.

## 1.7 Rangkuman bab

1. Lending untung dari margin bunga; satu-satunya biaya yang liar adalah **credit loss** — mengelolanya = mengelola hidup-mati perusahaan.
2. Kerangka pikirnya **Expected Loss = PD × LGD × EAD**; karena itu keputusan kredit bukan cuma ya/tidak tapi juga **limit, tenor, DP, harga**.
3. Kebijakan kredit = **pilihan sadar posisi di trade-off** risiko vs pertumbuhan (ukuran mata jaring).
4. Orang asing dinilai lewat **5C** yang diterjemahkan menjadi fitur terukur — bahan baku rules & model.
