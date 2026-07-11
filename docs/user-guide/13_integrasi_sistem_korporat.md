# Bab 13 — Integrasi OSCAR dengan LOS, LMS, Collection, dan Muffin

## 13.1 Latar belakang dan prinsip dasarnya

Perusahaan Anda sudah punya ekosistem lengkap. Ada LOS tempat aplikasi masuk, ada Muffin sebagai core system yang memegang kontrak dan pembukuan, ada LMS untuk kredit berjalan, dan ada sistem collection untuk yang menunggak. OSCAR datang bukan untuk menggantikan satu pun dari mereka, melainkan mengisi satu lubang yang selama ini tertanam di dalam LOS atau di kepala analis, yaitu titik pengambilan keputusan kredit.

Karena itu ada tiga prinsip yang harus dipegang sejak awal, dan semuanya punya alasan.

1. **Setiap sistem tetap menjadi tuan atas datanya sendiri.** LOS memegang aplikasi dan dokumen, OSCAR memegang kebijakan beserta keputusan dan trace, Muffin memegang kontrak dan pembukuan, LMS memegang tagihan dan pembayaran, sedangkan collection memegang catatan penagihan. Tidak ada yang menulis ke buku milik sistem lain. Begitu dua sistem saling menulis ke data yang sama, rekonsiliasi jadi mimpi buruk dan tidak ada lagi yang bisa dipercaya sebagai sumber kebenaran.
2. **Hubungannya longgar tapi kontraknya ketat.** Sistem-sistem berbicara lewat API dengan kontrak yang jelas dan berversi, bukan dengan saling baca tulis database satu sama lain. Menyambung langsung ke database sistem lain memang terasa cepat di awal, tapi lama-lama menjadi rantai besi, karena setiap perubahan struktur tabel di satu sistem bisa diam-diam mematahkan sistem lainnya.
3. **OSCAR berada di jalur yang ditunggu hanya untuk satu hal**, yaitu memutus. Semua kebutuhan lain, misalnya kiriman data ke data warehouse, berjalan belakangan tanpa ada yang menunggu, supaya tidak pernah memperlambat keputusan.

Supaya gampang membayangkannya, pakai analogi rumah sakit. LOS adalah loket pendaftaran dan rekam medis, laboratorium adalah SLIK dan eKYC, OSCAR adalah dokter beserta protokol diagnosisnya, Muffin adalah farmasi dan kasir yang mencatat transaksi resmi, LMS adalah poli kontrol untuk pasien rawat jalan, sedangkan collection adalah bagian yang menangani pasien penunggak biaya. Rumah sakit menjadi kacau bukan ketika salah satu unit sibuk, melainkan ketika unit-unit mulai saling mengerjakan pekerjaan unit lain.

## 13.2 Peta besar, siapa berbicara dengan siapa

```
                                 ┌──────────────┐
   Cabang / Dealer / Aplikasi ──▶│     LOS      │◀── eKYC ── gateway SLIK ── Appraisal
                                 │ (pintu masuk │      (dipanggil LOS, hasilnya
                                 │  pengajuan)  │       melengkapi payload)
                                 └──────┬───────┘
                       payload lengkap  │  ▲ keputusan + alasan + limit/tenor
                       (real time)      ▼  │
                                 ┌──────────────┐
                                 │    OSCAR     │── trace, audit, kebijakan (miliknya sendiri)
                                 └──────┬───────┘
                                        │ kiriman batch / event (tidak ditunggu)
                                        ▼
   ┌─────────┐   booking    ┌──────────────┐   kontrak aktif   ┌─────────┐   tunggakan   ┌────────────┐
   │  MUFFIN │◀─────────────│  LOS (akad)  │                   │   LMS   │──────────────▶│ COLLECTION │
   │  (core) │──────────────▶ pencairan                        └────┬────┘               └─────┬──────┘
   └────┬────┘                                                      │ perilaku bayar           │ hasil penagihan
        └───────────────────────────┬───────────────────────────────┴──────────────────────────┘
                                    ▼
                            ┌──────────────┐   label lancar/macet, vintage, bahan model
                            │Data Warehouse│──────────────────────────────▶ Data Scientist
                            └──────────────┘        (kembali ke OSCAR lewat scorecard & simulasi)
```

Perhatikan ada dua jenis panah di peta itu. Panah yang ditunggu jawabannya cuma satu, yaitu ketika LOS bertanya dan OSCAR menjawab saat keputusan dibutuhkan. Semua panah lain berjalan belakangan lewat batch atau event, tanpa ada proses yang berdiri menunggu.

## 13.3 Kontrak integrasi per sistem

