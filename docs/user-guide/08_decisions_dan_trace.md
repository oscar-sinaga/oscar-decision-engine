# Bab 08 — Dashboard, Decisions, dan Trace, Membaca Apa yang Terjadi

## 8.1 Latar belakang, keputusan harus bisa dipertanggungjawabkan selamanya

Tiga layar di bab ini melayani satu kebutuhan yang sama, yaitu **akuntabilitas**. Regulator, auditor, nasabah yang komplain, dan tim risk sendiri semuanya menanyakan hal serupa, kenapa hasilnya begini dan apa yang sedang terjadi sekarang. Sistem yang tidak bisa menjawab akan membayar mahal, entah lewat temuan audit, sengketa yang kalah, atau kerugian yang terlambat disadari. Karena itu setiap keputusan di OSCAR meninggalkan **trace** yang tidak bisa diubah, dan kesehatan keseluruhan dipantau lewat dashboard.

## 8.2 Bagaimana keputusan tercipta

Dalam operasi nyata, sistem LOS mengirim aplikasi ke API `POST /v1/decisions` memakai akun mesin seperti `los-client`, dan jawabannya kembali dalam ratusan milidetik. Manusia tidak mengetik apa pun di langkah ini. Yang perlu Anda kenali adalah bentuk kirimannya, karena bidang-bidang inilah yang menjadi fitur.

| Bagian payload | Isi penting |
|---|---|
| `application_id`, `product_type`, `channel` | Identitas aplikasi, sekaligus penentu strategy mana yang menyambutnya |
| `applicant` | Umur, penghasilan, kewajiban berjalan, dan data pemohon lain |
| `loan` | Jumlah dan tenor yang diminta |
| `vehicle` | Jenis, tahun, dan nilai taksiran jaminan |
| `bureau` | Ringkasan SLIK, misalnya keterlambatan terburuk setahun terakhir |
| `fraud` | Hasil verifikasi identitas, dokumen, daftar hitam, skor risiko perangkat |
| `model_outputs` | Skor kredit beserta versi modelnya |

Jawabannya memuat keputusan, kode alasan, limit dan tenor bila ada, versi strategy, nomor trace, dan nomor kasus review bila kasusnya lari ke manusia. Ada satu detail desain yang layak tahu, yaitu **idempotency**. Pengiriman ulang dengan kunci yang sama tidak melahirkan keputusan kedua. Latar belakangnya, jaringan di dunia nyata suka putus di tengah, dan LOS akan mencoba lagi. Tanpa pagar ini, satu pemohon bisa tercatat diputus dua kali dengan dua hasil, mimpi buruk rekonsiliasi.

## 8.3 Dashboard, kaca depan bukan spion

Menu **Dashboard** menampilkan angka harian, yaitu volume, approval rate, reject rate, manual review rate, latency, ukuran antrean review, distribusi keputusan, kode alasan teratas, dan tren volume, semuanya bisa disaring per produk dan channel.

Kenapa metrik keputusan dipantau seketat ini padahal sudah ada laporan NPL? Karena NPL adalah spion, ia bercerita tentang kecelakaan yang terjadi enam bulan lalu. Metrik keputusan adalah kaca depan. Approval rate yang bergeser lima poin tanpa perubahan kebijakan berarti populasi pemohonnya yang berubah, dan kode alasan teratas menunjukkan lewat pintu mana pergeserannya masuk. Menyelidikinya hari ini jauh lebih murah daripada membacanya di laporan NPL tahun depan.

## 8.4 Decisions, mencari keputusan lama

Menu **Decisions** adalah riwayat semua keputusan, dengan saringan application ID untuk menjawab pertanyaan tentang satu aplikasi, saringan decision untuk melihat semua penolakan atau semua review, saringan produk dan channel untuk menyempitkan segmen, serta rentang tanggal untuk investigasi periode. Klik nomor keputusan untuk membuka detail dan trace-nya.

## 8.5 Trace, membedah satu keputusan

Trace adalah kotak hitamnya, dan cara membacanya dari atas ke bawah.

1. **Kartu keputusan akhir**, berisi keputusan, grade, skor, limit, tenor, versi strategy, dan tautan ke kasus review bila ada.
2. **Kode alasan** beserta pesannya.
3. **Linimasa eksekusi**, node demi node sesuai urutan dilalui. Node CONDITION mencantumkan hasil evaluasinya dan cabang TRUE atau FALSE yang diambil, jadi rute persimpangan tidak pernah misterius.
4. **Rincian rule**, bagian paling berharga. Setiap rule menampilkan kondisi per kondisi berupa nilai ambang berhadapan dengan nilai aktual pemohon, cabang ke berapa yang cocok, dan aksi yang dijalankan termasuk output yang ditulis. Perhatikan desainnya, trace menyimpan **nilai aktual saat itu**, bukan sekadar nama aturannya, karena penjelasan yang jujur membutuhkan angka yang dipakai saat memutus, bukan rekonstruksi belakangan.
5. **Kartu outputs**, nilai akhir semua tulisan rule selama eksekusi.
6. **Fitur terhitung dan snapshot input**. Data sensitif pada snapshot sudah tersamar, karena kebutuhan menjelaskan keputusan tidak boleh menjadi pintu bocornya data pribadi.
7. Tautan **view flow** membuka kanvas baca-saja dari versi strategy yang dipakai.

Dua sifat penting menutup bagian ini. Trace tidak bisa diubah siapa pun termasuk admin, sebab bukti yang bisa disunting bukan bukti. Dan membuka trace pun tercatat di audit log, sebab isinya data sensitif dan akses ke data sensitif adalah peristiwa yang patut berjejak.

## 8.6 Studi kasus, menjawab komplain dalam lima menit

Cabang meneruskan komplain, aplikasi A-2210 ditolak padahal kata nasabah penghasilannya cukup.

Compliance menyaring Decisions dengan application ID dan menemukan keputusannya, REJECT beralasan HIGH_DTI. Di trace, rincian rule menunjukkan `affordability.dti` bernilai 0.51 berhadapan dengan ambang 0.45 milik DTI_MAX_STANDARD versi satu, dan bagian fitur terhitung memperlihatkan sumber angkanya, yaitu kewajiban berjalan 3,2 juta ditambah estimasi cicilan baru, dibagi penghasilan 8 juta. Jawaban ke nasabah pun konkret, penghasilannya memang cukup untuk cicilan baru saja, tetapi total kewajiban berjalannya membuat rasio melampaui batas, dan bila salah satu pinjaman lamanya lunas ia dipersilakan mengajukan lagi. Lima menit, nol tebakan, setiap klaim didukung angka yang terekam saat keputusan dibuat.

## 8.7 Siapa memakainya

Risk Manager membuka Dashboard tiap pagi. Underwriter membaca trace sebagai bahan investigasi. Compliance dan auditor memakai Decisions serta trace untuk rekonstruksi. Data scientist menambang trace sebagai sumber fitur historis paling jujur, karena nilainya persis nilai saat keputusan diambil.
