# Bab 4 — Membuka Kap Mesin, Cara Kerja Decision Engine

Bab ini membedah anatomi decision engine memakai istilah yang persis dipakai OSCAR. Dengan begitu, saat Anda membuka aplikasinya nanti, semuanya sudah terasa akrab.

## 4.1 Peta besar, dari payload sampai keputusan

```
  PAYLOAD (data aplikasi dari LOS)
      │
      ▼
  ① FEATURES ── data mentah dinormalkan dan dihitung (LTV, DTI, umur kendaraan…)
      │
      ▼
  ② STRATEGY / DECISION FLOW ── "rute pemeriksaan" langkah demi langkah:
      ├─ VALIDATION      (kelengkapan data)
      ├─ CALCULATION     (hitung fitur turunan)
      ├─ RULE SET(s)     (kumpulan aturan: eligibility, fraud, affordability…)
      ├─ SCORECARD       (skor → grade risiko)
      └─ DECISION TABLE  (matriks keputusan akhir)
      │
      ▼
  ③ OUTPUT: keputusan + reason codes + limit/tenor/pricing
      │
      ▼
  ④ TRACE & AUDIT: rekaman lengkap "kenapa"-nya (kotak hitam)
```

## 4.2 Bagian pertama, features sebagai bahasa yang dimengerti mesin

Payload mentah, misalnya penghasilan 8.500.000 dan tahun motor 2020, diubah menjadi fitur dengan nama baku seperti `applicant.monthly_income` dan `vehicle.age_years`. Ada juga fitur turunan yang dihitung oleh engine, misalnya `loan.ltv` yang merupakan hasil pembagian pinjaman dengan nilai taksiran, serta `affordability.dti` yang merupakan rasio total cicilan terhadap penghasilan.

Daftar fitur yang sah tersimpan di feature catalog, semacam kamus data resmi. Aturan hanya boleh menyebut fitur yang ada di kamus tersebut. Kalau ada yang salah ketik, misalnya `aplicant.income`, sistem langsung menolaknya saat aturan dibuat, bukan meledak di produksi.

> **Analogi.** Bayangkan formulir medical check-up. Apa pun cerita pasien, hasilnya selalu ditulis dalam kolom yang baku, yaitu tensi, gula darah, dan kolesterol. Dokter mana pun membaca kolom yang sama, dan rule mana pun juga begitu. Feature catalog adalah daftar kolom resminya.

## 4.3 Bagian kedua, rules sebagai kalimat kebijakan yang bisa dieksekusi

Satu rule terdiri dari kondisi dan aksi. Berikut contoh nyata dari data awal OSCAR.

```
JIKA  affordability.dti > 0.45         → REJECT,        alasan HIGH_DTI
JIKA  loan.ltv > 0.85                  → MANUAL_REVIEW, alasan LTV_ABOVE_THRESHOLD
JIKA  fraud.identity_match = false     → FRAUD_INVESTIGATION, alasan APPLICATION_DATA_MISMATCH
JIKA  applicant.age < 21               → REJECT,        alasan APPLICANT_UNDER_MIN_AGE
```

Kondisi bisa digabung dengan DAN atau ATAU, bahkan bisa bersarang. Rules kemudian dikelompokkan menjadi rule set per tema, misalnya ELIGIBILITY_MOTOR, FRAUD_BASIC, dan AFFORDABILITY_STANDARD, supaya rapi dan bisa dipakai ulang di banyak strategy.

Ada satu hal penting. Hasil sebuah rule tidak harus berupa vonis akhir. Rule bisa sekadar "mengangkat bendera", artinya menambah reason code lalu melanjutkan proses. Setelah Phase 3 nanti, rule bahkan bisa menulis nilai, misalnya `outputs.collateral_risk = HIGH`, yang kemudian dipakai oleh langkah berikutnya. Vonis akhirnya lahir belakangan.

> **Analogi.** Rules ibarat daftar periksa pramugari sebelum terbang. Setiap butir jelas dan tegas. Ada butir yang fatal, misalnya pintu belum tertutup sehingga penerbangan batal, dan itu setara STOP. Ada pula butir yang sekadar catatan, misalnya satu lampu baca mati sehingga dicatat tetapi pesawat tetap terbang, dan itu setara CONTINUE dengan penanda.

