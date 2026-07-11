# Bab 10 — Expression, Menulis Aturan sebagai Teks (Khusus Admin)

## 10.1 Latar belakang, "free SQL" yang dijinakkan

Produk decision engine kelas enterprise biasanya menyediakan mode "free SQL", yaitu pengguna mahir menulis logika sebagai teks bebas alih-alih mengklik builder. Kebutuhan di baliknya nyata, karena ada formula yang terasa bertele-tele bila dirakit kotak per kotak, misalnya batas cicilan yang merupakan nilai terkecil dari dua perhitungan.

Masalahnya, SQL bebas di mesin keputusan itu berbahaya. Teks bebas bisa membaca data yang bukan haknya, hasilnya bisa berubah-ubah, dan menyuntikkan perintah lewat teks adalah serangan tertua di dunia perangkat lunak. OSCAR mengambil jalan tengahnya, yaitu **kekuatan menulis teks tetap ada, bahayanya dibuang**. Teks yang Anda tulis tidak pernah dieksekusi sebagai SQL. Server mengurainya menjadi struktur terkontrol yang hanya mengenal operasi yang diizinkan, dan mesin sendiri yang menghitungnya. Tidak ada akses tabel, tidak ada perintah tersembunyi, tidak ada tanggal hari ini atau angka acak, sehingga hasilnya selalu deterministik dan bisa direproduksi untuk audit.

Karena kekuatannya tetap besar, penulisannya dibatasi lewat izin khusus yang untuk sekarang hanya dipegang `admin`. Pembatasan ini disengaja bertahap, mulai dari lingkar paling kecil dulu, dan bisa diperluas ke analis senior kapan saja lewat menu Admin tanpa perubahan sistem.

## 10.2 Sintaks yang didukung

| Unsur | Bentuk | Contoh |
|---|---|---|
| Formula nilai | aritmetika biasa | `monthly_income * 0.3 - existing_monthly_obligation` |
| Perbandingan | `=` `!=` `>` `>=` `<` `<=` `IN (...)` `NOT IN (...)` `IS NULL` `IS NOT NULL` | `loan.ltv > 0.85 AND vehicle.type = 'MOTOR'` |
| Logika | `AND` `OR` `NOT` dengan kurung | `NOT (a OR b)` |
| Bercabang | `CASE WHEN ... THEN ... ELSE ... END` | contoh di bawah |
| Fungsi | `MIN` `MAX` `ROUND` `ABS` `COALESCE` | `ROUND(MIN(x, y) / 12)` |
| Nilai | angka, teks berkutip tunggal, TRUE, FALSE, NULL | `'MOTOR'`, `0.45` |

Identifier hanya boleh fitur yang terdaftar dan aktif di katalog, dan itu bukan kebetulan, melainkan kamus data yang sama dari bab 02 bekerja lagi di sini. Nilai yang hilang menjadi NULL, perhitungan dengan NULL menghasilkan NULL, cabang WHEN bernilai NULL dianggap tidak cocok, dan `COALESCE` adalah alat resmi memberi nilai pengganti. Lima fungsi itu saja yang ada, karena setiap fungsi tambahan adalah permukaan serangan tambahan, dan lima itu sudah menutup kebutuhan formula kredit yang lazim.

Contoh lengkap bergaya papan tarif.

```
CASE WHEN applicant.saving_account_balance > 50000000 THEN 20000
     WHEN applicant.saving_account_balance > 10000000 THEN 15000
     WHEN applicant.saving_account_balance > 5000000  THEN 10000
     ELSE 0
END
```

## 10.3 Cara memakainya

1. Buka Rules lalu New rule dan pilih jenis EXPRESSION. Pilihan ini hanya muncul untuk akun berizin.
2. Tulis teksnya. Setiap kali Anda berhenti mengetik, server memvalidasi, dan editor menampilkan tanda sah beserta tipe hasil yang disimpulkan, atau pesan kesalahan lengkap dengan baris dan kolomnya. Tombol insert feature membuka pemilih katalog dan menyisipkan path di posisi kursor, membunuh salah ketik.
3. Pilih **output target**, yaitu output writable yang menampung hasil formula, misalnya `outputs.max_installment`. Aturan writable dari bab 02 berlaku persis sama di sini.
4. Simpan sebagai draft, uji lewat form uji, lalu jalani siklus persetujuan biasa. Tidak ada jalur pintas, expression pun melewati maker-checker, karena kekuatan lebih justru menuntut tata kelola yang sama ketatnya.

Ada juga batas ukuran, yaitu panjang teks, kedalaman kurung, jumlah cabang, dan panjang daftar IN semuanya dibatasi. Kalau tertabrak, editor memberi tahu dengan jelas. Batas ini pagar terakhir supaya tidak ada teks raksasa yang membebani mesin keputusan.

## 10.4 Pratinjau bergaya SQL untuk semua orang

Terlepas dari cara pembuatannya, setiap rule punya tab pratinjau bergaya SQL berbentuk `CASE WHEN ... END`, dengan spanduk pengingat bahwa itu tampilan semata. Latar belakang fitur kecil ini menarik, yaitu banyak orang risk yang besar di dunia SQL membaca CASE WHEN lebih cepat daripada membuka kartu cabang satu per satu. Jadi meskipun eksekusi SQL ditolak, **bahasa bacanya** dipertahankan sebagai jembatan untuk mereka.

## 10.5 Studi kasus

Admin diminta menulis batas cicilan maksimal, yaitu nilai terkecil antara sepertiga penghasilan dan seperdua belas limit yang layak.

Dia membuat rule EXPRESSION bertarget `outputs.max_installment`, lalu menulis `ROUND(MIN(applicant.monthly_income * 0.3, outputs.eligible_limit / 12))`. Perhatikan formula ini membaca output tulisan rule lain, dan itu sah selama rule penulisnya berjalan lebih dulu di alur. Validasi hijau, diuji beberapa kombinasi, diajukan, disetujui manager, aktif. Decision table kemudian tinggal memakai `outputs.max_installment` sebagai kolom kondisi. Coba bayangkan formula yang sama dirakit lewat builder kotak per kotak, bisa, tetapi jauh lebih berbelit, dan justru untuk kasus seperti inilah expression ada.

## 10.6 Siapa memakainya

Admin atau engineering menulisnya, biasanya atas pesanan tim policy untuk formula yang builder kurang luwes. Semua peran lain menikmati pratinjau SQL-nya sebagai alat baca.
