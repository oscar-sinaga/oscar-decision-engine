# Bab 6 — Konsep-Konsep Penting yang Selalu Muncul di Dunia Decision Engine

Ada delapan konsep yang akan terus Anda dengar di rapat-rapat risk. Masing-masing dijelaskan lewat empat hal, yaitu apa maksudnya, kenapa penting, analoginya, dan contohnya.

## 6.1 Versioning dan immutability, ibarat undang-undang bernomor yang tak bisa disunting diam-diam

**Apa maksudnya.** Setiap konfigurasi, baik rule, scorecard, decision table, maupun strategy, hidup sebagai versi. Versi yang sudah aktif tidak bisa diedit. Kalau mau mengubah, buatlah versi baru yang berjalan dari draft, lalu diajukan, disetujui, dan akhirnya aktif. Versi lama menjadi arsip yang tetap tersimpan. Setiap keputusan mencatat versi mana yang persis dipakainya.

**Kenapa penting.** Pertama demi rekonstruksi, karena keputusan dua tahun lalu harus bisa dijelaskan dengan aturan yang berlaku saat itu. Kedua demi tanggung jawab, karena jelas siapa menerbitkan versi mana. Ketiga demi rollback, karena kembali ke versi lama berarti mengaktifkan arsip, bukan menulis ulang sejarah.

> **Analogi.** Perundang-undangan. UU Nomor 5 Tahun 2023 tidak pernah "diedit", melainkan diubah oleh UU Nomor 12 Tahun 2025. Keduanya tetap ada di lembaran negara, dan perkara tahun 2024 diadili dengan undang-undang yang berlaku pada tahun 2024. Bandingkan dengan file Excel bernama `kebijakan_final_v2_FIX_beneran.xlsx` yang ditimpa orang setiap minggu.

**Contoh.** Seorang nasabah menggugat penolakan bulan Maret. Compliance membuka trace dan menemukan catatan `DTI_MAX_STANDARD v3` dengan ambang 0.45. Meskipun sekarang aturannya sudah versi 5 dengan ambang 0.42, versi 3 tetap bisa dibuka utuh. Kasus selesai.

## 6.2 Simulation dan impact analysis, ibarat terowongan angin sebelum terbang

**Apa maksudnya.** Kebijakan yang masih draft dijalankan terhadap data, entah satu kasus atau ribuan kasus historis, tanpa efek apa pun ke produksi. Hasilnya lalu dibandingkan dengan kebijakan yang aktif. Berapa perubahan approval rate, siapa yang tadinya disetujui menjadi ditolak dan sebaliknya, serta reason code apa yang naik.

**Kenapa penting.** Kebijakan kredit adalah keputusan bernilai miliaran dengan umpan balik yang baru datang enam sampai dua puluh empat bulan kemudian. Satu-satunya cara mencicipi masa depan adalah mengujinya ke masa lalu.

> **Analogi.** Terowongan angin untuk desain pesawat, atau dapur uji sebelum menu baru dikirim ke lima ratus cabang. Tidak ada maskapai yang menguji sayap baru langsung dengan penumpang sungguhan.

**Contoh.** Ada usulan menurunkan ambang DTI dari 0.45 ke 0.40. Simulasi batch atas sepuluh ribu aplikasi historis menunjukkan approval turun dari 44% ke 38%, penolakan naik terpusat di channel dealer, ada estimasi volume yang hilang, dan ada estimasi penurunan bad rate. Rapat pun memutuskan dengan angka, bukan firasat. Hasil simulasi ini juga wajib dilampirkan saat meminta persetujuan aktivasi, dan di OSCAR kewajiban itu ditegakkan oleh sistem.

## 6.3 Cutoff dan swap set, ibarat menggeser passing grade

**Apa maksudnya.** Cutoff adalah ambang skor keputusan, misalnya skor 640 ke atas disetujui dan di bawahnya tidak. Menggeser cutoff berarti menggeser tarik-menarik di bab 1 secara paling langsung. Adapun swap set adalah analisis tentang siapa saja yang bertukar nasib ketika kebijakan berubah. Ada swap-in, yaitu yang dulu ditolak menjadi diterima, dan ada swap-out, yaitu yang dulu diterima menjadi ditolak.

