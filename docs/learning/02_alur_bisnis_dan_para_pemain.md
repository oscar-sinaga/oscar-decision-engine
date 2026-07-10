# Bab 2 — Alur Bisnis Kredit End-to-End & Para Pemainnya

## 2.1 Siklus hidup kredit: tiga babak

> **Analogi penerbangan:** originasi = pre-flight check & lepas landas; servicing = terbang jelajah (dipantau terus); collection = prosedur darurat kalau ada masalah. Kecelakaan paling sering terjadi karena pre-flight check yang buruk — makanya originasi adalah babak yang paling dijaga, dan di sanalah decision engine hidup.

```
BABAK 1: ORIGINATION (originasi)          ← fokus OSCAR & kurikulum ini
  Prospek → Aplikasi → Verifikasi data → PENILAIAN & KEPUTUSAN → Akad → Pencairan

BABAK 2: SERVICING (masa berjalan)
  Tagihan bulanan → Pembayaran → Administrasi kontrak → (top-up, pelunasan dipercepat)

BABAK 3: COLLECTION & RECOVERY (kalau macet)
  Telat bayar (DPD 1+) → Penagihan → Restrukturisasi → Penarikan jaminan → Lelang → Write-off
```

Tiga babak ini biasanya ditangani sistem berbeda: **LOS** (Loan Origination System) untuk babak 1, **LMS** (Loan Management System) untuk babak 2, **Collection System** untuk babak 3. Ingat pembagian ini — sebentar lagi penting.

## 2.2 Zoom in babak 1: perjalanan satu aplikasi

Pak Budi datang ke cabang mau lease-back motornya (kasus bab 1):

1. **Pengajuan** — CS/sales menginput data ke **LOS**: identitas, penghasilan, data motor, foto dokumen.
2. **Verifikasi** — cek KTP (eKYC/Dukcapil), survey/telepon kantor, taksiran harga motor (appraisal), tarik riwayat kredit dari **SLIK OJK** (dulu "BI checking") — riwayat semua kredit Pak Budi di semua lembaga: berapa pinjaman aktif, pernah nunggak berapa hari (DPD), status kolektibilitas 1–5.
3. **Penilaian & keputusan** ← *titik di mana decision engine bekerja.* Semua data tadi dinilai terhadap kebijakan: umur oke? DTI oke? LTV oke? riwayat bersih? skor berapa? → hasil: **APPROVE / REJECT / APPROVE dengan syarat (limit-tenor disesuaikan) / MANUAL REVIEW** + alasan-alasannya.
4. **Manual review (jika perlu)** — kasus abu-abu diperiksa manusia (underwriter): telepon ulang, minta slip gaji tambahan, putuskan final.
5. **Akad & pencairan** — kontrak ditandatangani, uang cair, motor tercatat sebagai jaminan (fidusia).

Kecepatan babak ini adalah senjata dagang: pesaing yang bisa jawab **15 menit** akan merebut nasabah dari yang jawabnya 3 hari. Tapi cepat *tanpa* akurat = bunuh diri (bab 1). **Cepat DAN konsisten DAN akurat** — itulah janji otomasi keputusan.

## 2.3 Peta sistem: siapa sistem apa

> **Analogi restoran:** **LOS = pelayan** yang menerima & mencatat pesanan. **Decision engine = dapur + buku resep**: menentukan pesanan bisa dibuat atau tidak, dengan porsi & harga berapa, berdasarkan resep yang disepakati. **LMS = kasir & program langganan** yang mengurus tagihan bulanan. **Collection = petugas penagihan**. OSCAR adalah **dapurnya saja** — ia tidak menggantikan pelayan atau kasir; ia menerima "pesanan" dari LOS dan mengembalikan keputusan.

```
        ┌─────────┐  payload aplikasi   ┌──────────────────┐  keputusan+alasan  ┌─────────┐
Nasabah →│   LOS   │────────────────────▶│ DECISION ENGINE  │───────────────────▶│   LOS   │→ akad
        └─────────┘                      │     (OSCAR)      │                    └─────────┘
                                         │ rules·score·flow │
             data pendukung ────────────▶│ trace·audit      │
             (SLIK, eKYC, appraisal)     └──────────────────┘
```

## 2.4 Para pemain: siapa mengerjakan apa

Inilah orang-orang yang nanti jadi **pengguna** decision engine (dan sudah jadi *persona* di PRD OSCAR):

