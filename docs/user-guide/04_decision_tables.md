# Bab 04 — Decision Tables, Matriks Keputusan Rasa Spreadsheet

## 4.1 Latar belakang, kenapa perlu tabel padahal sudah ada rule

Kalau rule sudah bisa memvonis, buat apa tabel? Jawabannya soal bentuk pikiran. Kebijakan penggabung, misalnya "grade B dengan DTI sedang boleh jalan, grade C hanya kalau DTI rendah", paling alami dituangkan sebagai **matriks**, bukan serangkaian kalimat jika maka yang saling menimpa. Coba tulis matriks lima kali lima sebagai dua puluh lima rule terpisah, lalu bayangkan merawatnya. Tabel membuat kombinasi terlihat sekali pandang, dan lubang kebijakan, yaitu kombinasi yang belum terjawab, langsung tampak sebagai baris yang belum ada.

Ada alasan kedua yang lebih dalam. Sejak rule bisa menulis nilai, dibutuhkan satu tempat yang membaca semua nilai itu dan mengetok palu. Kalau rule ibarat para analis yang menulis penilaian, decision table ibarat **ketua rapat**. Memisahkan penilai dari pemutus membuat keduanya bisa diubah sendiri-sendiri, dan itu inti pola modular.

Sejak Phase 3 pengeditannya memakai **grid** bergaya spreadsheet. Latar belakangnya sederhana, yaitu pemilik kebijakan ini terbiasa berpikir di Excel, dan sebelumnya mereka dipaksa mengedit JSON. Alat harus mengikuti pemakainya, bukan sebaliknya. Letaknya di menu **Decision Tables**.

## 4.2 Anatomi tabel dan alasan desainnya

| Bagian | Parameter | Kenapa dirancang begini |
|---|---|---|
| **Kolom kondisi** | Fitur dari katalog plus operator per sel | Boleh fitur apa pun termasuk output tulisan rule seperti `outputs.collateral_risk`, karena justru di sinilah nilai-nilai itu dipertemukan. Sel kosong berarti berapa pun cocok dan tampil sebagai bintang, supaya baris umum tidak perlu mengulang semua kolom |
| **Kolom hasil** | decision, risk_grade, approved_limit, approved_tenor_months, pricing_rate, reason_code | Hasil sengaja lebih kaya daripada sekadar vonis, karena pelajaran dasar kredit berbunyi keputusan terbaik sering berupa syarat, misalnya limit dikecilkan, bukan tolak mentah |
| **Hit policy** | FIRST_MATCH atau PRIORITY | FIRST_MATCH berarti baris teratas yang cocok menang, cocok untuk matriks bertingkat, dengan konsekuensi urutan baris adalah kebijakan. PRIORITY memakai kolom prioritas eksplisit untuk tabel yang barisnya sering ditata ulang, supaya menggeser tampilan tidak diam-diam mengubah makna |
| **Baris** | Tambah, gandakan, hapus, geser | Menggandakan baris lalu mengubah satu sel adalah cara tercepat menulis matriks bertingkat |

Lalu ada **peringatan tumpang tindih**. Mesin menghitung pasangan baris yang bisa sama-sama cocok untuk satu kasus dan menandainya. Kenapa hanya memperingatkan, bukan memblokir? Karena pada FIRST_MATCH, tumpang tindih sering kali memang disengaja, yaitu baris spesifik di atas menutup baris umum di bawah. Yang berbahaya adalah tumpang tindih yang **tidak disadari**, dan tanda itu memastikan Anda menyadarinya sebelum menyimpan.

## 4.3 Cara memakainya

Buka tabel atau buat baru, lalu bekerja di versi draft. Tambahkan kolom kondisi lewat pemilih fitur, isi sel dengan input yang mengikuti tipe, dan susun baris dari kasus paling spesifik di atas menuju baris jaring pengaman di paling bawah, yaitu baris yang semua kondisinya bintang. Setelah rapi, jalani siklus ajukan dan setujui seperti biasa.

Soal jaring pengaman itu, biasakan selalu ada. Tanpa baris serba bintang, kasus yang lolos dari semua baris jatuh ke jalur konservatif bawaan mesin, yaitu manual review dengan alasan tidak ada baris yang cocok. Perilaku bawaan itu sengaja dibuat konservatif, sebab diam-diam meloloskan kasus tak terjawab jauh lebih berbahaya daripada diam-diam menahannya. Tetap saja, antrean review yang penuh kasus semacam itu artinya tabel Anda bolong.

## 4.4 Studi kasus, menggabungkan hasil dua rule klasifikasi

Melanjutkan bab 03. Dua rule CLASSIFICATION sudah menulis `outputs.collateral_risk` dan `outputs.affordability_risk`. Tabel inilah yang memutus.

| collateral_risk | affordability_risk | decision | reason_code |
|---|---|---|---|
| HIGH | HIGH | REJECT | HIGH_DTI |
| HIGH | * | MANUAL_REVIEW | LTV_ABOVE_THRESHOLD |
| * | HIGH | MANUAL_REVIEW | DTI_NEAR_THRESHOLD |
| * | * | APPROVE | |

Kekuatan pola ini terasa saat kebijakan berubah. Misalnya manajemen melunak, kombinasi HIGH dan HIGH cukup manual review. Perubahannya **satu sel** pada baris pertama, tanpa menyentuh rule mana pun, tanpa efek samping ke kebijakan lain. Bandingkan bila logika gabungan tertanam di dalam rule, revisi kecil pun jadi bongkar pasang.

Tabel bawaan `FINAL_DECISION_MOTOR` memakai pola serupa dengan masukan grade skor dan DTI, lengkap dengan kolom limit dan tenor. Bukalah sebagai contoh hidup.

## 4.5 Siapa memakainya

Risk Policy Analyst menyusun barisnya. Risk Manager paling sering membaca tabel ini saat menyetujui, karena formatnya paling enak direview dalam rapat. Underwriter membukanya sesekali untuk memahami kenapa sebuah kasus jatuh ke barisnya, dan data scientist berkepentingan pada tabel yang membaca grade, karena di situlah band model bertemu kebijakan.