## 4.4 Bagian ketiga, scorecard sebagai tempat model statistik menumpang

Scorecard menerjemahkan skor, yang berasal dari model buatan Anda, menjadi grade risiko. Misalnya skor 684 menjadi grade B. Grade inilah yang dipakai aturan dan tabel keputusan berikutnya. Versi modelnya juga tercatat di setiap keputusan, contohnya `MOTOR_SCORE_V1`. Ini penting untuk audit, sekaligus berguna bagi Anda saat menganalisis performa model per versi.

> **Analogi.** Nilai ujian mentah, misalnya 684, dikonversi menjadi nilai huruf B berdasarkan tabel konversi yang disepakati fakultas. Dosen, dalam hal ini model, memberi angka. Namun tabel konversinya, yaitu scorecard, adalah kebijakan. Fakultas bisa mengubah batas nilai B tanpa perlu mengganti dosennya.

## 4.5 Bagian keempat, decision table sebagai matriks sang ketua rapat

Decision table menggabungkan beberapa masukan menjadi keputusan akhir. Bentuknya paling disukai orang bisnis karena berupa baris-baris seperti Excel, dievaluasi dari atas ke bawah dengan prinsip yang cocok pertama menang.

| Grade | DTI | Keputusan | Limit |
|---|---|---|---|
| A | ≤ 0.45 | APPROVE | sesuai pengajuan |
| B | ≤ 0.40 | APPROVE | sesuai pengajuan |
| B | 0.40–0.45 | APPROVE_WITH_CONDITION | pengajuan × 85% |
| C | ≤ 0.35 | MANUAL_REVIEW | — |
| * | * | REJECT | — |

Baris terakhir dengan tanda bintang berperan sebagai jaring pengaman, artinya berlaku untuk semua kasus yang tidak tertangkap baris di atasnya. Mesin juga memberi peringatan kalau ada dua baris yang tumpang-tindih dan berpotensi ambigu.

## 4.6 Bagian kelima, strategy atau decision flow sebagai rute pemeriksaan

Strategy menyusun semua komponen di atas menjadi urutan langkah. Setelah Phase 3, urutan ini bahkan bisa berupa alur bercabang. Strategy yang aktif dipilih otomatis berdasarkan kombinasi produk dan segmen. Produk motor lease-back punya rutenya sendiri, begitu pula produk mobil.

Urutan langkahnya punya makna bisnis. Pemeriksaan yang murah dan fatal ditaruh di depan, misalnya validasi, daftar hitam, dan umur, supaya kasus yang jelas-jelas gagal berhenti lebih cepat. Prinsip ini sering disebut fail fast. Pemeriksaan yang mahal, misalnya penarikan skor dan perhitungan detail, ditaruh belakangan.

> **Analogi.** Alur pemeriksaan di bandara juga begitu. Tiket dicek lebih dulu karena murah dan cepat, baru kemudian bagasi masuk mesin x-ray yang mahal dan lambat. Tidak ada gunanya meng-x-ray barang milik orang yang tanggal tiketnya saja salah.

## 4.7 Bagian keenam, output yang lebih kaya daripada sekadar ya atau tidak

Satu keputusan yang lengkap berisi tiga hal. Pertama, decision itu sendiri, yaitu APPROVE, REJECT, MANUAL_REVIEW, APPROVE_WITH_CONDITION, atau FRAUD_INVESTIGATION. Kedua, reason codes, yaitu kode alasan baku, bukan teks bebas, supaya bisa dihitung dan dilaporkan. Ketiga, bila relevan, limit, tenor, dan pricing yang disetujui. Ingat pelajaran bab 1, bahwa mengecilkan limit atau menaikkan uang muka sering kali lebih cerdas daripada menolak mentah-mentah.

## 4.8 Bagian ketujuh, trace sebagai kotak hitam setiap keputusan

Setiap keputusan menyimpan decision trace, yaitu rekaman berisi salinan input, nilai semua fitur, langkah-langkah yang dilalui beserta hasilnya, rule mana saja yang kena lengkap dengan nilai aktual dibanding ambangnya, skor beserta versi modelnya, versi strategy dan rules yang persis dipakai, sampai keputusan akhirnya. Rekaman ini tidak bisa diubah oleh siapa pun.