| Peran | Tugas sehari-hari | Analogi | Pertanyaan khasnya |
|---|---|---|---|
| **Risk Policy Analyst** | Merumuskan & menulis aturan kredit: threshold DTI, LTV maksimal, umur kendaraan, segmen yang boleh/tidak. Menguji dampak sebelum aturan berlaku | **Pembuat resep** di dapur pusat — menu yang sama harus konsisten di semua cabang | "Kalau DTI max diturunkan 45%→40%, approval rate turun berapa?" |
| **Credit Risk Manager** | Menetapkan risk appetite, **menyetujui** perubahan kebijakan, memantau kesehatan portofolio, menarik rem/gas | **Kepala dapur (executive chef)** — resep baru harus lewat persetujuannya | "Bad rate segmen dealer naik — kebijakan mana yang harus diketatkan?" |
| **Underwriter / Credit Analyst** | Memutus **kasus abu-abu** yang dilempar mesin ke manual review: verifikasi tambahan, judgment call, approve dengan syarat | **Dokter spesialis** — pasien rujukan yang tidak bisa ditangani protokol standar | "Data bilang borderline; setelah saya telepon kantornya, layak nggak?" |
| **Fraud Analyst** | Mencium pemalsuan: KTP palsu, slip gaji editan, sindikat, identitas tidak cocok | **Satpam berpengalaman** yang hafal gerak-gerik mencurigakan | "Kenapa 15 aplikasi minggu ini fotonya latar belakangnya sama?" |
| **Compliance / Internal Audit** | Memastikan semua sesuai aturan (OJK, internal): keputusan bisa dipertanggungjawabkan, perubahan kebijakan tercatat | **Wasit + notulen** — bukan pemain, tapi tanpa mereka pertandingan tidak sah | "Aplikasi ini ditolak 6 bulan lalu — tunjukkan kenapa, aturan versi mana" |
| **Data Scientist** *(Anda)* | Membangun scorecard/model prediksi risiko, memantau performa model, analisis portofolio | **Ahli meteorologi** — membuat prakiraan hujan; keputusan bawa payung tetap di tangan kebijakan | "Model saya Gini-nya turun — populasi bergeser atau modelnya basi?" |
| **Engineering/IT** | Menjaga sistem: integrasi, uptime, keamanan | Teknisi dapur | "Latency P95 naik — kenapa?" |

## 2.5 Konflik sehat antar peran (supaya Anda paham dinamika rapatnya)

- **Sales vs Risk**: sales dibayar dari volume, risk dinilai dari kerugian → tarik-menarik gas/rem itu *by design*, bukan disfungsi.
- **Policy Analyst vs Underwriter**: analis ingin semua terkodifikasi (konsisten); underwriter tahu selalu ada kasus yang butuh judgment. Solusinya justru desain manual-review yang baik: mesin menangani mayoritas, manusia menangani perkecualian — **dengan alasan yang tercatat** (nanti: *override + reason*, diaudit).
- **DS vs Policy**: model bilang "orang ini 92% aman", kebijakan bilang "tapi umurnya 19, di bawah batas legal-comfort kami" → **model memprediksi, kebijakan memutuskan**. Model tidak pernah jalan telanjang; selalu dibungkus *policy overlay* (bab 7).
- **Semua vs Compliance**: setiap "cepat sedikit lah, langsung ubah di produksi" akan ditolak compliance — karena satu perubahan tak tercatat bisa jadi temuan audit/regulator. Ini alasan *governance* (bab 6) tampak "ribet" tapi wajib.

## 2.6 Contoh kasus: satu hari di tim risk multifinance

- **08:30** — Dashboard pagi: approval rate kemarin 41% (biasanya 44%). Risk Manager minta dicek.
- **09:15** — Policy Analyst menemukan: lonjakan aplikasi dari channel dealer wilayah X dengan DTI tinggi → bukan sistem error, memang kualitas pemohon menurun.
- **10:00** — Rapat: sales protes approval turun; Risk Manager menahan; kompromi: turunkan minimum DP untuk segmen skor tinggi saja (jaring diketatkan di satu sisi, dilonggarkan di sisi lain).
- **11:00** — Policy Analyst menyiapkan perubahan aturan + **menguji dampaknya di data historis** sebelum diberlakukan.
- **13:00** — Underwriter memproses 30 kasus manual review; 4 di antaranya di-approve dengan limit diturunkan, alasan tercatat.
- **15:00** — Fraud Analyst eskalasi: pola dokumen mencurigakan dari satu dealer → dealer dibekukan sementara lewat aturan routing.
- **16:30** — Compliance menarik laporan perubahan kebijakan minggu ini untuk arsip audit.

Sekarang pertanyaannya: **dengan alat apa semua itu dikerjakan?** Kalau jawabannya "Excel, email, dan minta IT ubah kode" — di situlah rasa sakit yang melahirkan decision engine. Lanjut ke bab 3.

## 2.7 Rangkuman bab

1. Siklus kredit = **originasi → servicing → collection**; decision engine hidup di titik keputusan originasi.
2. **LOS menerima, engine memutuskan, LMS mengelola** — OSCAR adalah "dapurnya", bukan seluruh restoran.
3. Ada tujuh peran kunci dengan kepentingan berbeda yang **memang didesain saling menyeimbangkan**.
4. Semua peran itu adalah calon pengguna decision engine — masing-masing lewat layar yang berbeda (bab 5).