| Sistem | Arah | Cara | Isi | Seberapa sering |
|---|---|---|---|---|
| **LOS ke OSCAR** | tanya | REST API `POST /v1/decisions` dengan Idempotency-Key dan correlation ID | Payload aplikasi lengkap yang sudah dilengkapi hasil eKYC, SLIK, dan appraisal | Setiap aplikasi, target di bawah setengah detik |
| **OSCAR ke LOS** | jawab | Respons pada panggilan yang sama | Keputusan, kode alasan, limit dan tenor, nomor trace, serta nomor kasus review bila ada | Bersama panggilan di atas |
| **Muffin ke OSCAR** | data masukan | Lewat payload yang dirakit LOS | Data internal pemohon, misalnya jumlah kontrak aktif dan riwayat bayar internal, sebagai fitur | Saat aplikasi diputus |
| **OSCAR ke Muffin** | tidak ada | Booking tetap dilakukan LOS setelah akad lewat jalur yang ada sekarang | OSCAR tidak pernah menyentuh pembukuan | — |
| **LMS dan Collection ke Data Warehouse** | umpan balik | Batch atau event yang sudah berjalan hari ini | Perilaku bayar, tunggakan, dan hasil penagihan | Harian |
| **OSCAR ke Data Warehouse** | kiriman | Batch atau event, di luar jalur keputusan | Keputusan dan trace untuk analitik, pelatihan model, dan vintage | Harian atau lebih sering |
| **Data Warehouse ke OSCAR** | bahan uji | Diunduh sebagai payload historis | Populasi untuk simulasi massal dan backtest kebijakan | Sesuai kebutuhan analis |

Dua keputusan desain di tabel itu layak digarisbawahi. Pertama, OSCAR tidak menulis apa pun ke Muffin. Keputusan kredit adalah rekomendasi yang mengikat proses, sedangkan pencatatan kontrak dan pencairan tetap menjadi ritual resmi core system lewat alur LOS yang sudah teruji bertahun-tahun. Memotong jalur itu berarti membangun ulang kontrol yang sudah ada, dan itu pekerjaan besar tanpa manfaat. Kedua, yang melengkapi data adalah LOS, bukan OSCAR yang memanggil SLIK atau eKYC sendiri. Alasannya sederhana, karena LOS Anda sudah punya koneksi, kuota, dan perjanjian dengan para penyedia data itu. Membangun koneksi kedua di OSCAR berarti dua sambungan yang harus dirawat untuk data yang sama. Kalau kelak perusahaan ingin OSCAR memanggil langsung, itu perubahan yang sah, tapi jadikan keputusan sadar dan bukan kecelakaan arsitektur.

## 13.4 Alur ujung ke ujung yang realistis

Mari ikuti Pak Budi menembus seluruh ekosistem.

1. Cabang menginput pengajuan lease-back di LOS. LOS menjalankan rangkaian verifikasinya seperti biasa, yaitu memanggil eKYC untuk identitas, gateway SLIK untuk riwayat kredit, dan penilai untuk taksiran motor. Semua hasil terkumpul di berkas aplikasi.
2. LOS merakit payload lengkap, menempelkan `Idempotency-Key` unik per pengajuan dan `X-Correlation-Id` dari transaksinya sendiri, lalu memanggil `POST /v1/decisions`.
3. OSCAR memutus dalam hitungan ratusan milidetik dan menjawab, misalnya APPROVE_WITH_CONDITION dengan limit 12,5 juta, lengkap dengan kode alasan dan nomor trace. Trace tersimpan di OSCAR, jadi LOS cukup menyimpan nomornya tanpa perlu menyalin isinya.
4. LOS melanjutkan alurnya ke akad, lalu booking kontrak dan pencairan di Muffin lewat integrasi yang sudah ada hari ini. Tidak ada yang berubah di langkah ini.
5. Kontrak hidup dan pengelolaannya berpindah ke LMS. Pembayaran berjalan dan datanya mengalir ke data warehouse seperti sekarang.
6. Enam bulan kemudian tim data menarik satu angkatan kontrak dari data warehouse, menempelkan label lancar atau menunggak, lalu mengembalikannya sebagai bahan dua hal, yaitu pelatihan model berikutnya dan simulasi massal di OSCAR untuk menguji kebijakan baru terhadap populasi nyata.
7. Ketika auditor bertanya tentang keputusan Pak Budi, siapa pun tinggal membuka trace di OSCAR lewat nomor yang tercatat di LOS, dan correlation ID menghubungkan jejak di kedua sistem menjadi satu cerita utuh.

## 13.5 Menghindari bottleneck, karena inilah kekhawatiran paling wajar