Inilah jawaban untuk pertanyaan compliance di bab 2 tadi, yaitu kenapa aplikasi enam bulan lalu ditolak. Cukup buka trace, dan terlihat persis bahwa DTI 51% melebihi ambang 45% menurut aturan versi ketiga. Kasus selesai tanpa perlu arkeologi kode.

> **Analogi.** Bayangkan kotak hitam pesawat digabung dengan struk belanja yang super rinci. Bukan cuma "totalnya 150 ribu", melainkan barang per barang, harga saat itu, kasir siapa, dan promo versi apa.

## 4.9 Jalan cerita lengkap, aplikasi Pak Budi masuk mesin

Payload-nya dari bab 1, dan strategy LEASEBACK_MOTOR sedang aktif.

```
Langkah 1 VALIDATION      : kolom wajib lengkap                     → LOLOS
Langkah 2 CALCULATION     : loan.ltv = 15jt/18jt = 0.83
                            affordability.dti = 0.39                → LOLOS
Langkah 3 RULE_SET fraud  : identitas ✓, dokumen ✓, blacklist ✗     → LOLOS
Langkah 4 RULE_SET elig.  : umur 34 ≥ 21 ✓, motor 2020 ≤ 8 th ✓     → LOLOS
Langkah 5 RULE_SET afford.: dti 0.39 ≤ 0.45 ✓, tapi dekat ambang    → TERPICU (hanya penanda)
Langkah 6 SCORECARD       : skor 684 → grade B, model MOTOR_SCORE_V1→ LOLOS
Langkah 7 DECISION_TABLE  : baris "B, dti 0.35–0.45" cocok
                            → APPROVE_WITH_CONDITION, limit 12,5jt  → COCOK
──────────────────────────────────────────────────────────────
HASIL : APPROVE_WITH_CONDITION · limit 12.500.000 · tenor 18 bulan
ALASAN: REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT
TRACE : tersimpan lengkap, tujuh langkah di atas beserta versi semua konfigurasi
WAKTU : sekitar 130 milidetik
```

Sekarang bandingkan dengan Mas Roni dari bab 1. Di langkah kelima dia langsung terkena aturan DTI karena 0.67 melebihi 0.45, sehingga hasilnya REJECT dengan alasan HIGH_DTI. Aturan LTV juga menambah alasan karena 2.0 jauh melebihi 0.85. Mesin berhenti lebih awal, jawaban keluar dalam sekejap, dan kedua alasannya tercatat.

Lalu bagaimana dengan kasus abu-abu? Pemohon dengan DTI 0.43 yang mepet ambang akan diarahkan decision table ke MANUAL_REVIEW. Kasusnya otomatis menjadi tiket antrean underwriter, lengkap dengan trace sebagai bahan pemeriksaan. Mesin tahu batas kemampuannya sendiri, dan itu justru fitur, bukan kelemahan.

## 4.10 Sifat-sifat yang membuatnya layak dipercaya

| Sifat | Artinya | Kenapa penting |
|---|---|---|
| **Deterministik** | Input yang sama dengan versi kebijakan yang sama selalu menghasilkan keputusan yang sama | Adil antar pemohon, bisa diuji, dan bisa direproduksi untuk audit maupun sengketa hukum |
| **Explainable** | Selalu ada reason code dan trace | Dibutuhkan regulator, nasabah, dan proses perbaikan kebijakan |
| **Versioned dan immutable** | Konfigurasi aktif tidak bisa diubah diam-diam, dan setiap perubahan menjadi versi baru | Masa lalu bisa direkonstruksi dan tanggung jawab menjadi jelas |
| **Simulasi tanpa efek samping** | Kebijakan draft bisa diuji tanpa menyentuh produksi | Kebijakan bisa diubah tanpa berjudi |
| **Terpisah dari kode** | Tim risk mengubah kebijakan tanpa menunggu rilis software | Bisnis bisa bereaksi cepat |

## 4.11 Rangkuman bab

Payload berubah menjadi fitur lewat kamus resmi. Strategy kemudian menjalankan rule sets, scorecard, dan decision table dalam rute yang disengaja, lalu keluarlah keputusan beserta alasan dan syaratnya. Semuanya terekam di trace, setiap komponen punya versi, dan mesin yang sama melayani produksi maupun simulasi. Bab berikutnya membahas siapa memakai layar yang mana untuk mengurus semua ini.
