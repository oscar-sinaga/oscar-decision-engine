# Bab 03 — Rules, Menulis Aturan Kredit Tanpa Menyentuh Kode

## 3.1 Kegunaannya

Rule adalah kalimat kebijakan yang bisa dieksekusi mesin. Bentuk dasarnya "JIKA kondisi terpenuhi MAKA lakukan aksi". Di sinilah ambang DTI, batas umur kendaraan, larangan daftar hitam, dan semua kebijakan kredit dituliskan. Letaknya di menu **Rules**.

## 3.2 Empat jenis rule dan kapan memakainya

| Jenis | Hasilnya | Kapan dipakai | Contoh |
|---|---|---|---|
| **POLICY_OUTCOME** | Keputusan plus kode alasan | Kebijakan yang langsung memvonis | DTI di atas 45% berarti REJECT dengan alasan HIGH_DTI |
| **STATEMENT** | Nilai yang ditulis ke sebuah output | Menentukan angka bertingkat | Saldo tabungan menentukan band harga kendaraan |
| **CLASSIFICATION** | Label yang ditulis ke sebuah output | Memberi kelas, bukan vonis | Umur kendaraan menjadi collateral_risk HIGH, MEDIUM, atau LOW |
| **EXPRESSION** | Ditulis sebagai teks formula, khusus admin | Formula yang terlalu rumit untuk builder | Bab 10 membahasnya |

Jenis STATEMENT dan CLASSIFICATION inilah yang memungkinkan pola modular, yaitu beberapa rule menulis penilaian masing-masing lalu sebuah decision table menggabungkannya menjadi keputusan akhir. Rule jadi tidak harus memvonis.

## 3.3 Anatomi sebuah rule di form pembuatan

**Bagian informasi umum.** Rule code sebagai nama teknis unik, misalnya `VEHICLE_PRICE_BAND`, lalu nama ramah, deskripsi, kategori dari katalog, jenis rule, dan catatan versi.

**Bagian kondisi, dibangun dengan builder.** Satu baris kondisi terdiri dari tiga bagian.

| Bagian | Cara mengisi | Catatan |
|---|---|---|
| **Fitur** | Ketik untuk mencari di katalog, misalnya ketik "saldo" | Hanya fitur aktif yang muncul, lengkap dengan tipe datanya |
| **Operator** | Pilih dari dropdown yang menyesuaikan tipe fitur | Fitur NUMBER dan DATE menawarkan `=` `!=` `>` `>=` `<` `<=` `in` `not_in` `exists` `is_null`. Fitur STRING tidak menawarkan lebih besar atau lebih kecil. Fitur BOOLEAN hanya `=` `!=` `exists` `is_null` |
| **Nilai** | Kotak input menyesuaikan tipe | Angka memunculkan kotak angka, boolean memunculkan pilihan benar salah, tanggal memunculkan kalender, sedangkan `in` dan `not_in` menerima daftar nilai. Operator `exists` dan `is_null` tidak butuh nilai |

Baris-baris kondisi digabung dalam grup ALL yang berarti semua harus terpenuhi, atau ANY yang berarti cukup salah satu. Grup bisa **bersarang** lewat tombol Add Group, sehingga syarat berkurung seperti "DTI tinggi DAN (motor tua ATAU LTV tinggi)" bisa dirakit tanpa mengetik apa pun. Ada pula tombol NOT untuk membalik sebuah grup.

**Bagian cabang, gaya CASE WHEN.** Sebuah rule boleh punya banyak cabang WHEN yang masing-masing membawa kondisi dan daftar aksinya sendiri, ditambah satu bagian ELSE opsional. Evaluasinya dari atas ke bawah dan **cabang pertama yang cocok itulah yang menang**, persis cara membaca papan tarif bertingkat. Cabang bisa diurut ulang, jadi taruh kondisi yang paling spesifik di atas.

## 3.4 Enam jenis aksi dan parameternya

Setiap cabang membawa satu atau beberapa aksi yang dijalankan berurutan.

| Aksi | Parameter | Kegunaan |
|---|---|---|
| **SET_OUTPUT** | target berupa output writable dari katalog, dan value yang tipenya harus cocok | Menulis nilai atau label, misalnya `outputs.vehicle_price_band` diisi 15000. Nilai ini terbaca oleh rule dan tabel di langkah berikutnya |
| **SET_DECISION** | decision dan reason code opsional | Mengusulkan keputusan. Kalau beberapa rule mengusulkan keputusan berbeda, yang paling berat yang menang, urutan beratnya REJECT dan FRAUD_INVESTIGATION di atas MANUAL_REVIEW di atas APPROVE |
| **ADD_REASON_CODE** | reason code | Menambah alasan tanpa memvonis, cocok untuk sekadar menandai |
| **ROUTE_MANUAL_REVIEW** | reason code opsional | Mengusulkan MANUAL_REVIEW, jalan pintas yang sering dipakai |
| **STOP_EXECUTION** | decision dan reason code opsional | Menghentikan seluruh alur saat itu juga, untuk kondisi fatal seperti daftar hitam |
| **CONTINUE** | reason code opsional | Menandai lalu lanjut, tanpa efek lain |

