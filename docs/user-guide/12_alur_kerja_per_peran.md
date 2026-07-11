# Bab 12 — Alur Kerja per Peran, Satu Cerita dari Semua Kacamata

Bab penutup ini merangkai semua bab sebelumnya menjadi skenario kerja nyata. Latar ceritanya satu kebijakan yang sama, yaitu perusahaan ingin memperketat segmen dealer yang kualitasnya memburuk, sambil tetap melonggarkan pemohon terbaiknya. Perhatikan bagaimana pekerjaan yang sama berpindah tangan dari peran ke peran, dan bagaimana setiap perpindahan meninggalkan jejak. Pembagian peran itu bukan birokrasi, melainkan cara sistem menjaga dirinya, seperti yang dibahas di bab 01 dan 11.

## 12.1 Risk Policy Analyst, dari mandat menjadi kebijakan hidup

Masuk sebagai `riskanalyst`.

1. **Memahami situasi.** Dashboard disaring ke channel dealer. Approval masih tinggi, tetapi kode alasan DTI_NEAR_THRESHOLD menanjak. Ada yang bergeser di populasi. Bab 08.
2. **Menyiapkan fondasi data.** Cek Feature Catalog, pastikan `outputs.affordability_risk` tersedia dan writable. Kalau belum, daftarkan dulu. Bab 02.
3. **Menulis aturannya.** Buat rule CLASSIFICATION yang menulis affordability_risk bertingkat berdasarkan DTI, tiga cabang plus ELSE, semuanya lewat builder. Uji tiap cabang di form uji otomatis. Bab 03.
4. **Merakit penggabungnya.** Di Decision Tables, buat versi draft yang membaca affordability_risk sebagai kolom baru, lalu ketatkan baris untuk kombinasi berisiko. Bab 04.
5. **Merangkai alurnya.** Di kanvas strategy, buat versi draft. Tambahkan node CONDITION untuk channel dealer, cabang TRUE melewati rule set pengetatan, cabang FALSE jalur normal, lalu keduanya menyatu lagi. Bab 06.
6. **Membuktikan dampaknya.** Simulasi massal seribu payload historis dengan perbandingan menyala. Baca decision shifts untuk tahu siapa yang bertukar nasib, dan segment impact untuk memastikan yang terpukul memang segmen bermasalah. Bab 07.
7. **Mengajukan.** Submit strategy dengan simulasi terlampir. Sampai di sini tugasnya selesai, karena langkah berikutnya memang bukan wewenangnya.

## 12.2 Credit Risk Manager, pemegang kunci kedua

Masuk sebagai `riskmanager`.

1. Pagi dimulai dari Dashboard, lalu antrean persetujuan di Admin. Bab 08 dan 11.
2. Usulan analis dibuka. Catatan perubahan dibaca, lampiran simulasinya dibuka, angka pergeserannya ditimbang terhadap selera risiko. Kanvas draft bisa dilihat baca-saja untuk memahami alurnya.
3. Setujui dengan alasan tertulis. Sistem tadi sudah menolak analis menyetujui usulannya sendiri, dan akan menolak pula aktivasi tanpa simulasi. Versi baru aktif, versi lama pensiun dengan sendirinya.
4. Sepanjang minggu berikutnya, pantau apakah approval bergerak sesuai simulasi dan apakah override underwriter melonjak. Kalau kebijakan ternyata memukul terlalu dalam, tombol rollback di versi lama selalu siap, dengan alasan wajib. Bab 06.

## 12.3 Underwriter, memutus yang abu-abu

Masuk sebagai `underwriter`.

Antrean Manual Review terisi kasus baru hasil pengetatan, dikerjakan dari prioritas dan tenggat terdekat. Setiap kasus dibuka bersama trace-nya, jadi jelas kenapa mesin ragu. Investigasi berjalan lewat telepon, permintaan dokumen dengan checklist, dan komentar kronologi. Putusan diambil di form analis, dan bila berbeda dari usulan mesin, alasan override wajib ditulis. Menolak berarti wajib memilih kode alasan. Satu batas yang harus diingat, membatalkan vonis fraud bukan wewenangnya dan harus dieskalasi. Bab 09.

## 12.4 Fraud Analyst, merespons pola baru

Dari kasus-kasus review terlihat pola slip gaji bernomor seri berurutan dari dua dealer. Bersama analis kebijakan, dia menyusun rule fraud baru yang mengarahkan kombinasi mencurigakan itu ke FRAUD_INVESTIGATION, mengujinya ke data seminggu lewat simulasi supaya tahu berapa tertangkap dan berapa salah tangkap, lalu mengajukannya lewat jalur yang sama. Disetujui siang itu, dan pertahanan baru hidup hari itu juga. Kecepatan inilah alasan kebijakan dibuat sebagai konfigurasi, bukan kode. Bab 03 dan 07.

## 12.5 Compliance dan Internal Audit, membuktikan semuanya sah

Masuk sebagai `compliance` atau `auditor`.

Pertanyaan "kenapa aplikasi ini ditolak" dijawab lewat Decisions dan trace dalam hitungan menit. Pertanyaan "siapa mengubah kebijakan dan atas persetujuan siapa" dijawab Audit Log dengan saringan entity, lengkap dengan before after dan alasan. Sampel override underwriter ditarik beserta alasannya untuk mencari pola janggal, dan bahkan akses ke data sensitif pun berjejak, termasuk siapa membuka trace apa. Bab 08 dan 11.

## 12.6 Data Scientist, memberi otak dan membaca jejak

Masuk sebagai `datascientist`.

Model baru didaftarkan di Model Registry, band-nya dituangkan sebagai versi scorecard bersama analis, dan decision table tidak perlu disentuh karena hanya mengenal grade. Usulan geser band diuji lewat simulasi massal, yang decision shifts-nya adalah analisis swap set. Trace ditambang sebagai sumber fitur historis paling jujur, karena nilainya persis nilai saat keputusan diambil. Dan distribusi skor di dashboard menjadi alarm dini pergeseran populasi, jauh sebelum NPL bergerak. Bab 05, 07, dan 08.

## 12.7 Penutup

Perhatikan sekali lagi polanya. Semua peran bekerja pada objek yang sama tetapi lewat pintu berbeda, dan setiap perpindahan tangan tercatat. Analis tidak bisa mengaktifkan sendiri, manager tidak bisa mengubah isi, underwriter tidak bisa menghapus jejak, dan auditor bisa membaca semuanya. Justru keterbatasan tiap peran itulah yang membuat keseluruhan sistem layak dipercaya.

Kalau ada layar yang belum terbayang, kembalilah ke bab detailnya. Kalau konsep bisnis di baliknya yang belum terbayang, kurikulum `docs/learning/` menjelaskannya dari dasar.
