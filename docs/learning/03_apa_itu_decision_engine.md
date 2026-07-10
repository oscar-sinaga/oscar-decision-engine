# Bab 3 — Apa Itu Decision Engine, dan Kenapa Dunia Keuangan Membutuhkannya

## 3.1 Definisi dalam satu kalimat

Decision engine adalah perangkat lunak yang menerima data satu kasus, misalnya sebuah aplikasi kredit, menjalankannya melewati kebijakan yang tersimpan sebagai konfigurasi, lalu mengembalikan keputusan beserta alasannya. Semuanya berlangsung otomatis, konsisten, cepat, dan bisa diaudit.

Kata kuncinya ada di frasa "tersimpan sebagai konfigurasi". Artinya, kebijakan disimpan sebagai data yang bisa diubah oleh orang bisnis, bukan sebagai kode program yang hanya bisa diubah programmer. Dalam istilah industri, keluarga perangkat lunak ini disebut BRMS atau Business Rules Management System, kadang juga disebut credit decisioning platform. Contoh produk komersialnya antara lain FICO Blaze, Experian PowerCurve, SAS, Provenir, serta iDecision yang menjadi benchmark OSCAR.

> **Analogi inti, yaitu dapur dan buku resep.** Restoran waralaba bisa menyajikan menu yang sama di cabang mana pun karena ada buku resep standar. Decision engine ibarat dapur yang membaca resep dari buku setiap kali memasak. Kalau mau mengubah rasa, yang diubah adalah bukunya. Terbitkan resep edisi baru dengan persetujuan kepala dapur, bukan membongkar dapurnya. Sistem lama ibarat dapur yang resepnya dilas ke kompor. Setiap ganti resep harus memanggil tukang las, dalam hal ini programmer, dan tidak ada yang tahu persis resep edisi berapa yang dipakai kemarin.

## 3.2 Latar belakang, tiga era pengambilan keputusan kredit

**Era pertama, manual sepenuhnya.** Di bank tempo dulu, setiap aplikasi dinilai analis manusia satu per satu. Cara ini lambat karena butuh hitungan hari sampai minggu, mahal, dan yang paling parah tidak konsisten. Pemohon yang sama bisa diterima analis A tetapi ditolak analis B. Cara ini juga rawan bias dan "faktor kedekatan". Soal skala jangan ditanya, karena menilai lima ribu aplikasi sehari jelas mustahil.

**Era kedua, scorecard dan aturan yang ditanam di kode.** Statistik mulai masuk sejak era FICO tahun 1960-an dan menjadi masif sejak 1990-an. Karakteristik pemohon diberi poin lewat scorecard, lalu keputusan diambil berdasarkan ambang skor ditambah aturan. Awalnya di kertas, kemudian ditanam ke sistem, tepatnya ke dalam kode program core system. Hasilnya memang konsisten dan cepat. Namun muncul rasa sakit baru yang mungkin terdengar akrab di telinga Anda.

- Tim risk berkata, "Tolong ubah DTI maksimal dari 45% ke 40%." Permintaan itu antre di backlog IT selama tiga bulan, padahal kondisi pasar berubah minggu ini.
- Ada yang bertanya, "Kenapa aplikasi ini ditolak?" Jawabannya, "Hmm, harus baca kodenya dulu."
- Ada juga yang bertanya, "Aturan yang berlaku bulan Maret tahun lalu apa?" Tidak ada yang tahu pasti, karena kode sudah berubah berkali-kali tanpa arsip versi kebijakan.
- Menguji dampak sebelum aturan berlaku? Tidak bisa. Ubah langsung di produksi, lalu berdoa.

**Era ketiga, decision engine dengan kebijakan sebagai konfigurasi.** Kebijakan dipindahkan keluar dari kode ke dalam mesin khusus. Tim risk mengubah sendiri aturannya lewat antarmuka, setiap versi terarsip, setiap keputusan meninggalkan jejak berupa trace, perubahan bisa disimulasikan dulu sebelum berlaku, dan harus disetujui pejabat yang berwenang. IT tetap penting untuk menjaga mesinnya, tetapi tidak lagi menjadi hambatan bagi isi kebijakan.

> **Analogi hukum.** Era kedua itu seperti negara yang undang-undangnya tertanam di kepala hakim, sehingga mengubah undang-undang berarti mengganti hakimnya. Era ketiga seperti negara dengan undang-undang tertulis yang bernomor dan bertahun, diubah lewat prosedur legislasi, dan setiap vonis mengutip pasal yang dipakai. Nomor dan tahun itulah versioning, prosedur legislasi itulah governance, dan kutipan pasal itulah reason code beserta trace.

## 3.3 Masalah-masalah spesifik yang diselesaikan

Daftar berikut sebenarnya adalah problem statement di PRD OSCAR. Sekarang Anda tahu konteks bisnisnya.

| Masalah tanpa decision engine | Akibat bisnisnya | Jawaban decision engine |
|---|---|---|
| Kebijakan tertanam di kode, sehingga mengubahnya berarti proyek IT | Reaksi terhadap pasar dan fraud terlambat berbulan-bulan | Kebijakan menjadi konfigurasi. Tim risk mengubah sendiri dan aktif dalam hitungan jam, tetap dengan persetujuan |
| Keputusan tidak bisa dijelaskan | Nasabah komplain, regulator bertanya, dan organisasi tidak bisa belajar | Ada reason code dan decision trace untuk setiap keputusan |
| Versi aturan tidak terlacak | Audit gagal merekonstruksi keputusan lama, posisi hukum lemah | Versioning yang tidak bisa diutak-atik. Setiap keputusan mencatat versi aturan dan model yang persis dipakai |
| Tidak ada uji dampak | Kebijakan baru menjadi perjudian, dan kesalahan baru ketahuan setelah rugi | Simulation dan impact analysis sebelum aktivasi |
| Perubahan tanpa kontrol | Satu orang khilaf bisa mengubah nasib portofolio | Maker-checker, artinya pembuat dan penyetuju harus orang berbeda, dan semuanya tercatat |
| Override manual tidak terdokumentasi | "Katanya dulu disetujui Pak X" tidak pernah bisa dibuktikan | Override wajib disertai alasan, tercatat siapa, kapan, dan kenapa |
| Tidak ada monitoring keputusan | Pergeseran kualitas baru ketahuan setelah NPL meledak, terlambat enam sampai dua belas bulan | Metrik harian seperti approval rate, reason code teratas, dan override rate |
| Kecepatan manusia terbatas | Nasabah lari ke pesaing yang menjawab lima belas menit | Keputusan otomatis dalam hitungan detik untuk mayoritas kasus |

