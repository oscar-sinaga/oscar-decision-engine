# Bab 10 — Expression, Menulis Aturan sebagai Teks (Khusus Admin)

## 10.1 Kegunaannya dan kenapa dibatasi

Expression adalah cara menulis rule sebagai teks formula, untuk kasus yang terasa bertele-tele kalau dirakit lewat builder. Dua bentuk pemakaiannya, yaitu rule berjenis EXPRESSION yang seluruh logikanya ditulis sebagai teks, dan aksi SET_OUTPUT yang nilainya berupa formula alih-alih angka mati.

Kemampuan ini setara dengan fitur "free SQL" di produk sejenis, tetapi dengan satu perbedaan prinsip. Teks yang Anda tulis **tidak pernah dieksekusi sebagai SQL**. Server mengurainya menjadi struktur terkontrol yang hanya mengenal operasi yang diizinkan, lalu mesin sendiri yang menghitungnya. Karena kekuatannya besar, penulisannya dibatasi izin khusus yang di lingkungan demo hanya dimiliki akun `admin`. Semua orang lain tetap bisa **membaca** hasilnya lewat pratinjau.

## 10.2 Sintaks yang didukung

| Unsur | Bentuk | Contoh |
|---|---|---|
| Formula nilai | aritmetika biasa | `monthly_income * 0.3 - existing_monthly_obligation` |
| Perbandingan | `=` `!=` `>` `>=` `<` `<=` `IN (...)` `NOT IN (...)` `IS NULL` `IS NOT NULL` | `loan.ltv > 0.85 AND vehicle.type = 'MOTOR'` |
| Logika | `AND` `OR` `NOT` dengan tanda kurung | `NOT (a OR b)` |
| Bercabang | `CASE WHEN ... THEN ... ELSE ... END` | contoh di bawah |
| Fungsi | `MIN` `MAX` `ROUND` `ABS` `COALESCE` | `ROUND(MIN(x, y) / 12)` |
| Nilai | angka, teks berkutip tunggal, TRUE, FALSE, NULL | `'MOTOR'`, `0.45` |

Identifier hanya boleh berupa fitur yang terdaftar dan aktif di katalog, memakai path bertitiknya. Kata kunci boleh huruf besar atau kecil. Nilai yang hilang menjadi NULL, perhitungan dengan NULL menghasilkan NULL, cabang WHEN yang hasilnya NULL dianggap tidak cocok, dan `COALESCE` adalah alat resmi untuk memberi nilai pengganti.

Contoh lengkap gaya papan tarif.

```
CASE WHEN applicant.saving_account_balance > 50000000 THEN 20000
     WHEN applicant.saving_account_balance > 10000000 THEN 15000
     WHEN applicant.saving_account_balance > 5000000  THEN 10000
     ELSE 0
END
```

## 10.3 Cara memakainya

1. Buka Rules lalu New rule, pilih jenis EXPRESSION. Pilihan ini hanya tampil untuk akun berizin.
2. Tulis teksnya di editor. Setiap Anda berhenti mengetik, server memvalidasi dan editor menampilkan hasilnya, entah tanda sah beserta tipe hasil yang disimpulkan, entah pesan kesalahan lengkap dengan baris dan kolomnya. Tombol insert feature membuka pemilih katalog dan menyisipkan path di posisi kursor supaya tidak salah ketik.
3. Pilih **output target**, yaitu output writable yang akan menampung hasil formula, misalnya `outputs.max_installment`.
4. Simpan sebagai draft, uji lewat form uji seperti rule biasa, lalu jalani siklus persetujuan yang sama. Tidak ada jalur pintas, expression pun melewati maker-checker.

## 10.4 Pratinjau bergaya SQL untuk semua orang

Terlepas dari cara pembuatannya, setiap rule punya tab pratinjau bergaya SQL yang menampilkan bentuk `CASE WHEN ... END` yang familiar, dengan spanduk pengingat bahwa itu hanya tampilan. Gunanya untuk membaca cepat, misalnya risk manager yang terbiasa membaca SQL bisa mereview rule buatan builder tanpa membuka cabang satu per satu.

## 10.5 Batas yang sengaja dipasang

Panjang teks, kedalaman kurung, jumlah cabang, dan panjang daftar IN semuanya dibatasi. Tidak ada akses ke tabel, tidak ada fungsi di luar lima yang disebut, tidak ada tanggal hari ini atau angka acak, sehingga hasil formula selalu deterministik dan bisa direproduksi untuk audit. Kalau Anda menabrak batas ini, editor memberi tahu dengan jelas.

## 10.6 Studi kasus

Admin diminta menulis batas cicilan maksimal yang bergantung dua hal sekaligus, yaitu sepertiga penghasilan atau seperdua belas limit yang layak, mana yang lebih kecil.

1. Dia membuat rule EXPRESSION dengan output target `outputs.max_installment`.
2. Teksnya `ROUND(MIN(applicant.monthly_income * 0.3, outputs.eligible_limit / 12))`. Perhatikan formula ini membaca output tulisan rule lain, dan itu sah selama rule penulisnya berjalan lebih dulu di alur.
3. Validasi hijau, diuji dengan beberapa kombinasi nilai, diajukan, disetujui manager, aktif. Decision table kemudian memakai `outputs.max_installment` sebagai kolom kondisi.

## 10.7 Siapa memakainya

Admin atau engineering menulisnya, biasanya atas permintaan tim policy untuk formula yang builder tidak cukup luwes. Semua peran lain memanfaatkan pratinjau SQL-nya sebagai alat baca. Kalau kelak perusahaan ingin analis senior ikut menulis expression, izinnya tinggal diberikan lewat menu Admin tanpa perubahan sistem.
