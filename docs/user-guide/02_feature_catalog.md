# Bab 02 — Feature Catalog, Kamus Data Resmi

## 2.1 Latar belakang, masalah apa yang mau dicegah

Bayangkan tiga analis menulis aturan tentang hal yang sama. Analis A menyebutnya `masa_kerja`, analis B menulis `lamaKerja`, analis C mengetik `employment_yrs`. Tiga nama untuk satu makna, dan decision table yang mau membacanya bingung memilih yang mana. Tambahkan satu masalah lagi, yaitu salah ketik. Aturan yang menyebut `aplicant.income` tidak akan pernah cocok dengan data siapa pun, dan kesalahannya baru ketahuan setelah ribuan keputusan aneh lolos ke produksi.

Feature Catalog lahir untuk menutup dua lubang itu. Ia adalah **kamus data resmi**, yaitu daftar tunggal semua variabel yang boleh disebut oleh rule, tabel keputusan, dan kondisi alur. Nama yang tidak ada di kamus ditolak saat aturan disimpan, jauh sebelum sempat menyakiti produksi. Satu nama, satu makna, satu tempat mendokumentasikannya.

Sejak Phase 3 kamus ini merangkap peran kedua sebagai **katalog output**. Ceritanya begini. Rule kini boleh menulis nilai, misalnya band risiko agunan, yang dibaca aturan berikutnya. Kalau setiap rule bebas mengarang nama tampungannya sendiri, kekacauan tiga-nama-satu-makna tadi terulang di sisi output. Maka target tulisan rule pun diwajibkan terdaftar di kamus, ditandai lewat kolom writable.

Letaknya di menu **Feature Catalog**, dan halaman yang sama memuat kartu pengelolaan **kategori rule**.

## 2.2 Parameter sebuah fitur dan alasan desainnya

| Parameter | Arti | Kenapa dirancang begini |
|---|---|---|
| **Path** | Nama teknis unik bertitik, misalnya `applicant.monthly_income` | Bertitik supaya terkelompok alami per bagian payload. Sekali dibuat tidak bisa diganti, karena path ini tertanam di rule aktif dan di trace keputusan lama. Mengganti nama berarti memutus jejak sejarah |
| **Label** dan **Description** | Nama ramah dan penjelasan makna | Kamus tanpa definisi hanyalah daftar kata. Deskripsi yang serius mencegah dua analis memahami satu fitur secara berbeda, misalnya penghasilan kotor versus bersih |
| **Data type** | NUMBER, STRING, BOOLEAN, atau DATE | Inilah yang membuat builder "sadar tipe". Fitur NUMBER memunculkan operator pembanding dan kotak angka, fitur BOOLEAN hanya menawarkan benar salah. Tanpa tipe, kesalahan konyol seperti membandingkan umur dengan teks baru ketahuan di produksi |
| **Source** | PAYLOAD dari kiriman LOS, DERIVED dihitung mesin, SCORE dari scorecard, RULE_OUTPUT ditulis rule | Pembaca aturan perlu tahu dari mana angka berasal saat menelusuri masalah. Source juga menjadi dasar aturan writable di bawah |
| **Writable** | Boleh menjadi target tulisan rule atau tidak | Hanya boleh menyala untuk source DERIVED atau RULE_OUTPUT. Fitur PAYLOAD tidak pernah boleh writable, karena data kiriman LOS adalah fakta tentang pemohon, dan fakta tidak boleh ditimpa aturan. Kalau aturan bisa menulis ulang penghasilan pemohon, seluruh trace kehilangan makna |
| **Category** | Pengelompokan seperti LOAN, APPLICANT, OUTPUTS | Murni kenyamanan, supaya pemilih fitur yang panjang tetap bisa dijelajahi |
| **Allowed values** | Daftar nilai sah untuk fitur STRING tertentu, misalnya HIGH, MEDIUM, LOW | Pagar tata kelola untuk label klasifikasi, supaya tidak ada rule yang menulis TINGGI sementara tabel menunggu HIGH |
| **Active** | Masih boleh dipakai aturan baru atau tidak | Perhatikan, pilihannya menonaktifkan, bukan menghapus. Rule lama yang terlanjur memakai fitur itu harus tetap bisa dibaca dan direproduksi, jadi fitur tidak pernah benar-benar hilang, hanya ditutup untuk pemakaian baru |

## 2.3 Cara memakainya

**Menambah fitur input.** Misalnya LOS mulai mengirim saldo tabungan. Tekan New feature, isi path `applicant.saving_account_balance`, tipe NUMBER, source PAYLOAD, lalu simpan. Sejak detik itu pemilih fitur di builder rule menampilkannya.

**Menambah output.** Ingin rule bisa menulis band risiko agunan? Buat `outputs.collateral_risk`, tipe STRING, source RULE_OUTPUT, nyalakan writable, dan isi allowed values HIGH, MEDIUM, LOW. Aksi SET_OUTPUT kini bisa menargetkannya, dan tabel keputusan bisa membacanya sebagai kolom kondisi.

**Menonaktifkan fitur.** Tekan Deactivate pada barisnya. Aturan yang sudah aktif tetap berjalan, tetapi aturan baru yang menyebut fitur itu akan ditolak.

**Mengelola kategori rule.** Kartu kategori di halaman yang sama dipakai menambah kategori baru, misalnya SYARIAH_COMPLIANCE, atau menonaktifkan yang tak terpakai. Dulu daftar kategori tertanam di kode, dan setiap tambahan berarti menunggu rilis software. Sekarang cukup satu klik, karena daftar itu pun sudah menjadi data.

## 2.4 Studi kasus

Tim risk ingin kebijakan berbasis lama bekerja, padahal fiturnya belum ada.

Analis lebih dulu meminta LOS menyertakan masa kerja di payload. Sambil menunggu, dia membuka Feature Catalog dan mendaftarkan `applicant.employment_years`, tipe NUMBER, source PAYLOAD, dengan deskripsi "lama bekerja di pemberi kerja saat ini, dalam tahun". Lima menit kemudian rule "kurang dari satu tahun berarti tandai untuk review" sudah bisa dirakit di builder. Tidak ada tiket IT, tidak ada rilis, dan yang terpenting tidak akan pernah ada kembaran fitur bernama `lama_kerja` buatan orang lain, karena semua orang melihat kamus yang sama.

## 2.5 Siapa memakainya

Risk Policy Analyst adalah pengguna utamanya, baik mendaftarkan input maupun mendefinisikan output. Data scientist ikut berkepentingan, sebab fitur yang terdaftar di sinilah yang nilainya terekam di trace tiap keputusan, dan rekaman itu kelak menjadi bahan analisis serta pelatihan model. Auditor cukup membaca, terutama kolom deskripsi, untuk memahami arti variabel yang muncul di trace.
