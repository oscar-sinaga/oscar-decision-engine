# Bab 06 — Strategies dan Kanvas Alur, Merangkai Semua Komponen

## 6.1 Kegunaannya

Strategy adalah rute pemeriksaan yang dilalui setiap aplikasi, yaitu rangkaian node berisi validasi, kalkulasi, rule set, scorecard, decision table, dan percabangan kondisi. Satu strategy melayani satu kombinasi produk dan segmen, misalnya LEASEBACK_MOTOR untuk produk motor lease-back segmen DEFAULT, dan hanya satu versi yang boleh aktif untuk kombinasi itu.

Sejak Phase 3, strategy berbentuk **graph** yang dirancang di **kanvas visual**. Alur boleh bercabang lewat node CONDITION dan cabang-cabangnya boleh bertemu kembali, tetapi tidak boleh berputar, sehingga eksekusinya selalu deterministik.

Letaknya di menu **Strategies**. Versi draft bisa diedit di kanvas, sedangkan versi yang sudah diajukan atau aktif tampil sebagai baca-saja.

## 6.2 Delapan jenis node dan parameternya

Seret node dari palet kiri ke kanvas, sambungkan dengan panah, lalu klik node untuk membuka panel konfigurasinya.

| Node | Parameter | Kegunaan |
|---|---|---|
| **START** | tidak ada | Titik masuk, tepat satu per alur, dibuat otomatis |
| **VALIDATION** | required_fields berupa daftar fitur dari katalog | Menolak dini aplikasi yang datanya tidak lengkap |
| **CALCULATION** | calculations berupa daftar fitur turunan | Menghitung LTV, DTI, dan umur kendaraan sebelum aturan membacanya |
| **RULE_SET** | reference berupa rule set, plus on_error | Menjalankan sekumpulan rule secara berurutan |
| **SCORECARD** | reference berupa scorecard, plus on_error | Memetakan skor menjadi grade |
| **DECISION_TABLE** | reference berupa decision table, plus on_error | Matriks penggabung keputusan |
| **CONDITION** | condition yang dirakit dengan builder yang sama seperti di rule | Persimpangan. Punya tepat dua panah keluar berlabel TRUE dan FALSE |
| **END** | tidak ada | Titik akhir alur |

Parameter **on_error** menentukan nasib alur kalau sebuah node gagal, misalnya scorecard tidak menerima skor. Pilihannya FAIL untuk menghentikan dengan status error, MANUAL_REVIEW untuk mengarahkan kasus ke manusia, atau CONTINUE untuk mencatat lalu jalan terus. Untuk node yang hasilnya krusial seperti scorecard, MANUAL_REVIEW biasanya pilihan paling aman.

## 6.3 Aturan main graph

Kanvas dan server sama-sama memeriksa hal berikut sebelum menyimpan, dan pelanggaran ditampilkan dengan menyalakan node atau panah yang bermasalah.

1. Tepat satu START, dan semua node harus terjangkau darinya.
2. Tidak boleh ada putaran. Cabang boleh bertemu kembali, tetapi tidak boleh kembali ke belakang.
3. Node CONDITION wajib punya tepat dua panah keluar, satu TRUE dan satu FALSE. Node lain paling banyak satu panah keluar.
4. Semua reference harus menunjuk objek yang ada, dan saat aktivasi objek yang dirujuk harus punya versi aktif.

Urutan node adalah bagian dari kebijakan. Taruh pemeriksaan yang murah dan fatal di depan, misalnya validasi dan daftar hitam, supaya kasus yang jelas gagal berhenti cepat sebelum pemeriksaan yang mahal.

## 6.4 Siklus hidup strategy, ada satu syarat tambahan

Siklusnya sama seperti objek lain, dengan satu kekhususan penting. **Mengajukan strategy mengharuskan melampirkan simulasi** dari versi yang persis itu. Tanpa lampiran, tombol aktivasi akan ditolak dengan pesan yang menyebut simulasi. Alasannya sederhana, penyetuju berhak melihat bukti dampak sebelum kebijakan hidup. Alur ringkasnya begini.

1. Buat versi draft, rakit alurnya di kanvas, simpan.
2. Jalankan simulasi untuk versi draft itu dari menu Simulations, atau biarkan tombol submit menjalankan satu simulasi cepat secara otomatis.
3. Submit for approval dengan simulasi terlampir.
4. Risk manager yang berbeda orang menyetujui, dan versi menjadi ACTIVE sementara versi aktif sebelumnya pensiun.

Kalau kebijakan baru ternyata berdampak buruk, tombol **rollback** pada versi RETIRED menghidupkannya kembali dengan alasan wajib. Tidak ada yang dihapus, hanya bertukar status, dan semuanya tercatat di audit.

## 6.5 Studi kasus, menambah cabang pemeriksaan fraud

Kebijakan baru berbunyi begini. Aplikasi dengan skor risiko perangkat tinggi harus melewati pemeriksaan fraud mendalam, sedangkan yang normal cukup pemeriksaan dasar, supaya mayoritas pemohon tidak ikut melambat.

1. Buka strategy LEASEBACK_MOTOR lalu buat versi draft baru dari versi aktif.
2. Seret node CONDITION ke antara kalkulasi dan pemeriksaan fraud. Isi kondisinya `fraud.device_risk_score` lebih besar dari 0.5 lewat builder.
3. Sambungkan panah TRUE ke node RULE_SET baru yang mereferensikan rule set FRAUD_DEEP, dan panah FALSE ke rule set FRAUD_BASIC yang lama.
4. Sambungkan kedua cabang kembali ke node SCORECARD yang sama, karena setelah pemeriksaan fraud jalurnya kembali menyatu.
5. Simpan. Kalau ada panah yang lupa tersambung, validasi menyalakannya merah dengan pesan yang menyebut nodenya.
6. Jalankan simulasi dua kasus, satu dengan device_risk_score 0.7 dan satu 0.1, lalu periksa di hasilnya bahwa jalur yang dilalui memang berbeda.
7. Submit dengan simulasi terlampir, minta persetujuan, aktifkan. Sejak itu trace setiap keputusan mencantumkan cabang mana yang dilalui.

## 6.6 Siapa memakainya

Risk Policy Analyst merancang alur di kanvas. Risk Manager menyetujui, mengaktifkan, dan memegang tombol rollback. Underwriter serta auditor memakai tampilan baca-saja lewat tautan "view flow" di trace untuk memahami rute yang dilalui sebuah keputusan. Fraud analyst berkepentingan pada cabang-cabang pemeriksaan yang bisa ditambah cepat saat pola serangan berubah.
