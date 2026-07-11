# Bab 11 — Governance, Audit Log, dan Admin

## 11.1 Latar belakang, kepercayaan yang tidak bergantung pada orang baik

Semua layar di bab ini menjawab satu pertanyaan yang sama, yaitu bagaimana sebuah sistem yang mengubah nasib finansial ribuan orang bisa dipercaya. Jawaban yang naif adalah "percayalah pada orang-orangnya". Jawaban yang matang adalah membangun sistem yang tetap aman **bahkan ketika** orangnya lelah, khilaf, atau nakal. Tiga mekanismenya adalah persetujuan berlapis, jejak yang tidak bisa disunting, dan pembagian kekuasaan lewat peran.

## 11.2 Antrean persetujuan

Setiap pengajuan versi, entah rule, tabel, scorecard, maupun strategy, melahirkan permintaan persetujuan yang antre di kartu **Pending approvals** pada halaman Admin. Penyetuju melihat objeknya, versinya, pengajunya, catatan perubahan, dan khusus strategy juga referensi simulasi yang dilampirkan.

Dua pagar ditegakkan mesin di sini, dan keduanya sudah Anda kenal dari bab 01. Pengaju tidak bisa menyetujui usulannya sendiri, meskipun akunnya punya izin approve, karena kebijakan kredit tidak boleh diputuskan sepasang tangan. Dan strategy tanpa lampiran simulasi tidak bisa diaktifkan, karena penyetuju berhak atas bukti dampak. Menolak usulan mengembalikannya sebagai REJECTED beserta alasan, dan pengaju bisa memulai draft baru dari sana. Perhatikan bahwa penolakan pun berjejak, karena "usulan yang pernah ditolak dan kenapa" adalah pengetahuan organisasi yang berharga.

## 11.3 Audit Log dan cara menyaringnya

Menu **Audit Log** memuat jejak semua tindakan yang mengubah keadaan. Sifatnya hanya bisa bertambah, dan tidak seorang pun bisa menyunting isinya, termasuk admin. Alasannya sudah disinggung berkali-kali, yaitu bukti yang bisa disunting bukan bukti. Koreksi atas kesalahan dicatat sebagai peristiwa baru, seperti jurnal balik di akuntansi, dan keduanya tetap terbaca.

| Saringan | Menjawab pertanyaan |
|---|---|
| **Event type** | Semua peristiwa sejenis, misalnya seluruh aktivasi rule |
| **Entity type dan entity ID** | Seluruh riwayat satu objek, misalnya rule DTI_MAX_STANDARD dari lahir sampai kini |
| **Actor** | Semua tindakan satu orang dalam suatu masa |
| **Rentang tanggal** | Perubahan pada periode tertentu |

Setiap baris bisa dibuka untuk melihat nilai **before dan after**, alasan yang ditulis pelaku, dan correlation ID yang menghubungkannya dengan permintaan teknisnya. Yang tercatat bukan hanya perubahan kebijakan, melainkan juga keputusan yang dieksekusi, override analis beserta alasannya, perubahan peran pengguna, sampai **aktivitas membuka trace**. Yang terakhir itu sering mengejutkan orang baru, kenapa membaca saja dicatat. Karena trace berisi data pribadi pemohon, dan di dunia data pribadi, siapa melihat apa adalah pertanyaan audit yang sah.

Cara memakainya sederhana. Mulai dari pertanyaan, terjemahkan ke saringan, baca before after. Dan ingat pembagian tugasnya, pertanyaan "kenapa keputusan ini begini" dijawab trace, pertanyaan "siapa mengubah apa" dijawab di sini.

## 11.4 Admin, mengelola pengguna dan peran

Halaman **Admin** berisi tiga bagian, yaitu daftar pengguna dengan tombol edit roles, matriks peran ke izin yang sifatnya baca-saja, dan antrean persetujuan yang dibahas di atas.

Kenapa izin dikemas sebagai **peran**, bukan diberikan satu per satu? Karena izin lepasan cepat menjadi belantara yang tidak bisa diaudit. Peran seperti RISK_MANAGER adalah paket izin yang maknanya dipahami organisasi, mudah diperiksa, dan mudah dicabut utuh ketika orangnya pindah tugas. Perubahan peran berlaku seketika dan tercatat di audit. Perlakukan menu ini seserius menyerahkan kunci brankas, karena memberi peran manager sama artinya memberi kuasa menyetujui kebijakan.

Matriks baca-saja di sebelahnya kelihatan sepele tetapi sering menyelamatkan waktu, yaitu ketika seseorang bertanya kenapa dia tidak melihat sebuah tombol, jawabannya hampir selalu ada di matriks itu.

## 11.5 Studi kasus, pemeriksaan audit internal

Auditor ingin memastikan perubahan ambang DTI kuartal lalu sah prosedurnya.

Dia menyaring Audit Log dengan entity ID DTI_MAX_STANDARD dan mendapat rangkaian utuh, versi dua dibuat riskanalyst dengan catatan perubahan, diajukan, lalu diaktifkan riskmanager dengan alasan tertulis, dan before after menunjukkan ambang bergeser dari 0.45 ke 0.42. Kolom actor membuktikan pengaju dan penyetuju orang berbeda. Untuk strategy pengiringnya, dia membuka permintaan persetujuan dan menemukan referensi simulasi yang dilampirkan, lalu membuka hasil simulasinya. Seluruh rantai bukti terkumpul dalam satu sesi duduk, tanpa meminta tangkapan layar atau menelusuri email siapa pun. Itulah perbedaan antara tata kelola yang diklaim dan tata kelola yang bisa dibuktikan.

## 11.6 Siapa memakainya

Risk Manager hidup di antrean persetujuan. Compliance dan auditor hidup di Audit Log. Admin memegang pengguna dan peran, dan analis biasanya hanya mampir melihat status usulannya sendiri.
