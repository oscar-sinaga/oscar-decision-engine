# Bab 6 — Konsep-Konsep Penting yang Selalu Muncul di Dunia Decision Engine

Delapan konsep yang akan terus Anda dengar di rapat risk. Masing-masing: apa, kenapa, analogi, contoh.

## 6.1 Versioning & Immutability — "UU bernomor, tak bisa disunting diam-diam"

**Apa:** setiap konfigurasi (rule, scorecard, decision table, strategy) hidup sebagai **versi**. Versi yang sudah AKTIF tidak bisa diedit — perubahan = membuat versi baru (draft → diajukan → disetujui → aktif; yang lama jadi RETIRED tapi tetap tersimpan). Setiap keputusan mencatat versi persis yang dipakainya.

**Kenapa:** (1) rekonstruksi — keputusan 2 tahun lalu harus bisa dijelaskan dengan aturan *saat itu*; (2) tanggung jawab — jelas siapa menerbitkan versi mana; (3) rollback — kembali ke versi lama itu mengaktifkan arsip, bukan menulis ulang.

**Analogi:** perundang-undangan. UU No. 5/2023 tidak "diedit" — ia diubah oleh UU No. 12/2025; keduanya tetap ada di lembaran negara, dan perkara tahun 2024 diadili dengan UU yang berlaku tahun 2024. Bandingkan dengan file Excel `kebijakan_final_v2_FIX_beneran.xlsx` yang di-overwrite orang tiap minggu.

**Contoh:** nasabah menggugat penolakan Maret. Compliance membuka trace → tercatat `DTI_MAX_STANDARD v3` (ambang 0.45). Meskipun sekarang sudah v5 (ambang 0.42), v3 tetap bisa dibuka utuh. Kasus selesai.

## 6.2 Simulation & Impact Analysis — "terowongan angin sebelum terbang"

**Apa:** menjalankan kebijakan **draft** terhadap data (satu kasus atau ribuan kasus historis) **tanpa efek apa pun ke produksi**, lalu membandingkan hasilnya dengan kebijakan aktif: approval rate berubah berapa, siapa yang tadinya approve jadi reject (dan sebaliknya), reason code apa yang naik.

**Kenapa:** kebijakan kredit itu keputusan bernilai miliaran dengan umpan balik 6–24 bulan. Satu-satunya cara "mencicipi masa depan" adalah menguji ke masa lalu.

**Analogi:** terowongan angin untuk desain pesawat, atau *test kitchen* sebelum menu masuk ke 500 cabang. Tidak ada maskapai yang menguji sayap baru dengan penumpang sungguhan.

**Contoh:** usulan DTI max 0.45→0.40. Simulasi batch atas 10.000 aplikasi historis: approval 44%→38% (−6 pp), reject naik terpusat di channel dealer, estimasi volume hilang Rp X, estimasi bad rate turun Y. Rapat memutuskan dengan angka, bukan firasat — dan hasil simulasi ini **wajib dilampirkan** saat minta persetujuan aktivasi (di OSCAR: enforced).

## 6.3 Cutoff & Swap Set — "menggeser passing grade"

**Apa:** *cutoff* = ambang skor keputusan (skor ≥ 640 approve, di bawahnya tidak). Menggeser cutoff = menggeser trade-off bab 1 secara paling langsung. *Swap set* = analisis **siapa yang bertukar nasib** ketika kebijakan berubah: *swap-in* (dulu ditolak, kini diterima) vs *swap-out* (dulu diterima, kini ditolak).

**Kenapa:** dua kebijakan bisa punya approval rate sama tapi *komposisi* berbeda. Yang menentukan untung-rugi bukan berapa banyak yang diterima, tapi **siapa**.

**Analogi:** passing grade ujian masuk. Menurunkan passing grade menambah jumlah mahasiswa — pertanyaannya: mahasiswa *tambahan* itu (swap-in) kualitasnya seperti apa? Menaikkan passing grade membuang sebagian pendaftar — apakah yang terbuang (swap-out) memang yang bermasalah, atau ikut terbuang yang baik?

**Contoh:** cutoff 640→620: +7 pp approval; kohor swap-in diperkirakan bad rate 6% (vs portofolio 3%). Layak? Hitung: margin tambahan vs expected loss tambahan — kalau margin per kontrak menutup EL kohor itu, ambil; kalau tidak, jangan — atau ambil *dengan syarat* (limit lebih kecil/DP lebih besar khusus band skor 620–639; ingat: keputusan tidak biner).

## 6.4 Reason Codes — "diagnosis tertulis, bukan 'pokoknya sakit'"

**Apa:** kode alasan baku (HIGH_DTI, LTV_ABOVE_THRESHOLD, BLACKLIST_HIT…) yang menyertai setiap reject/review/approve-bersyarat. Dikelola sebagai katalog (ada pesan internal & pesan versi nasabah).

**Kenapa:** (1) komunikasi ke nasabah & regulator; (2) **agregasi** — karena baku, bisa dihitung: "penyebab reject #1 bulan ini adalah HIGH_DTI (38%)" — teks bebas tidak bisa dihitung; (3) bahan analisis kebijakan: reason code = telemetri kebijakan.

