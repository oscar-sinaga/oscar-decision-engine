# Bab 8 — Studi Kasus Utuh: Membangun Kebijakan Lease-Back Motor dari Nol dengan OSCAR

Ini satu cerita panjang yang mengikat semua bab sebelumnya. Tokohnya tim fiktif di sebuah perusahaan multifinance, dan semua angkanya ilustratif. Setiap langkah menyebut fitur OSCAR yang sedang dipakai, ditulis miring di dalam kurung.

## Babak 1 — Mandat bisnis

Direksi meluncurkan produk lease-back motor. Lewat produk ini, pemilik motor mendapat dana tunai, motornya menjadi jaminan, lalu diangsur dua belas sampai tiga puluh enam bulan. Targetnya jelas, yaitu keputusan kurang dari satu menit di cabang, dengan bad rate dua belas bulan tidak lebih dari 3,5%.

Para tokohnya begini. Bu Maya sebagai Risk Manager memegang selera risiko. Bu Rani sebagai Policy Analyst merancang kebijakan. Mas Adit sebagai Data Scientist memegang model. Pak Dimas sebagai Underwriter menangani kasus abu-abu.

## Babak 2 — Merumuskan kebijakan, dari 5C menjadi aturan

Bu Rani menerjemahkan selera risiko menjadi kebijakan yang terukur, memakai kerangka 5C dari bab 1.

| 5C | Kebijakannya | Wujud aturannya |
|---|---|---|
| Character | Riwayat SLIK harus bersih | `bureau.max_dpd_12m > 30 → REJECT (BUREAU_BAD_HISTORY)`, dan daftar hitam langsung REJECT |
| Capacity | Cicilan harus wajar | `affordability.dti > 0.45 → REJECT (HIGH_DTI)`, sedangkan 0.40 sampai 0.45 cukup ditandai untuk review |
| Capital dan Collateral | Jangan membiayai melebihi nilai jaminan | `loan.ltv > 0.85 → MANUAL_REVIEW (LTV_ABOVE_THRESHOLD)`, dan motor berumur lebih dari delapan tahun masuk review |
| Condition | Batas legal dan batas produk | `applicant.age < 21 → REJECT`, dan produk hanya untuk motor milik sendiri |
| Fraud | Identitas dan dokumen harus cocok | `identity_match = false ATAU document_match = false → FRAUD_INVESTIGATION` |

Semua fitur yang dipakai dia daftarkan ke kamus resmi (*feature catalog*). Aturan-aturannya dia tulis di rule builder, lalu dikelompokkan menjadi rule set ELIGIBILITY_MOTOR, FRAUD_BASIC, dan AFFORDABILITY_STANDARD (*rules dan rule sets*). Kode-kode alasan juga dia daftarkan, lengkap dengan pesan versi nasabah yang sopan (*reason codes*).

## Babak 3 — Model masuk lewat kolaborasi dengan data scientist

Mas Adit melatih model PD dari data produk serupa. Hasilnya skor pada rentang 300 sampai 850 dengan Gini 0.42. Bersama Bu Rani dia menetapkan band skor (*scorecard*, berversi). Skor 720 ke atas menjadi grade A, 650 sampai 719 grade B, 580 sampai 649 grade C, 520 sampai 579 grade D, dan di bawah 520 grade E. Modelnya dicatat sebagai MOTOR_SCORE_V1 (*model registry*). Kesepakatan cutoff awalnya begini. Grade E ditolak otomatis, grade D masuk review, dan grade A sampai C lanjut ke matriks keputusan.

Mereka lalu menyusun matriks keputusan akhir (*decision table*, evaluasi cocok-pertama-menang).

| Grade | DTI | Keputusan |
|---|---|---|
| A | ≤ 0.45 | APPROVE |
| B | ≤ 0.40 | APPROVE |
| B | 0.40–0.45 | APPROVE_WITH_CONDITION dengan limit 85% |
| C | ≤ 0.35 | MANUAL_REVIEW |
| * | * | REJECT |

## Babak 4 — Merangkai alur dan menguji sebelum terbang

Bu Rani menyusun strategy LEASEBACK_MOTOR versi 1 (*strategy*, berbasis langkah, dan setelah Phase 3 bisa berupa kanvas alur bercabang). Urutannya validasi, lalu kalkulasi LTV dan DTI, lalu fraud, eligibility, affordability, scorecard, dan terakhir decision table. Prinsipnya fail fast, artinya pemeriksaan yang fatal dan murah ditaruh di depan.

Sebelum meminta persetujuan, dia menguji dulu (*simulation*).

- Uji kasus tunggal. Payload Pak Budi dari bab 1 menghasilkan APPROVE_WITH_CONDITION, payload Mas Roni menghasilkan REJECT dengan alasan HIGH_DTI plus LTV, dan payload fraud menghasilkan FRAUD_INVESTIGATION. Semuanya sesuai harapan.
- Uji batch terhadap delapan ribu aplikasi historis produk sejenis (*policy impact analysis*). Proyeksinya approval 43%, review 22%, reject 35%, dengan penyebab penolakan teratas HIGH_DTI. Masuk akal.

Dia lalu mengajukan aktivasi dengan lampiran hasil simulasi, yang di OSCAR memang wajib. Bu Maya, orang yang berbeda sesuai prinsip maker-checker, meninjau lalu menyetujui (*approval dan audit event*). Versi 1 pun aktif, dan seluruh langkah tadi otomatis tercatat (*audit trail*).

