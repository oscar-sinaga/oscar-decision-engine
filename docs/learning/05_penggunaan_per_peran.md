# Bab 5 — Sehari-hari Memakai Decision Engine, Peran demi Peran

Bab 2 memperkenalkan orangnya; bab 4 memperkenalkan mesinnya. Sekarang: **bagaimana tiap orang memakai mesin itu** — dipetakan langsung ke layar-layar OSCAR yang sudah ada.

## 5.1 Risk Policy Analyst — "penulis resep"

**Misi:** menerjemahkan risk appetite menjadi aturan yang presisi, dan tidak pernah menerbitkan aturan tanpa tahu dampaknya.

Alur kerja khas (layar: *Rules, Feature Catalog, Simulations, Strategies*):

1. **Menerima mandat** dari Risk Manager: "kualitas segmen dealer memburuk, ketatkan."
2. **Menulis/merevisi rule** di rule builder: buka rule `DTI_MAX_STANDARD` → buat **versi draft baru** (versi aktif tidak bisa diedit — immutable) → ubah ambang 0.45 → 0.42.
3. **Menguji satu kasus** (dry-run): masukkan contoh pemohon, lihat cabang mana yang kena.
4. **Simulasi dampak populasi** (*policy impact analysis*): jalankan kebijakan draft terhadap ribuan aplikasi historis → "approval rate turun 44% → 39%, reject naik terutama di channel dealer, reason code HIGH_DTI naik 3×". Inilah bedanya *mengira* dan *tahu*.
5. **Mengajukan approval** dengan lampiran hasil simulasi (di OSCAR: simulasi **wajib** dilampirkan sebelum strategy bisa diaktifkan).
6. Setelah aktif: **memantau** reason code teratas & approval rate di dashboard — apakah dampak nyata sesuai simulasi?

> **Analogi:** koki R&D di restoran waralaba. Resep baru dicoba di *test kitchen* (simulasi), dicicip panel (review), disetujui executive chef (approval), baru dicetak ke buku resep edisi baru (aktivasi berversi) — tidak pernah langsung ganti resep di dapur cabang saat jam makan siang.

## 5.2 Credit Risk Manager — "kepala dapur & pemegang rem"

**Misi:** menjaga portofolio pada risk appetite; menjadi *checker* atas semua perubahan; menarik rem darurat saat perlu.

Alur kerja khas (layar: *Dashboard, Approvals, Strategies, Audit Log*):

- **Pagi:** dashboard — approval/reject/manual-review rate, tren volume, reason code teratas, ukuran antrean review. Anomali = pertanyaan.
- **Approval queue:** meninjau usulan analis. Karena **maker-checker**, ia tidak bisa menyetujui usulan buatannya sendiri — dan sistem menolak aktivasi tanpa lampiran simulasi. Ia membaca ringkasan dampak, lalu approve/reject **dengan alasan tercatat**.
- **Krisis:** kebijakan baru ternyata memukul approval terlalu dalam → **rollback**: mengaktifkan kembali versi strategy sebelumnya (bukan menghapus yang sekarang — sejarah tak pernah dihapus), wajib menulis alasan, semua terekam.
- **Override monitoring:** kalau underwriter terlalu sering membatalkan keputusan mesin (override rate tinggi), itu sinyal kebijakan tidak realistis → agenda rapat.

> **Analogi:** kapten kapal. Tidak memegang kemudi tiap menit (itu mesin & kru), tapi menentukan arah, menyetujui perubahan rute, membaca instrumen, dan berwenang memutar balik. Setiap perintahnya masuk **log pelayaran** (audit log).

## 5.3 Underwriter / Credit Analyst — "dokter spesialis kasus abu-abu"

**Misi:** memutus kasus yang mesin sendiri bilang "saya tidak yakin", secara cepat, adil, terdokumentasi.

Alur kerja khas (layar: *Manual Review queue & case detail*):

1. **Antrean** sudah terprioritaskan (fraud = HIGH, ber-SLA — kasus mendekati tenggat menyala).
2. Buka kasus → semua bahan tersaji: ringkasan pemohon/pinjaman/kendaraan (data sensitif tersamar), **keputusan sistem + alasannya**, dan **link trace** — ia tahu persis *kenapa* mesin ragu (mis. "DTI 0.43, mepet ambang 0.45").
3. **Investigasi manusia:** telepon HRD kantor pemohon, minta dokumen tambahan (checklist dokumen: slip gaji, rekening 3 bulan), tulis catatan di kasus.
4. **Putusan:** approve / reject (wajib pilih reason code) / **approve dengan syarat** (limit atau tenor diturunkan) / eskalasi ke senior. Kalau putusannya **berbeda dari mesin → wajib menulis alasan override**; membatalkan vonis FRAUD_INVESTIGATION butuh izin khusus level supervisor.
5. Keputusan analis tersimpan **berdampingan** dengan keputusan sistem (bukan menimpanya) — "Decision by System" vs "Decision by Analyst".