## 3.4 Kenapa ini sangat penting justru di dunia keuangan

Ada lima alasan yang membuat decision engine jauh lebih vital di keuangan dibanding industri lain.

Pertama, keputusannya bernilai uang secara langsung dan berulang ribuan kali sehari. Salah satu persen secara konsisten berarti miliaran rupiah, seperti hitungan di bab 1. Konsistensi bukan kemewahan, melainkan kebutuhan aritmetika.

Kedua, industrinya diatur ketat. OJK dan regulator mana pun menuntut lembaga keuangan mampu menjelaskan serta mempertanggungjawabkan keputusan kreditnya, punya manajemen risiko, dan punya jejak audit. Jawaban "sistemnya memang begitu, kami tidak tahu kenapa" tidak akan diterima.

Ketiga, ada lawan yang aktif, yaitu fraud. Ada pihak yang setiap hari mencoba menipu, sehingga kebijakan harus bisa berubah cepat begitu pola penipuan baru muncul. Kecepatan mengubah aturan adalah senjata pertahanan.

Keempat, akibat dari keputusan hari ini baru terlihat enam sampai dua puluh empat bulan kemudian, karena kredit macet butuh waktu untuk "matang". Umpan balik yang lambat membuat disiplin mencatat, yaitu apa yang diputuskan dengan aturan versi apa, menjadi satu-satunya cara belajar dari masa lalu. Catatan itu sekaligus bahan baku model Anda sebagai data scientist.

Kelima, ada dimensi keadilan. Keputusan kredit menyangkut akses ekonomi orang banyak. Aturan yang eksplisit dan alasan yang tercatat bisa diperiksa adil atau tidaknya, sedangkan keputusan berdasarkan "perasaan analis" tidak bisa diperiksa sama sekali.

## 3.5 Decision engine itu bukan apa

Supaya tidak salah paham, mari tegaskan batasannya.

- Dia bukan LOS. Dia tidak mengurus formulir pengajuan, dokumen, atau alur kerja cabang. Justru dialah yang dipanggil oleh LOS.
- Dia bukan core system atau LMS, karena tidak mengurus pembukuan cicilan.
- Dia bukan model machine learning. Model hanyalah salah satu bahan di dalamnya, yaitu penghasil skor, sedangkan engine adalah kerangka kebijakan yang memakai skor itu bersama aturan-aturan lain. Bab 7 membahas hubungan ini khusus untuk Anda.
- Dia juga bukan robot yang menggantikan semua manusia. Justru dia merutekan kasus abu-abu ke manusia lewat manual review, sambil menangani mayoritas kasus yang jelas secara otomatis.

> **Analogi bandara.** E-gate imigrasi memproses 80% penumpang dalam sepuluh detik, sedangkan penumpang yang "tidak biasa" diarahkan ke konter petugas. Jumlah petugasnya jadi lebih sedikit, tetapi mereka lebih fokus pada kasus yang benar-benar butuh keahlian. Decision engine adalah e-gate untuk aplikasi kredit, dan underwriter adalah petugas konternya.

## 3.6 Nilai bisnisnya dalam satu tabel

Kalau pertanyaannya "membantu di sisi apa", inilah jawaban ringkasnya.

| Sisi | Bantuan nyata |
|---|---|
| **Pendapatan** | Keputusan dalam hitungan detik menaikkan conversion, dan kebijakan yang presisi per segmen membuat lebih banyak orang baik disetujui, padahal dulu tertolak oleh aturan yang kasar |
| **Kerugian** | Aturan yang konsisten dan cepat diubah saat ada fraud atau pemburukan membuat bad rate terkendali |
| **Biaya operasional** | Mayoritas keputusan berjalan otomatis, sehingga underwriter cukup fokus ke kasus abu-abu |
| **Kepatuhan** | Trace, audit log, dan versioning membuat perusahaan siap diperiksa regulator maupun auditor kapan saja |
| **Kecepatan belajar organisasi** | Simulasi dan data keputusan yang terstruktur membuat iterasi kebijakan berbasis bukti, bukan perasaan |

## 3.7 Rangkuman bab

1. Decision engine adalah mesin yang menjalankan kebijakan-sebagai-konfigurasi untuk memutus kasus secara otomatis sekaligus akuntabel.
2. Dia lahir dari rasa sakit era kode, yaitu lambat diubah, tidak bisa dijelaskan, tidak berversi, tidak teruji, dan tidak terkontrol.
3. Di dunia keuangan dia vital karena skala uangnya, regulasinya, ancaman fraudnya, umpan baliknya yang lambat, dan tuntutan keadilannya.
4. Dia melengkapi LOS, LMS, model machine learning, dan manusia, bukan menggantikan mereka.

Bab berikutnya membuka kap mesinnya, yaitu apa yang sebenarnya terjadi di dalam ketika satu aplikasi masuk.
