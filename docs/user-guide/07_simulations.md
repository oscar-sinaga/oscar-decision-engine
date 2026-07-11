# Bab 07 — Simulations, Menguji Kebijakan Tanpa Menyentuh Produksi

## 7.1 Kegunaannya

Simulasi menjalankan mesin keputusan yang sama persis dengan produksi, tetapi tanpa efek samping apa pun. Tidak ada keputusan produksi yang tercipta, tidak ada kasus review yang lahir, dan tidak ada konfigurasi yang tersentuh. Kegunaannya dua. Pertama menguji kebijakan draft sebelum berlaku, kedua membandingkan kebijakan kandidat dengan yang sedang aktif memakai data yang sama.

Letaknya di menu **Simulations**. Ada dua mode, yaitu simulasi satu kasus dan simulasi massal yang disebut policy impact analysis.

## 7.2 Simulasi satu kasus

Cocok untuk pertanyaan "kalau pemohon seperti ini, keputusannya apa".

| Parameter | Arti | Catatan |
|---|---|---|
| **Application payload** | Data aplikasi lengkap dalam bentuk JSON | Halaman ini menyediakan contoh payload lease-back motor yang tinggal diubah angkanya |
| **Strategy version** | Versi strategy yang diuji | Kosongkan untuk memakai strategy aktif, atau pilih versi draft mana pun. Inilah cara menguji draft |
| **Compare with active** | Centang untuk membandingkan | Payload yang sama dijalankan dua kali, sekali di versi target dan sekali di versi aktif |

Hasilnya menampilkan keputusan versi target, keputusan versi aktif bila dibandingkan, daftar **differences** per bidang seperti keputusan, grade, limit, dan alasan, serta trace lengkap bergaya simulasi. Setiap hasil diberi tanda SIMULATION yang jelas supaya tidak pernah tertukar dengan bukti produksi.

## 7.3 Simulasi massal, alias policy impact analysis

Cocok untuk pertanyaan "kalau kebijakan ini berlaku, dampaknya ke seluruh populasi seperti apa". Buka lewat tautan policy impact di halaman simulasi.

| Parameter | Arti | Catatan |
|---|---|---|
| **Candidate strategy version** | Versi kandidat yang dievaluasi | Wajib dipilih |
| **Application payloads** | Kumpulan payload dalam satu array JSON | Sampai lima ribu aplikasi sekali jalan, biasanya diambil dari data historis |
| **Compare with active** | Bandingkan dengan strategy aktif per produk dan segmen | Nyalakan untuk melihat pergeseran |

Cara membaca hasilnya.

1. **Agregat kandidat dan aktif**, berisi approval rate, reject rate, manual review rate, distribusi kode alasan, dan distribusi grade. Bandingkan dulu angka besarnya.
2. **Decision shifts**, yaitu matriks perpindahan nasib dari keputusan versi aktif ke keputusan versi kandidat. Baris "APPROVE menjadi REJECT sebanyak 214" artinya ada 214 pemohon yang tadinya diterima akan tertolak. Inilah swap set, bagian paling penting untuk rapat, karena yang menentukan untung rugi bukan berapa banyak yang bergeser melainkan siapa.
3. **Segment impact**, yaitu rincian per kombinasi produk dan channel, untuk melihat apakah dampaknya merata atau menghantam satu segmen saja.

## 7.4 Hubungannya dengan aktivasi strategy

Hasil simulasi bukan sekadar alat analisis, melainkan **syarat**. Strategy tidak bisa diaktifkan tanpa lampiran simulasi versi tersebut, dan referensi simulasinya tercatat pada permintaan persetujuan sehingga penyetuju bisa membukanya. Anggaplah begini, simulasi adalah dokumen uji terowongan angin yang wajib menempel di proposal sebelum pesawat boleh terbang.

## 7.5 Studi kasus

Usulan kebijakan berbunyi menurunkan ambang DTI dari 0.45 menjadi 0.42.

1. Analis membuat versi rule dan versi strategy draft yang memuat ambang baru.
2. Dia menyiapkan seribu payload historis bulan lalu dalam satu array, lalu menjalankan simulasi massal dengan kandidat versi draft dan perbandingan menyala.
3. Hasilnya, approval turun dari 44 persen ke 40 persen. Decision shifts menunjukkan mayoritas perpindahan adalah APPROVE menjadi MANUAL_REVIEW, bukan langsung REJECT, dan segment impact menunjukkan pergeseran terkonsentrasi di channel dealer.
4. Rapat memutuskan lanjut karena kohor yang bergeser memang segmen bermasalah. Analis submit strategy dengan simulasi ini terlampir, manager membuka lampirannya, membaca angka yang sama, lalu menyetujui.
5. Seminggu setelah aktif, dashboard menunjukkan approval rate turun mendekati angka simulasi. Kebijakan berperilaku seperti yang diramalkan, dan itulah gunanya menguji sebelum berlaku.

## 7.6 Siapa memakainya

Risk Policy Analyst menjalankannya hampir setiap kali menyiapkan perubahan. Risk Manager membacanya saat menyetujui. Data scientist memakainya sebagai alat backtest untuk usulan cutoff dan band, karena pertanyaannya sama, yaitu siapa yang bertukar nasib kalau kebijakan berubah.