Satu cabang boleh menggabungkan beberapa aksi. Contohnya menulis `outputs.affordability_risk` menjadi HIGH sekaligus menambah alasan DTI_NEAR_THRESHOLD.

## 3.5 Panel kanan, yaitu pratinjau dan alat bantu

Selagi Anda merakit, panel kanan selalu menampilkan dua pratinjau. Pratinjau **manusiawi** berbentuk kalimat, misalnya "WHEN saldo lebih dari 50.000.000 THEN band harga = 20.000, ELSE 0". Pratinjau **bergaya SQL** menampilkan bentuk CASE WHEN yang familiar bagi yang terbiasa, dengan spanduk pengingat bahwa itu hanya tampilan dan OSCAR tidak pernah mengeksekusi SQL. Tab **Advanced** memuat JSON mentah untuk yang membutuhkannya, tetapi Anda tidak pernah diwajibkan menyentuhnya.

## 3.6 Menguji rule sebelum diajukan

Di halaman detail rule ada **form uji yang dibuat otomatis**. Sistem membaca fitur mana saja yang disebut rule, lalu membuatkan kotak input bertipe untuk masing-masing. Isi nilai contoh, tekan Run test, dan hasilnya menunjukkan cabang mana yang cocok, evaluasi tiap kondisi dengan nilai harapan versus nilai aktual, aksi apa saja yang akan berjalan, serta isi output setelahnya. Ujilah minimal satu kasus per cabang plus satu kasus ELSE sebelum mengajukan.

Panel **Used by** di halaman yang sama menunjukkan rule set dan strategy mana saja yang memakai rule ini, sehingga Anda tahu radius dampak sebelum mengubah atau memensiunkan.

## 3.7 Studi kasus, membuat rule band harga langkah demi langkah

Kebijakan yang diminta berbunyi begini. Band harga kendaraan yang layak ditentukan saldo tabungan, yaitu 20.000 kalau saldo di atas 50 juta, 15.000 kalau di atas 10 juta, 10.000 kalau di atas 5 juta, dan selain itu 0.

1. Pastikan `outputs.vehicle_price_band` sudah writable di katalog. Kalau belum, ikuti bab 02.
2. Buka Rules lalu New rule. Isi code `VEHICLE_PRICE_BAND`, kategori LIMIT, jenis STATEMENT.
3. Cabang pertama. Kondisinya saldo lebih dari 50000000, aksinya SET_OUTPUT ke `outputs.vehicle_price_band` dengan nilai 20000.
4. Tambah cabang kedua dan ketiga dengan pola yang sama untuk 10 juta dan 5 juta. Urutannya penting karena evaluasinya cocok pertama menang, jadi ambang terbesar di atas.
5. Nyalakan ELSE, isikan SET_OUTPUT nilai 0.
6. Lirik pratinjau kanan untuk memastikan bunyinya sesuai niat, lalu simpan sebagai draft.
7. Di halaman detail, uji dengan saldo 12 juta. Hasilnya harus cabang kedua yang cocok dan output terisi 15000.
8. Submit for approval, lalu minta risk manager menyetujui. Setelah aktif, rule ini bisa dimasukkan ke rule set dan hasil tulisannya bisa dibaca decision table.

## 3.8 Rule set, mengelompokkan aturan

Rule tidak dieksekusi sendirian, melainkan lewat **rule set**, yaitu kumpulan rule bertema yang dipasang sebagai satu node di strategy. Contoh bawaannya ELIGIBILITY_MOTOR, FRAUD_BASIC, dan AFFORDABILITY_STANDARD. Anggota rule set dieksekusi berurutan, dan rule yang menulis output lebih dulu bisa dibaca rule setelahnya. Kelola anggotanya dari halaman rule set, dan ingat bahwa strategy selalu menjalankan **versi aktif** tiap rule di dalamnya.

## 3.9 Siapa memakainya

Risk Policy Analyst hidup di layar ini setiap hari. Risk Manager menyentuhnya saat menyetujui versi. Fraud Analyst memakainya untuk menambah aturan penangkal pola penipuan baru. Data scientist sesekali ikut merancang rule CLASSIFICATION yang membungkus band model. Compliance cukup membaca, terutama pratinjau manusiawi dan riwayat versinya.
