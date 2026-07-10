# Bab 7 — Anda, Data Scientist, di Ekosistem Credit Risk & Decision Engine

Bab ini khusus menjembatani dunia yang sudah Anda kuasai (model, data, evaluasi) dengan dunia kebijakan kredit — dan menunjukkan di mana persisnya pekerjaan Anda "menempel" pada decision engine.

## 7.1 Kalimat paling penting di bab ini

> **Model memprediksi; kebijakan memutuskan.**

Model Anda menjawab: *"berapa peluang orang ini gagal bayar?"* (PD). Ia **tidak pernah** menjawab: *"jadi, kita terima atau tidak?"* — karena jawaban itu tergantung hal-hal di luar model: risk appetite perusahaan, batas regulasi (umur minimal, larangan segmen tertentu), strategi bisnis (lagi ekspansi atau mengerem), kondisi pendanaan, bahkan etika. Semua itu hidup sebagai **kebijakan** di decision engine, membungkus model Anda — istilahnya *policy overlay*.

> **Analogi:** Anda ahli meteorologi. Model Anda bilang "besok 70% hujan". Keputusan "acara kantor tetap outdoor atau pindah indoor?" tetap di tangan panitia — mempertimbangkan biaya pindah, tamu VIP, tenda cadangan. Prakiraan terbaik pun bukan keputusan. Dan sebaliknya: panitia yang mengabaikan prakiraan adalah panitia yang buruk. **Keduanya saling butuh.**

Konsekuensi praktis yang harus Anda terima dengan lapang dada: pemohon dengan skor model bagus bisa tetap ditolak (kena rule umur/blacklist/LTV), dan sebagian pemohon skor jelek tetap masuk ke manusia (manual review), bukan auto-reject. Itu bukan "model saya tidak dihargai" — itu sistem bekerja sebagaimana didesain.

## 7.2 Ke mana model Anda masuk ke mesin: scorecard & model registry

Alurnya di OSCAR (dan umumnya engine lain):

1. Anda melatih model PD (logistic regression / GBM / scorecard klasik WoE) → menghasilkan **skor** (mis. 300–850).
2. Skor masuk ke engine lewat payload (`model_outputs.credit_score`, `model_version`) atau — nanti — dipanggil dari model service.
3. Komponen **scorecard** di engine memetakan skor → **grade** (A/B/C/D/E) lewat tabel band yang *berversi*. Grade inilah bahasa yang dipakai kebijakan ("grade B dengan DTI ≤ 0.40 → approve").
4. **Model registry** mencatat identitas & versi model (MOTOR_SCORE_V1, provider, deskripsi, metadata mis. AUC saat development). Setiap keputusan men-trace versi model yang dipakai.

Kenapa pemisahan skor→grade ini bagus untuk Anda: risk bisa menggeser batas band (kebijakan) **tanpa menyentuh model Anda**, dan Anda bisa merilis model baru **tanpa menulis ulang kebijakan** — selama skala skornya terjaga. Kontrak yang bersih di antara dua dunia.

## 7.3 Cutoff: titik temu paling panas antara Anda dan bisnis

Model memberi *ranking*; **cutoff** menentukan nasib. Dan cutoff adalah keputusan bisnis berbasis analisis Anda:

1. Anda menyajikan **tabel per band skor**: volume, bad rate historis, margin.
2. Bisnis memilih titik potong = memilih trade-off (bab 1 & 6.3): cutoff turun → volume naik + bad rate naik.
3. Analisis **swap set** (siapa bertukar nasib) adalah kontribusi khas DS: bukan "approval naik 7 pp" tapi "7 pp tambahan itu berisi siapa, dan seburuk apa".
4. Ingat opsi non-biner: band skor marginal tidak harus ditolak — bisa diterima dengan limit kecil/DP besar (kebijakan bertingkat per band). Sarankan ini; bisnis menyukainya.

**Batch simulation di OSCAR = alat backtest Anda**: jalankan kebijakan kandidat (cutoff/band baru) atas ribuan aplikasi historis, dapatkan pergeseran keputusan per segmen — *sebelum* satu rupiah pun dipertaruhkan.

## 7.4 Umpan balik yang lambat & bias yang menjebak: dua jebakan klasik

**Jebakan 1 — label datang terlambat.** Kredit macet butuh 6–24 bulan untuk "matang". Model yang Anda latih hari ini memakai keputusan 1–2 tahun lalu. Definisikan target dengan sadar (mis. *ever 90+ DPD dalam 12 bulan pertama* — "bad"), dan pahami *vintage analysis*: kualitas dinilai per kohor bulan pencairan, seperti menilai kopi per musim panen.

