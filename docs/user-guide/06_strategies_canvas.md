# Bab 06 — Strategies dan Kanvas Alur, Merangkai Semua Komponen

## 6.1 Latar belakang, dari rel lurus menjadi jalan bercabang

Strategy adalah rute pemeriksaan yang dilalui setiap aplikasi. Dulu rute ini berupa **daftar lurus**, yaitu langkah satu, dua, tiga sampai selesai, dan semua pemohon melewati stasiun yang sama. Masalahnya, kebijakan nyata sering butuh persimpangan. Aplikasi yang berbau fraud selayaknya melewati pemeriksaan mendalam, sementara mayoritas yang bersih cukup jalur cepat. Di model lurus, pilihannya dua-duanya buruk, yaitu semua orang ikut jalur mendalam yang lambat, atau logika cabangnya diselundupkan ke dalam rule sehingga alurnya tidak terlihat siapa pun.

Phase 3 mengubah strategy menjadi **graph**, yaitu rangkaian node yang boleh bercabang lewat node CONDITION dan boleh bertemu kembali. Ada satu larangan keras, yaitu alur tidak boleh berputar ke belakang. Larangan itu bukan selera teknis. Alur yang bisa berputar bisa berjalan berbeda-beda atau tak berujung, sementara keputusan kredit wajib **deterministik**, artinya input sama dengan kebijakan sama harus selalu menghasilkan keputusan yang sama, karena begitulah keadilan antar pemohon dan reprodusibilitas audit dijaga.

Perubahan kedua, alur kini dirancang di **kanvas visual**, bukan formulir daftar. Alasannya sama dengan builder rule, yaitu pemilik alur adalah analis. Denah bergambar panah terbaca sekali pandang, salah sambung langsung kelihatan, dan alur yang sedang aktif bisa ditunjukkan di rapat tanpa menerjemahkan apa pun.

Satu strategy melayani satu kombinasi produk dan segmen, dan hanya satu versi yang boleh aktif untuk kombinasi itu, supaya tidak pernah ada dua kebijakan yang berebut memutus aplikasi yang sama. Letaknya di menu **Strategies**.

## 6.2 Delapan jenis node dan parameternya

Seret node dari palet, sambungkan dengan panah, klik untuk membuka panel konfigurasinya.

| Node | Parameter | Kegunaan dan alasannya |
|---|---|---|
| **START** | tidak ada | Titik masuk, tepat satu, dibuat otomatis. Dua pintu masuk berarti ambigu, maka dilarang |
| **VALIDATION** | required_fields, daftar fitur dari katalog | Menolak dini aplikasi yang datanya bolong. Ditaruh terdepan karena memeriksa kelengkapan itu murah, dan tidak ada gunanya menilai aplikasi yang datanya saja tidak utuh |
| **CALCULATION** | calculations, daftar fitur turunan | Menghitung LTV, DTI, umur kendaraan. Dipisah sebagai node sendiri supaya jelas sejak titik mana angka-angka itu tersedia untuk dibaca aturan |
| **RULE_SET** | reference rule set, on_error | Menjalankan sekumpulan rule berurutan |
| **SCORECARD** | reference scorecard, on_error | Memetakan skor menjadi grade |
| **DECISION_TABLE** | reference tabel, on_error | Matriks penggabung, biasanya menjelang akhir alur |
| **CONDITION** | condition, dirakit dengan builder yang sama seperti di rule | Persimpangan. Wajib punya tepat dua panah keluar berlabel TRUE dan FALSE, tidak boleh satu, tidak boleh tiga. Ketegasan ini membuat setiap persimpangan selalu punya jawaban dan trace selalu bisa mencatat cabang mana yang diambil |
| **END** | tidak ada | Titik akhir |

