# Bab 3 — Apa Itu Decision Engine & Kenapa Dunia Finance Membutuhkannya

## 3.1 Definisi satu kalimat

**Decision engine adalah perangkat lunak yang menerima data satu kasus (mis. aplikasi kredit), menjalankannya melewati kebijakan yang tersimpan sebagai konfigurasi (rules, scorecard, decision table, alur), lalu mengembalikan keputusan beserta alasannya — secara otomatis, konsisten, cepat, dan bisa diaudit.**

Kata kuncinya: kebijakan disimpan sebagai **konfigurasi** (data yang bisa diubah orang bisnis), bukan **kode program** (yang hanya bisa diubah programmer). Kalau di istilah industri, keluarga perangkat lunak ini disebut BRMS (Business Rules Management System) / credit decisioning platform — contoh komersial: FICO Blaze, Experian PowerCurve, SAS, Provenir, dan iDecision yang jadi benchmark OSCAR.

> **Analogi inti — dapur & buku resep:** restoran cabang mana pun bisa masak menu yang sama karena ada **buku resep standar**. Decision engine = dapur yang *membaca resep dari buku* setiap kali memasak. Mau ubah rasa? **Ubah bukunya** (terbitkan resep edisi baru, dengan persetujuan kepala dapur) — bukan membongkar dapurnya. Sistem lama ibarat dapur yang resepnya *dilas ke kompor*: tiap ganti resep harus panggil tukang las (programmer), dan tidak ada yang tahu persis resep edisi berapa yang dipakai kemarin.

## 3.2 Latar belakang: tiga era pengambilan keputusan kredit

**Era 1 — Manual/judgmental (bank tempo dulu).** Setiap aplikasi dinilai analis manusia satu per satu. Masalah: lambat (hari–minggu), mahal, dan **tidak konsisten** — pemohon yang sama bisa diterima analis A dan ditolak analis B; rawan bias dan "kedekatan". Skala? Mustahil menilai 5.000 aplikasi/hari.

**Era 2 — Scorecard & aturan yang di-hardcode (mulai 1960-an: FICO; masif sejak 1990-an).** Statistik masuk: karakteristik pemohon diberi poin (scorecard), keputusan berdasarkan ambang skor + aturan. Awalnya di kertas, lalu ditanam ke sistem — **di dalam kode program core system**. Konsisten dan cepat, TAPI muncul rasa sakit baru yang mungkin familiar buat Anda:

- Risk team: "Tolong ubah DTI max dari 45% ke 40%." → antre backlog IT 3 bulan; padahal kondisi pasar berubah minggu ini.
- "Kenapa aplikasi ini ditolak?" → "Hmm, harus baca kodenya dulu…"
- "Aturan yang berlaku bulan Maret tahun lalu apa?" → tidak ada yang tahu pasti (kode sudah berubah berkali-kali, tanpa arsip versi kebijakan).
- Uji dampak sebelum berlaku? Tidak bisa — ubah di produksi, berdoa.

**Era 3 — Decision engine (kebijakan = konfigurasi).** Kebijakan dipindah keluar dari kode ke dalam mesin khusus: risk team **mengubah sendiri** aturannya lewat antarmuka, setiap versi **terarsip**, setiap keputusan **meninggalkan jejak** (trace), perubahan bisa **disimulasikan** sebelum berlaku dan harus **disetujui** pejabat berwenang. IT tetap penting — menjaga mesinnya — tapi tidak lagi jadi bottleneck isi kebijakan.

> **Analogi hukum:** era 2 itu seperti negara yang undang-undangnya tertanam di kepala hakim — mengubah UU = mengganti hakim. Era 3 = UU tertulis, bernomor & bertahun (versi!), diubah lewat prosedur legislasi (governance), dan setiap vonis mengutip pasal yang dipakai (reason code + trace).

## 3.3 Masalah-masalah spesifik yang diselesaikan

(Ini persis daftar "problem statement" di PRD OSCAR — sekarang Anda tahu konteks bisnisnya.)

| Masalah tanpa decision engine | Akibat bisnis | Jawaban decision engine |
|---|---|---|
| Policy tertanam di kode, ubah = proyek IT | Reaksi terhadap pasar/fraud lambat berbulan-bulan | Kebijakan = konfigurasi; risk team ubah sendiri, aktif dalam hitungan jam (dengan approval) |
| Keputusan tidak bisa dijelaskan | Nasabah komplain, regulator bertanya, internal tidak bisa belajar | **Reason codes** + **decision trace** per keputusan |
| Versi aturan tidak terlacak | Audit gagal merekonstruksi keputusan lama; sengketa hukum lemah | **Versioning immutable**: setiap keputusan mencatat versi aturan/model yang persis dipakai |
| Tidak ada uji dampak | Kebijakan baru = judi; kesalahan ketahuan setelah rugi | **Simulation / impact analysis** sebelum aktivasi |
| Perubahan tanpa kontrol | Satu orang iseng/khilaf bisa mengubah nasib portofolio | **Maker-checker**: pembuat ≠ penyetuju; semua tercatat di audit log |
| Override manual tak terdokumentasi | "Katanya dulu di-approve pak X" — tidak bisa dibuktikan | Override wajib beralasan, tercatat siapa-kapan-kenapa |
| Tidak ada monitoring keputusan | Pergeseran kualitas ketahuan setelah NPL meledak (telat 6–12 bulan) | Metrik real-time: approval rate, reason code teratas, override rate |
| Kecepatan manusia | Nasabah lari ke pesaing yang jawab 15 menit | Keputusan otomatis dalam hitungan detik untuk mayoritas kasus |

