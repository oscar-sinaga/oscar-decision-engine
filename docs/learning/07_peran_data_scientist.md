# Bab 7 — Anda, Data Scientist, di Ekosistem Credit Risk dan Decision Engine

Bab ini khusus menjembatani dunia yang sudah Anda kuasai, yaitu model, data, dan evaluasi, dengan dunia kebijakan kredit. Tujuannya menunjukkan di titik mana persisnya pekerjaan Anda menempel pada decision engine.

## 7.1 Kalimat paling penting di bab ini

> **Model memprediksi, kebijakan memutuskan.**

Model Anda menjawab pertanyaan berapa peluang seseorang gagal bayar, alias PD. Model tidak pernah menjawab pertanyaan apakah orang itu kita terima atau tidak. Jawaban yang kedua bergantung pada hal-hal di luar model, misalnya selera risiko perusahaan, batas regulasi seperti umur minimal dan larangan segmen tertentu, strategi bisnis yang sedang ekspansi atau justru mengerem, kondisi pendanaan, bahkan pertimbangan etika. Semua itu hidup sebagai kebijakan di decision engine dan membungkus model Anda. Istilah kerennya policy overlay.

> **Analogi.** Anda ahli prakiraan cuaca. Model Anda berkata besok ada 70% kemungkinan hujan. Keputusan apakah acara kantor tetap di luar ruangan atau pindah ke dalam tetap ada di tangan panitia, yang menimbang biaya pindah, tamu penting, dan ketersediaan tenda. Prakiraan sebagus apa pun bukanlah keputusan. Sebaliknya juga benar, panitia yang mengabaikan prakiraan adalah panitia yang buruk. Keduanya saling membutuhkan.

Ada konsekuensi praktis yang perlu Anda terima dengan lapang dada. Pemohon dengan skor bagus bisa tetap ditolak karena terkena aturan umur, daftar hitam, atau LTV. Sebagian pemohon berskor jelek pun tidak langsung ditolak otomatis, melainkan diarahkan ke manual review. Itu bukan berarti model Anda tidak dihargai. Itu artinya sistem bekerja sebagaimana dirancang.

## 7.2 Ke mana model Anda masuk, yaitu lewat scorecard dan model registry

Beginilah alurnya di OSCAR, dan umumnya juga di engine lain.

1. Anda melatih model PD, entah logistic regression, GBM, atau scorecard klasik berbasis WoE, dan hasil akhirnya berupa skor, misalnya pada rentang 300 sampai 850.
2. Skor itu masuk ke engine lewat payload, tepatnya `model_outputs.credit_score` beserta `model_version`, atau nantinya dipanggil langsung dari model service.
3. Komponen scorecard di engine memetakan skor menjadi grade, misalnya A sampai E, lewat tabel band yang berversi. Grade inilah bahasa yang dipakai kebijakan, misalnya "grade B dengan DTI di bawah 0.40 disetujui".
4. Model registry mencatat identitas dan versi model, misalnya MOTOR_SCORE_V1 beserta pembuat dan metadatanya. Setiap keputusan lalu men-trace versi model yang dipakai.

Pemisahan skor dan grade ini menguntungkan Anda. Tim risk bisa menggeser batas band, yang merupakan urusan kebijakan, tanpa menyentuh model Anda. Sebaliknya Anda bisa merilis model baru tanpa menulis ulang kebijakan, selama skala skornya terjaga. Ini kontrak yang bersih antara dua dunia.

## 7.3 Cutoff, titik temu paling panas antara Anda dan bisnis

Model memberi urutan alias ranking, sedangkan cutoff yang menentukan nasib. Dan cutoff adalah keputusan bisnis yang berbasis analisis Anda.

1. Anda menyajikan tabel per band skor, berisi volume, bad rate historis, dan margin.
2. Bisnis memilih titik potong, yang artinya memilih posisi di tarik-menarik bab 1 dan bab 6. Cutoff turun berarti volume naik sekaligus bad rate naik.
3. Analisis swap set, yaitu siapa saja yang bertukar nasib, adalah sumbangan khas seorang data scientist. Bukan sekadar "approval naik tujuh poin", melainkan "tujuh poin tambahan itu berisi siapa saja, dan seburuk apa mereka".
4. Ingat juga pilihan yang tidak biner. Band skor yang tanggung tidak harus ditolak, karena bisa diterima dengan limit kecil atau uang muka besar. Kebijakan bertingkat per band semacam ini biasanya disukai bisnis, jadi jangan ragu mengusulkannya.

Batch simulation di OSCAR pada dasarnya adalah alat backtest Anda. Jalankan kebijakan kandidat, misalnya cutoff atau band baru, terhadap ribuan aplikasi historis, dan dapatkan pergeseran keputusan per segmen sebelum satu rupiah pun dipertaruhkan.

## 7.4 Dua jebakan klasik, ditambah satu bonus

**Jebakan pertama, label datang terlambat.** Kredit macet butuh enam sampai dua puluh empat bulan untuk "matang". Model yang Anda latih hari ini memakai keputusan satu sampai dua tahun lalu. Karena itu definisikan target dengan sadar, misalnya "pernah menunggak 90 hari atau lebih dalam dua belas bulan pertama" sebagai definisi bad. Pahami juga vintage analysis, yaitu menilai kualitas per kohor bulan pencairan, mirip menilai kopi per musim panen.

