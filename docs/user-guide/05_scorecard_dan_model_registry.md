# Bab 05 — Scorecard dan Model Registry, Tempat Model Statistik Bertemu Kebijakan

## 5.1 Latar belakang, kenapa skor tidak langsung dipakai

Model skor menghasilkan angka, misalnya 684 pada rentang 300 sampai 850. Secara teknis aturan bisa saja langsung berbunyi "skor di atas 663 boleh jalan". Tapi bayangkan akibatnya. Setiap kali data scientist merilis model baru yang distribusi skornya bergeser, **semua** aturan yang menyebut angka skor harus ditulis ulang. Sebaliknya, setiap kali tim risk ingin mengetat, mereka harus paham seluk-beluk skala skor model.

Jalan keluarnya adalah menaruh satu lapisan penerjemah di tengah, yaitu **scorecard**, yang memetakan skor menjadi **grade** seperti A sampai E lewat tabel band. Kebijakan hanya bicara grade, model hanya bicara skor, dan tabel band menjadi kontrak di antara keduanya. Risk bisa menggeser batas band tanpa menyentuh model, data scientist bisa merilis model baru tanpa menulis ulang kebijakan. Batas band itu sendiri adalah kebijakan, karena itu ia berversi dan melewati persetujuan seperti aturan lain.

Lalu kenapa perlu **Model Registry**? Karena setiap keputusan wajib bisa menjawab "model versi apa yang dipakai saat itu". Tanpa katalog resmi, jawaban itu tersebar di ingatan orang. Registry mencatat identitas tiap model beserta versinya, dan trace tiap keputusan menunjuk ke sana. Registry ini katalog dokumentasi, bukan tempat menjalankan model. Modelnya sendiri berjalan di luar, dan skornya dikirim LOS lewat payload pada bagian `model_outputs`.

## 5.2 Scorecard dan parameternya

| Parameter | Arti | Kenapa dirancang begini |
|---|---|---|
| **Code** | Nama teknis, misalnya `MOTOR_SCORECARD` | Dirujuk oleh node strategy, jadi stabil |
| **Bands** | Daftar ambang skor dan grade hasilnya, dibaca dari ambang tertinggi | Bentuk band dipilih karena persis begitulah risk berpikir, yaitu kelas-kelas risiko, bukan angka kontinu. Dibaca dari atas supaya perilakunya sama dengan cabang rule, cocok pertama menang |
| **Fallback** | Nasib alur saat skor tidak tersedia | Diatur lewat on_error pada node scorecard di strategy. Bawaannya diarahkan ke manual review beralasan SCORE_UNAVAILABLE, karena tanpa skor mesin kehilangan mata, dan kasus tanpa mata paling aman diserahkan ke manusia |

Hasil pemetaan tersedia sebagai fitur `score.value` dan `score.risk_grade` yang bisa dibaca aturan berikutnya, dan keduanya terekam di trace.

## 5.3 Model Registry dan parameternya

Letaknya di menu **Model Registry**.

| Parameter | Arti | Kenapa ada |
|---|---|---|
| **Code** dan **Version label** | Identitas model dan versinya, misalnya `MOTOR_SCORE` `V2` | Pasangannya wajib unik, dan versi lama tidak dihapus saat versi baru datang, karena keputusan lama tetap menunjuk versi lama. Menghapusnya berarti memutus jejak audit |
| **Name, Provider, Description** | Nama ramah, pembuat, ringkasan model | Dokumentasi untuk manusia, misalnya populasi pelatihan dan definisi target |
| **Metadata** | Catatan terstruktur bebas | Tempat menaruh rentang skor atau AUC saat pengembangan, supaya konteks evaluasi tidak hilang bersama orangnya |
| **Active** | Status pemakaian | Sekali lagi pensiun, bukan hapus |

## 5.4 Studi kasus, merilis model baru tanpa mengguncang kebijakan

Data scientist selesai melatih model dengan daya pisah lebih baik.

1. Dia mendaftarkan `MOTOR_SCORE` `V2` di registry, lengkap dengan deskripsi dan metadata evaluasinya.
2. Karena distribusi skor V2 bergeser, batas grade B perlu turun dari 650 ke 640. Bersama analis dia menuangkan band baru sebagai **versi scorecard baru**. Perhatikan pembagian kerjanya, model urusan data scientist, batas band urusan kebijakan.
3. Decision table tidak berubah sehuruf pun, karena tabel hanya mengenal grade. Di sinilah nilai lapisan penerjemah terasa.
4. Band baru diuji lewat simulasi massal untuk melihat pergeseran approval per grade, diajukan, disetujui manager, lalu aktif.
5. LOS mulai mengirim `model_version` V2, dan sejak itu tiap trace mencatatnya. Kelak performa V1 dan V2 bisa dibandingkan bersih, kohor per kohor, karena batas pergantiannya terdokumentasi.

## 5.5 Siapa memakainya

Data scientist adalah pemilik alaminya, dari mendaftarkan model sampai memantau band. Risk Policy Analyst mengurus versi scorecard karena batas band adalah kebijakan. Risk Manager menyetujuinya seperti kebijakan lain, dan auditor memakai registry untuk menjawab model versi apa yang berdiri di belakang sebuah keputusan.
