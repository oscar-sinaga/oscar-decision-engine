# Bab 04 — Decision Tables, Matriks Keputusan Rasa Spreadsheet

## 4.1 Kegunaannya

Decision table adalah tabel baris demi baris yang menggabungkan beberapa masukan menjadi satu hasil. Kalau rule ibarat analis yang menulis penilaian, decision table ibarat ketua rapat yang membaca semua penilaian lalu mengetok palu. Bentuk tabelnya sengaja mirip spreadsheet karena memang begitulah orang bisnis terbiasa menulis kebijakan.

Letaknya di menu **Decision Tables**, dan sejak Phase 3 pengeditannya memakai grid, bukan JSON.

## 4.2 Anatomi tabel

Sebuah tabel terdiri dari kolom kondisi di kiri, kolom hasil di kanan, dan baris-baris yang dievaluasi dari atas ke bawah.

| Bagian | Parameter | Penjelasan |
|---|---|---|
| **Kolom kondisi** | Fitur dari katalog plus operator per sel | Bisa fitur apa pun termasuk output tulisan rule seperti `outputs.collateral_risk`. Sel yang dikosongkan berarti "berapa pun cocok" dan tampil sebagai tanda bintang |
| **Kolom hasil** | decision, risk_grade, approved_limit, approved_tenor_months, pricing_rate, reason_code | Tidak semua wajib diisi. Sel limit boleh berupa angka pasti maupun persentase dari pengajuan sesuai kebijakan |
| **Hit policy** | FIRST_MATCH atau PRIORITY | FIRST_MATCH berarti baris teratas yang cocok itulah yang menang, jadi urutan baris adalah bagian dari kebijakan. PRIORITY memakai kolom prioritas eksplisit sehingga urutan visual tidak menentukan |
| **Baris** | Tambah, gandakan, hapus, geser urutan | Menggandakan baris lalu mengubah satu sel adalah cara tercepat menulis matriks bertingkat |

Mesin juga menghitung **peringatan tumpang tindih**. Kalau dua baris bisa sama-sama cocok untuk satu kasus, baris yang bermasalah diberi tanda supaya Anda sadar ada ambiguitas. Peringatan ini tidak memblokir penyimpanan karena kadang tumpang tindih memang disengaja dengan FIRST_MATCH, tetapi selalu periksa dulu sebelum mengabaikannya.

## 4.3 Cara memakainya

1. Buka Decision Tables lalu pilih tabel, atau buat baru.
2. Pada versi draft, tambahkan kolom kondisi lewat pemilih fitur, lalu isi sel-selnya dengan input yang menyesuaikan tipe.
3. Susun baris dari kasus paling spesifik di atas menuju baris jaring pengaman di paling bawah, yaitu baris yang semua kondisinya bintang.
4. Simpan, lalu jalani siklus submit dan approve seperti biasa. Versi aktif tidak bisa diedit.

Saran praktis. Selalu sediakan baris terakhir serba bintang sebagai jaring pengaman. Tanpa itu, kasus yang lolos dari semua baris membuat mesin memakai jalur konservatif bawaan, yaitu manual review dengan alasan tidak ada baris yang cocok. Aman, tetapi antrean review Anda jadi penuh kasus yang seharusnya terjawab tabel.

## 4.4 Studi kasus, menggabungkan hasil dua rule klasifikasi

Lanjutan pola modular dari bab 03. Dua rule CLASSIFICATION sudah menulis `outputs.collateral_risk` dan `outputs.affordability_risk`. Sekarang tabel FINAL yang memutus.

| collateral_risk | affordability_risk | decision | reason_code |
|---|---|---|---|
| HIGH | HIGH | REJECT | HIGH_DTI |
| HIGH | * | MANUAL_REVIEW | LTV_ABOVE_THRESHOLD |
| * | HIGH | MANUAL_REVIEW | DTI_NEAR_THRESHOLD |
| * | * | APPROVE | |

Kekuatan pola ini terasa saat kebijakan berubah. Misalnya manajemen memutuskan kombinasi HIGH dan HIGH cukup manual review, bukan langsung tolak. Anda hanya mengubah **satu sel** pada baris pertama, tanpa menyentuh rule mana pun. Bandingkan kalau logika gabungan itu tertanam di dalam rule, perubahan kecil pun jadi operasi bongkar pasang.

Tabel bawaan `FINAL_DECISION_MOTOR` memakai pola serupa dengan masukan grade skor dan DTI, lengkap dengan kolom limit dan tenor. Bukalah sebagai contoh hidup.

## 4.5 Siapa memakainya

Risk Policy Analyst menyusun barisnya. Risk Manager membaca tabel ini paling sering saat menyetujui, karena formatnya paling mudah direview dalam rapat. Underwriter sesekali membukanya untuk memahami kenapa sebuah kasus jatuh ke barisnya. Data scientist berkepentingan pada tabel yang membaca grade skor, karena di situlah band model bertemu kebijakan.
