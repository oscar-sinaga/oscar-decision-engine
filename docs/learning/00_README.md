# Kurikulum Belajar: Credit Risk & Decision Engine

> Materi pembelajaran (bukan spesifikasi teknis) untuk memahami **bisnis credit risk** dan **peran decision engine** di dalamnya. Ditulis untuk pembaca berlatar data science yang ingin paham sisi bisnis, sisi pengambil keputusan kredit, sisi analis, dan sisi kebijakan. Bahasa Indonesia, penuh analogi dan contoh kasus.

## Untuk siapa

Terutama untuk **data scientist / engineer** yang akan bekerja dengan OSCAR Decision Engine tapi masih awam dengan alur bisnis credit risk management. Juga berguna untuk onboarding siapa pun yang baru masuk ke tim risk.

## Cara membaca

Urut dari 01 sampai 09 — tiap bab dibangun di atas bab sebelumnya. Kalau waktu terbatas:

- **Jalur cepat (±45 menit):** 01 → 03 → 04 → 08.
- **Jalur data scientist:** 01 → 03 → 04 → 07 → 08.
- **Jalur lengkap:** semua, berurutan.

## Daftar isi

| # | File | Isi | Pertanyaan yang dijawab |
|---|------|-----|--------------------------|
| 01 | `01_dasar_bisnis_credit_risk.md` | Cara bisnis lending menghasilkan uang, risiko kredit, expected loss, trade-off risiko vs pertumbuhan | "Kenapa perusahaan mau meminjamkan uang ke orang asing?" |
| 02 | `02_alur_bisnis_dan_para_pemain.md` | Siklus kredit end-to-end, LOS/LMS/collection, siapa saja orang-orangnya dan apa kerjanya | "Aplikasi kredit itu perjalanannya seperti apa, dan siapa mengerjakan apa?" |
| 03 | `03_apa_itu_decision_engine.md` | Definisi, sejarah/latar belakang, masalah yang diselesaikan | "Kenapa dunia finance butuh mesin pengambil keputusan?" |
| 04 | `04_cara_kerja_decision_engine.md` | Anatomi: feature, rule, scorecard, decision table, strategy/flow, trace | "Kalau satu aplikasi masuk, apa yang terjadi di dalam mesin?" |
| 05 | `05_penggunaan_per_peran.md` | Hari-hari tiap persona memakai engine: policy analyst, risk manager, underwriter, compliance, DS | "Nanti dipakainya bagaimana, oleh siapa?" |
| 06 | `06_konsep_penting.md` | Versioning, simulasi, cutoff & swap set, reason code, maker-checker, audit, monitoring | "Konsep-konsep yang selalu muncul di rapat risk itu maksudnya apa?" |
| 07 | `07_peran_data_scientist.md` | Scorecard, model vs kebijakan, cutoff, monitoring model, bagaimana engine membantu DS | "Sebagai DS, posisi saya di mana dan kerja saya berubah bagaimana?" |
| 08 | `08_studi_kasus_oscar.md` | Studi kasus utuh: membangun kebijakan lease-back motor dari nol memakai OSCAR | "Coba tunjukkan semuanya jalan bareng dalam satu cerita" |
| 09 | `09_glosarium.md` | Kamus istilah credit risk & decision engine | "Istilah ini artinya apa?" |

## Hubungan dengan dokumen lain di repo ini

- Materi ini **konseptual & edukatif** — boleh dibaca siapa saja, tidak mengikat implementasi.
- Spesifikasi produk yang mengikat: `docs/01..18` (MVP) dan `docs/phase3/` (fase berikutnya).
- Penjelasan fitur Phase 3 dengan analogi (masih produk-spesifik): `docs/phase3/12_penjelasan_fitur_id.md`.
- Contoh-contoh di kurikulum ini memakai **OSCAR** dan konteks **multifinance Indonesia** (pembiayaan motor/mobil, lease-back, SLIK/OJK) supaya nyambung dengan pekerjaan nyata.

> ⚠️ Semua angka di contoh (bunga, biaya, loss rate, skor) adalah **ilustrasi yang disederhanakan** untuk belajar — bukan angka kebijakan nyata perusahaan.
