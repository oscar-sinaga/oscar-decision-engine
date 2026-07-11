# Bab 02 — Feature Catalog, Kamus Data Resmi

## 2.1 Kegunaannya

Feature Catalog adalah daftar resmi semua "variabel" yang boleh disebut oleh rule, tabel keputusan, dan kondisi alur. Fungsinya seperti kamus data. Selama sebuah fitur belum terdaftar dan aktif di katalog, tidak ada aturan yang bisa memakainya, dan salah ketik nama fitur akan ditolak saat aturan disimpan, bukan meledak di produksi.

Sejak Phase 3, katalog ini juga menjadi **katalog output**. Fitur yang ditandai writable adalah "kotak" yang boleh diisi nilai oleh rule, misalnya `outputs.collateral_risk`, dan nilainya bisa dibaca lagi oleh aturan atau tabel di langkah berikutnya.

Letaknya di menu **Feature Catalog**. Halaman yang sama juga memuat kartu pengelolaan **kategori rule**.

## 2.2 Parameter sebuah fitur

| Parameter | Arti | Contoh | Catatan pemakaian |
|---|---|---|---|
| **Path** | Nama teknis unik bertitik yang dipakai aturan | `applicant.monthly_income` | Huruf kecil, ada minimal satu titik. Setelah dibuat tidak bisa diganti, jadi pilih nama yang jelas |
| **Label** | Nama ramah yang tampil di dropdown | Penghasilan Bulanan | Untuk pencarian di builder |
| **Description** | Penjelasan artinya | Penghasilan bersih per bulan dari slip gaji | Sangat membantu analis lain, isilah dengan serius |
| **Data type** | Tipe nilainya | NUMBER, STRING, BOOLEAN, DATE | Menentukan operator dan kotak input yang muncul di builder. Fitur NUMBER memunculkan operator lebih besar atau lebih kecil, fitur BOOLEAN hanya sama dengan atau tidak sama dengan |
| **Source** | Asal nilainya | PAYLOAD, DERIVED, SCORE, RULE_OUTPUT | PAYLOAD berarti dikirim LOS di aplikasi. DERIVED berarti dihitung mesin, misalnya LTV. SCORE berasal dari scorecard. RULE_OUTPUT berarti hanya diisi oleh rule |
| **Category** | Pengelompokan tampilan | LOAN, APPLICANT, OUTPUTS | Untuk memilah daftar panjang di picker |
| **Writable** | Boleh ditulis rule atau tidak | true untuk `outputs.*` | Hanya boleh true kalau source-nya DERIVED atau RULE_OUTPUT. Fitur PAYLOAD tidak pernah boleh writable, karena data kiriman LOS tidak boleh ditimpa aturan |
| **Allowed values** | Daftar nilai sah untuk fitur STRING tertentu | HIGH, MEDIUM, LOW | Opsional, sebagai pagar tata kelola |
| **Active** | Masih boleh dipakai aturan baru atau tidak | true | Menonaktifkan fitur tidak merusak rule lama, hanya mencegah rule baru memakainya |

## 2.3 Cara memakainya

**Menambah fitur input baru.** Misalnya LOS mulai mengirim saldo tabungan. Klik New feature, isi path `applicant.saving_account_balance`, tipe NUMBER, source PAYLOAD, lalu simpan. Sejak detik itu builder rule bisa memilihnya.

**Menambah output baru.** Misalnya Anda ingin rule bisa menulis band risiko agunan. Buat fitur `outputs.collateral_risk`, tipe STRING, source RULE_OUTPUT, centang writable, dan isi allowed values HIGH, MEDIUM, LOW. Aksi SET_OUTPUT di rule kini bisa menargetkannya, dan tabel keputusan bisa membacanya sebagai kolom kondisi.

**Menonaktifkan fitur.** Klik Deactivate pada barisnya. Rule yang sudah aktif tetap berjalan, tetapi rule baru atau revisi yang menyebut fitur itu akan ditolak.

**Mengelola kategori rule.** Di kartu kategori pada halaman yang sama Anda bisa menambah kategori baru, misalnya SYARIAH_COMPLIANCE, atau menonaktifkan kategori yang tidak terpakai. Kategori inilah yang muncul di form pembuatan rule.

## 2.4 Studi kasus

Tim risk ingin kebijakan baru berbasis lama bekerja pemohon, padahal fitur itu belum ada.

1. Analis meminta LOS mengirim field masa kerja di payload.
2. Analis membuka Feature Catalog, membuat `applicant.employment_years`, tipe NUMBER, source PAYLOAD, kategori APPLICANT, deskripsi "lama bekerja di pemberi kerja saat ini, dalam tahun".
3. Lima menit kemudian dia sudah bisa menulis rule "JIKA `applicant.employment_years` kurang dari 1 MAKA tandai untuk review" di builder, tanpa menunggu rilis software apa pun.

Bandingkan dengan tanpa katalog. Analis A menulis `masa_kerja`, analis B menulis `lamaKerja`, dan tabel keputusan bingung membaca yang mana. Katalog memaksa satu nama untuk satu makna.

## 2.5 Siapa memakainya

Risk Policy Analyst adalah pengguna utamanya, baik untuk mendaftarkan fitur input maupun mendefinisikan output. Data scientist ikut berkepentingan karena fitur yang terdaftar di sinilah yang nilainya terekam di trace setiap keputusan, dan rekaman itu kelak menjadi bahan analisis serta pelatihan model. Auditor cukup membaca untuk memahami arti tiap variabel yang muncul di trace.
