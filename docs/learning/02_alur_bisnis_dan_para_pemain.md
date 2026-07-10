# Bab 2 — Alur Bisnis Kredit dari Awal sampai Akhir, serta Para Pemainnya

## 2.1 Siklus hidup kredit terdiri dari tiga babak

> **Analogi penerbangan.** Originasi ibarat pemeriksaan sebelum terbang dan lepas landas. Servicing ibarat terbang jelajah yang terus dipantau. Collection ibarat prosedur darurat kalau ada masalah. Kecelakaan paling sering terjadi karena pemeriksaan pra-terbang yang buruk. Karena itu originasi menjadi babak yang paling dijaga, dan di sanalah decision engine hidup.

```
BABAK 1: ORIGINATION (originasi)          ← fokus OSCAR dan kurikulum ini
  Prospek → Aplikasi → Verifikasi data → PENILAIAN & KEPUTUSAN → Akad → Pencairan

BABAK 2: SERVICING (masa berjalan)
  Tagihan bulanan → Pembayaran → Administrasi kontrak → (top-up, pelunasan dipercepat)

BABAK 3: COLLECTION & RECOVERY (kalau macet)
  Telat bayar → Penagihan → Restrukturisasi → Penarikan jaminan → Lelang → Hapus buku
```

Ketiga babak ini biasanya ditangani sistem yang berbeda. Babak pertama ditangani LOS atau Loan Origination System, babak kedua ditangani LMS atau Loan Management System, dan babak ketiga ditangani Collection System. Ingat pembagian ini karena sebentar lagi menjadi penting.

## 2.2 Memperbesar babak pertama, yaitu perjalanan satu aplikasi

Mari ikuti Pak Budi dari bab 1 yang datang ke cabang untuk lease-back motornya.

1. **Pengajuan.** Petugas cabang memasukkan data ke LOS, mulai dari identitas, penghasilan, data motor, sampai foto dokumen.
2. **Verifikasi.** KTP dicek lewat layanan eKYC, kantor pemohon ditelepon, harga motor ditaksir oleh penilai, lalu riwayat kredit ditarik dari SLIK OJK, yang dulu dikenal sebagai BI checking. Dari SLIK terlihat riwayat semua kredit Pak Budi di semua lembaga, misalnya berapa pinjaman aktifnya, pernah menunggak berapa hari, dan bagaimana status kolektibilitasnya.
3. **Penilaian dan keputusan.** Inilah titik tempat decision engine bekerja. Semua data tadi dinilai terhadap kebijakan. Umurnya memenuhi syarat atau tidak, DTI-nya wajar atau tidak, LTV-nya aman atau tidak, riwayatnya bersih atau tidak, dan skornya berapa. Hasilnya berupa APPROVE, REJECT, APPROVE dengan syarat berupa penyesuaian limit atau tenor, atau MANUAL REVIEW, lengkap dengan alasan-alasannya.
4. **Manual review kalau diperlukan.** Kasus abu-abu diperiksa manusia, yaitu underwriter. Dia bisa menelepon ulang, meminta slip gaji tambahan, lalu memutus final.
5. **Akad dan pencairan.** Kontrak ditandatangani, uang cair, dan motor tercatat sebagai jaminan.

Kecepatan babak ini adalah senjata dagang. Pesaing yang bisa menjawab dalam lima belas menit akan merebut nasabah dari perusahaan yang menjawabnya tiga hari. Namun cepat tanpa akurat sama saja bunuh diri, seperti pelajaran bab 1. Yang dikejar adalah cepat, konsisten, sekaligus akurat, dan itulah janji otomasi keputusan.

## 2.3 Peta sistem, siapa mengerjakan apa

> **Analogi restoran.** LOS adalah pelayan yang menerima dan mencatat pesanan. Decision engine adalah dapur beserta buku resepnya, yang menentukan pesanan bisa dibuat atau tidak, dengan porsi dan harga berapa, sesuai resep yang disepakati. LMS adalah kasir dan program langganan yang mengurus tagihan bulanan, sedangkan collection adalah petugas penagihan. OSCAR hanyalah dapurnya. Dia tidak menggantikan pelayan maupun kasir. Dia menerima "pesanan" dari LOS lalu mengembalikan keputusan.

```
        ┌─────────┐  payload aplikasi   ┌──────────────────┐  keputusan+alasan  ┌─────────┐
Nasabah →│   LOS   │────────────────────▶│ DECISION ENGINE  │───────────────────▶│   LOS   │→ akad
        └─────────┘                      │     (OSCAR)      │                    └─────────┘
                                         │ rules·score·flow │
             data pendukung ────────────▶│ trace·audit      │
             (SLIK, eKYC, appraisal)     └──────────────────┘
```

## 2.4 Para pemain dan pekerjaannya

Berikut orang-orang yang nantinya menjadi pengguna decision engine. Mereka jugalah persona yang tercantum di PRD OSCAR.

