# Bab 5 — Keseharian Memakai Decision Engine, Peran demi Peran

Bab 2 sudah memperkenalkan orang-orangnya dan bab 4 sudah memperkenalkan mesinnya. Sekarang kita lihat bagaimana tiap orang memakai mesin itu sehari-hari, dipetakan langsung ke layar-layar OSCAR yang sudah ada.

## 5.1 Risk Policy Analyst, sang penulis resep

Misinya adalah menerjemahkan selera risiko perusahaan menjadi aturan yang presisi, dan tidak pernah menerbitkan aturan tanpa tahu dampaknya lebih dulu.

Beginilah alur kerjanya yang khas. Layar yang dipakai antara lain Rules, Feature Catalog, Simulations, dan Strategies.

1. Dia menerima mandat dari Risk Manager, misalnya "kualitas segmen dealer memburuk, tolong diketatkan".
2. Dia menulis atau merevisi rule di rule builder. Rule `DTI_MAX_STANDARD` dibuka, lalu dia membuat versi draft baru karena versi yang aktif memang tidak bisa diedit. Ambangnya diubah dari 0.45 menjadi 0.42.
3. Dia menguji satu kasus lewat dry-run, yaitu memasukkan contoh pemohon dan melihat cabang mana yang kena.
4. Dia menyimulasikan dampaknya ke populasi lewat policy impact analysis. Kebijakan draft dijalankan terhadap ribuan aplikasi historis, dan hasilnya misalnya begini. Approval rate turun dari 44% ke 39%, penolakan naik terutama di channel dealer, dan reason code HIGH_DTI naik tiga kali lipat. Di sinilah bedanya mengira-ngira dengan benar-benar tahu.
5. Dia mengajukan persetujuan dengan lampiran hasil simulasi. Di OSCAR, lampiran simulasi memang wajib sebelum strategy bisa diaktifkan.
6. Setelah aturan aktif, dia memantau reason code teratas dan approval rate di dashboard untuk memastikan dampak nyatanya sesuai simulasi.

> **Analogi.** Dia seperti koki riset di restoran waralaba. Resep baru dicoba dulu di dapur uji, dicicipi panel penilai, disetujui kepala koki, baru dicetak ke buku resep edisi baru. Tidak pernah ada cerita resep diganti langsung di dapur cabang saat jam makan siang.

## 5.2 Credit Risk Manager, kepala dapur sekaligus pemegang rem

Misinya adalah menjaga portofolio tetap pada selera risiko, menjadi penyetuju atas semua perubahan, dan menarik rem darurat saat diperlukan. Layar yang dipakainya antara lain Dashboard, Approvals, Strategies, dan Audit Log.

Paginya dimulai dari dashboard, yaitu memeriksa approval rate, reject rate, manual review rate, tren volume, reason code teratas, dan ukuran antrean review. Setiap keanehan menjadi pertanyaan.

Selanjutnya dia membuka antrean persetujuan untuk meninjau usulan para analis. Berkat prinsip maker-checker, dia tidak bisa menyetujui usulan buatannya sendiri, dan sistem juga menolak aktivasi yang tidak menyertakan bukti simulasi. Dia membaca ringkasan dampak, lalu menyetujui atau menolak dengan alasan yang tercatat.

Saat krisis, misalnya kebijakan baru ternyata memukul approval terlalu dalam, dia bisa melakukan rollback, yaitu mengaktifkan kembali versi strategy sebelumnya. Versi yang sekarang tidak dihapus karena sejarah memang tidak pernah dihapus. Alasannya wajib ditulis dan semuanya terekam.

Dia juga memantau override. Kalau underwriter terlalu sering membatalkan keputusan mesin, itu sinyal bahwa kebijakan tidak realistis, dan hal itu menjadi agenda rapat.