Sistem korporat Anda besar, jadi menambahkan satu panggilan yang ditunggu jawabannya di jalur pengajuan memang harus dihitung serius. Kabar baiknya, jalur yang ditunggu itu cuma satu dan pendek. Berikut strateginya, dari desain sampai operasional.

**Satu panggilan gemuk, bukan banyak panggilan kurus.** Kontraknya sengaja dibuat supaya LOS mengirim seluruh data dalam satu payload dan menerima seluruh jawaban dalam satu respons. Pola tanya jawab bolak-balik berkali-kali untuk satu aplikasi adalah resep kelambatan.

**OSCAR itu stateless, jadi gampang diperbanyak.** Mesin keputusannya tidak menyimpan apa pun di memori antar permintaan, sehingga menghadapi lonjakan volume cukup dengan menambah jumlah instance di belakang load balancer. Seperti gerbang tol, kalau antrean memanjang maka buka gardu tambahan, tidak perlu membangun jalan baru.

**Pisahkan beban memutus dari beban membaca.** Keputusan menulis ke database produksi, sedangkan dashboard, riwayat, dan terutama analitik jangan ikut membebani database yang sama. Analitik berat berjalan di data warehouse atas data kiriman, dan kalau workbench mulai ramai, bacaannya bisa diarahkan ke read replica. Banyak sistem melambat bukan karena transaksinya berat, melainkan karena laporan bulanan ikut berjalan di database transaksi.

**Semua yang tidak ditunggu dibuat mengantre.** Kiriman ke data warehouse, notifikasi, dan pekerjaan sampingan lain berjalan lewat antrean di belakang layar. Jalur yang ditunggu hanya berisi hal yang benar-benar harus selesai sebelum menjawab, yaitu memutus lalu menyimpan keputusan, trace, dan audit.

**Idempotency adalah sabuk pengaman lonjakan.** Saat jaringan tersendat, LOS akan mengirim ulang, dan tanpa pagar ini setiap kiriman ulang menjadi keputusan ganda. Dengan `Idempotency-Key`, kiriman ulang seagresif apa pun aman, sehingga Anda justru bisa menyetel retry dengan berani.

**Sepakati target kecepatan dan pantau lintas sistem.** Targetnya harus menjadi angka tertulis, misalnya 95 persen panggilan keputusan selesai di bawah 500 milidetik, dan angka itu sudah terbukti di pengujian lokal sekitar 300 milidetik. Correlation ID yang sama mengalir di log LOS dan OSCAR, jadi saat ada keluhan lambat, kedua tim membaca transaksi yang sama dan tidak saling menunjuk.

**Rencanakan kegagalan, bukan hanya keberhasilan.** Sepakati batas waktu tunggu di sisi LOS, misalnya dua detik, ditambah circuit breaker supaya gangguan di OSCAR tidak ikut menyeret antrean LOS. Lalu tuliskan prosedur daruratnya sebagai keputusan bisnis, bukan improvisasi tengah malam. Pilihannya biasanya aplikasi diantrekan dulu dan diputus begitu OSCAR pulih, atau ada jalur manual untuk kasus mendesak. Yang tidak boleh adalah diam-diam meloloskan aplikasi tanpa keputusan.

**Uji kapasitas sebelum hari besar.** Promo dealer akhir tahun bisa melipatgandakan volume dalam sehari. Jalankan uji beban dengan profil lonjakan seperti itu di lingkungan staging, temukan titik jenuhnya, lalu pasang rate limit per kanal sebagai sekring supaya satu kanal yang mengamuk tidak menumbangkan semua.

## 13.6 Tata kelola data lintas sistem

Kirim yang perlu saja. OSCAR membutuhkan fitur untuk memutus, bukan seluruh isi berkas, jadi jangan mengirim foto dokumen atau data mentah eKYC di payload. Data sensitif yang memang harus lewat akan tersamar di trace dan log OSCAR, dan siapa pun yang membukanya tercatat di audit. Masa simpan trace dan audit mengikuti kebijakan legal perusahaan, dan sebaiknya diselaraskan dengan masa simpan berkas di LOS supaya tidak ada cerita yang putus di tengah ketika sengketa datang bertahun-tahun kemudian.

## 13.7 Jujur tentang yang belum ada, yaitu daftar pekerjaan integrasi

OSCAR hari ini sudah menyediakan sisi dirinya, yaitu API keputusan yang idempotent, correlation ID, trace, audit, dan akun mesin untuk sistem lain. Tapi integrasi adalah pekerjaan dua sisi, dan daftar berikut realistisnya digarap bersama tim IT korporat sebagai proyek tersendiri.

