# Bab 1 — Dasar Bisnis Credit Risk: Kenapa Ada yang Mau Meminjamkan Uang?

## 1.1 Mulai dari warung, analogi paling dasar

Bayangkan warung Bu Tejo. Pelanggan tetapnya boleh ngebon alias kasbon, yaitu mengambil barang sekarang dan membayarnya akhir bulan. Kenapa Bu Tejo mau repot-repot begitu?

Pertama, penjualannya naik karena orang yang sedang tidak pegang uang pun tetap bisa belanja. Kedua, pelanggan jadi setia, sebab orang yang diberi bon jarang pindah ke warung lain. Ketiga, dan ini kuncinya, Bu Tejo kenal pelanggannya. Dia tahu Pak RT pasti bayar, dan dia juga tahu si Anu suka ngemplang.

Tentu ada risikonya, yaitu sebagian bon tidak pernah dibayar. Karena itu, diam-diam Bu Tejo melakukan tiga hal yang ternyata merupakan inti seluruh industri kredit.

1. Dia menyeleksi siapa yang boleh ngebon. Tidak semua orang!
2. Dia membatasi besar bon per orang. Pak RT boleh sampai lima ratus ribu, sedangkan orang baru cukup lima puluh ribu.
3. Dia menaikkan harga sedikit untuk menutup bon yang hangus.

Bank dan multifinance pada dasarnya adalah warung Bu Tejo dalam skala jutaan pelanggan. Bedanya, Bu Tejo mengenal kelima puluh pelanggannya secara pribadi, sementara multifinance harus menilai ribuan orang asing setiap hari. Seluruh disiplin credit risk management lahir dari satu pertanyaan sederhana. Bagaimana caranya menilai orang asing secepat dan seakurat Bu Tejo menilai tetangganya sendiri?

## 1.2 Dari mana untungnya, dan ke mana perginya

Mari kita sederhanakan mesin uang bisnis pembiayaan untuk satu kontrak motor.

```
Pendapatan bunga dan biaya    : + Rp 3.000.000   (selama masa kredit)
Biaya dana (cost of fund)     : - Rp 1.200.000   (uang yang dipinjamkan pun "disewa" dari bank atau obligasi)
Biaya operasional & akuisisi  : - Rp   700.000   (gaji sales, survei, sistem)
Kerugian kredit (credit loss) : - Rp   ???       ← inilah yang dikelola tim credit risk
─────────────────────────────
Laba                          : sisanya
```

Perhatikan baik-baik. Tiga baris pertama nilainya relatif tetap, sehingga satu-satunya angka yang bisa meledak adalah kerugian kredit. Kalau dari seratus kontrak ada tiga yang gagal bayar total, bisnis masih untung. Namun kalau yang gagal delapan, seluruh laba ikut hangus, bahkan modal pun tergerus. Margin bisnis pembiayaan itu tipis. Selisih beberapa persen tingkat gagal bayar saja sudah menentukan hidup matinya perusahaan.

> **Analogi.** Pedagang buah selalu memperhitungkan bahwa dari seratus kilo mangga, lima kilo pasti busuk sebelum laku. Dia tetap untung karena tingkat busuknya terprediksi dan sudah dimasukkan ke harga jual. Bisnisnya hancur bukan karena ada buah busuk, melainkan kalau tiba-tiba yang busuk dua puluh kilo. Credit risk management adalah pekerjaan memastikan "tingkat busuk" tetap berada di angka yang sudah diperhitungkan.

## 1.3 Rumus mental orang risk, yaitu expected loss

Orang risk memandang setiap pinjaman lewat tiga pertanyaan. Kerangka ini nantinya juga dekat dengan dunia Anda sebagai data scientist.

| Komponen | Pertanyaannya | Contoh |
|---|---|---|
| **PD** (Probability of Default) | Berapa peluang orang ini gagal bayar? | 4% |
| **LGD** (Loss Given Default) | Kalau dia gagal, berapa persen uang yang benar-benar hilang setelah motornya ditarik dan dilelang? | 40% |
| **EAD** (Exposure at Default) | Saat dia gagal, sisa utangnya berapa? | Rp 10 juta |

Ketiganya dikalikan menjadi expected loss. Dalam contoh ini, 4% dikali 40% dikali sepuluh juta menghasilkan Rp 160.000. Kalau margin bersih dari kontrak itu Rp 900.000, kontraknya layak diambil. Sebaliknya, kalau PD-nya 15%, expected loss membengkak menjadi Rp 600.000 dan hampir memakan seluruh margin. Pilihannya menjadi menolak, atau mengecilkan pinjaman supaya EAD turun, atau meminta uang muka lebih besar supaya LGD turun, atau menaikkan bunga supaya marginnya naik.

Di sinilah terlihat satu hal penting. Keputusan kredit bukan sekadar ya atau tidak, melainkan juga bisa berupa penyesuaian limit, tenor, uang muka, dan harga. Itulah alasan decision engine nantinya tidak hanya mengeluarkan APPROVE atau REJECT, tetapi juga limit, tenor, dan pricing.

## 1.4 Tarik-menarik abadi antara gas dan rem

Setiap perusahaan pembiayaan punya dua pedal. Pedal gas dipegang tim bisnis, karena semakin banyak yang disetujui, volume dan pangsa pasar ikut naik. Pedal rem dipegang tim risk, karena semakin selektif persetujuan, kerugian semakin kecil walaupun volumenya ikut turun.