> **Analogi.** Dia seperti kapten kapal. Dia tidak memegang kemudi setiap menit karena itu tugas mesin dan kru, tetapi dialah yang menentukan arah, menyetujui perubahan rute, membaca instrumen, dan berwenang memutar balik. Setiap perintahnya masuk ke log pelayaran, dalam hal ini audit log.

## 5.3 Underwriter atau Credit Analyst, dokter spesialis kasus abu-abu

Misinya adalah memutus kasus-kasus yang mesin sendiri mengaku tidak yakin, secara cepat, adil, dan terdokumentasi. Layarnya adalah antrean Manual Review beserta halaman detail kasus.

1. Antreannya sudah terprioritaskan. Kasus fraud berprioritas tinggi, ada SLA-nya, dan kasus yang mendekati tenggat akan menyala.
2. Saat kasus dibuka, semua bahan sudah tersaji, mulai dari ringkasan pemohon, pinjaman, dan kendaraan dengan data sensitif yang tersamar, keputusan sistem beserta alasannya, sampai tautan ke trace. Dia jadi tahu persis kenapa mesin ragu, misalnya karena DTI 0.43 mepet dengan ambang 0.45.
3. Dia lalu melakukan investigasi manusiawi, misalnya menelepon HRD kantor pemohon, meminta dokumen tambahan lewat daftar periksa dokumen seperti slip gaji dan rekening tiga bulan, serta menulis catatan di kasus.
4. Dia memutus. Pilihannya menyetujui, menolak dengan kewajiban memilih reason code, menyetujui dengan syarat berupa limit atau tenor yang diturunkan, atau mengeskalasi ke senior. Kalau putusannya berbeda dari mesin, dia wajib menulis alasan override. Khusus membatalkan vonis FRAUD_INVESTIGATION, dibutuhkan wewenang setingkat supervisor.
5. Keputusannya tersimpan berdampingan dengan keputusan sistem, bukan menimpanya. Ada "Decision by System" dan ada "Decision by Analyst".

> **Analogi.** Dia seperti dokter jaga IGD yang dibantu sistem triase. Mesin triase sudah memilah pasien dan melampirkan hasil lab, dalam hal ini trace. Sang dokter cukup fokus pada pasien kuning dan merah, dan setiap tindakan di luar protokol harus ditulis alasannya di rekam medis.

## 5.4 Fraud Analyst, satpam yang berpengalaman

Misinya adalah mendeteksi dan memutus pola penipuan secepat mungkin.

Dia memantau kasus-kasus berlabel FRAUD_INVESTIGATION serta reason code bertema fraud seperti APPLICATION_DATA_MISMATCH dan BLACKLIST_HIT. Saat pola baru ditemukan, misalnya sindikat dokumen dari satu dealer, dia mengusulkan rule fraud baru atau pembaruan daftar hitam. Karena kebijakan berbentuk konfigurasi, pertahanan baru bisa aktif hari itu juga lewat jalur persetujuan, tanpa menunggu rilis software kuartal depan. Kecepatan mengubah aturan memang senjata utamanya, sebab penipu berpindah pola dalam hitungan hari.

## 5.5 Compliance dan Internal Audit, wasit sekaligus notulen

Misinya adalah membuktikan bahwa semua keputusan dan semua perubahan kebijakan itu sah, tercatat, dan bisa direkonstruksi.

Untuk rekonstruksi keputusan, ketika regulator atau nasabah menanyakan keputusan delapan bulan lalu, dia cukup mencari keputusannya lalu membuka trace. Di sana tampak input, aturan versi berapa yang dipakai, dan alasannya. Kasus selesai dalam hitungan menit.

Untuk audit perubahan, layar Audit Log menjawab pertanyaan siapa mengubah apa, kapan, kenapa, dari nilai berapa ke nilai berapa, dan siapa yang menyetujui. Semua itu berlaku untuk rule, strategy, override, sampai perubahan role. Catatannya bersifat tambah-saja, sehingga tidak seorang pun, termasuk admin, bisa menyunting sejarah.

