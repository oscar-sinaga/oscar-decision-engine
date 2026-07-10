# Bab 8 — Studi Kasus Utuh: Membangun Kebijakan Lease-Back Motor dari Nol dengan OSCAR

Satu cerita panjang yang mengikat semua bab. Tokohnya tim fiktif di sebuah multifinance; semua angka ilustratif. Setiap langkah menyebut fitur OSCAR yang dipakai (miring dalam kurung).

## Babak 1 — Mandat bisnis

Direksi meluncurkan produk **lease-back motor**: pemilik motor mendapat dana tunai, motornya jadi jaminan, diangsur 12–36 bulan. Target: keputusan < 1 menit di cabang, bad rate 12-bulan ≤ 3,5%. Risk Manager **Bu Maya** memegang risk appetite; Policy Analyst **Bu Rani** merancang kebijakan; DS **Mas Adit** memegang model; Underwriter **Pak Dimas** menangani kasus abu-abu.

## Babak 2 — Merumuskan kebijakan (dari 5C ke aturan)

Bu Rani menerjemahkan risk appetite menjadi kebijakan terukur (bab 1 §5C):

| 5C | Kebijakan | Wujud rule |
|---|---|---|
| Character | Riwayat SLIK bersih | `bureau.max_dpd_12m > 30 → REJECT (BUREAU_BAD_HISTORY)`; blacklist → REJECT |
| Capacity | Cicilan wajar | `affordability.dti > 0.45 → REJECT (HIGH_DTI)`; 0.40–0.45 → flag review |
| Capital/Collateral | Jangan overfinance | `loan.ltv > 0.85 → MANUAL_REVIEW (LTV_ABOVE_THRESHOLD)`; motor > 8 th → review |
| Condition | Batas legal & produk | `applicant.age < 21 → REJECT`; produk hanya motor milik sendiri |
| Fraud | Identitas & dokumen | `identity_match = false ATAU document_match = false → FRAUD_INVESTIGATION` |

Ia memasukkan semua fitur yang dipakai ke **kamus resmi** (*feature catalog*), menulis rule di **rule builder**, mengelompokkannya (*rule sets*: ELIGIBILITY_MOTOR, FRAUD_BASIC, AFFORDABILITY_STANDARD), dan mendaftarkan **kode alasan** (*reason codes*) dengan pesan versi-nasabah yang sopan.

## Babak 3 — Model masuk (kolaborasi DS)

Mas Adit melatih model PD dari data produk serupa: skor 300–850, Gini 0.42. Bersama Bu Rani ia menetapkan band (*scorecard*, berversi): ≥720→A, 650–719→B, 580–649→C, 520–579→D, <520→E, dan mencatat modelnya (*model registry*: MOTOR_SCORE_V1). Kesepakatan cutoff awal: E auto-reject, D review, A–C lanjut ke matriks.

Lalu mereka menyusun **matriks keputusan akhir** (*decision table*, first-match):

| Grade | DTI | Keputusan |
|---|---|---|
| A | ≤0.45 | APPROVE |
| B | ≤0.40 | APPROVE |
| B | 0.40–0.45 | APPROVE_WITH_CONDITION (limit 85%) |
| C | ≤0.35 | MANUAL_REVIEW |
| * | * | REJECT |

## Babak 4 — Merangkai alur & uji sebelum terbang

Bu Rani menyusun **strategy** LEASEBACK_MOTOR v1 (*step-based; setelah Phase 3: kanvas alur bercabang*): validasi → kalkulasi (LTV, DTI) → fraud → eligibility → affordability → scorecard → decision table. Prinsip *fail fast*: pemeriksaan fatal & murah di depan.

Sebelum minta persetujuan, ia menguji (*simulation*):
- **Kasus tunggal**: payload Pak Budi (bab 1) → APPROVE_WITH_CONDITION ✓; payload Mas Roni → REJECT dengan HIGH_DTI + LTV ✓; payload fraud → FRAUD_INVESTIGATION ✓.
- **Batch** 8.000 aplikasi historis produk sejenis (*policy impact analysis*): proyeksi approval 43%, review 22%, reject 35%; penyebab reject teratas HIGH_DTI — masuk akal.

Ia mengajukan aktivasi **dengan lampiran simulasi** (di OSCAR wajib). Bu Maya — orang berbeda (*maker-checker*) — meninjau dan menyetujui (*approval + audit event*). **v1 AKTIF.** Semua langkah di atas otomatis tercatat (*audit trail*).

