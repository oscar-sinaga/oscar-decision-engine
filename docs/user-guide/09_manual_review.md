# Bab 09 — Manual Review, Meja Kerja Underwriter

## 9.1 Latar belakang, mesin yang tahu batas dirinya

Otomasi penuh terdengar gagah, tetapi naif. Data tidak pernah lengkap, dunia tidak pernah rapi, dan selalu ada kasus yang angkanya tanggung. Memaksakan mesin memutus semuanya berarti memilih salah satu dari dua keburukan, yaitu terlalu galak sehingga nasabah baik tertolak, atau terlalu longgar sehingga risiko lolos. Desain yang matang justru membuat mesin **tahu kapan harus menyerah**, yaitu menangani mayoritas kasus yang jelas secara otomatis, lalu menyerahkan kasus abu-abu ke manusia lengkap dengan seluruh bahan pertimbangannya.

Manual review adalah meja penyerahan itu. Setiap keputusan MANUAL_REVIEW atau FRAUD_INVESTIGATION otomatis melahirkan sebuah **case** yang antre di sini. Ada satu keputusan desain yang penting dipahami sejak awal, yaitu keputusan manusia disimpan **berdampingan** dengan keputusan mesin, bukan menimpanya. Alasannya dua. Pertama, jejak, karena "apa kata sistem" dan "apa kata analis" sama-sama fakta yang kelak perlu dibaca. Kedua, pembelajaran, karena selisih antara keduanya adalah bahan evaluasi paling jujur untuk kebijakan maupun untuk analisnya.

Letaknya di menu **Manual Review**.

## 9.2 Antrean dan parameternya

| Hal | Arti | Kenapa dirancang begini |
|---|---|---|
| **Status** | NEW, ASSIGNED, IN_REVIEW, PENDING_DOCUMENTS, ESCALATED, lalu APPROVED_BY_ANALYST atau REJECTED_BY_ANALYST | Status memisahkan "belum dipegang" dari "sedang menunggu nasabah", supaya antrean bisa dikelola dan tidak ada kasus yang mengambang tanpa pemilik |
| **Priority** | HIGH untuk kasus fraud, MEDIUM untuk review biasa | Kasus fraud membusuk cepat, pelakunya bisa mengajukan di tempat lain hari itu juga, maka ia melompati antrean |
| **SLA** | Tenggat dari prioritas, empat jam untuk HIGH dan dua puluh empat jam untuk MEDIUM, yang lewat ditandai breached | Bagi nasabah, menunggu keputusan adalah siksaan, dan bagi bisnis, keputusan yang lama berarti nasabah lari. SLA membuat kecepatan menjadi angka yang bisa dipantau, bukan harapan |
| **Assigned to** | Pemegang kasus, ada tombol assign to me | Satu kasus satu pemilik, supaya tidak dikerjakan dua orang atau tidak dikerjakan siapa pun |

## 9.3 Halaman detail kasus

Semua bahan investigasi sengaja disajikan dalam satu layar, yaitu ringkasan pemohon, pinjaman, dan kendaraan dengan data sensitif tersamar, keputusan sistem beserta alasannya, tautan trace untuk melihat persis kenapa mesin ragu, catatan, komentar, dan dokumen. Prinsip desainnya, analis tidak boleh menghabiskan waktu berburu data ke sana kemari, karena waktunya lebih berharga untuk menimbang.

Tiga alat pendukungnya begini.

| Alat | Parameter | Kegunaan dan alasannya |
|---|---|---|
| **Comments** | teks bebas | Kronologi investigasi, misalnya sudah telepon HRD dan menunggu balasan. Hanya bisa ditambah dan tidak bisa dihapus, karena kronologi yang bisa disunting bukan kronologi |
| **Request documents** | pesan plus daftar nama dokumen | Kasus berpindah ke PENDING_DOCUMENTS dan tercipta checklist per dokumen yang bisa ditandai received atau waived. Bentuk checklist dipilih supaya jelas dokumen mana yang sudah datang, bukan sekadar catatan "minta dokumen" yang nasibnya kabur |
| **Escalate** | alasan plus tujuan | Menaikkan kasus ke jenjang berikutnya dengan alasan tercatat, karena ada kasus yang memang bukan porsi satu orang |

