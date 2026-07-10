# Bab 4 — Membuka Kap Mesin: Cara Kerja Decision Engine

Bab ini membedah anatomi decision engine memakai istilah yang persis dipakai OSCAR, supaya saat Anda membuka aplikasinya semuanya terasa familiar.

## 4.1 Peta besar: dari payload sampai keputusan

```
  PAYLOAD (data aplikasi dari LOS)
      │
      ▼
  ① FEATURES ── data mentah dinormalkan + dihitung (LTV, DTI, umur kendaraan…)
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

## 4.2 ① Features — bahasa yang dimengerti mesin

Payload mentah (`penghasilan: 8.500.000`, `tahun motor: 2020`) diubah jadi **fitur** bernama baku: `applicant.monthly_income`, `vehicle.age_years`, dan fitur **turunan** yang dihitung engine: `loan.ltv = pinjaman / nilai taksiran`, `affordability.dti = (cicilan berjalan + cicilan baru) / penghasilan`.

Daftar fitur yang sah hidup di **feature catalog** — kamus data resmi. Aturan hanya boleh menyebut fitur yang ada di kamus (typo `aplicant.income` langsung ditolak saat aturan dibuat, bukan meledak di produksi).

> **Analogi:** formulir medical check-up. Apa pun cerita pasien, hasilnya ditulis dalam kolom baku: tensi, gula darah, kolesterol. Dokter mana pun (rule mana pun) membaca kolom yang sama. Feature catalog = daftar kolom resminya.

## 4.3 ② Rules — kalimat kebijakan yang bisa dieksekusi

Satu rule = **kondisi** + **aksi**. Contoh nyata dari seed OSCAR:

```
JIKA  affordability.dti > 0.45         → REJECT,        alasan HIGH_DTI
JIKA  loan.ltv > 0.85                  → MANUAL_REVIEW, alasan LTV_ABOVE_THRESHOLD
JIKA  fraud.identity_match = false     → FRAUD_INVESTIGATION, alasan APPLICATION_DATA_MISMATCH
JIKA  applicant.age < 21               → REJECT,        alasan APPLICANT_UNDER_MIN_AGE
```

Kondisi bisa digabung AND/OR dan bersarang. Rules dikelompokkan jadi **rule set** per tema (ELIGIBILITY_MOTOR, FRAUD_BASIC, AFFORDABILITY_STANDARD) supaya rapi dan bisa dipakai-ulang di banyak strategy.

Penting: hasil rule **tidak harus vonis final**. Rule bisa hanya "mengangkat bendera" (tambah reason code lalu lanjut), dan — setelah Phase 3 — bisa **menulis nilai** (`outputs.collateral_risk = HIGH`) yang dipakai langkah berikutnya. Vonis finalnya lahir belakangan.

> **Analogi:** rules = **daftar periksa (checklist) pramugari sebelum terbang**. Tiap butir jelas, biner, tertulis. Ada butir yang fatal (pintu tidak tertutup → batal terbang = STOP), ada yang catatan (satu lampu baca mati → catat, tetap terbang = CONTINUE + flag).

## 4.4 ② Scorecard — tempat model statistik menumpang

Scorecard menerjemahkan **skor** (dari model — dunia Anda!) menjadi **grade risiko**: skor 684 → grade **B**. Grade inilah yang dipakai aturan/tabel berikutnya. Versi model tercatat di setiap keputusan (`MOTOR_SCORE_V1`) — penting untuk audit dan untuk Anda saat menganalisis performa model per versi.

> **Analogi:** nilai ujian mentah (684) dikonversi jadi nilai huruf (B) berdasarkan tabel konversi yang disepakati fakultas. Dosen (model) memberi angka; **tabel konversinya (scorecard) adalah kebijakan** — fakultas bisa mengubah batas nilai B tanpa mengganti dosennya.

## 4.5 ② Decision table — matriks "ketua rapat"

Tabel keputusan menggabungkan beberapa masukan jadi keputusan akhir, dalam bentuk yang paling disukai orang bisnis — **baris-baris seperti Excel**, dievaluasi dari atas ke bawah (first match):

| Grade | DTI | Keputusan | Limit |
|---|---|---|---|
| A | ≤ 0.45 | APPROVE | sesuai pengajuan |
| B | ≤ 0.40 | APPROVE | sesuai pengajuan |
| B | 0.40–0.45 | APPROVE_WITH_CONDITION | pengajuan × 85% |
| C | ≤ 0.35 | MANUAL_REVIEW | — |
| * | * | REJECT | — |

Baris terakhir (`*`,`*`) = jaring pengaman "selain itu semua". Mesin juga memperingatkan kalau ada dua baris yang tumpang-tindih (ambigu).

## 4.6 ② Strategy / decision flow — rute pemeriksaannya

Strategy menyusun semua komponen di atas jadi **urutan** (dan setelah Phase 3: **alur bercabang**). Strategy aktif dipilih otomatis berdasarkan **produk + segmen** — produk motor lease-back punya rute sendiri, mobil punya rute sendiri.

Urutannya bermakna bisnis: pemeriksaan **murah & fatal duluan** (validasi, blacklist, umur) supaya kasus yang jelas-jelas gagal berhenti cepat ("fail fast") sebelum pemeriksaan mahal (tarik skor, hitung-hitungan detail).

> **Analogi:** alur pemeriksaan bandara — cek tiket dulu (murah, cepat), baru x-ray bagasi (mahal, lambat). Tidak ada gunanya meng-x-ray orang yang tiketnya saja salah tanggal.

## 4.7 ③ Output — bukan sekadar ya/tidak

Satu keputusan lengkap berisi: **decision** (APPROVE / REJECT / MANUAL_REVIEW / APPROVE_WITH_CONDITION / FRAUD_INVESTIGATION), **reason codes** (kode alasan baku — bukan teks bebas, supaya bisa dihitung & dilaporkan), dan bila relevan **limit / tenor / pricing** yang disetujui. Ingat pelajaran bab 1: mengecilkan limit atau menaikkan DP sering lebih cerdas daripada menolak mentah.

## 4.8 ④ Trace — kotak hitam setiap keputusan

Setiap keputusan menyimpan **decision trace**: snapshot input, nilai semua fitur, langkah-langkah yang dilalui beserta hasilnya, rule mana yang kena (nilai aktual vs ambang), skor & versi model, versi strategy/rules yang persis dipakai, sampai keputusan akhir. Immutable — tidak bisa diedit siapa pun.

Inilah jawaban atas pertanyaan compliance di bab 2: *"aplikasi 6 bulan lalu ini kenapa ditolak?"* → buka trace → terlihat persis: DTI 51% > ambang 45% versi aturan #3. Selesai, tanpa arkeologi kode.

> **Analogi:** black box pesawat + struk belanja super rinci digabung jadi satu. Bukan cuma "totalnya 150 ribu", tapi item per item, harga saat itu, kasir siapa, promo versi apa.

## 4.9 Jalan cerita lengkap: aplikasi Pak Budi masuk mesin

(payload dari bab 1; strategy LEASEBACK_MOTOR aktif)

```
Step 1 VALIDATION      : kolom wajib lengkap                     → PASSED
Step 2 CALCULATION     : loan.ltv = 15jt/18jt = 0.83
                         affordability.dti = 0.39                → PASSED