Dia juga rutin mengambil sampel override underwriter beserta alasannya untuk mencari pola penyimpangan. Bahkan aktivitas membuka trace pun tercatat, karena akses ke data sensitif ikut diaudit.

> **Analogi.** Dia seperti petugas arsip yang ruang arsipnya sendiri dipasangi kamera. Bukan hanya dokumennya lengkap, siapa pun yang membuka laci mana pun ikut terekam.

## 5.6 Data Scientist, yaitu Anda

Versi ringkasnya begini, sedangkan bab 7 membahasnya khusus.

- Anda memasok otak statistiknya, yaitu membangun model skor. Engine mengonsumsinya lewat scorecard dan mencatat versinya di model registry.
- Anda juga mengonsumsi jejaknya. Decision trace yang digabung dengan outcome pembayaran adalah dataset training dan validasi paling bersih yang pernah Anda punya, karena fiturnya persis seperti saat keputusan dibuat, bukan hasil rekonstruksi.
- Anda bisa menguji ide kebijakan lewat batch simulation, yang pada dasarnya adalah backtest kebijakan. Pertanyaan seperti "kalau cutoff digeser, siapa saja yang bertukar nasib" bisa dijawab dengan data, bukan opini.
- Anda pun memantau distribusi skor dan approval per grade dari dashboard, sehingga drift terdeteksi lebih dini daripada menunggu NPL.

## 5.7 Satu insiden yang menggerakkan semua peran

- **Senin 09.00.** Dashboard menunjukkan manual review rate melonjak dari 27% ke 41% sejak Jumat. Risk Manager bertanya-tanya.
- **09.30.** Penelusuran reason code menunjukkan DTI_NEAR_THRESHOLD meledak. Dari trace terlihat lonjakan aplikasi berpenghasilan tepat di sekitar ambang, semuanya dari channel dealer tertentu. Ini temuan Policy Analyst.
- **10.15.** Sampel kasus dibuka. Slip gaji dari tiga dealer ternyata bernomor seri berurutan, indikasi dokumen "dipabrikkan" supaya lolos ambang. Fraud Analyst dan Underwriter yang menemukannya.
- **11.00.** Rule fraud baru dibuat sebagai draft, yaitu kombinasi channel dan pola penghasilan yang diarahkan ke FRAUD_INVESTIGATION. Diuji ke data seminggu terakhir lewat simulasi, dan hasilnya menangkap 61 aplikasi dengan perkiraan salah tangkap yang rendah. Ini kerja Policy Analyst.
- **13.00.** Usulan disetujui dan diaktifkan oleh Risk Manager, lengkap dengan maker-checker dan alasan yang tercatat.
- **13.05.** Aturan sudah hidup di produksi, dan aplikasi sindikat berikutnya langsung tertahan.
- **Selasa.** Compliance menarik jejak insiden, mulai dari siapa yang menemukan, aturan apa yang berubah, siapa yang menyetujui, sampai apa dampaknya. Semuanya menjadi satu narasi utuh dari audit log dan trace, tanpa perlu mencari-cari email.

Tanpa decision engine, cerita yang sama memakan waktu berminggu-minggu karena harus mengubah kode dan menunggu rilis, tanpa simulasi, dan tanpa jejak. Sementara itu sindikatnya sudah pindah kota.

## 5.8 Rangkuman bab

| Peran | Layar utama | Kata kerjanya |
|---|---|---|
| Policy Analyst | Rules, Simulations, Strategies | menulis, menguji, mengusulkan |
| Risk Manager | Dashboard, Approvals, Audit | memantau, menyetujui, me-rollback |
| Underwriter | Manual Review | menginvestigasi, memutus, meng-override dengan alasan |
| Fraud Analyst | Kasus fraud dan rules fraud | mendeteksi, merespons cepat |
| Compliance | Audit Log, Trace | merekonstruksi, membuktikan |
| Data Scientist | Model registry, Simulations, Dashboard | memasok skor, mem-backtest, memantau drift |