**Analogi:** kode diagnosis di rumah sakit (ICD). Karena semua dokter memakai kode yang sama, manajemen bisa melihat "kasus DBD naik 3× bulan ini" — hal yang mustahil kalau tiap dokter menulis narasi bebas.

## 6.5 Maker-Checker — "dua kunci peluncuran"

**Apa:** pembuat perubahan (maker) **tidak boleh** menjadi penyetujunya (checker). Di OSCAR ini ditegakkan mesin: self-approval ditolak; aktivasi strategy juga menuntut bukti simulasi terlampir.

**Kenapa:** kebijakan kredit terlalu berdampak untuk satu pasang tangan — melindungi dari kesalahan, kelalaian, dan niat jahat sekaligus melindungi *si pembuat* ("bukan saya sendiri yang memutuskan").

**Analogi:** peluncuran rudal butuh dua kunci diputar dua orang; cek perusahaan butuh dua tanda tangan. Bukan karena tidak percaya orangnya — karena sistemnya tidak boleh bergantung pada kepercayaan.

## 6.6 Audit Trail — "CCTV di ruang arsip"

**Apa:** catatan **append-only** atas setiap tindakan yang mengubah keadaan: siapa, kapan, apa, dari-nilai-apa ke-nilai-apa, alasan, siapa penyetujunya. Terpisah dari log teknis (untuk engineer) dan dari trace (untuk menjelaskan satu keputusan) — tiga lapisan bukti dengan pembaca berbeda.

**Kenapa:** regulator & auditor tidak menilai niat baik; mereka menilai **bukti**. Append-only berarti koreksi pun dicatat sebagai peristiwa baru — sejarah tidak pernah ditulis ulang.

**Analogi:** buku besar akuntansi bertinta permanen: salah catat tidak di-tip-ex, tapi dijurnal-balik — dua-duanya tetap terbaca. Plus CCTV yang merekam siapa membuka lemari arsip (di OSCAR, membuka trace pun tercatat).

## 6.7 Manual Review & Override — "mesin yang tahu batas dirinya"

**Apa:** mesin sengaja didesain menyerah pada kasus abu-abu → masuk antrean manusia (ber-SLA, berprioritas). Keputusan manusia tercatat **berdampingan** dengan keputusan mesin; kalau berbeda (override), alasan wajib; membatalkan vonis fraud butuh wewenang lebih tinggi.

**Kenapa:** otomasi 100% itu naif — data tidak pernah lengkap, dunia tidak pernah rapi. Yang optimal: mesin menangani mayoritas kasus jelas (murah & konsisten), manusia menangani perkecualian (mahal tapi bijak). **Override rate** jadi metrik kesehatan: terlalu tinggi = kebijakan tidak realistis; nol sama sekali = underwriter cuma tukang stempel.

**Analogi:** gerbang tol — e-toll otomatis untuk 95% mobil, gardu petugas untuk kendaraan khusus. Dan setiap kali petugas membuka palang manual, alasannya dicatat.

## 6.8 Monitoring — "dashboard kokpit, bukan spion"

**Apa:** metrik keputusan yang dilihat harian: approval/reject/manual-review rate, volume, reason code teratas, ukuran & SLA antrean review, override rate, distribusi skor/grade, latency & error sistem — bisa dipotong per produk/channel/waktu.

**Kenapa:** NPL adalah **spion** — memberi tahu kecelakaan 6–12 bulan setelah terjadi. Metrik keputusan adalah **kaca depan**: pergeseran kualitas pemohon, kebijakan yang salah tembak, atau serangan fraud terlihat dalam hitungan hari lewat pergeseran approval rate & reason code, jauh sebelum jadi kerugian.

**Analogi:** kokpit pesawat. Pilot tidak menunggu jatuh untuk tahu ada masalah — altimeter, fuel, engine temp dibaca terus-menerus. Approval rate yang tiba-tiba berubah 5 pp tanpa perubahan kebijakan = lampu indikator menyala: *populasinya yang berubah* — selidiki.

## 6.9 Bagaimana semua konsep ini saling mengunci

```
   Ide kebijakan → [SIMULATION] uji dampak → [MAKER-CHECKER] disetujui orang lain
        → [VERSIONING] terbit sebagai versi baru, yang lama diarsip
        → produksi berjalan → [REASON CODES + TRACE] tiap keputusan terjelaskan
        → [MANUAL REVIEW + OVERRIDE] kasus abu-abu ke manusia, tercatat
        → [MONITORING] dampak dipantau harian → [AUDIT TRAIL] semua langkah terbukti
        → temuan monitoring memicu ide kebijakan berikutnya → (siklus berulang)
```

Satu konsep tanpa yang lain pincang: simulasi tanpa versioning tidak tahu membandingkan apa; monitoring tanpa reason code buta penyebab; maker-checker tanpa audit trail tidak bisa dibuktikan. Decision engine yang baik = **kedelapan konsep ini terpasang sebagai satu sistem** — dan itulah tepatnya daftar fitur OSCAR.