Step 3 RULE_SET fraud  : identity ✓, dokumen ✓, blacklist ✗      → PASSED
Step 4 RULE_SET elig.  : umur 34 ≥ 21 ✓, motor 2020 ≤ 8 th ✓     → PASSED
Step 5 RULE_SET afford.: dti 0.39 ≤ 0.45 ✓ (dekat ambang → flag) → TRIGGERED (flag saja)
Step 6 SCORECARD       : skor 684 → grade B, model MOTOR_SCORE_V1→ PASSED
Step 7 DECISION_TABLE  : baris "B, dti 0.35–0.45" match
                         → APPROVE_WITH_CONDITION, limit 12,5jt  → MATCHED
──────────────────────────────────────────────────────────────
HASIL : APPROVE_WITH_CONDITION · limit 12.500.000 · tenor 18 bln
ALASAN: REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT
TRACE : tersimpan lengkap (7 langkah di atas, versi semua konfigurasi)
WAKTU : ±130 ms
```

Bandingkan dengan **Mas Roni** (bab 1): step 5 langsung kena `dti 0.67 > 0.45 → REJECT (HIGH_DTI)` dan step LTV `2.0 > 0.85` menambah alasan — mesin berhenti lebih awal, jawaban keluar dalam sekejap, alasan tercatat dua-duanya.

Dan kasus abu-abu? Pemohon dengan DTI 0.43 (mepet) → decision table mengarahkan **MANUAL_REVIEW** → otomatis jadi tiket antrean underwriter, lengkap dengan trace-nya sebagai bahan pemeriksaan. Mesin tahu batas kemampuannya — itu fitur, bukan kelemahan.

## 4.10 Sifat-sifat yang membuatnya layak dipercaya

| Sifat | Artinya | Kenapa penting |
|---|---|---|
| **Deterministik** | Input sama + versi kebijakan sama = hasil selalu sama | Keadilan antar pemohon; bisa diuji; bisa direproduksi di pengadilan/audit |
| **Explainable** | Selalu ada reason code + trace | Regulator, nasabah, dan perbaikan kebijakan |
| **Versioned & immutable** | Konfigurasi aktif tak bisa diubah diam-diam; perubahan = versi baru | Rekonstruksi masa lalu; tanggung jawab jelas |
| **Side-effect-free simulation** | Kebijakan draft bisa diuji tanpa menyentuh produksi | Ubah kebijakan tanpa berjudi |
| **Terpisah dari kode** | Risk mengubah kebijakan tanpa deploy software | Kecepatan reaksi bisnis |

## 4.11 Rangkuman bab

Payload → **fitur** (kamus resmi) → **strategy** menjalankan **rule sets**, **scorecard**, **decision table** dalam rute yang disengaja → keluar **keputusan + alasan + syarat** → semuanya terekam di **trace**. Setiap komponen berversi, dan mesin yang sama melayani produksi maupun simulasi. Bab berikutnya: siapa memakai layar yang mana untuk mengurus semua ini.
