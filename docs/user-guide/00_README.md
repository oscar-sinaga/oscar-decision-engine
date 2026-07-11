# Panduan Penggunaan OSCAR Decision Engine

> Ini panduan cara **memakai** aplikasinya, layar demi layar. Fokusnya pada kegunaan tiap fitur, arti tiap parameter, dan contoh kasus nyata. Kalau Anda ingin memahami konsep bisnisnya lebih dulu, misalnya apa itu decision engine dan kenapa dunia kredit membutuhkannya, bacalah kurikulum di `docs/learning/` sebelum panduan ini.

## Cara menjalankan aplikasi

```bash
docker compose up -d --build
```

Setelah itu buka workbench di `http://localhost:3000`. API berjalan di `http://localhost:8000` dan dokumentasi teknisnya ada di `http://localhost:8000/docs`.

## Akun demo

Semua akun memakai kata sandi `OscarDemo123!`. Pilih akun sesuai peran yang ingin Anda coba, karena menu dan tombol yang muncul mengikuti izin masing-masing peran.

| Akun | Peran | Kegunaan utamanya |
|---|---|---|
| `riskanalyst` | Risk Policy Analyst | Membuat rule, tabel keputusan, strategy, dan simulasi |
| `riskmanager` | Credit Risk Manager | Menyetujui perubahan, mengaktifkan strategy, memantau dashboard |
| `underwriter` | Underwriter | Memutus kasus manual review |
| `compliance` | Compliance | Membaca trace dan audit log |
| `datascientist` | Data Scientist | Model registry, simulasi, monitoring |
| `auditor` | Internal Audit | Membaca semuanya tanpa bisa mengubah |
| `admin` | Administrator | Semua izin, termasuk menulis rule expression |
| `los-client` | Sistem LOS | Akun mesin untuk mengirim aplikasi ke API keputusan |

## Peta menu dan bab panduan

| Menu di aplikasi | Kegunaan singkat | Bab |
|---|---|---|
| Dashboard | Memantau kesehatan keputusan harian | 08 |
| Decisions | Riwayat keputusan dan trace | 08 |
| Rules | Membuat dan mengelola aturan kredit | 03 |
| Decision Tables | Matriks keputusan bergaya spreadsheet | 04 |
| Feature Catalog | Kamus data resmi, input dan output | 02 |
| Strategies | Alur keputusan di kanvas visual | 06 |
| Simulations | Menguji kebijakan tanpa menyentuh produksi | 07 |
| Model Registry | Katalog versi model skor | 05 |
| Manual Review | Antrean kasus abu-abu untuk manusia | 09 |
| Audit Log | Jejak semua perubahan dan keputusan | 11 |
| Admin | Pengguna, peran, dan antrean persetujuan | 11 |

## Daftar isi

| Bab | File | Isi |
|---|---|---|
| 01 | `01_mulai_navigasi_dan_siklus.md` | Masuk aplikasi, siklus hidup versi, prinsip maker-checker, tabel siapa boleh apa |
| 02 | `02_feature_catalog.md` | Kamus fitur, parameter tiap kolom, output yang bisa ditulis rule, kategori rule |
| 03 | `03_rules.md` | Empat jenis rule, builder kondisi, cabang WHEN THEN ELSE, enam jenis aksi, uji coba |
| 04 | `04_decision_tables.md` | Grid editor, hit policy, baris wildcard, peringatan tumpang tindih |
| 05 | `05_scorecard_dan_model_registry.md` | Band skor menjadi grade, katalog versi model |
| 06 | `06_strategies_canvas.md` | Kanvas alur, delapan jenis node beserta parameternya, aturan graph, aktivasi dan rollback |
| 07 | `07_simulations.md` | Simulasi satu kasus dan simulasi massal, cara membaca hasilnya |
| 08 | `08_decisions_dan_trace.md` | Mengirim aplikasi, membaca riwayat, dan membedah trace |
| 09 | `09_manual_review.md` | Antrean, SLA, form keputusan analis, override, dokumen, eskalasi |
| 10 | `10_expression_admin.md` | Bahasa expression untuk admin beserta preview bergaya SQL |
| 11 | `11_audit_admin_governance.md` | Antrean persetujuan, audit log, kelola pengguna dan peran |
| 12 | `12_alur_kerja_per_peran.md` | Skenario lengkap dari kacamata tiap peran divisi credit risk |

## Cara membaca

Bab 01 wajib dibaca lebih dulu karena menjelaskan siklus hidup versi yang berlaku untuk hampir semua objek. Setelah itu bab-bab bisa dibaca sesuai kebutuhan. Kalau Anda ingin langsung merasakan alurnya dari ujung ke ujung, lompat ke bab 12 lalu kembali ke bab detail saat menemui layar yang belum familiar.

Setiap bab memakai pola yang sama, yaitu kegunaan fitur, letaknya di aplikasi, arti tiap parameter, cara memakainya langkah demi langkah, studi kasus, lalu catatan tentang siapa biasanya yang memakainya.

> Catatan. Semua data di lingkungan demo bersifat sintetis. Angka pada contoh hanyalah ilustrasi, bukan kebijakan nyata perusahaan.