**Jebakan kedua, reject inference alias bias seleksi.** Data outcome hanya ada untuk pemohon yang diterima. Pemohon yang ditolak tidak pernah menghasilkan label, padahal model berikutnya akan dipakai menilai populasi pengaju, bukan populasi penerima. Ini bias seleksi yang melekat secara struktural di credit scoring. Mitigasi yang lazim antara lain teknik reject inference, pemantauan karakteristik populasi pengaju dibanding penerima, dan sesekali kebijakan menyisakan "jendela belajar" yang terkontrol. Paling minimal, sadarilah bahwa metrik validasi pada data penerima tidak sama dengan performa di populasi yang sebenarnya.

**Bonus, jebakan ketiga berupa feedback loop kebijakan.** Kalau kebijakan menolak semua DTI di atas 45%, data training yang baru tidak akan punya sampel DTI tinggi, sehingga model perlahan "lupa" area itu. Jangan pernah mengartikan tidak adanya kasus macet di DTI tinggi sebagai bukti bahwa DTI tinggi itu aman.

## 7.5 Monitoring model, karena pekerjaan Anda tidak selesai saat deploy

| Yang dipantau | Alat atau metrik | Sinyal bahaya |
|---|---|---|
| Populasinya bergeser atau tidak | PSI atau CSI per fitur dan per band skor | PSI di atas 0.25 berarti populasi sudah bukan yang dulu dilatih |
| Daya pisahnya masih ada atau tidak | Gini, AUC, atau KS pada kohor yang sudah matang | Gini yang turun bertahap berarti model menua |
| Kalibrasinya masih benar atau tidak | Bad rate aktual per band dibanding prediksi | Band B yang berperilaku seperti band D |
| Skornya dipakai wajar atau tidak | Distribusi skor masuk, approval per band, dan override rate pada band tinggi | Override yang tinggi di skor bagus berarti kebijakan dan model sedang "bertengkar" |

Decision engine mempermudah semua ini karena setiap keputusan men-trace fitur dan skor persis pada saat keputusan diambil, bukan hasil rekonstruksi belakangan yang rawan selisih antara data training dan data produksi. Dashboard distribusi juga sudah tersedia. Boleh dibilang, trace adalah feature store historis gratis untuk Anda.

## 7.6 Interpretabilitas bukan hiasan

Di domain ini, pertanyaan "kenapa saya ditolak" harus terjawab kasus per kasus lewat reason code, dan regulator menuntut model yang bisa dipertanggungjawabkan. Dalam praktiknya, scorecard dan model linear yang transparan masih sangat dominan untuk keputusan akhir. Model yang kompleks seperti GBM atau neural network lebih sering ditempatkan sebagai challenger, atau dipakai untuk keperluan di luar keputusan akhir seperti prioritisasi dan deteksi fraud, atau dipakai dengan kerangka explainability yang disepakati. Ketika skor Anda memicu penolakan, engine-lah yang menerjemahkannya menjadi reason code baku, misalnya LOW_CREDIT_SCORE. Karena itu rancanglah band dan alasannya bersama tim policy.

## 7.7 Ritme kolaborasi antara data scientist dan tim policy

```
 Anda (DS)                                   Tim Policy/Risk
 ─────────                                   ────────────────
 melatih model, mengusulkan band dan cutoff ▶ membungkusnya jadi scorecard dan rules (versi baru)
                                             menyimulasikan dampak ◀ Anda membantu membaca hasilnya
                                             maker-checker, lalu aktivasi
 memantau drift, Gini, kalibrasi   ◀───────  memantau approval, override, reason codes
        └──────── temuan dari dua arah memicu iterasi berikutnya ────────┘
```

Pertemuan rutin yang sehat biasanya membahas dua temuan sekaligus. Anda datang membawa "PSI naik di fitur X", mereka datang membawa "reason code Y melonjak". Dari situ lahir hipotesis bersama, diuji lewat simulasi, lalu diputuskan.

## 7.8 Peta kebutuhan Anda dan fitur OSCAR yang menjawabnya

| Kebutuhan Anda | Fitur OSCAR |
|---|---|
| Menyalurkan skor ke keputusan | Scorecard dengan band berversi, plus payload `model_outputs` |
| Melacak versi model di tiap keputusan | Model registry dan trace |
| Backtest kebijakan atau cutoff | Batch simulation alias policy impact analysis |
| Dataset fitur historis yang jujur | Decision trace, karena berisi snapshot fitur saat keputusan |
| Memantau distribusi dan override | Dashboard monitoring dan audit log |
| Bereksperimen dengan aturan turunan fitur | Feature catalog, dan setelah Phase 3, rules yang bisa menghasilkan nilai |

## 7.9 Rangkuman bab

1. Model memprediksi, kebijakan memutuskan. Anda memasok komponen yang paling tajam, sedangkan engine membungkusnya dengan akuntabilitas.
2. Titik sambung Anda adalah skor yang masuk ke scorecard dengan band berversi, lalu dipakai kebijakan. Identitas model dijaga oleh registry dan trace.
3. Sumbangan analitik khas Anda adalah analisis cutoff dan swap set, yang dibaca lewat batch simulation.
4. Waspadai tiga jebakan, yaitu label yang terlambat, reject inference, dan feedback loop kebijakan.
5. Setelah deploy, pantau PSI, Gini, kalibrasi, dan override. Trace dari engine adalah sumber data terbersih Anda.
