# Bab 08 — Dashboard, Decisions, dan Trace, Membaca Apa yang Terjadi

## 8.1 Bagaimana keputusan tercipta

Dalam operasi nyata, sistem LOS mengirim aplikasi ke API `POST /v1/decisions` memakai akun mesin seperti `los-client`, dan jawabannya kembali dalam hitungan ratusan milidetik. Manusia tidak mengetik apa pun di sini. Yang perlu Anda pahami adalah bentuk kirimannya, karena bidang-bidang inilah yang menjadi fitur.

| Bagian payload | Isi penting |
|---|---|
| `application_id`, `product_type`, `channel` | Identitas aplikasi serta penentu strategy mana yang dipakai |
| `applicant` | Umur, penghasilan, kewajiban berjalan, dan data pemohon lain |
| `loan` | Jumlah dan tenor yang diminta |
| `vehicle` | Jenis, tahun, dan nilai taksiran jaminan |
| `bureau` | Ringkasan SLIK seperti keterlambatan maksimal dua belas bulan terakhir |
| `fraud` | Hasil verifikasi identitas, dokumen, daftar hitam, skor risiko perangkat |
| `model_outputs` | Skor kredit beserta versi modelnya |

Jawabannya memuat keputusan, kode-kode alasan, limit dan tenor yang disetujui bila ada, versi strategy yang dipakai, nomor trace, dan nomor kasus review bila kasusnya diarahkan ke manusia. Pengiriman ulang dengan kunci idempotency yang sama tidak menciptakan keputusan ganda, jadi LOS aman melakukan retry.

## 8.2 Dashboard, memantau kesehatan harian

Menu **Dashboard** menampilkan angka hari-hari, yaitu jumlah aplikasi, approval rate, reject rate, manual review rate, latency, ukuran antrean review, distribusi keputusan, kode alasan teratas, dan tren volume harian. Semuanya bisa disaring per produk dan channel.

Cara membacanya sederhana. Angka-angka ini adalah kaca depan, bukan spion. Approval rate yang bergeser lima poin tanpa ada perubahan kebijakan berarti populasi pemohonnya yang berubah, dan kode alasan teratas memberi tahu lewat pintu mana pergeserannya masuk. Selidiki sebelum menjadi kerugian.

## 8.3 Decisions, mencari keputusan lama

Menu **Decisions** adalah riwayat semua keputusan dengan saringan berikut.

| Saringan | Kegunaan |
|---|---|
| Application ID | Menjawab pertanyaan nasabah atau cabang tentang satu aplikasi |
| Decision | Melihat semua REJECT atau semua MANUAL_REVIEW |
| Product dan Channel | Menyempitkan ke segmen |
| Rentang tanggal | Investigasi periode tertentu |

Klik nomor keputusan untuk membuka detailnya, dan dari sana masuk ke trace.

## 8.4 Trace, membedah satu keputusan

Trace adalah bukti lengkap yang menjawab "kenapa hasilnya begini". Bacalah dari atas ke bawah.

1. **Kartu keputusan akhir**, berisi keputusan, grade, skor, limit, tenor, dan versi strategy. Bila kasus lari ke review, ada tautan langsung ke kasusnya.
2. **Kode alasan**, lengkap dengan pesan internalnya.
3. **Linimasa eksekusi**, yaitu node demi node sesuai urutan dilalui. Node CONDITION menampilkan hasil evaluasinya dan cabang TRUE atau FALSE yang diambil. Klik sebuah node untuk membuka rinciannya.
4. **Rincian rule**, bagian paling berharga. Setiap rule yang dievaluasi menampilkan kondisi per kondisi dengan nilai ambang berhadapan dengan nilai aktual pemohon, cabang ke berapa yang cocok bila rule-nya bercabang, dan aksi yang dijalankan termasuk output yang ditulis.
5. **Kartu outputs**, berisi nilai akhir semua output yang ditulis rule selama eksekusi.
6. **Fitur terhitung dan snapshot input**, yaitu LTV, DTI, dan kawan-kawan, plus salinan input yang datanya sensitif sudah tersamar.
7. Tautan **view flow** membuka kanvas baca-saja dari versi strategy yang dipakai, sehingga rute yang dilalui bisa dilihat sebagai gambar.

Dua hal penting soal trace. Pertama, trace tidak bisa diubah siapa pun, termasuk admin. Kedua, membuka trace pun tercatat di audit log karena isinya data sensitif.

## 8.5 Studi kasus, menjawab komplain dalam lima menit

Cabang meneruskan komplain, yaitu aplikasi A-2210 ditolak padahal menurut nasabah penghasilannya cukup.

1. Compliance membuka Decisions, menyaring dengan application ID, dan menemukan keputusannya, REJECT dengan alasan HIGH_DTI.
2. Dia membuka trace. Di rincian rule terlihat `affordability.dti` bernilai 0.51 berhadapan dengan ambang 0.45 dari rule DTI_MAX_STANDARD versi satu.
3. Di fitur terhitung terlihat sumber angkanya, yaitu kewajiban berjalan 3,2 juta ditambah estimasi cicilan baru, dibagi penghasilan 8 juta.
4. Jawaban ke nasabah menjadi konkret. Penghasilannya memang cukup untuk cicilan baru saja, tetapi total kewajiban berjalannya membuat rasio melampaui batas kebijakan. Kalau salah satu pinjaman lamanya lunas, silakan mengajukan lagi.
5. Lima menit, tanpa satu pun tebakan, dan setiap klaim didukung angka yang terekam saat keputusan dibuat.

## 8.6 Siapa memakainya

Risk Manager membuka Dashboard tiap pagi. Underwriter membaca trace sebagai bahan investigasi kasus. Compliance dan auditor memakai Decisions serta trace untuk rekonstruksi. Data scientist menambang trace sebagai sumber fitur historis yang jujur, karena nilainya persis seperti saat keputusan diambil, bukan rekonstruksi belakangan.