Tentang **on_error**. Node bisa gagal, misalnya scorecard tidak menerima skor karena LOS lupa mengirimnya. Kebijakan harus menentukan lebih dulu nasib kasus semacam itu, bukan menyerahkannya pada kebetulan. Pilihannya FAIL untuk berhenti dengan status error, MANUAL_REVIEW untuk menyerahkan ke manusia, atau CONTINUE untuk mencatat lalu jalan terus. Untuk node yang hasilnya krusial, MANUAL_REVIEW hampir selalu pilihan paling aman, karena kasus yang mesinnya buta paling pantas dilihat mata manusia.

## 6.3 Aturan main graph

Kanvas dan server sama-sama memeriksa hal berikut, dan pelanggarannya ditampilkan dengan menyalakan node atau panah yang bermasalah.

1. Tepat satu START, dan semua node terjangkau darinya. Node yatim biasanya sisa eksperimen yang terlupa.
2. Tidak boleh ada putaran, alasannya determinisme tadi. Cabang boleh bertemu kembali.
3. CONDITION wajib dua panah berlabel TRUE dan FALSE, node lain paling banyak satu panah keluar.
4. Semua reference harus menunjuk objek yang ada, dan saat aktivasi objek rujukan harus punya versi aktif, supaya tidak ada alur hidup yang menunjuk kebijakan kosong.

Di luar aturan keras itu ada satu kebiasaan baik, yaitu taruh pemeriksaan murah dan fatal di depan, pemeriksaan mahal di belakang. Prinsip berhenti cepat ini menghemat waktu semua orang.

## 6.4 Siklus hidup strategy, dengan satu syarat tambahan

Siklusnya sama seperti objek lain, ditambah satu kekhususan, yaitu **mengajukan strategy mengharuskan melampirkan simulasi** dari versi yang persis itu. Kebijakan alur adalah kebijakan paling berdampak di seluruh sistem, karena menyentuh semua aplikasi sekaligus. Wajar bila penyetujunya berhak atas bukti dampak, bukan sekadar keyakinan pengusul. Alurnya menjadi begini. Rakit draft di kanvas, jalankan simulasinya, ajukan dengan lampiran, lalu manager yang berbeda orang menyetujui, dan versi lama pensiun dengan sendirinya.

Kalau kebijakan baru ternyata memukul terlalu dalam, tombol **rollback** pada versi RETIRED menghidupkannya kembali, dengan alasan wajib diisi. Perhatikan filosofinya, jalan pulang selalu ada, tetapi tidak pernah diam-diam.

## 6.5 Studi kasus, menambah cabang pemeriksaan fraud

Kebijakan barunya, aplikasi dengan skor risiko perangkat tinggi harus melewati pemeriksaan fraud mendalam, sisanya cukup pemeriksaan dasar.

1. Buka strategy LEASEBACK_MOTOR, buat versi draft dari versi aktif.
2. Seret node CONDITION ke antara kalkulasi dan pemeriksaan fraud, isi kondisinya `fraud.device_risk_score` lebih besar dari 0.5.
3. Sambungkan panah TRUE ke node RULE_SET baru berisi FRAUD_DEEP, panah FALSE ke FRAUD_BASIC yang lama.
4. Pertemukan kembali kedua cabang di node SCORECARD, karena setelah urusan fraud selesai jalurnya memang menyatu lagi.
5. Simpan. Panah yang lupa tersambung akan menyala merah dengan pesan yang menyebut nodenya.
6. Simulasikan dua kasus, satu dengan skor perangkat 0.7 dan satu 0.1, lalu pastikan jalur yang tercatat memang berbeda.
7. Ajukan dengan simulasi terlampir, minta persetujuan, aktifkan. Sejak itu trace setiap keputusan mencantumkan cabang yang dilalui, dan mayoritas pemohon yang bersih tidak pernah ikut melambat.

## 6.6 Siapa memakainya

Risk Policy Analyst merancang alurnya. Risk Manager menyetujui, mengaktifkan, dan memegang tombol rollback. Underwriter dan auditor menikmati tampilan baca-saja lewat tautan view flow di trace untuk melihat rute sebuah keputusan sebagai gambar. Fraud analyst berkepentingan pada cabang pemeriksaan yang bisa ditambah cepat begitu pola serangan berubah.
