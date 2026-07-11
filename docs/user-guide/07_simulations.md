# Bab 07 — Simulations, Menguji Kebijakan Tanpa Menyentuh Produksi

## 7.1 Latar belakang, kenapa fitur ini nyaris wajib di dunia kredit

Kebijakan kredit punya sifat yang kejam, yaitu akibatnya baru terlihat lama sekali. Kredit yang salah diloloskan hari ini baru ketahuan macet enam sampai dua puluh empat bulan lagi. Artinya, kalau kebijakan baru langsung dilepas ke produksi tanpa uji, kesalahannya terlanjur menumpuk berbulan-bulan sebelum ada yang sadar. Di sisi lain, satu perubahan ambang saja bisa menggeser nasib ribuan pemohon dan miliaran rupiah.

Simulasi adalah jawabannya, yaitu menjalankan kebijakan kandidat terhadap data **masa lalu** untuk mencicipi masa depan. Dua keputusan desain membuatnya bisa dipercaya. Pertama, simulasi memakai **mesin yang sama persis** dengan produksi, bukan tiruan, sehingga hasil uji dan perilaku nyata tidak mungkin berbeda mesin. Kedua, simulasi **bebas efek samping sepenuhnya**, tidak melahirkan keputusan, tidak melahirkan kasus review, tidak menyentuh konfigurasi, dan hasilnya selalu bertanda SIMULATION supaya tidak pernah tertukar dengan bukti produksi.

Letaknya di menu **Simulations**, dengan dua mode.

## 7.2 Simulasi satu kasus

Untuk pertanyaan "kalau pemohonnya seperti ini, keputusannya apa".

| Parameter | Arti | Catatan |
|---|---|---|
| **Application payload** | Data aplikasi lengkap dalam JSON | Halaman menyediakan contoh payload yang tinggal diubah angkanya |
| **Strategy version** | Versi yang diuji | Kosongkan untuk strategy aktif, atau pilih **versi draft** mana pun. Kemampuan menguji draft inilah gunanya parameter ini ada, kebijakan bisa dicoba sebelum jadi apa-apa |
| **Compare with active** | Jalankan juga di versi aktif | Payload yang sama dieksekusi dua kali supaya bedanya terlihat langsung |

Hasilnya memuat keputusan versi target, keputusan versi aktif bila dibandingkan, daftar perbedaan per bidang, dan trace lengkap bergaya simulasi.

## 7.3 Simulasi massal, alias policy impact analysis

Untuk pertanyaan "kalau kebijakan ini berlaku, seluruh populasi bergeser bagaimana". Satu kasus tidak bisa menjawab itu, karena kebijakan yang bagus untuk satu orang bisa buruk untuk portofolio.

| Parameter | Arti | Catatan |
|---|---|---|
| **Candidate strategy version** | Versi kandidat | Wajib dipilih |
| **Application payloads** | Kumpulan payload dalam satu array | Sampai lima ribu sekali jalan, lazimnya diambil dari aplikasi historis |
| **Compare with active** | Bandingkan dengan strategy aktif | Nyalakan hampir selalu |

Hasilnya dibaca bertingkat. Mulailah dari **agregat**, yaitu approval rate, reject rate, manual review rate, distribusi kode alasan, dan distribusi grade untuk kandidat berdampingan dengan aktif. Lalu turun ke **decision shifts**, matriks perpindahan nasib, misalnya "APPROVE menjadi REJECT sebanyak 214". Bagian ini yang paling berharga, karena untung rugi kebijakan tidak ditentukan berapa banyak yang bergeser melainkan **siapa** yang bergeser. Analisis inilah yang di dunia risk disebut swap set. Terakhir lihat **segment impact** per produk dan channel, untuk memastikan dampaknya merata dan bukan menghantam satu segmen diam-diam.

## 7.4 Kenapa simulasi menjadi syarat aktivasi

Hasil simulasi bukan sekadar alat analisis. Saat mengajukan strategy, simulasi versi itu **wajib dilampirkan**, dan referensinya menempel di permintaan persetujuan sehingga penyetuju bisa membukanya. Latar belakang aturan ini sederhana, yaitu tanpa paksaan, uji dampak adalah langkah yang paling sering dilewati orang saat terburu-buru, padahal justru paling penting. Menjadikannya syarat memindahkan disiplin dari niat baik ke sistem.

## 7.5 Studi kasus

Usulannya menurunkan ambang DTI dari 0.45 menjadi 0.42.

1. Analis menyiapkan versi rule dan versi strategy draft yang memuat ambang baru.
2. Seribu payload historis bulan lalu dijalankan lewat simulasi massal, kandidat versi draft, perbandingan menyala.
3. Hasilnya, approval turun dari 44 persen ke 40 persen. Decision shifts menunjukkan mayoritas perpindahan menuju MANUAL_REVIEW dan bukan langsung REJECT, sedangkan segment impact menunjukkan pergeseran terkonsentrasi di channel dealer, persis segmen yang memang bermasalah.
4. Rapat memutuskan lanjut, dengan bukti bukan firasat. Analis mengajukan strategy berlampiran simulasi ini, manager membuka lampiran, membaca angka yang sama, lalu menyetujui.
5. Seminggu kemudian dashboard menunjukkan approval turun mendekati angka simulasi. Kebijakan berperilaku seperti ramalannya, dan begitulah seharusnya.

## 7.6 Siapa memakainya

Risk Policy Analyst menjalankannya hampir setiap menyiapkan perubahan. Risk Manager membacanya saat menyetujui. Data scientist memakainya sebagai backtest untuk usulan cutoff dan band, karena pertanyaannya memang sama, siapa yang bertukar nasib bila kebijakan berubah.
