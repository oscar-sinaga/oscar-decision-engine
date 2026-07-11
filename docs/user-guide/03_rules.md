# Bab 03 — Rules, Menulis Aturan Kredit Tanpa Menyentuh Kode

## 3.1 Latar belakang, dari vonis tunggal menjadi aturan serbaguna

Generasi pertama OSCAR hanya mengenal satu bentuk aturan, yaitu "JIKA kondisi terpenuhi MAKA keputusan plus kode alasan". Bentuk itu cukup untuk kebijakan yang memvonis, tetapi kaku untuk kebijakan dunia nyata yang sering **bertingkat** dan hasilnya **angka atau kategori**, bukan vonis. Papan tarif parkir tidak berbunyi boleh atau tidak boleh parkir, melainkan jam pertama sekian, jam berikutnya sekian.

Setelah dibandingkan dengan decision engine kelas enterprise, kekurangannya jelas, yaitu rule di sana bisa **menghasilkan nilai** yang dipakai langkah berikutnya, sementara rule OSCAR selalu buru-buru mengetok palu. Phase 3 memperbaikinya. Rule kini bisa bercabang gaya CASE WHEN, menjalankan lebih dari satu aksi, dan menulis nilai ke output. Vonis akhir bisa diserahkan ke decision table yang membaca nilai-nilai itu, dan pola inilah yang membuat kebijakan jadi modular, yaitu tiap rule menilai satu hal, penggabungnya di satu tempat.

Satu keputusan desain lain yang penting, yaitu semua ini dirakit lewat **builder visual**, bukan JSON atau kode. Alasannya, penulis kebijakan adalah analis risiko, bukan programmer, dan aturan yang tidak bisa dibaca pemiliknya adalah aturan yang salah tempat.

Letaknya di menu **Rules**.

## 3.2 Empat jenis rule dan kapan memakainya

| Jenis | Hasilnya | Kapan dipakai | Contoh |
|---|---|---|---|
| **POLICY_OUTCOME** | Keputusan plus kode alasan | Kebijakan yang memang memvonis langsung | DTI di atas 45% berarti REJECT |
| **STATEMENT** | Angka yang ditulis ke output | Ketentuan bertingkat bergaya papan tarif | Saldo tabungan menentukan band harga kendaraan |
| **CLASSIFICATION** | Label yang ditulis ke output | Memberi kelas tanpa memvonis | Umur kendaraan menjadi collateral_risk HIGH, MEDIUM, LOW |
| **EXPRESSION** | Ditulis sebagai teks formula, khusus admin | Formula yang terlalu rumit untuk builder | Dibahas di bab 10 |

Jenis ini sebetulnya label penggolong untuk memilah daftar, karena perilaku sesungguhnya ditentukan isi aturannya. Namun label yang jujur memudahkan orang lain membaca niat Anda.

## 3.3 Merakit kondisi di builder

Satu baris kondisi terdiri dari fitur, operator, dan nilai. Tiga-tiganya saling mengunci, dan penguncian itu disengaja.

**Fitur** dipilih dari katalog lewat kotak pencarian. Hanya fitur aktif yang muncul, jadi salah ketik mustahil sejak awal.

**Operator** menyesuaikan tipe fitur. Fitur NUMBER dan DATE menawarkan sama dengan, tidak sama, lebih besar, lebih kecil, beserta in, not in, exists, dan is null. Fitur STRING tidak menawarkan lebih besar atau lebih kecil, karena membandingkan besar kecil dua teks tidak punya makna bisnis yang jelas. Fitur BOOLEAN hanya sama dengan dan tidak sama. Pembatasan ini mencegah aturan yang secara teknis tersimpan tetapi secara logika omong kosong.

**Nilai** diisi lewat kotak yang mengikuti tipe, yaitu kotak angka, pilihan benar salah, kalender tanggal, atau daftar nilai untuk in dan not in. Operator exists dan is null tidak butuh nilai. Dulu kolom nilai berupa teks bebas, dan bedanya `"MOTOR"` dengan `MOTOR` pernah jadi sumber kebingungan. Kotak bertipe menghapus kelas kesalahan itu.

Baris-baris digabung dalam grup **ALL** yang berarti semua harus terpenuhi atau **ANY** yang berarti cukup salah satu, dan grup bisa **bersarang** lewat tombol Add Group. Syarat berkurung seperti "DTI tinggi DAN (motor tua ATAU LTV tinggi)" jadi bisa dirakit dengan klik. Ada juga NOT untuk membalik satu grup.

## 3.4 Cabang WHEN THEN ELSE

Sebuah rule boleh memuat banyak cabang WHEN, masing-masing dengan kondisi dan daftar aksinya sendiri, ditutup satu bagian ELSE opsional. Evaluasinya dari atas ke bawah dan **cabang pertama yang cocok itulah yang menang**.

Kenapa cocok pertama, bukan semua yang cocok? Karena begitulah manusia membaca ketentuan bertingkat. Saat papan tarif berbunyi "di atas 50 juta dapat A, di atas 10 juta dapat B", saldo 60 juta jelas dimaksudkan dapat A saja, meskipun secara matematika ia juga di atas 10 juta. Aturan cocok pertama membuat niat penulis dan perilaku mesin selalu sejalan, dengan satu konsekuensi, yaitu **urutan cabang adalah bagian dari kebijakan**. Taruh yang paling spesifik di atas.

## 3.5 Enam jenis aksi dan alasan masing-masing

