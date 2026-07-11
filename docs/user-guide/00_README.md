# Panduan Penggunaan OSCAR Decision Engine

> Ini panduan cara memakai aplikasinya, layar demi layar. Setiap bab menjelaskan tiga hal sekaligus, yaitu **latar belakang** kenapa fitur itu ada, **kegunaan** beserta arti tiap parameternya lengkap dengan alasan desainnya, dan **contoh kasus** pemakaiannya. Tujuannya bukan sekadar supaya Anda bisa mengklik, melainkan supaya Anda paham cara berpikir di balik setiap layar, sehingga kelak bisa menilai sendiri mana fitur yang perlu direvisi.

Kalau konsep dasarnya sendiri masih terasa asing, misalnya apa itu decision engine dan kenapa dunia kredit membutuhkannya, bacalah dulu kurikulum di `docs/learning/`. Panduan ini melanjutkan dari sana ke praktik.

## Menjalankan aplikasi

```bash
docker compose up -d --build
```

Setelah semuanya berjalan, buka workbench di `http://localhost:3000`. API ada di `http://localhost:8000`, dan dokumentasi teknisnya bisa dilihat di `http://localhost:8000/docs`.

## Akun demo

Semua akun memakai kata sandi `OscarDemo123!`. Cobalah berganti-ganti akun, karena menu dan tombol yang tampil mengikuti izin peran masing-masing. Itu cara tercepat merasakan bagaimana sistem membagi kekuasaan.

| Akun | Peran | Dipakai untuk apa |
|---|---|---|
| `riskanalyst` | Risk Policy Analyst | Membuat rule, tabel keputusan, strategy, dan simulasi |
| `riskmanager` | Credit Risk Manager | Menyetujui perubahan, mengaktifkan strategy, memantau dashboard |
| `underwriter` | Underwriter | Memutus kasus manual review |
| `compliance` | Compliance | Membaca trace dan audit log |
| `datascientist` | Data Scientist | Model registry, simulasi, monitoring |
| `auditor` | Internal Audit | Membaca semuanya tanpa bisa mengubah apa pun |
| `admin` | Administrator | Semua izin, termasuk menulis rule expression |
| `los-client` | Sistem LOS | Akun mesin yang mengirim aplikasi ke API keputusan |

## Peta menu dan daftar isi

| Menu | Kegunaan singkat | Bab |
|---|---|---|
| Dashboard | Memantau kesehatan keputusan harian | 08 |
| Decisions | Riwayat keputusan dan trace | 08 |
| Rules | Menulis aturan kredit | 03 |
| Decision Tables | Matriks keputusan bergaya spreadsheet | 04 |
| Feature Catalog | Kamus data resmi, input dan output | 02 |
| Strategies | Alur keputusan di kanvas visual | 06 |
| Simulations | Menguji kebijakan tanpa menyentuh produksi | 07 |
| Model Registry | Katalog versi model skor | 05 |
| Manual Review | Antrean kasus abu-abu untuk manusia | 09 |
| Audit Log | Jejak semua perubahan dan keputusan | 11 |
| Admin | Pengguna, peran, dan antrean persetujuan | 11 |

Urutan babnya begini. Bab 01 wajib dibaca lebih dulu karena menjelaskan siklus hidup versi yang berlaku untuk hampir semua objek. Bab 02 sampai 11 membedah tiap layar. Bab 12 merangkai semuanya menjadi skenario lengkap dari kacamata tiap peran di divisi credit risk. Bab 13 keluar dari layar dan membahas gambaran integrasi OSCAR dengan sistem korporat yang sudah ada, yaitu LOS, LMS, collection, dan Muffin, termasuk cara menghindari bottleneck.

> Catatan. Semua data di lingkungan demo bersifat sintetis, dan semua angka pada contoh hanyalah ilustrasi, bukan kebijakan nyata perusahaan.
