# Bab 05 — Scorecard dan Model Registry, Tempat Model Statistik Bertemu Kebijakan

## 5.1 Kegunaannya

Model skor menghasilkan angka, misalnya 684 pada rentang 300 sampai 850. Angka mentah sulit dipakai kebijakan, karena itu **scorecard** menerjemahkannya menjadi **grade** seperti A sampai E lewat tabel band. Grade inilah bahasa yang dipakai rule dan decision table. Sementara itu **Model Registry** adalah katalog identitas model, mencatat model apa saja yang dikonsumsi mesin beserta versinya, supaya setiap keputusan bisa menunjuk model versi mana yang dipakainya.

Pemisahan ini disengaja dan menguntungkan dua pihak. Tim risk bisa menggeser batas band tanpa menyentuh model, dan data scientist bisa merilis model baru tanpa menulis ulang kebijakan.

## 5.2 Scorecard dan parameternya

Scorecard dikelola lewat versi seperti objek lain. Isinya sederhana, yaitu daftar band.

| Parameter | Arti | Contoh |
|---|---|---|
| **Code** | Nama teknis scorecard | `MOTOR_SCORECARD` |
| **Bands** | Daftar ambang skor dan grade hasilnya, dibaca dari ambang tertinggi | min_score 720 berarti grade A, 650 grade B, 580 grade C, 520 grade D, sisanya E |
| **Fallback** | Perilaku saat skor tidak tersedia di payload | Mengikuti pengaturan on_error node scorecard di strategy, umumnya diarahkan ke manual review dengan alasan SCORE_UNAVAILABLE |

Hasil pemetaan tersedia sebagai fitur `score.value` dan `score.risk_grade` yang bisa dibaca aturan berikutnya, dan keduanya terekam di trace.

Dari mana skornya datang? Pada penyiapan saat ini skor dikirim LOS di payload pada bagian `model_outputs`, berisi `credit_score` dan `model_version`. Mesin tinggal memetakan dan mencatat.

## 5.3 Model Registry dan parameternya

Letaknya di menu **Model Registry**. Ini katalog dokumentasi dan siklus hidup, bukan tempat menjalankan model.

| Parameter | Arti | Contoh |
|---|---|---|
| **Code** | Identitas model | `MOTOR_SCORE` |
| **Version label** | Versi yang didaftarkan | `V1` |
| **Name** | Nama ramah | Motor Leaseback Credit Score |
| **Provider** | Pembuatnya | INTERNAL atau nama vendor |
| **Description** | Ringkasan model | Populasi pelatihan, definisi target |
| **Metadata** | Catatan bebas terstruktur | Misalnya rentang skor atau AUC saat pengembangan |
| **Active** | Status pemakaian | Retire saat versi baru menggantikan |

Kombinasi code dan version label harus unik. Mendaftarkan `MOTOR_SCORE` `V2` tidak menghapus `V1`, dan itu memang intinya, karena keputusan lama tetap menunjuk V1.

## 5.4 Studi kasus

Data scientist selesai melatih model baru dengan daya pisah lebih baik.

1. Dia mendaftarkan `MOTOR_SCORE` `V2` di Model Registry lengkap dengan deskripsi dan metadata evaluasinya.
2. Bersama policy analyst dia meninjau band. Karena distribusi skor V2 bergeser, batas grade B perlu turun dari 650 menjadi 640. Analis membuat versi scorecard baru dengan band tersebut.
3. Kebijakan di decision table tidak berubah sama sekali, karena tabel hanya mengenal grade.
4. Perubahan diuji lewat simulasi massal untuk melihat pergeseran approval per grade, diajukan, disetujui manager, lalu aktif.
5. LOS mulai mengirim `model_version` V2. Sejak itu setiap trace mencatat V2, sehingga performa V1 dan V2 bisa dibandingkan bersih di kemudian hari.

## 5.5 Siapa memakainya

Data scientist adalah pemilik alaminya, dari mendaftarkan model sampai memantau band. Risk Policy Analyst mengurus versi scorecard karena batas band adalah kebijakan. Risk Manager menyetujui perubahan band seperti kebijakan lain. Auditor memakai registry untuk menjawab model versi apa yang dipakai keputusan tertentu.