| Aksi | Parameter | Kegunaannya dan kenapa ada |
|---|---|---|
| **SET_OUTPUT** | target output writable, nilai yang tipenya cocok | Menulis angka atau label yang terbaca langkah berikutnya. Inilah jantung pola modular. Targetnya wajib terdaftar writable di katalog, alasannya di bab 02 |
| **SET_DECISION** | keputusan, kode alasan opsional | Mengusulkan vonis. Disebut mengusulkan karena kalau beberapa rule bersuara, **yang terberat yang menang**, dengan urutan REJECT dan FRAUD_INVESTIGATION di atas MANUAL_REVIEW di atas APPROVE. Urutan ini konservatif dengan sengaja, sebab salah meloloskan lebih mahal daripada salah menahan |
| **ADD_REASON_CODE** | kode alasan | Menandai tanpa memvonis. Berguna untuk rule yang sifatnya peringatan |
| **ROUTE_MANUAL_REVIEW** | kode alasan opsional | Jalan pintas mengusulkan MANUAL_REVIEW, karena mengarahkan ke manusia adalah aksi paling sering dipakai |
| **STOP_EXECUTION** | keputusan dan kode alasan opsional | Menghentikan seluruh alur seketika, untuk kondisi fatal seperti daftar hitam. Buat apa menghitung skor orang yang sudah pasti ditolak |
| **CONTINUE** | kode alasan opsional | Menandai lalu jalan terus |

Kode alasan wajib berasal dari katalog reason code, bukan teks bebas. Alasannya, alasan yang baku bisa dihitung. Kalimat "penyebab penolakan terbanyak bulan ini adalah HIGH_DTI" hanya mungkin kalau semua orang memakai kode yang sama.

Satu cabang boleh menggabungkan beberapa aksi, misalnya menulis output sekaligus menambah penanda alasan.

## 3.6 Pratinjau dan alat bantu di panel kanan

Selagi merakit, panel kanan menampilkan pratinjau **manusiawi** berbentuk kalimat dan pratinjau **bergaya SQL** berbentuk CASE WHEN, lengkap dengan spanduk bahwa itu tampilan semata dan OSCAR tidak pernah mengeksekusi SQL. Kenapa repot-repot ada dua? Karena pembacanya dua macam. Analis membaca kalimat, sedangkan orang yang besar di dunia SQL membaca CASE WHEN lebih cepat daripada membuka cabang satu per satu. Tab Advanced tetap menyimpan JSON mentah untuk yang membutuhkan, tetapi tidak ada pekerjaan yang mewajibkannya.

## 3.7 Menguji sebelum mengajukan

Halaman detail rule menyediakan **form uji yang dibuat otomatis**. Sistem membaca fitur mana saja yang disebut rule lalu membuatkan kotak input bertipe untuk masing-masing. Isi nilai contoh, jalankan, dan hasilnya menunjukkan cabang yang cocok, evaluasi tiap kondisi berupa nilai ambang berhadapan dengan nilai uji, aksi yang akan berjalan, serta isi output sesudahnya. Dulu pengujian menuntut menulis JSON payload sendiri, dan itu pagar tak kasat mata yang membuat orang malas menguji. Form otomatis mencabut pagar itu. Biasakan menguji minimal satu kasus per cabang ditambah satu kasus ELSE.

Panel **Used by** menunjukkan rule set dan strategy mana yang memakai rule ini. Gunanya mengukur radius ledakan sebelum mengubah atau memensiunkan, karena satu rule bisa dipakai banyak alur.

## 3.8 Studi kasus, rule band harga dari nol

Kebijakan yang diminta, yaitu band harga kendaraan ditentukan saldo tabungan. Di atas 50 juta band-nya 20.000, di atas 10 juta 15.000, di atas 5 juta 10.000, selain itu 0.

1. Pastikan `outputs.vehicle_price_band` sudah writable di katalog, kalau belum ikuti bab 02.
2. Buka Rules, tekan New rule, isi code `VEHICLE_PRICE_BAND`, kategori LIMIT, jenis STATEMENT.
3. Rakit cabang pertama, kondisinya saldo lebih dari 50000000, aksinya SET_OUTPUT band 20000.
4. Tambah cabang 10 juta dan 5 juta dengan pola sama. Ambang terbesar di atas, karena cocok pertama menang.
5. Nyalakan ELSE dengan SET_OUTPUT 0, lirik pratinjau untuk memastikan bunyinya sesuai niat, simpan sebagai draft.
6. Uji dengan saldo 12 juta, hasilnya harus cabang kedua dan output 15000. Uji juga saldo 3 juta untuk memastikan ELSE bekerja.
7. Ajukan, minta manager menyetujui, dan setelah aktif rule ini siap dipasang ke rule set serta dibaca decision table.

## 3.9 Rule set, mengelompokkan aturan

Rule tidak dieksekusi sendirian melainkan lewat **rule set**, yaitu kumpulan rule setema yang dipasang sebagai satu node di strategy, misalnya FRAUD_BASIC atau AFFORDABILITY_STANDARD. Kenapa perlu lapisan ini? Supaya strategy tetap terbaca. Alur berisi lima node bernama jelas lebih mudah dipahami daripada alur berisi empat puluh rule lepas. Anggota rule set berjalan berurutan, jadi rule yang menulis output lebih dulu terbaca oleh rule sesudahnya, dan strategy selalu menjalankan versi aktif tiap rule.

## 3.10 Siapa memakainya

Risk Policy Analyst hidup di layar ini. Risk Manager menyentuhnya saat menyetujui. Fraud Analyst memakainya menambah penangkal pola penipuan baru dalam hitungan jam. Data scientist ikut merancang rule CLASSIFICATION yang membungkus band model, dan compliance cukup membaca pratinjau serta riwayat versi.
