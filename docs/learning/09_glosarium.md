# Bab 9 — Glosarium Credit Risk & Decision Engine

Urut alfabetis. Istilah bertanda ★ punya makna spesifik di OSCAR.

| Istilah | Arti singkat |
|---|---|
| **Appraisal** | Penaksiran nilai jaminan (mis. harga pasar motor) oleh penilai |
| **Approval rate** | % aplikasi yang disetujui dari total yang diputus |
| **APPROVE_WITH_CONDITION** ★ | Disetujui dengan syarat (limit/tenor/DP disesuaikan) |
| **Audit trail / audit log** ★ | Catatan append-only semua tindakan pengubah keadaan: siapa, kapan, apa, dari→ke, alasan, penyetuju |
| **Bad rate** | % kontrak yang menjadi "bad" (mis. pernah 90+ DPD) dalam suatu kohor/periode |
| **Bureau / SLIK** | Sistem Layanan Informasi Keuangan OJK — riwayat kredit lintas lembaga (dulu "BI checking") |
| **BRMS** | Business Rules Management System — keluarga software decision engine |
| **Champion/Challenger** | Menjalankan kebijakan/model penantang pada sebagian trafik untuk dibandingkan dengan yang berlaku |
| **Collection** | Proses penagihan & pemulihan kredit bermasalah |
| **Cutoff** | Ambang skor untuk keputusan; menggesernya = menggeser trade-off volume vs risiko |
| **Decision table** ★ | Matriks baris kondisi→hasil (first-match/priority) untuk keputusan/limit/pricing |
| **Decision trace** ★ | Rekaman immutable satu keputusan: input, fitur, langkah, rule yang kena, skor, versi konfigurasi, hasil |
| **Default** | Gagal bayar (definisi operasional bervariasi, mis. 90+ DPD) |
| **DP (down payment)** | Uang muka; memperkecil LTV & LGD |
| **DPD (days past due)** | Jumlah hari keterlambatan pembayaran |
| **DTI / FOIR** | Rasio total cicilan terhadap penghasilan (debt-to-income / financing-to-income) — ukuran capacity |
| **EAD** | Exposure at Default — sisa utang saat gagal bayar |
| **eKYC** | Verifikasi identitas elektronik (mis. cek Dukcapil, biometrik) |
| **Expected Loss (EL)** | PD × LGD × EAD — kerugian yang "sudah diperhitungkan" |
| **Feature / fitur** ★ | Nilai terukur milik satu aplikasi (penghasilan, LTV, skor); daftar resminya = **feature catalog** |
| **First-match** | Evaluasi dari atas ke bawah; yang pertama cocok menang (CASE WHEN) |
| **FRAUD_INVESTIGATION** ★ | Keputusan merutekan aplikasi ke pemeriksaan fraud |
| **Gini / AUC / KS** | Metrik daya pisah model skor |
| **Grade / risk grade** | Kelas risiko hasil pemetaan skor lewat band (A–E) |
| **Hardcode** | Kebijakan tertanam di kode program — lawan dari kebijakan-sebagai-konfigurasi |
| **Idempotency** ★ | Pengiriman ulang request yang sama tidak menciptakan keputusan ganda |
| **Kolektibilitas (Kol 1–5)** | Klasifikasi kualitas kredit regulator: 1 Lancar … 5 Macet |
| **Lease-back** | Nasabah "menjual" asetnya (motor) lalu mengangsurnya kembali; aset jadi jaminan, tunai cair |
| **LGD** | Loss Given Default — % eksposur yang benar-benar hilang setelah pemulihan |
| **LOS** | Loan Origination System — sistem pengajuan & proses aplikasi (yang memanggil decision engine) |
| **LMS** | Loan Management System — administrasi kredit berjalan |
| **LTV** | Loan-to-Value — pinjaman ÷ nilai jaminan |
| **Maker-checker** ★ | Pembuat perubahan ≠ penyetuju; ditegakkan sistem |
| **Manual review** ★ | Antrean kasus abu-abu untuk diputus manusia (ber-SLA, berprioritas) |
| **Model registry** ★ | Katalog identitas & versi model yang dikonsumsi engine |
| **NPL / NPF** | Non-Performing Loan/Financing — kredit bermasalah (umumnya Kol 3–5) |
| **Origination** | Babak pengadaan kredit: aplikasi → keputusan → pencairan |
| **Override** ★ | Keputusan manusia yang berbeda dari keputusan mesin — wajib beralasan & tercatat |
| **PD** | Probability of Default — peluang gagal bayar (inilah yang diprediksi model skor) |
| **Policy overlay** | Lapisan aturan kebijakan yang membungkus output model |
| **PSI / CSI** | Population/Characteristic Stability Index — metrik drift populasi |
| **Reason code** ★ | Kode alasan baku yang menyertai keputusan (bisa diagregasi & dilaporkan) |
| **Reject inference** | Teknik menangani bias karena yang ditolak tidak punya label outcome |
| **Risk appetite** | Tingkat risiko yang sengaja dipilih perusahaan — dasar semua kebijakan |
| **Rollback** ★ | Mengaktifkan kembali versi kebijakan sebelumnya (dengan alasan; sejarah tidak dihapus) |
| **Rule / rule set** ★ | Aturan kondisi→aksi; kumpulannya per tema untuk dipakai strategy |
| **Scorecard** ★ | Pemetaan skor→grade lewat band berversi (jembatan model↔kebijakan) |
| **Simulation** ★ | Menjalankan kebijakan draft tanpa efek produksi; **batch simulation/impact analysis** untuk populasi historis |
| **SLA** | Batas waktu layanan (mis. kasus review wajib diputus ≤ 24 jam) |
| **Strategy / decision flow** ★ | Rangkaian langkah (Phase 3: graph bercabang) yang mengeksekusi kebijakan per produk/segmen |
| **Swap set** | Analisis siapa yang bertukar nasib (swap-in/swap-out) saat kebijakan berubah |
| **Tenor** | Jangka waktu kredit (bulan) |
| **Underwriting** | Proses menilai & memutus kelayakan kredit; pelakunya **underwriter** |
| **Versioning** ★ | Setiap konfigurasi berversi; versi aktif immutable; keputusan mencatat versi yang dipakai |
| **Vintage analysis** | Menilai kualitas kredit per kohor bulan pencairan seiring umur kontrak |
| **WoE / IV** | Weight of Evidence / Information Value — teknik klasik pembangunan scorecard |

> Tips membaca rapat risk: kalau ada istilah asing, 90% kemungkinan ia ada di tabel ini; sisanya tanyakan — orang risk senang menjelaskan istilahnya sendiri.