## Babak 5 — Hari-hari produksi

LOS di cabang mengirim aplikasi ke `POST /v1/decisions`. Mayoritas terjawab dalam hitungan detik, dan setiap keputusan membawa reason codes serta trace (*decision history dan trace*). Kasus abu-abu mengalir ke antrean Pak Dimas (*manual review*, dengan SLA dan prioritas). Dia membaca keputusan sistem beserta trace-nya, menelepon kantor pemohon, meminta slip gaji lewat daftar dokumen (*document checklist*), lalu memutus. Ketika putusannya berbeda dari mesin, dia wajib menulis alasan, dan keputusannya tersimpan berdampingan dengan keputusan sistem (*override dengan alasan, tercatat*).

Sementara itu Bu Maya memantau harian lewat dashboard. Approval 44%, review 21%, override rate 9%. Semuanya sehat.

## Babak 6 — Insiden fraud, ujian bagi kecepatan mengubah aturan

Minggu ketujuh, fraud analyst mencium pola aneh. Belasan aplikasi dari dua dealer memakai slip gaji bernomor seri berurutan, dengan penghasilan yang persis sedikit di atas ambang DTI. Responsnya hanya butuh satu hari kerja, seperti cerita di bab 5. Rule fraud baru dibuat, diuji ke data seminggu terakhir lewat simulasi dan berhasil menangkap 61 aplikasi, lalu disetujui Bu Maya dan aktif. Sindikat itu tertahan hari itu juga (*rules, simulation, maker-checker, audit*).

## Babak 7 — Tiga bulan kemudian, iterasi kebijakan berbasis data

Kohor awal mulai matang (*vintage*). Ternyata band C berperilaku dua kali lebih buruk dari proyeksi. Di sisi lain, banyak nasabah band A ditolak hanya karena LTV-nya sedikit terlewat. Rapat memutuskan dua perubahan sekaligus, sesuai prinsip bab 1 bahwa jaring boleh diketatkan di satu sisi sambil dilonggarkan di sisi lain.

1. Band C yang tadinya MANUAL_REVIEW menjadi REJECT, kecuali DTI-nya 0.30 ke bawah.
2. Band A dengan LTV 0.85 sampai 0.90, yang tadinya review, menjadi APPROVE_WITH_CONDITION dengan tambahan uang muka.

Bu Rani membuat strategy versi 2 sebagai draft, sementara versi 1 tetap aktif. Batch simulation membandingkan keduanya. Approval hanya turun 1,8 poin, komposisinya jauh lebih sehat, dan analisis swap set menunjukkan yang terbuang memang kohor yang buruk. Hasil simulasi dilampirkan, usulan diajukan, disetujui, lalu versi 2 aktif dan versi 1 pensiun namun tetap tersimpan (*versioning, simulation compare*).

Dua minggu kemudian dampak di satu wilayah ternyata terlalu dalam. Bu Maya tidak panik, karena rollback ke versi 1 bisa dilakukan kapan saja dengan alasan tercatat. Setelah dicek lebih teliti, ternyata cukup penyesuaian kecil lewat versi 3 (*rollback tersedia, audit lengkap*).

## Babak 8 — Kunjungan audit, ujian yang sesungguhnya

Auditor datang dengan permintaan klasik. "Tunjukkan mengapa aplikasi A-4412 ditolak tanggal 28 Maret, dan buktikan aturan yang dipakai saat itu sah."

Compliance menjawabnya dalam hitungan menit, bukan minggu. Keputusan dicari, trace dibuka, dan terlihat DTI 0.51 melebihi ambang 0.45 menurut `DTI_MAX_STANDARD v1`, ditambah skor 545 alias grade D menurut MOTOR_SCORE_V1. Audit log kemudian menunjukkan versi 1 diusulkan Bu Rani tanggal 12 Februari, disimulasikan, lalu disetujui Bu Maya tanggal 14 Februari. Rantai buktinya lengkap (*trace, versioning, audit trail*).

## Epilog — apa yang membuat cerita ini mungkin

| Momen dalam cerita | Tanpa decision engine | Dengan OSCAR |
|---|---|---|
| Menerbitkan kebijakan baru | Proyek IT berbulan-bulan | Dikerjakan Bu Rani sendiri dalam hitungan hari, tetap terkontrol |
| Mengetahui dampak sebelum berlaku | Tidak bisa, jadi berjudi | Batch simulation |
| Merespons sindikat fraud | Hitungan minggu sampai bulan | Satu hari |
| Menjawab auditor | Arkeologi kode dan email | Trace plus audit log, hitungan menit |
| Menangani kasus abu-abu | Semuanya manual, atau semuanya otomatis | Mesin menangani 80%, manusia menangani 20% yang tepat |
| Salah kebijakan | Bertahan sampai rilis software berikutnya | Rollback beralasan, kapan saja |

Yang juga penting, peran setiap orang tetap manusiawi. Bu Rani berpikir soal kebijakan dan bukan menulis kode. Bu Maya mengendalikan dan bukan menebak-nebak. Pak Dimas menilai kasus sulit dan bukan menstempel ribuan berkas. Mas Adit memperbaiki model dari data trace yang jujur. Mesin mengerjakan yang dikuasai mesin, manusia mengerjakan yang dikuasai manusia, dan semuanya tercatat.
