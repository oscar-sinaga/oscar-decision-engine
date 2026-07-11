# Bab 09 — Manual Review, Meja Kerja Underwriter

## 9.1 Kegunaannya

Manual review adalah tempat kasus abu-abu diputus manusia. Mesin sengaja menyerah pada kasus yang datanya mepet ambang, jaminannya meragukan, atau berbau fraud, lalu menciptakan sebuah **case** yang antre di sini. Keputusan manusia kemudian tersimpan berdampingan dengan keputusan mesin, bukan menimpanya, sehingga selalu terlihat "kata sistem apa" dan "kata analis apa".

Letaknya di menu **Manual Review**.

## 9.2 Antrean dan parameternya

| Kolom atau saringan | Arti |
|---|---|
| **Status** | NEW baru lahir, ASSIGNED sudah dipegang seseorang, IN_REVIEW sedang dikerjakan, PENDING_DOCUMENTS menunggu dokumen nasabah, ESCALATED naik ke atasan, APPROVED_BY_ANALYST atau REJECTED_BY_ANALYST sudah diputus |
| **Priority** | HIGH untuk kasus fraud, MEDIUM untuk kasus review biasa. Menentukan urutan kerja |
| **SLA** | Tenggat waktu penyelesaian yang dihitung dari prioritas, empat jam untuk HIGH dan dua puluh empat jam untuk MEDIUM. Kasus yang melewati tenggat ditandai breached |
| **Assigned to** | Pemegang kasus. Tombol assign to me mengambil kasus dari antrean |

## 9.3 Halaman detail kasus

Semua bahan investigasi tersaji dalam satu layar, yaitu ringkasan pemohon, pinjaman, dan kendaraan dengan data sensitif tersamar, keputusan sistem beserta kode alasannya, tautan ke trace untuk melihat persis kenapa mesin ragu, catatan kasus, utas komentar, dan daftar dokumen.

Tiga alat kerja pendukungnya begini.

| Alat | Parameter | Kegunaan |
|---|---|---|
| **Comments** | teks bebas | Utas kronologi investigasi, misalnya "sudah telepon HRD, menunggu konfirmasi". Hanya bisa ditambah, tidak bisa dihapus |
| **Request documents** | pesan plus daftar nama dokumen | Menandai kasus PENDING_DOCUMENTS dan membuat checklist per dokumen yang bisa ditandai received atau waived satu per satu |
| **Escalate** | alasan plus tujuan eskalasi | Menaikkan kasus ke atasan atau tim lain, misalnya SENIOR_UNDERWRITER, dengan alasan tercatat |

## 9.4 Form keputusan analis dan parameternya

| Parameter | Arti | Aturan pentingnya |
|---|---|---|
| **Analyst decision** | APPROVE, APPROVE_WITH_CONDITION, REJECT, atau FRAUD_INVESTIGATION | Pilihan finalnya |
| **Approved limit** dan **approved tenor** | Angka persetujuan yang disesuaikan | Dipakai saat menyetujui dengan syarat, misalnya limit diturunkan supaya LTV masuk akal |
| **Reason code** | Kode alasan dari katalog | **Wajib untuk REJECT**, supaya penolakan manusia pun bisa diagregasi seperti penolakan mesin |
| **Override reason** | Teks alasan | **Wajib setiap kali keputusan analis berbeda dari keputusan sistem.** Inilah jejak pertanggungjawaban override |
| **Notes** | Catatan tambahan | Menempel di kasus |

Dua pagar pengaman yang perlu Anda tahu. Pertama, kasus yang sudah diputus terkunci dan tidak bisa diputus ulang. Kedua, **menyetujui kasus yang divonis FRAUD_INVESTIGATION oleh mesin membutuhkan izin override tingkat tinggi**, yang di lingkungan demo hanya dimiliki risk manager dan admin. Underwriter biasa akan ditolak sistem, dan itu disengaja karena membatalkan vonis fraud adalah tindakan paling berisiko di seluruh alur.

## 9.5 Studi kasus

Kasus CASE-0917 masuk antrean dengan keputusan sistem MANUAL_REVIEW beralasan DTI_NEAR_THRESHOLD.

1. Pak Dimas menekan assign to me. Status menjadi ASSIGNED, dan SLA-nya masih delapan belas jam lagi.
2. Dari trace dia melihat DTI pemohon 0.43, mepet ambang 0.45. Mesin ragu bukan karena datanya buruk, melainkan karena tanggung.
3. Dia meminta dokumen lewat request documents, mengetik slip gaji terbaru dan rekening tiga bulan sebagai checklist. Status menjadi PENDING_DOCUMENTS, dan dia menulis komentar kronologinya.
4. Dokumen datang, kedua item checklist ditandai received. Slip gaji menunjukkan penghasilan naik sejak data diajukan, sehingga DTI riilnya lebih rendah.
5. Dia mengisi form keputusan, yaitu APPROVE_WITH_CONDITION, limit diturunkan ke 12 juta, override reason "penghasilan terverifikasi lebih tinggi dari data pengajuan, limit disesuaikan agar rasio aman". Karena keputusannya berbeda dari usulan mesin, alasan itu memang wajib.
6. Kasus tertutup. Di halaman kasus kini terlihat dua kolom berdampingan, keputusan sistem MANUAL_REVIEW dan keputusan analis APPROVE_WITH_CONDITION, lengkap dengan siapa dan kapan. Audit log mencatat seluruh langkahnya.

## 9.6 Siapa memakainya

Underwriter adalah penghuni utamanya. Risk Manager memantau ukuran antrean dan tingkat override, karena override yang terlalu sering berarti kebijakan tidak realistis, sedangkan nol sama sekali berarti review cuma formalitas. Compliance mengambil sampel kasus override beserta alasannya. Fraud analyst mengawal kasus berprioritas HIGH.