**Kenapa penting.** Dua kebijakan bisa menghasilkan approval rate yang sama tetapi komposisinya berbeda. Yang menentukan untung rugi bukan berapa banyak yang diterima, melainkan siapa saja yang diterima.

> **Analogi.** Passing grade ujian masuk. Menurunkan passing grade memang menambah jumlah mahasiswa, tetapi pertanyaannya adalah seperti apa kualitas mahasiswa tambahan itu, alias kelompok swap-in. Sebaliknya, menaikkan passing grade membuang sebagian pendaftar. Apakah yang terbuang memang yang bermasalah, atau justru ikut terbuang juga yang baik?

**Contoh.** Cutoff diturunkan dari 640 ke 620 sehingga approval naik tujuh poin persentase. Kohor swap-in diperkirakan punya bad rate 6%, padahal portofolio saat ini 3%. Layak atau tidak? Hitung saja margin tambahan dibanding expected loss tambahan. Kalau margin per kontrak menutup kerugian kohor itu, ambil. Kalau tidak, jangan, atau ambil dengan syarat, misalnya limit lebih kecil dan uang muka lebih besar khusus band skor 620 sampai 639. Ingat, keputusan kredit tidak harus biner.

## 6.4 Reason codes, ibarat diagnosis tertulis dan bukan sekadar "pokoknya sakit"

**Apa maksudnya.** Reason code adalah kode alasan baku, misalnya HIGH_DTI, LTV_ABOVE_THRESHOLD, dan BLACKLIST_HIT, yang menyertai setiap penolakan, review, maupun persetujuan bersyarat. Kode-kode ini dikelola sebagai katalog dan punya dua versi pesan, yaitu pesan internal dan pesan yang pantas dibaca nasabah.

**Kenapa penting.** Pertama untuk komunikasi ke nasabah dan regulator. Kedua untuk agregasi, karena kode yang baku bisa dihitung. Kalimat seperti "penyebab penolakan nomor satu bulan ini adalah HIGH_DTI sebesar 38%" hanya mungkin kalau alasannya berbentuk kode, bukan teks bebas. Ketiga sebagai bahan analisis, karena reason code pada dasarnya adalah telemetri kebijakan.

> **Analogi.** Kode diagnosis di rumah sakit. Karena semua dokter memakai kode yang sama, manajemen bisa melihat bahwa kasus DBD naik tiga kali lipat bulan ini. Hal itu mustahil kalau setiap dokter menulis narasi bebas semaunya.

## 6.5 Maker-checker, ibarat dua kunci peluncuran

**Apa maksudnya.** Pembuat perubahan, sang maker, tidak boleh menjadi penyetujunya, sang checker. Di OSCAR aturan ini ditegakkan mesin. Menyetujui usulan sendiri akan ditolak, dan aktivasi strategy juga menuntut bukti simulasi terlampir.

**Kenapa penting.** Kebijakan kredit terlalu berdampak untuk diputuskan sepasang tangan saja. Mekanisme ini melindungi dari kesalahan, kelalaian, dan niat jahat sekaligus. Ia bahkan melindungi si pembuat sendiri, karena dia bisa berkata bahwa keputusan itu bukan keputusannya seorang diri.

> **Analogi.** Peluncuran rudal membutuhkan dua kunci yang diputar dua orang, dan cek perusahaan membutuhkan dua tanda tangan. Bukan karena orangnya tidak dipercaya, melainkan karena sistemnya memang tidak boleh bergantung pada kepercayaan.

## 6.6 Audit trail, ibarat kamera pengawas di ruang arsip

**Apa maksudnya.** Audit trail adalah catatan yang hanya bisa ditambah, tidak bisa diubah, atas setiap tindakan yang mengubah keadaan. Isinya siapa, kapan, melakukan apa, dari nilai berapa ke nilai berapa, apa alasannya, dan siapa penyetujunya. Catatan ini terpisah dari log teknis yang dibaca engineer, dan terpisah pula dari trace yang menjelaskan satu keputusan. Jadi ada tiga lapisan bukti dengan pembaca yang berbeda-beda.