## 3.4 Kenapa ini *sangat* penting justru di finance (dibanding industri lain)

1. **Keputusannya bernilai uang langsung dan berulang ribuan kali per hari.** Salah 1% konsisten = miliaran rupiah (bab 1). Konsistensi bukan kemewahan, tapi kebutuhan aritmetika.
2. **Diregulasi ketat.** OJK (dan regulator mana pun) menuntut lembaga keuangan mampu menjelaskan & mempertanggungjawabkan keputusan kreditnya, punya manajemen risiko dan jejak audit. "Sistemnya begitu, kami tidak tahu kenapa" bukan jawaban yang diterima.
3. **Adversarial.** Ada pihak yang aktif mencoba menipu (fraud). Kebijakan harus bisa berubah **cepat** ketika pola fraud baru muncul — kecepatan-ubah adalah senjata pertahanan.
4. **Keputusan hari ini, akibatnya baru terlihat 6–24 bulan lagi** (kredit macet butuh waktu untuk "matang"). Karena umpan balik lambat, disiplin *mencatat apa yang diputuskan dengan aturan versi apa* jadi satu-satunya cara belajar dari masa lalu — dan bahan baku model Anda sebagai DS.
5. **Fairness/etika.** Keputusan menyangkut akses ekonomi orang. Aturan eksplisit + alasan tercatat = bisa diperiksa apakah adil; keputusan "perasaan analis" tidak bisa.

## 3.5 Apa yang decision engine BUKAN

- **Bukan LOS** — ia tidak mengurus form pengajuan, dokumen, alur cabang. (Ia dipanggil *oleh* LOS.)
- **Bukan core system/LMS** — tidak mengurus pembukuan cicilan.
- **Bukan model machine learning** — model adalah *salah satu bahan* di dalamnya (skor); engine adalah *kerangka kebijakan* yang memakai skor itu bersama aturan lain. (Bab 7 membahas hubungan ini khusus untuk Anda.)
- **Bukan robot yang menggantikan semua manusia** — justru ia *merutekan* kasus abu-abu ke manusia (manual review) sambil menangani mayoritas kasus jelas secara otomatis.

> **Analogi bandara:** e-gate imigrasi memproses 80% penumpang dalam 10 detik; sisanya yang "tidak biasa" diarahkan ke konter petugas. Petugasnya jadi lebih sedikit tapi lebih fokus pada kasus yang benar-benar butuh keahlian. Decision engine = e-gate untuk aplikasi kredit; underwriter = petugas konternya.

## 3.6 Nilai bisnisnya dalam satu tabel (jawaban untuk "membantu di sisi apa?")

| Sisi | Bantuan konkret |
|---|---|
| **Pendapatan** | Keputusan detik-an → conversion naik; kebijakan bisa dibuat presisi per segmen → approve lebih banyak orang baik yang dulunya tertolak aturan kasar |
| **Kerugian** | Aturan konsisten + cepat-ubah saat fraud/pemburukan → bad rate terkendali |
| **Biaya operasi** | Mayoritas keputusan otomatis → underwriter fokus ke kasus abu-abu saja |
| **Kepatuhan** | Trace + audit log + versioning → siap diperiksa regulator/audit kapan pun |
| **Kecepatan belajar organisasi** | Simulasi & data keputusan terstruktur → iterasi kebijakan berbasis bukti, bukan feeling |

## 3.7 Rangkuman bab

1. Decision engine = mesin yang menjalankan **kebijakan-sebagai-konfigurasi** untuk memutus kasus secara otomatis + akuntabel.
2. Ia lahir dari rasa sakit era hardcode: lambat ubah, tak terjelaskan, tak berversi, tak teruji, tak terkontrol.
3. Di finance ia vital karena skala uang, regulasi, fraud, umpan balik lambat, dan tuntutan keadilan.
4. Ia melengkapi — bukan menggantikan — LOS, LMS, model ML, dan manusia.

Bab berikutnya membuka kap mesinnya: apa yang sebenarnya terjadi di dalam ketika satu aplikasi masuk.
