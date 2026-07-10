# Bab 9 — Glosarium Credit Risk dan Decision Engine

Daftar ini urut abjad. Istilah bertanda ★ punya makna yang spesifik di OSCAR.

| Istilah | Artinya secara singkat |
|---|---|
| **Appraisal** | Penaksiran nilai jaminan oleh penilai, misalnya harga pasar sebuah motor |
| **Approval rate** | Persentase aplikasi yang disetujui dari seluruh aplikasi yang diputus |
| **APPROVE_WITH_CONDITION** ★ | Disetujui dengan syarat, misalnya limit, tenor, atau uang muka yang disesuaikan |
| **Audit trail / audit log** ★ | Catatan yang hanya bisa ditambah atas semua tindakan pengubah keadaan, berisi siapa, kapan, apa, dari nilai berapa ke nilai berapa, alasan, dan penyetujunya |
| **Bad rate** | Persentase kontrak yang menjadi "bad" dalam suatu kohor atau periode, misalnya pernah menunggak 90 hari lebih |
| **Bureau / SLIK** | Sistem Layanan Informasi Keuangan OJK yang berisi riwayat kredit lintas lembaga, dulu dikenal sebagai BI checking |
| **BRMS** | Business Rules Management System, keluarga perangkat lunak tempat decision engine bernaung |
| **Champion/Challenger** | Menjalankan kebijakan atau model penantang pada sebagian trafik untuk dibandingkan dengan yang sedang berlaku |
| **Collection** | Proses penagihan dan pemulihan kredit bermasalah |
| **Cutoff** | Ambang skor untuk mengambil keputusan. Menggesernya berarti menggeser keseimbangan antara volume dan risiko |
| **Decision table** ★ | Matriks berisi baris kondisi dan hasilnya, dievaluasi dengan prinsip cocok pertama menang atau berdasarkan prioritas |
| **Decision trace** ★ | Rekaman permanen satu keputusan, berisi input, fitur, langkah-langkah, rule yang kena, skor, versi konfigurasi, dan hasil akhirnya |
| **Default** | Gagal bayar. Definisi operasionalnya bervariasi, misalnya menunggak 90 hari atau lebih |
| **DP (down payment)** | Uang muka, yang efeknya memperkecil LTV dan LGD |
| **DPD (days past due)** | Jumlah hari keterlambatan pembayaran |
| **DTI / FOIR** | Rasio total cicilan terhadap penghasilan, ukuran utama kemampuan bayar |
| **EAD** | Exposure at Default, yaitu sisa utang pada saat gagal bayar |
| **eKYC** | Verifikasi identitas secara elektronik, misalnya pencocokan ke Dukcapil atau biometrik |
| **Expected Loss (EL)** | Hasil kali PD, LGD, dan EAD. Inilah kerugian yang "sudah diperhitungkan" |
| **Feature / fitur** ★ | Nilai terukur milik satu aplikasi, misalnya penghasilan, LTV, dan skor. Daftar resminya disebut feature catalog |
| **First-match** | Cara evaluasi dari atas ke bawah, dan yang pertama cocok itulah yang menang, seperti CASE WHEN |
| **FRAUD_INVESTIGATION** ★ | Keputusan yang merutekan aplikasi ke pemeriksaan fraud |
| **Gini / AUC / KS** | Metrik daya pisah sebuah model skor |
| **Grade / risk grade** | Kelas risiko hasil pemetaan skor lewat band, misalnya A sampai E |
| **Hardcode** | Kebijakan yang tertanam di kode program, kebalikan dari kebijakan sebagai konfigurasi |
| **Idempotency** ★ | Jaminan bahwa pengiriman ulang permintaan yang sama tidak menciptakan keputusan ganda |
| **Kolektibilitas (Kol 1–5)** | Klasifikasi kualitas kredit menurut regulator, dari 1 yang berarti lancar sampai 5 yang berarti macet |
| **Lease-back** | Skema ketika nasabah "menjual" asetnya, misalnya motor, lalu mengangsurnya kembali. Asetnya menjadi jaminan dan uang tunainya cair |
| **LGD** | Loss Given Default, yaitu persentase eksposur yang benar-benar hilang setelah upaya pemulihan |
| **LOS** | Loan Origination System, sistem pengajuan dan pemrosesan aplikasi, yang memanggil decision engine |
| **LMS** | Loan Management System, sistem administrasi kredit yang sedang berjalan |
| **LTV** | Loan to Value, yaitu pinjaman dibagi nilai jaminan |
| **Maker-checker** ★ | Prinsip bahwa pembuat perubahan dan penyetujunya harus orang berbeda, dan sistem yang menegakkannya |
| **Manual review** ★ | Antrean kasus abu-abu untuk diputus manusia, lengkap dengan SLA dan prioritas |
| **Model registry** ★ | Katalog identitas dan versi model yang dikonsumsi engine |
| **NPL / NPF** | Non-Performing Loan atau Financing, yaitu kredit bermasalah, umumnya kolektibilitas 3 sampai 5 |
| **Origination** | Babak pengadaan kredit, dari aplikasi, keputusan, sampai pencairan |
| **Override** ★ | Keputusan manusia yang berbeda dari keputusan mesin. Wajib disertai alasan dan selalu tercatat |
| **PD** | Probability of Default, yaitu peluang gagal bayar. Inilah yang diprediksi model skor |
| **Policy overlay** | Lapisan aturan kebijakan yang membungkus keluaran model |
| **PSI / CSI** | Population atau Characteristic Stability Index, metrik untuk mendeteksi pergeseran populasi |
| **Reason code** ★ | Kode alasan baku yang menyertai keputusan, sehingga bisa diagregasi dan dilaporkan |
| **Reject inference** | Teknik menangani bias yang muncul karena pemohon yang ditolak tidak pernah punya label outcome |
| **Risk appetite** | Tingkat risiko yang sengaja dipilih perusahaan, dan menjadi dasar semua kebijakan |
| **Rollback** ★ | Mengaktifkan kembali versi kebijakan sebelumnya, dengan alasan tercatat dan tanpa menghapus sejarah |
| **Rule / rule set** ★ | Aturan berbentuk kondisi dan aksi. Kumpulannya dikelompokkan per tema untuk dipakai strategy |
| **Scorecard** ★ | Pemetaan skor menjadi grade lewat band yang berversi. Inilah jembatan antara model dan kebijakan |
| **Simulation** ★ | Menjalankan kebijakan draft tanpa efek ke produksi. Versi populasinya disebut batch simulation atau impact analysis |
| **SLA** | Batas waktu layanan, misalnya kasus review wajib diputus dalam 24 jam |
| **Strategy / decision flow** ★ | Rangkaian langkah yang mengeksekusi kebijakan per produk dan segmen. Setelah Phase 3 bentuknya bisa berupa alur bercabang |
| **Swap set** | Analisis tentang siapa yang bertukar nasib ketika kebijakan berubah, terdiri dari swap-in dan swap-out |
| **Tenor** | Jangka waktu kredit dalam bulan |
| **Underwriting** | Proses menilai dan memutus kelayakan kredit. Pelakunya disebut underwriter |
| **Versioning** ★ | Prinsip bahwa setiap konfigurasi punya versi, versi aktif tidak bisa diubah, dan setiap keputusan mencatat versi yang dipakainya |
| **Vintage analysis** | Cara menilai kualitas kredit per kohor bulan pencairan seiring bertambahnya umur kontrak |
| **WoE / IV** | Weight of Evidence dan Information Value, teknik klasik dalam membangun scorecard |

> Tips membaca rapat risk. Kalau ada istilah asing, kemungkinan besar dia ada di tabel ini. Kalau tidak ada, tanyakan saja, karena orang risk senang menjelaskan istilahnya sendiri.
