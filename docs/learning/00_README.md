# Kurikulum Belajar Credit Risk dan Decision Engine

> Ini materi pembelajaran, bukan spesifikasi teknis. Tujuannya membantu pembaca memahami bisnis credit risk serta peran decision engine di dalamnya. Materi ini ditulis terutama untuk pembaca berlatar data science yang ingin paham sisi bisnis, sisi pengambil keputusan kredit, sisi analis, dan sisi kebijakan. Bahasanya dibuat mengalir, dengan banyak analogi dan contoh kasus.

## Untuk siapa materi ini

Terutama untuk data scientist atau engineer yang akan bekerja dengan OSCAR Decision Engine namun masih awam dengan alur bisnis credit risk management. Materi ini juga cocok dipakai untuk onboarding siapa pun yang baru bergabung ke tim risk.

## Cara membaca

Bacalah berurutan dari bab 01 sampai 09 karena tiap bab dibangun di atas bab sebelumnya. Kalau waktu Anda terbatas, ada beberapa jalur pintas.

- Jalur cepat sekitar 45 menit, yaitu bab 01, 03, 04, lalu 08.
- Jalur khusus data scientist, yaitu bab 01, 03, 04, 07, lalu 08.
- Jalur lengkap, yaitu semua bab secara berurutan.

## Daftar isi

| Bab | File | Isi | Pertanyaan yang dijawab |
|---|------|-----|--------------------------|
| 01 | `01_dasar_bisnis_credit_risk.md` | Cara bisnis pembiayaan menghasilkan uang, risiko kredit, expected loss, serta tarik-menarik antara risiko dan pertumbuhan | "Kenapa ada perusahaan yang mau meminjamkan uang ke orang asing?" |
| 02 | `02_alur_bisnis_dan_para_pemain.md` | Siklus kredit dari awal sampai akhir, kedudukan LOS, LMS, dan collection, serta siapa saja orang-orangnya | "Aplikasi kredit itu perjalanannya seperti apa, dan siapa mengerjakan apa?" |
| 03 | `03_apa_itu_decision_engine.md` | Definisi, latar belakang sejarah, dan masalah yang diselesaikan | "Kenapa dunia keuangan butuh mesin pengambil keputusan?" |
| 04 | `04_cara_kerja_decision_engine.md` | Anatomi mesin, mulai dari feature, rule, scorecard, decision table, strategy, sampai trace | "Kalau satu aplikasi masuk, apa yang terjadi di dalam mesin?" |
| 05 | `05_penggunaan_per_peran.md` | Keseharian tiap peran ketika memakai mesin, dari policy analyst sampai data scientist | "Nanti dipakainya bagaimana, dan oleh siapa?" |
| 06 | `06_konsep_penting.md` | Versioning, simulasi, cutoff, swap set, reason code, maker-checker, audit, dan monitoring | "Istilah yang selalu muncul di rapat risk itu maksudnya apa?" |
| 07 | `07_peran_data_scientist.md` | Scorecard, hubungan model dengan kebijakan, cutoff, dan monitoring model | "Sebagai data scientist, posisi saya di mana?" |
| 08 | `08_studi_kasus_oscar.md` | Studi kasus utuh membangun kebijakan lease-back motor dari nol memakai OSCAR | "Coba tunjukkan semuanya berjalan bersama dalam satu cerita." |
| 09 | `09_glosarium.md` | Kamus istilah credit risk dan decision engine | "Istilah ini artinya apa?" |

## Hubungan dengan dokumen lain di repositori ini

Materi ini bersifat konseptual dan edukatif, sehingga boleh dibaca siapa saja dan tidak mengikat implementasi. Spesifikasi produk yang mengikat tetap berada di `docs/01..18` untuk MVP dan `docs/phase3/` untuk fase berikutnya. Ada pula penjelasan fitur Phase 3 dengan analogi di `docs/phase3/12_penjelasan_fitur_id.md`, hanya saja dokumen itu lebih spesifik ke produk.

Contoh-contoh di kurikulum ini sengaja memakai OSCAR dan konteks multifinance Indonesia, misalnya pembiayaan motor, lease-back, serta SLIK dan OJK, supaya nyambung dengan pekerjaan sehari-hari.

> Catatan penting. Semua angka di dalam contoh, baik bunga, biaya, loss rate, maupun skor, hanyalah ilustrasi yang disederhanakan untuk belajar. Itu bukan angka kebijakan perusahaan yang sesungguhnya.