**Kenapa penting.** Regulator dan auditor tidak menilai niat baik. Mereka menilai bukti. Sifat tambah-saja berarti koreksi pun dicatat sebagai peristiwa baru, sehingga sejarah tidak pernah ditulis ulang.

> **Analogi.** Buku besar akuntansi bertinta permanen. Salah catat tidak dihapus dengan tip-ex, melainkan dijurnal balik, dan keduanya tetap terbaca. Tambahkan kamera pengawas yang merekam siapa saja yang membuka lemari arsip. Di OSCAR, bahkan aktivitas membuka trace pun tercatat.

## 6.7 Manual review dan override, ibarat mesin yang tahu batas dirinya

**Apa maksudnya.** Mesin sengaja dirancang untuk menyerah pada kasus abu-abu. Kasus semacam itu masuk ke antrean manusia yang punya SLA dan prioritas. Keputusan manusia tercatat berdampingan dengan keputusan mesin. Kalau keduanya berbeda, itulah override, dan alasannya wajib ditulis. Membatalkan vonis fraud bahkan membutuhkan wewenang yang lebih tinggi.

**Kenapa penting.** Otomasi seratus persen itu naif, karena data tidak pernah lengkap dan dunia tidak pernah rapi. Pola yang optimal adalah mesin menangani mayoritas kasus yang jelas karena murah dan konsisten, sedangkan manusia menangani perkecualian karena mahal tetapi bijak. Override rate pun menjadi metrik kesehatan. Terlalu tinggi berarti kebijakan tidak realistis, sedangkan nol sama sekali berarti underwriter cuma jadi tukang stempel.

> **Analogi.** Gerbang tol. E-toll otomatis melayani 95% kendaraan, sementara gardu petugas melayani kendaraan khusus. Setiap kali petugas membuka palang secara manual, alasannya dicatat.

## 6.8 Monitoring, ibarat dashboard kokpit dan bukan kaca spion

**Apa maksudnya.** Monitoring adalah metrik keputusan yang dilihat harian, antara lain approval rate, reject rate, manual review rate, volume, reason code teratas, ukuran dan SLA antrean review, override rate, distribusi skor dan grade, serta latency dan error sistem. Semuanya bisa dipotong per produk, per channel, dan per waktu.

**Kenapa penting.** NPL itu ibarat kaca spion, karena memberi tahu kecelakaan enam sampai dua belas bulan setelah terjadi. Metrik keputusan adalah kaca depan. Pergeseran kualitas pemohon, kebijakan yang salah sasaran, atau serangan fraud akan terlihat dalam hitungan hari lewat pergeseran approval rate dan reason code, jauh sebelum menjadi kerugian.

> **Analogi.** Kokpit pesawat. Pilot tidak menunggu jatuh untuk tahu ada masalah, karena altimeter, indikator bahan bakar, dan suhu mesin dibaca terus-menerus. Approval rate yang tiba-tiba bergeser lima poin tanpa ada perubahan kebijakan adalah lampu indikator yang menyala. Artinya populasinya yang berubah, maka selidikilah.

## 6.9 Bagaimana semua konsep ini saling mengunci

```
   Ide kebijakan → [SIMULATION] diuji dampaknya → [MAKER-CHECKER] disetujui orang lain
        → [VERSIONING] terbit sebagai versi baru, yang lama diarsip
        → produksi berjalan → [REASON CODES + TRACE] tiap keputusan terjelaskan
        → [MANUAL REVIEW + OVERRIDE] kasus abu-abu ke manusia, tercatat
        → [MONITORING] dampak dipantau harian → [AUDIT TRAIL] semua langkah terbukti
        → temuan monitoring memicu ide kebijakan berikutnya → siklus berulang
```

Satu konsep tanpa yang lain akan pincang. Simulasi tanpa versioning tidak tahu harus membandingkan dengan apa. Monitoring tanpa reason code buta terhadap penyebab. Maker-checker tanpa audit trail tidak bisa dibuktikan. Decision engine yang baik berarti kedelapan konsep ini terpasang sebagai satu sistem, dan itulah tepatnya daftar fitur OSCAR.
