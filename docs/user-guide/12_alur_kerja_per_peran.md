# Bab 12 — Alur Kerja per Peran, Satu Cerita dari Semua Kacamata

Bab penutup ini merangkai semua bab sebelumnya menjadi skenario kerja nyata per peran. Kebijakan yang menjadi latar ceritanya sama, yaitu perusahaan ingin memperketat segmen dealer yang kualitasnya memburuk, sambil tetap melonggarkan pemohon terbaik.

## 12.1 Risk Policy Analyst, dari mandat menjadi kebijakan hidup

Login sebagai `riskanalyst`.

1. **Pahami situasi.** Buka Dashboard, saring channel dealer. Approval masih tinggi tetapi kode alasan DTI_NEAR_THRESHOLD menanjak. Bab 08.
2. **Siapkan fondasi data.** Cek Feature Catalog, pastikan `outputs.affordability_risk` writable tersedia. Kalau belum, buat. Bab 02.
3. **Tulis aturannya.** Buat rule CLASSIFICATION yang menulis affordability_risk bertingkat berdasarkan DTI, tiga cabang plus ELSE, lewat builder tanpa JSON. Uji tiap cabang di form uji. Bab 03.
4. **Rakit penggabungnya.** Buka Decision Tables, buat versi draft yang membaca affordability_risk sebagai kolom baru, ketatkan barisnya khusus kombinasi berisiko. Bab 04.
5. **Rangkai alurnya.** Di kanvas strategy, buat versi draft. Tambahkan node CONDITION channel dealer, cabang TRUE melewati rule set pengetatan, cabang FALSE jalur normal, lalu kedua cabang menyatu lagi. Bab 06.
6. **Buktikan dampaknya.** Jalankan simulasi massal seribu payload historis dengan perbandingan menyala. Baca decision shifts dan segment impact, pastikan yang tergeser memang kohor bermasalah. Bab 07.
7. **Ajukan.** Submit strategy dengan simulasi terlampir. Tugasnya selesai, giliran atasan.

## 12.2 Credit Risk Manager, memegang kunci kedua

Login sebagai `riskmanager`.

1. **Pagi hari.** Dashboard dulu, lalu antrean persetujuan di Admin. Bab 08 dan 11.
2. **Review usulan.** Buka permintaan dari analis. Baca catatan perubahan, buka lampiran simulasinya, cocokkan angka pergeseran dengan selera risiko. Kanvas versi draft bisa dibuka baca-saja untuk melihat alurnya.
3. **Putuskan.** Approve dengan alasan tertulis. Sistem tadi menolak analis menyetujui sendiri, dan kini juga menolak aktivasi seandainya simulasi tidak terlampir. Versi baru aktif, versi lama pensiun.
4. **Pantau minggu berjalan.** Approval rate bergerak sesuai simulasi atau tidak, override rate underwriter naik atau tidak. Kalau kebijakan ternyata memukul terlalu dalam, tombol rollback di versi lama siap dengan alasan wajib. Bab 06.

## 12.3 Underwriter, memutus yang abu-abu

Login sebagai `underwriter`.

1. Antrean Manual Review terisi kasus baru hasil pengetatan. Kerjakan dari prioritas dan SLA terdekat. Bab 09.
2. Buka kasus, baca keputusan sistem dan trace-nya, jadi jelas kenapa mesin ragu.
3. Investigasi. Telepon, minta dokumen lewat checklist, catat kronologi di komentar.
4. Putus lewat form analis. Setuju bersyarat dengan limit diturunkan berarti mengisi limit baru plus alasan override, karena keputusannya berbeda dari usulan mesin. Menolak berarti wajib memilih kode alasan.
5. Ingat batasnya, membatalkan vonis FRAUD_INVESTIGATION bukan wewenangnya dan harus dieskalasi.

## 12.4 Fraud Analyst, merespons pola baru

Bekerja sama dengan analis kebijakan.

1. Dari kasus-kasus review terlihat pola slip gaji bernomor seri berurutan dari dua dealer.
2. Usulkan rule fraud baru, kombinasi channel dan pola penghasilan yang diarahkan ke FRAUD_INVESTIGATION. Bab 03.
3. Uji ke data seminggu lewat simulasi supaya tahu berapa yang tertangkap dan berapa salah tangkap. Bab 07.
4. Ajukan lewat jalur yang sama, disetujui manager, dan pertahanan baru hidup hari itu juga.

## 12.5 Compliance dan Internal Audit, membuktikan semuanya sah

Login sebagai `compliance` atau `auditor`.

1. Pertanyaan "kenapa aplikasi ini ditolak" dijawab lewat Decisions dan trace, lima menit selesai. Bab 08.
2. Pertanyaan "siapa mengubah kebijakan dan atas persetujuan siapa" dijawab lewat Audit Log dengan saringan entity, lengkap dengan before after dan alasan. Bab 11.
3. Sampling override underwriter, tarik peristiwa override beserta alasannya, cari pola yang janggal.
4. Semua akses ke data sensitif pun terekam, termasuk siapa membuka trace apa.

## 12.6 Data Scientist, memberi otak dan membaca jejak

Login sebagai `datascientist`.

1. **Memasok skor.** Model baru didaftarkan di Model Registry, band-nya dituangkan ke versi scorecard bersama analis. Bab 05.
2. **Menguji cutoff.** Usulan geser band diuji lewat simulasi massal, dan decision shifts menjadi analisis swap set, yaitu siapa yang bertukar nasib. Bab 07.
3. **Menambang trace.** Setiap keputusan menyimpan fitur persis saat keputusan diambil, jadi trace adalah sumber data pelatihan dan validasi paling jujur. Bab 08.
4. **Memantau.** Distribusi skor dan approval per grade di dashboard menjadi alarm dini pergeseran populasi, jauh sebelum NPL bergerak.

## 12.7 Penutup

Perhatikan polanya. Semua peran bekerja pada objek yang sama, tetapi lewat pintu yang berbeda, dan setiap perpindahan tangan tercatat. Analis tidak bisa mengaktifkan sendiri, manager tidak bisa mengubah isi, underwriter tidak bisa menghapus jejak, dan auditor bisa membaca semuanya. Justru keterbatasan tiap peran itulah yang membuat keseluruhan sistem bisa dipercaya.

Kalau ada layar yang belum terbayang, kembalilah ke bab detailnya. Dan kalau konsep bisnis di baliknya yang belum terbayang, kurikulum `docs/learning/` menjelaskannya dari dasar.
