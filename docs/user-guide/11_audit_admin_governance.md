# Bab 11 — Governance, Audit Log, dan Admin

## 11.1 Antrean persetujuan

Setiap kali seseorang mengajukan versi rule, tabel, scorecard, atau strategy, lahirlah sebuah permintaan persetujuan yang antre di kartu **Pending approvals** pada halaman Admin. Penyetuju melihat objek apa yang diajukan, versi berapa, siapa pengajunya, catatan perubahannya, dan khusus strategy juga referensi simulasi yang dilampirkan.

Dua aturan yang ditegakkan mesin di sini. Pertama, pengaju tidak bisa menyetujui usulannya sendiri, dan tombol approve akan ditolak server meskipun akunnya punya izin approve. Kedua, strategy tanpa lampiran simulasi tidak bisa diaktifkan. Keduanya bukan tata krama melainkan pagar sistem.

Menolak usulan mengembalikannya dengan status REJECTED beserta alasan, dan pembuatnya bisa membuat draft baru dari sana.

## 11.2 Audit Log dan cara menyaringnya

Menu **Audit Log** memuat jejak semua tindakan yang mengubah keadaan, hanya bisa bertambah dan tidak bisa disunting siapa pun.

| Saringan | Kegunaan | Contoh pertanyaan yang dijawab |
|---|---|---|
| **Event type** | Jenis peristiwa | Semua aktivasi rule, ketik RULE_VERSION_ACTIVATED |
| **Entity type dan entity ID** | Objek tertentu | Seluruh riwayat rule DTI_MAX_STANDARD |
| **Actor** | Pelaku | Semua tindakan si `riskanalyst` bulan ini |
| **Rentang tanggal** | Periode | Perubahan kebijakan kuartal lalu |

Setiap baris bisa dibuka untuk melihat nilai **before dan after** berupa perbandingan keadaan sebelum dan sesudah, alasan yang ditulis pelaku, serta correlation ID yang menghubungkannya dengan permintaan teknisnya. Peristiwa yang tercatat bukan hanya perubahan kebijakan, melainkan juga keputusan yang dieksekusi, override analis lengkap dengan alasannya, perubahan peran pengguna, bahkan aktivitas membuka trace.

Cara pakainya sederhana. Mulailah dari pertanyaan, terjemahkan ke saringan, lalu baca before after. Untuk pertanyaan "kenapa keputusan ini begini" tempatnya bukan di sini melainkan di trace, sedangkan "siapa mengubah apa" memang di sini.

## 11.3 Admin, mengelola pengguna dan peran

Halaman **Admin** untuk pemegang izin kelola berisi tiga hal.

| Bagian | Kegunaan |
|---|---|
| **Users** | Daftar pengguna dan tombol edit roles untuk memasang atau mencabut peran. Perubahan berlaku seketika dan tercatat di audit |
| **Role permission matrix** | Peta baca-saja peran ke izin, berguna saat bertanya-tanya kenapa seseorang tidak melihat sebuah tombol |
| **Pending approvals** | Antrean persetujuan yang dibahas di atas |

Ingat bahwa peran menentukan izin, dan izin ditegakkan server. Memberi seseorang peran RISK_MANAGER berarti memberinya kuasa menyetujui kebijakan, jadi perlakukan menu ini seserius memberi kunci brankas.

## 11.4 Studi kasus, pemeriksaan audit internal

Auditor internal ingin memastikan perubahan ambang DTI kuartal lalu sah prosedurnya.

1. Dia menyaring Audit Log dengan entity ID DTI_MAX_STANDARD.
2. Terlihat rangkaian utuh, yaitu versi dua dibuat oleh riskanalyst dengan catatan perubahan, diajukan, lalu diaktifkan oleh riskmanager dengan alasan tertulis. Before after menunjukkan ambang berubah dari 0.45 menjadi 0.42.
3. Dia memeriksa pengaju dan penyetuju adalah orang berbeda. Terbukti dari kolom actor pada dua peristiwa itu.
4. Untuk strategy yang menyertainya, dia membuka permintaan persetujuannya dan menemukan referensi simulasi yang dilampirkan, lalu membuka hasil simulasinya.
5. Seluruh rantai bukti terkumpul dalam satu sesi duduk, tanpa meminta tangkapan layar atau email dari siapa pun.

## 11.5 Siapa memakainya

Risk Manager hidup di antrean persetujuan. Compliance dan auditor hidup di Audit Log. Admin memegang halaman pengguna dan peran. Analis biasanya hanya mampir untuk melihat status usulannya sendiri.