| Pekerjaan | Isinya | Catatan |
|---|---|---|
| **Pemetaan payload LOS ke kontrak OSCAR** | Pemetaan field demi field, penyeragaman satuan, kesepakatan mana yang wajib dan mana yang opsional | Pekerjaan terbesar dan paling menentukan. Feature Catalog menjadi kamus bersamanya |
| **Autentikasi antar sistem** | Credential khusus untuk LOS yang disimpan di vault korporat, plus kesepakatan jalur jaringan dengan tim security | OSCAR hari ini memakai token akun mesin. Selaraskan dengan standar API gateway korporat |
| **SSO untuk workbench** | Menyambungkan login workbench ke identitas pegawai korporat | Pengguna hari ini dikelola lokal di OSCAR. Untuk skala korporat, penyambungan ke sistem identitas perusahaan adalah langkah wajar berikutnya |
| **Kiriman ke data warehouse** | Job batch atau event stream untuk keputusan dan trace | Belum dibangun, dan memang sengaja diputuskan belakangan bersama tim data platform |
| **Muffin sebagai sumber fitur internal** | Menyalurkan data kontrak aktif dan riwayat internal ke payload | Jalur termudahnya lewat LOS yang sudah tersambung ke Muffin |
| **Runbook operasional bersama** | Prosedur darurat, jalur eskalasi, dan rekonsiliasi harian antara jumlah pengajuan di LOS dan jumlah keputusan di OSCAR | Rekonsiliasi harian yang sederhana menangkap sebagian besar masalah integrasi lebih dini |
| **Penyelarasan jadwal rilis** | Lingkungan dev, UAT, dan produksi OSCAR mengikuti kalender perubahan korporat | Isi kebijakan bisa berubah harian di dalam OSCAR, tapi kontrak antar sistem hanya berubah lewat manajemen perubahan |

## 13.8 Studi kasus operasional

**Kasus satu, maintenance terjadwal.** OSCAR perlu maintenance tiga puluh menit. Sesuai runbook, LOS menahan aplikasi baru di antrean tunda, cabang melihat status keputusan menyusul, dan begitu OSCAR pulih antrean dikirim ulang. Berkat idempotency, kiriman yang tadi sempat terkirim setengah jalan tidak menjadi keputusan ganda. Tidak ada satu pun aplikasi yang lolos tanpa keputusan.

**Kasus dua, lonjakan promo.** Promo dealer membuat volume harian naik tiga kali lipat. Instance OSCAR ditambah dari dua menjadi enam pagi itu, kecepatan tetap di bawah target, dan rate limit per kanal menahan satu integrator dealer yang salah konfigurasi dan mengirim ulang membabi buta, tanpa mengganggu kanal lain.

**Kasus tiga, rekonsiliasi menemukan selisih.** Job rekonsiliasi pagi melaporkan LOS mencatat 4.210 pengajuan kemarin, sedangkan OSCAR mencatat 4.198 keputusan. Dua belas selisihnya ditelusuri lewat correlation ID, dan ternyata permintaannya gagal sampai karena gangguan jaringan di sisi cabang. LOS mengirim ulang kedua belasnya siang itu. Tanpa rekonsiliasi harian, selisih seperti ini baru ketahuan saat nasabah komplain.

## 13.9 Peta jalan integrasi bertahap

Jangan menyambung semuanya sekaligus. Urutan yang sehat kira-kira begini.

1. **Tahap satu, shadow mode.** LOS memanggil OSCAR untuk satu produk percontohan, tapi keputusannya belum dipakai dan hanya dibandingkan diam-diam dengan proses lama. Tahap ini membangun kepercayaan dengan risiko nol, karena kalau hasilnya aneh tidak ada nasabah yang terdampak.
2. **Tahap dua, cutover produk percontohan.** Keputusan OSCAR menjadi keputusan resmi untuk produk itu, lengkap dengan prosedur darurat dan rekonsiliasi harian yang sudah berjalan.
3. **Tahap tiga, perluasan dan umpan balik data.** Produk lain menyusul satu per satu, kiriman ke data warehouse dibangun, dan siklus label dari LMS serta collection mulai memberi makan simulasi dan model.
4. **Tahap empat, pendalaman.** SSO untuk workbench, fitur internal dari Muffin, dan bila memang dibutuhkan, koneksi langsung OSCAR ke penyedia data.

Setiap tahap punya pintu mundur yang jelas, dan itulah bedanya integrasi yang dikelola dengan integrasi yang dipaksakan. Sistem korporat yang besar sebenarnya tidak takut pada perubahan, ia takut pada perubahan yang tidak bisa mundur.
