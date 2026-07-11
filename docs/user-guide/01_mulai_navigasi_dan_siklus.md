# Bab 01 — Mulai, Navigasi, dan Siklus Hidup yang Berlaku di Mana-mana

## 1.1 Masuk ke aplikasi

Buka `http://localhost:3000`, masukkan akun demo dari bab 00, lalu Anda mendarat di Dashboard. Menu di sisi kiri mengikuti izin akun. Sebagai contoh, akun `underwriter` tidak akan melihat tombol aktivasi strategy karena memang tidak berwenang.

## 1.2 Satu konsep yang mengunci semuanya, yaitu siklus hidup versi

Hampir semua objek kebijakan di OSCAR, baik rule, decision table, scorecard, maupun strategy, mengikuti siklus hidup yang sama. Pahami sekali di sini, maka semua bab berikutnya terasa familiar.

```
DRAFT ──submit──▶ PENDING_APPROVAL ──approve──▶ ACTIVE ──versi baru aktif──▶ RETIRED
  ▲                     │reject                                                │
  └── buat draft baru ◀─┴────────── REJECTED                    rollback ◀─────┘  (khusus strategy)
```

Aturan mainnya begini.

1. **Hanya DRAFT yang bisa diedit.** Begitu diajukan atau aktif, isinya terkunci selamanya. Ingin mengubah aturan yang sedang aktif? Buat versi baru dari versi itu, edit draftnya, lalu jalani siklusnya lagi.
2. **Pengaju dan penyetuju harus orang berbeda.** Ini prinsip maker-checker. Sistem menolak kalau Anda menyetujui usulan buatan sendiri, jadi jangan heran kalau tombol approve menolak bekerja untuk draft Anda.
3. **Khusus strategy, aktivasi menuntut bukti simulasi.** Saat mengajukan strategy, lampirkan hasil simulasi versi tersebut. Tanpa lampiran itu aktivasi ditolak dengan pesan yang jelas.
4. **Versi lama tidak pernah dihapus.** Versi yang tergantikan menjadi RETIRED dan tetap bisa dibuka, karena keputusan lama harus selalu bisa dijelaskan dengan aturan yang berlaku saat itu. Untuk strategy, versi RETIRED bahkan bisa dihidupkan kembali lewat tombol rollback dengan alasan wajib.
5. **Semua langkah tercatat otomatis** di Audit Log, mulai dari siapa membuat, siapa menyetujui, sampai alasannya.

> **Analogi.** Anggap tiap versi seperti edisi buku resep yang dicetak. Edisi yang sudah beredar tidak bisa dicoret-coret. Kalau resep berubah, terbitkan edisi baru dengan persetujuan kepala dapur, dan edisi lama tetap diarsip supaya orang tahu masakan tahun lalu dimasak dengan resep yang mana.

## 1.3 Siapa boleh apa

Tabel ini merangkum izin yang paling sering Anda butuhkan. Ingat, pembatasan ini ditegakkan server, bukan sekadar disembunyikan di layar.

| Aksi | riskanalyst | riskmanager | underwriter | compliance | datascientist | auditor | admin |
|---|---|---|---|---|---|---|---|
| Melihat keputusan dan trace | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Membuat draft rule, tabel, strategy | ✓ | ✓ | — | — | — | — | ✓ |
| Menyetujui dan mengaktifkan | — | ✓ | — | — | — | — | ✓ |
| Menjalankan simulasi | ✓ | ✓ | — | — | ✓ | — | ✓ |
| Memutus kasus manual review | — | ✓ | ✓ | — | — | — | ✓ |
| Membatalkan vonis fraud (override tingkat tinggi) | — | ✓ | — | — | — | — | ✓ |
| Membaca audit log | — | ✓ | — | ✓ | — | ✓ | ✓ |
| Mengelola model registry | — | ✓ | — | — | ✓ | — | ✓ |
| Menulis rule expression | — | — | — | — | — | — | ✓ |
| Mengelola pengguna dan peran | — | — | — | — | — | — | ✓ |

Patokan paling pasti tetap menu yang tampil setelah Anda login dengan akun tersebut, karena tampilan mengikuti izin yang sama dengan yang ditegakkan server.

## 1.4 Pola kerja yang akan terus Anda ulangi

Hampir semua pekerjaan kebijakan di OSCAR mengikuti irama lima langkah berikut.

1. **Buat atau ubah** sesuatu sebagai draft, misalnya rule baru atau versi strategy baru.
2. **Uji** lewat tombol test pada rule, atau lewat menu Simulations untuk strategy.
3. **Ajukan** dengan tombol submit for approval, sertakan lampiran simulasi kalau objeknya strategy.
4. **Minta orang lain menyetujui**, biasanya risk manager, yang membaca ringkasan dampak sebelum menekan approve.
5. **Pantau** dampaknya di Dashboard setelah aktif, dan bersiap membuat iterasi berikutnya.

## 1.5 Tiga jenis rekaman yang sering tertukar

| Rekaman | Isi | Siapa pembacanya | Di mana |
|---|---|---|---|
| **Decision trace** | Bukti lengkap satu keputusan, mulai dari input, fitur, langkah, sampai hasil | Risk, underwriter, auditor | Halaman detail keputusan |
| **Audit log** | Jejak perubahan dan tindakan, siapa mengubah apa dan kenapa | Compliance dan audit | Menu Audit Log |
| **Log teknis** | Kesehatan sistem, latency, error | Engineering | Di luar workbench |

Kalau pertanyaannya "kenapa aplikasi ini ditolak", bukalah trace. Kalau pertanyaannya "siapa yang mengubah ambang DTI bulan lalu", bukalah audit log.