> **Analogi:** dokter jaga IGD dengan sistem triase. Mesin triase sudah memilah & melampirkan hasil lab (trace); dokter fokus pada pasien kuning/merah, dan setiap tindakan di luar protokol harus ditulis alasannya di rekam medis.

## 5.4 Fraud Analyst — "satpam berpengalaman"

**Misi:** mendeteksi & memutus pola penipuan secepat mungkin.

- Memantau kasus berlabel `FRAUD_INVESTIGATION` dan reason code fraud (APPLICATION_DATA_MISMATCH, BLACKLIST_HIT).
- Saat pola baru ditemukan (mis. sindikat dokumen dari satu dealer): mengusulkan **rule fraud baru** atau pembaruan daftar — dan karena kebijakan = konfigurasi, pertahanan baru bisa aktif **hari itu juga** (lewat jalur approval), bukan menunggu rilis software kuartal depan.
- Kecepatan-ubah inilah senjata utamanya: fraudster berpindah pola dalam hitungan hari.

## 5.5 Compliance & Internal Audit — "wasit & notulen"

**Misi:** membuktikan bahwa semua keputusan dan semua perubahan kebijakan sah, tercatat, dan dapat direkonstruksi.

- **Rekonstruksi keputusan:** regulator/nasabah menanyakan keputusan 8 bulan lalu → cari decision → buka **trace** → tampak input, aturan versi berapa, alasan → tutup kasus dalam menit.
- **Audit perubahan:** *Audit Log* menjawab "siapa mengubah apa, kapan, kenapa, dari nilai apa ke nilai apa, disetujui siapa" — untuk rule, strategy, override, role. Append-only: tak seorang pun (termasuk admin) bisa mengedit sejarah.
- **Sampling override:** menarik daftar override underwriter beserta alasannya — mencari pola penyimpangan.
- Bahkan *melihat trace* pun tercatat (akses ke data sensitif diaudit).

> **Analogi:** juru sita arsip dengan CCTV yang merekam ruangan arsip itu sendiri. Bukan hanya dokumennya lengkap — siapa membuka laci mana pun terekam.

## 5.6 Data Scientist — Anda (versi ringkas; bab 7 khusus untuk ini)

- **Memasok otak statistik:** membangun model skor; engine mengonsumsinya lewat *scorecard* & mencatat versinya (*model registry*).
- **Mengonsumsi jejaknya:** decision trace + outcome pembayaran = dataset training & validasi paling bersih yang pernah Anda punya (fitur *persis seperti saat keputusan dibuat* — bukan rekonstruksi).
- **Menguji ide kebijakan:** batch simulation = backtest kebijakan; Anda bisa menjawab "kalau cutoff digeser, siapa yang tertukar nasib?" dengan data, bukan opini.
- **Memantau:** distribusi skor & approval per grade dari dashboard — deteksi drift lebih dini daripada menunggu NPL.

## 5.7 Satu insiden, semua peran bergerak (studi kasus lintas-peran)

**Senin 09:00** — Dashboard: manual review rate melonjak 27% → 41% sejak Jumat. *(Risk Manager)*
**09:30** — Telusur reason code: DTI_NEAR_THRESHOLD meledak; dari trace terlihat lonjakan aplikasi berpenghasilan tepat di sekitar ambang dari channel dealer tertentu. *(Policy Analyst)*
**10:15** — Sampling kasus: slip gaji dari 3 dealer bernomor seri berurutan — indikasi dokumen "dipabrikkan" agar lolos ambang. *(Fraud Analyst + Underwriter)*
**11:00** — Rule fraud baru dibuat (draft): kombinasi channel + pola penghasilan → FRAUD_INVESTIGATION. Diuji ke data seminggu terakhir lewat simulasi: menangkap 61 aplikasi, false-positive diperkirakan rendah. *(Policy Analyst)*
**13:00** — Usulan disetujui & diaktifkan (maker-checker, alasan tercatat). *(Risk Manager)*
**13:05** — Aturan hidup di produksi. Aplikasi sindikat berikutnya langsung tertahan.
**Selasa** — Compliance menarik jejak insiden: siapa menemukan, aturan apa yang berubah, disetujui siapa, dampaknya apa — satu narasi utuh dari audit log + trace, tanpa satu email pun dicari-cari. *(Compliance)*

Tanpa decision engine, cerita yang sama memakan **berminggu-minggu** (ubah kode, deploy, tanpa simulasi, tanpa jejak) — dan sindikatnya sudah pindah kota.

## 5.8 Rangkuman bab

| Peran | Layar utama | Kata kerja utamanya |
|---|---|---|
| Policy Analyst | Rules, Simulations, Strategies | menulis, menguji, mengusulkan |
| Risk Manager | Dashboard, Approvals, Audit | memantau, menyetujui, me-rollback |
| Underwriter | Manual Review | menginvestigasi, memutus, meng-override (beralasan) |
| Fraud Analyst | Cases + Rules fraud | mendeteksi, merespons cepat |
| Compliance | Audit Log, Trace | merekonstruksi, membuktikan |
| Data Scientist | Model registry, Simulations, Dashboard | memasok skor, mem-backtest, memantau drift |