> **Analogi jaring ikan.** Kebijakan kredit itu seperti memilih ukuran mata jaring. Jaring yang rapat menyaring ikan kecil, dalam hal ini nasabah berisiko, tetapi banyak ikan bagus ikut lolos tak tertangkap, artinya bisnis hilang. Jaring yang longgar menghasilkan tangkapan banyak, tetapi penuh ikan buruk. Tidak ada ukuran jaring yang "benar". Yang ada hanyalah pilihan sadar perusahaan mau berdiri di titik mana, dan pilihan itulah yang disebut credit policy atau risk appetite.

Ada dua jenis kesalahan yang selalu ditimbang. Yang pertama salah tolak, yaitu menolak orang yang sebenarnya akan lancar, sehingga perusahaan kehilangan margin dan orang itu menjadi nasabah pesaing. Yang kedua salah terima, yaitu menerima orang yang akhirnya gagal bayar, sehingga perusahaan kehilangan pokok pinjaman.

Karena kehilangan pokok jauh lebih menyakitkan daripada kehilangan margin, dunia kredit secara alami cenderung konservatif. Namun terlalu konservatif juga mematikan karena tidak ada pendapatan sama sekali. Menyeimbangkan keduanya itulah pekerjaan harian orang-orang yang akan Anda temui di bab 2.

## 1.5 Cara menilai orang asing lewat kerangka 5C

Ada kerangka klasik penilaian kredit yang disebut 5C. Cara berpikir inilah yang nanti menjelma menjadi rule dan fitur model.

| C | Artinya | Analogi menilai calon penyewa kos | Wujudnya di data |
|---|---|---|---|
| **Character** | Niat dan rekam jejak bayar | "Di kos yang lama bayarnya lancar tidak?" | Riwayat SLIK, kolektibilitas, riwayat keterlambatan, daftar hitam |
| **Capacity** | Kemampuan bayar dari penghasilan | "Gajinya cukup tidak untuk bayar kos tiap bulan?" | Penghasilan, DTI atau FOIR, jumlah cicilan berjalan |
| **Capital** | Modal atau kekayaan sendiri | "Punya tabungan tidak kalau kepepet?" | Uang muka, saldo tabungan, aset |
| **Collateral** | Jaminan yang bisa diambil kalau gagal | "Ada deposit yang bisa dipotong?" | Nilai dan usia kendaraan, LTV |
| **Condition** | Kondisi eksternal | "Kerjanya di industri yang sedang PHK massal bukan?" | Jenis pekerjaan, industri, wilayah, kondisi ekonomi |

Multifinance menerjemahkan kelima C itu menjadi hal-hal yang terukur, misalnya umur, penghasilan, DTI yang merupakan rasio cicilan terhadap penghasilan, LTV yang merupakan rasio pinjaman terhadap nilai kendaraan, riwayat hari keterlambatan, dan skor kredit. Angka-angka inilah bahan baku rule dan model. Di OSCAR, semuanya hidup sebagai feature catalog, misalnya `applicant.monthly_income`, `loan.ltv`, `affordability.dti`, dan `bureau.max_dpd_12m`.

## 1.6 Contoh kasus mini, dua pemohon dengan satu kebijakan

Produknya lease-back motor. Artinya, pemilik motor "menjual" motornya ke perusahaan pembiayaan lalu mengangsurnya kembali. Motornya menjadi jaminan, sedangkan uang tunainya cair ke pemilik.

| | Pak Budi | Mas Roni |
|---|---|---|
| Pengajuan | 15 juta, 24 bulan | 18 juta, 36 bulan |
| Penghasilan | 8,5 juta per bulan | 4 juta per bulan, tidak tetap |
| Cicilan berjalan | 2,5 juta per bulan | 1,8 juta per bulan |
| **DTI (capacity)** | (2,5 jt + kira-kira 0,8 jt cicilan baru) dibagi 8,5 jt, sekitar **39%** | (1,8 jt + kira-kira 0,9 jt) dibagi 4 jt, sekitar **67%** |
| Motor (collateral) | Vario 2020, taksiran 18 juta, jadi **LTV 83%** | Beat 2013, taksiran 9 juta, jadi **LTV 200%** ⚠️ |
| Riwayat SLIK (character) | Lancar, tidak pernah telat | Pernah telat 45 hari tahun lalu |

Tanpa alat apa pun, intuisi Anda pasti sudah berbisik. Pak Budi layak dibiayai, mungkin dengan sedikit syarat, sedangkan Mas Roni sangat berisiko karena dia meminta dua kali lipat nilai motornya sendiri.

Credit policy pada dasarnya adalah pekerjaan menuliskan intuisi semacam itu menjadi aturan yang eksplisit. Misalnya DTI maksimal 45%, LTV maksimal 85%, dan keterlambatan dalam dua belas bulan terakhir maksimal 30 hari. Tujuannya supaya ribuan kasus per hari dinilai secara konsisten oleh siapa pun, termasuk oleh mesin, dan hasilnya bisa dipertanggungjawabkan. Bagaimana aturan-aturan itu dijalankan secara otomatis? Itulah cerita bab 3 dan bab 4.

## 1.7 Rangkuman bab

1. Bisnis pembiayaan untung dari margin bunga, dan satu-satunya biaya yang liar adalah kerugian kredit. Mengelola kerugian kredit sama saja dengan mengelola hidup matinya perusahaan.
2. Kerangka berpikirnya adalah expected loss, yaitu PD dikali LGD dikali EAD. Karena itu keputusan kredit bukan cuma ya atau tidak, melainkan juga limit, tenor, uang muka, dan harga.
3. Kebijakan kredit adalah pilihan sadar tentang posisi di tarik-menarik antara risiko dan pertumbuhan, seperti memilih ukuran mata jaring.
4. Orang asing dinilai lewat kerangka 5C yang diterjemahkan menjadi fitur terukur, dan fitur itulah bahan baku rule serta model.