**Jebakan 2 — reject inference / selection bias.** Data outcome hanya ada untuk yang **diterima**. Yang ditolak tidak pernah menghasilkan label — padahal model berikutnya akan dipakai menilai populasi *pengaju*, bukan populasi *penerima*. Ini bias seleksi struktural di credit scoring. Mitigasi yang lazim: teknik reject inference, memantau karakteristik populasi pengaju vs penerima, dan sesekali kebijakan menyisakan "jendela belajar" terkontrol. Minimal: **sadari** bahwa metrik validasi pada data penerima ≠ performa di populasi nyata.

**Bonus jebakan 3 — feedback loop kebijakan.** Kalau kebijakan menolak semua DTI > 45%, data training baru tidak punya sampel DTI tinggi → model "lupa" area itu → jangan artikan absennya bad di DTI tinggi sebagai amannya DTI tinggi.

## 7.5 Monitoring model: pekerjaan Anda tidak selesai saat deploy

| Yang dipantau | Alat/metrik | Sinyal bahaya |
|---|---|---|
| **Populasi bergeser?** (drift input) | PSI/CSI per fitur & per skor band | PSI > 0.25 = populasi sudah bukan yang dulu dilatih |
| **Daya pisah masih ada?** | Gini/AUC/KS pada kohor yang sudah matang | Gini turun bertahap = model menua |
| **Kalibrasi masih benar?** | bad rate aktual per band vs prediksi | Band B berperilaku seperti band D |
| **Skor dipakai wajar?** | distribusi skor masuk, approval per band, override rate pada band tinggi | Override tinggi di skor bagus = kebijakan & model "bertengkar" |

Decision engine mempermudah semua ini karena **setiap keputusan men-trace fitur & skor persis saat keputusan** (bukan rekonstruksi ex-post yang rawan *training-serving skew*), plus dashboard distribusi bawaan. Trace = *feature store historis* gratis untuk Anda.

## 7.6 Interpretabilitas bukan hiasan

Di domain ini, "kenapa ditolak?" harus dijawab per-kasus (reason code), dan regulator menuntut model yang dapat dipertanggungjawabkan. Praktiknya: scorecard/GLM yang transparan masih sangat dominan untuk keputusan final; model kompleks (GBM/NN) sering ditempatkan sebagai *challenger* atau untuk kasus non-keputusan (prioritisasi, deteksi fraud) — atau dipakai dengan kerangka explainability yang disepakati. Ketika skor Anda memicu penolakan, engine-lah yang menerjemahkannya menjadi reason code baku (mis. LOW_CREDIT_SCORE) — desainlah band & alasan bersama tim policy.

## 7.7 Siklus kolaborasi DS ↔ Policy (ritme kerja nyata)

```
 Anda (DS)                                   Tim Policy/Risk
 ─────────                                   ────────────────
 latih model → usul band & cutoff  ───────▶  bungkus jadi scorecard + rules (versi baru)
                                             simulasi dampak (batch) ◀── Anda bantu baca hasilnya
                                             maker-checker → aktivasi
 pantau drift/Gini/kalibrasi  ◀───────────  pantau approval/override/reason codes
        └────────── temuan dua arah memicu iterasi berikutnya ──────────┘
```

Pertemuan rutin yang sehat membahas: PSI naik di fitur X (Anda) + reason code Y melonjak (mereka) → hipotesis bersama → uji di simulasi → putuskan.

## 7.8 Peta fitur OSCAR ↔ kebutuhan Anda

| Kebutuhan DS | Fitur OSCAR |
|---|---|
| Menyalurkan skor ke keputusan | Scorecard (band berversi) + payload `model_outputs` |
| Melacak versi model di tiap keputusan | Model registry + trace |
| Backtest kebijakan/cutoff | Batch simulation (policy impact analysis) |
| Dataset fitur historis yang jujur | Decision trace (snapshot fitur saat keputusan) |
| Memantau distribusi & override | Dashboard monitoring + audit log |
| Eksperimen aturan turunan fitur | Feature catalog + (Phase 3) rules yang menghasilkan nilai |

## 7.9 Rangkuman bab

1. **Model memprediksi, kebijakan memutuskan** — Anda memasok komponen paling tajam, engine membungkusnya dengan akuntabilitas.
2. Titik sambung Anda: **skor → scorecard (band berversi) → kebijakan**; identitas model dijaga registry & trace.
3. Kontribusi analitik khas DS: **cutoff & swap set**, dibaca lewat batch simulation.
4. Waspadai tiga jebakan: **label lambat, reject inference, feedback loop kebijakan**.
5. Pasca-deploy: pantau **PSI, Gini, kalibrasi, override** — trace engine adalah sumber data terbersih Anda.