## Babak 5 — Hari-hari produksi

LOS cabang mengirim aplikasi ke `POST /v1/decisions`. Mayoritas terjawab detik-an; tiap keputusan membawa **reason codes** dan **trace** (*decision history & trace*). Kasus abu-abu mengalir ke antrean Pak Dimas (*manual review*, ber-SLA & prioritas): ia membaca keputusan-sistem + trace, menelepon kantor pemohon, meminta slip gaji (*document checklist*), lalu memutus — saat putusannya beda dari mesin, ia wajib menulis alasan (*override + reason, tercatat berdampingan*).

Bu Maya memantau harian (*dashboard*): approval 44%, review 21%, override rate 9% — sehat.

## Babak 6 — Insiden fraud (kecepatan-ubah diuji)

Minggu ke-7: fraud analyst mencium pola — belasan aplikasi dari dua dealer dengan slip gaji bernomor seri berurutan, penghasilan persis di atas ambang DTI. Respons (satu hari kerja, seperti bab 5 §5.7): rule fraud baru dibuat → diuji ke data seminggu (simulasi: menangkap 61 aplikasi) → disetujui Bu Maya → aktif. Sindikat tertahan hari itu juga. (*rules; simulation; maker-checker; audit*)

## Babak 7 — Tiga bulan kemudian: iterasi kebijakan berbasis data

Kohor awal mulai matang (*vintage*): band C ternyata 2× lebih buruk dari proyeksi; sementara itu banyak nasabah band A ditolak hanya karena LTV sedikit lewat. Rapat memutuskan dua perubahan sekaligus (jaring diketatkan di satu sisi, dilonggarkan di sisi lain — bab 1 §1.4):

1. Band C: dari MANUAL_REVIEW → REJECT kecuali DTI ≤ 0.30.
2. Band A dengan LTV 0.85–0.90: dari review → APPROVE_WITH_CONDITION (DP tambahan).

Bu Rani membuat **strategy v2 (draft)** — v1 tetap aktif — lalu **batch simulation membandingkan v2 vs v1**: approval −1,8 pp, komposisi jauh lebih sehat, *swap set* menunjukkan yang terbuang memang kohor buruk. Lampirkan, ajukan, disetujui, **v2 aktif; v1 RETIRED** (tetap tersimpan). Dua minggu kemudian ternyata dampak di satu wilayah terlalu dalam → Bu Maya… tidak panik: **rollback** ke v1 bisa dilakukan kapan pun dengan alasan tercatat — tapi setelah dicek, cukup penyesuaian kecil di v3. (*versioning; simulation compare; rollback; audit*)

## Babak 8 — Kunjungan audit (ujian sesungguhnya)

Auditor: *"Tunjukkan mengapa aplikasi #A-4412 ditolak 28 Maret, dan buktikan aturan saat itu sah."*
Compliance (menit, bukan minggu): buka decision → **trace** menunjukkan DTI 0.51 > 0.45 per `DTI_MAX_STANDARD v1` + skor 545 (grade D) per MOTOR_SCORE_V1 → **audit log** menunjukkan v1 diusulkan Bu Rani 12 Feb, disimulasikan, disetujui Bu Maya 14 Feb. Rantai bukti lengkap. (*trace; versioning; audit trail*)

## Epilog — apa yang membuat cerita ini mungkin

| Momen di cerita | Tanpa decision engine | Dengan OSCAR |
|---|---|---|
| Menerbitkan kebijakan baru | Proyek IT berbulan-bulan | Bu Rani sendiri, hari-an, tetap terkontrol |
| Tahu dampak sebelum berlaku | Tidak bisa — berjudi | Batch simulation |
| Merespons sindikat fraud | Minggu–bulan | Satu hari |
| Menjawab auditor | Arkeologi kode & email | Trace + audit log, hitungan menit |
| Kasus abu-abu | Semua manual ATAU semua auto | Mesin 80%, manusia 20% yang tepat |
| Salah kebijakan | Menetap sampai rilis berikutnya | Rollback beralasan, kapan pun |

Dan peran tiap orang tetap manusiawi: Bu Rani berpikir kebijakan (bukan menulis kode), Bu Maya mengendalikan (bukan menebak), Pak Dimas menilai kasus sulit (bukan menstempel ribuan berkas), Mas Adit memperbaiki model dari data trace yang jujur. **Mesinnya mengerjakan yang mesin kuasai; manusianya mengerjakan yang manusia kuasai — dan semuanya tercatat.**