| Peran | Tugas sehari-hari | Analogi | Pertanyaan khasnya |
|---|---|---|---|
| **Risk Policy Analyst** | Merumuskan dan menulis aturan kredit seperti ambang DTI, LTV maksimal, dan umur kendaraan, lalu menguji dampaknya sebelum aturan berlaku | Pembuat resep di dapur pusat, karena menu yang sama harus konsisten di semua cabang | "Kalau ambang DTI diturunkan dari 45% ke 40%, approval rate turun berapa?" |
| **Credit Risk Manager** | Menetapkan selera risiko, menyetujui perubahan kebijakan, memantau kesehatan portofolio, dan menarik rem atau gas | Kepala dapur, karena resep baru harus lewat persetujuannya | "Bad rate segmen dealer naik. Kebijakan mana yang harus diketatkan?" |
| **Underwriter / Credit Analyst** | Memutus kasus abu-abu yang dilempar mesin ke manual review lewat verifikasi tambahan dan pertimbangan manusia | Dokter spesialis yang menangani pasien rujukan di luar protokol standar | "Datanya bilang mepet. Setelah saya telepon kantornya, layak tidak ya?" |
| **Fraud Analyst** | Mencium pemalsuan seperti KTP palsu, slip gaji editan, sindikat, dan identitas yang tidak cocok | Satpam berpengalaman yang hafal gerak-gerik mencurigakan | "Kenapa lima belas aplikasi minggu ini latar belakang fotonya sama semua?" |
| **Compliance / Internal Audit** | Memastikan semuanya sesuai aturan OJK maupun internal, keputusan bisa dipertanggungjawabkan, dan perubahan kebijakan tercatat | Wasit sekaligus notulen. Bukan pemain, tetapi tanpa mereka pertandingan tidak sah | "Aplikasi ini ditolak enam bulan lalu. Tunjukkan alasannya dan aturan versi mana yang dipakai." |
| **Data Scientist** (Anda) | Membangun model skor risiko, memantau performa model, dan menganalisis portofolio | Ahli prakiraan cuaca. Dia membuat ramalan hujan, tetapi keputusan membawa payung tetap di tangan kebijakan | "Gini model saya turun. Populasinya bergeser atau modelnya sudah basi?" |
| **Engineering / IT** | Menjaga sistem, integrasi, ketersediaan, dan keamanan | Teknisi dapur | "Latency naik. Kenapa?" |

## 2.5 Konflik yang sehat antar peran

Supaya Anda paham dinamika rapatnya, kenali dulu beberapa tarik-menarik yang memang disengaja.

Pertama, sales melawan risk. Sales dibayar dari volume, sedangkan risk dinilai dari kerugian. Tarik-menarik gas dan rem ini memang dirancang begitu, bukan tanda organisasi tidak sehat.

Kedua, policy analyst melawan underwriter. Analis ingin semuanya terkodifikasi supaya konsisten, sementara underwriter tahu selalu ada kasus yang butuh pertimbangan manusia. Jalan tengahnya justru desain manual review yang baik. Mesin menangani mayoritas kasus, manusia menangani perkecualian, dan alasannya selalu tercatat lewat mekanisme override yang diaudit.

Ketiga, data scientist melawan policy. Model bilang orang ini 92% aman, tetapi kebijakan bilang umurnya 19 tahun dan itu di bawah batas kenyamanan legal perusahaan. Prinsipnya sederhana. Model memprediksi, kebijakan memutuskan. Model tidak pernah berjalan telanjang karena selalu dibungkus lapisan kebijakan. Bab 7 membahas ini khusus.

Keempat, semua orang melawan compliance. Setiap ajakan "ubah langsung saja di produksi, cepat kok" pasti ditolak compliance, karena satu perubahan yang tidak tercatat bisa menjadi temuan audit atau regulator. Inilah alasan tata kelola terasa "ribet" padahal wajib.

## 2.6 Contoh kasus, satu hari di tim risk multifinance

- **Pukul 08.30.** Dashboard pagi menunjukkan approval rate kemarin 41%, padahal biasanya 44%. Risk Manager minta dicek.
- **Pukul 09.15.** Policy Analyst menemukan penyebabnya, yaitu lonjakan aplikasi dari channel dealer wilayah X dengan DTI tinggi. Bukan sistem yang error, melainkan kualitas pemohonnya memang menurun.
- **Pukul 10.00.** Rapat. Sales protes karena approval turun, Risk Manager menahan. Kompromi tercapai, yaitu uang muka minimum diturunkan hanya untuk segmen berskor tinggi. Jaringnya diketatkan di satu sisi dan dilonggarkan di sisi lain.
- **Pukul 11.00.** Policy Analyst menyiapkan perubahan aturan dan mengujinya ke data historis sebelum diberlakukan.
- **Pukul 13.00.** Underwriter memproses tiga puluh kasus manual review. Empat di antaranya disetujui dengan limit diturunkan, dan alasannya tercatat.
- **Pukul 15.00.** Fraud Analyst melakukan eskalasi karena menemukan pola dokumen mencurigakan dari satu dealer. Dealer itu dibekukan sementara lewat aturan routing.
- **Pukul 16.30.** Compliance menarik laporan perubahan kebijakan minggu ini untuk arsip audit.

Sekarang pertanyaannya, dengan alat apa semua itu dikerjakan? Kalau jawabannya Excel, email, dan minta IT mengubah kode, di situlah letak rasa sakit yang melahirkan decision engine. Ceritanya berlanjut di bab 3.

## 2.7 Rangkuman bab

1. Siklus kredit terdiri dari originasi, servicing, dan collection. Decision engine hidup di titik keputusan pada babak originasi.
2. LOS menerima, engine memutuskan, dan LMS mengelola. OSCAR adalah dapurnya, bukan seluruh restoran.
3. Ada tujuh peran kunci dengan kepentingan berbeda yang memang dirancang untuk saling menyeimbangkan.
4. Semua peran itu adalah calon pengguna decision engine, dan masing-masing memakai layar yang berbeda seperti dibahas di bab 5.