## 9.4 Form keputusan analis dan pagar-pagarnya

| Parameter | Arti | Kenapa ada |
|---|---|---|
| **Analyst decision** | APPROVE, APPROVE_WITH_CONDITION, REJECT, FRAUD_INVESTIGATION | Pilihan finalnya |
| **Approved limit** dan **approved tenor** | Angka persetujuan yang disesuaikan | Karena keputusan terbaik untuk kasus tanggung sering bukan ya atau tidak, melainkan ya dengan porsi lebih kecil |
| **Reason code** | Kode dari katalog, **wajib untuk REJECT** | Penolakan manusia harus sama terhitungnya dengan penolakan mesin. Tanpa kode baku, laporan penyebab penolakan bolong sebelah |
| **Override reason** | Teks alasan, **wajib setiap kali keputusan analis berbeda dari keputusan sistem** | Inilah jantung akuntabilitas override. Membolehkan manusia mengoreksi mesin itu sehat, membolehkannya tanpa alasan tertulis itu pintu belakang. Kalimat "katanya dulu disetujui pak anu" tidak pernah lagi terjadi karena semuanya berjejak |
| **Notes** | Catatan tambahan | Menempel di kasus |

Dua pagar lagi yang perlu diketahui. Kasus yang sudah diputus **terkunci**, tidak bisa diputus ulang, karena keputusan yang bisa diganti-ganti bukan keputusan. Dan **membatalkan vonis FRAUD_INVESTIGATION membutuhkan izin override tingkat tinggi**, di lingkungan demo hanya risk manager dan admin. Latar belakangnya, meloloskan kasus yang dicurigai fraud adalah tindakan paling berisiko di seluruh alur, dan keputusan seberisiko itu pantas naik satu jenjang wewenang. Underwriter biasa yang mencobanya akan ditolak server, bukan sekadar dilarang di aturan tertulis.

## 9.5 Studi kasus

Kasus CASE-0917 masuk dengan keputusan sistem MANUAL_REVIEW beralasan DTI_NEAR_THRESHOLD.

Pak Dimas menekan assign to me, dan SLA-nya masih delapan belas jam. Dari trace ia tahu persis sumber keraguan mesin, yaitu DTI 0.43 yang mepet ambang 0.45. Ia meminta dokumen lewat checklist berisi slip gaji terbaru dan rekening tiga bulan, mencatat kronologinya di komentar, dan kasus menunggu di PENDING_DOCUMENTS. Dokumen tiba, kedua item ditandai received, dan slip gaji menunjukkan penghasilan sudah naik sejak pengajuan sehingga DTI riilnya lebih rendah. Ia mengisi form, APPROVE_WITH_CONDITION dengan limit diturunkan ke 12 juta, dan karena putusannya berbeda dari usulan mesin, kolom override reason wajib diisi, "penghasilan terverifikasi lebih tinggi dari data pengajuan, limit disesuaikan agar rasio aman". Kasus tertutup, dan di halamannya kini berdiri dua kolom berdampingan, kata sistem MANUAL_REVIEW, kata analis APPROVE_WITH_CONDITION, lengkap dengan siapa dan kapan.

## 9.6 Siapa memakainya

Underwriter adalah penghuninya. Risk Manager memantau ukuran antrean dan angka override, karena override yang terlalu sering berarti kebijakan tidak realistis, sedangkan nol sama sekali berarti review hanya formalitas. Compliance mengambil sampel override beserta alasannya, dan fraud analyst mengawal kasus berprioritas tinggi.
