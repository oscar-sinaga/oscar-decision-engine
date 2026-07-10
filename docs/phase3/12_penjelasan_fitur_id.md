# Penjelasan Fitur Phase 3 — Bahasa Sehari-hari

> Dokumen ini **bukan** spesifikasi teknis — ini penjelasan untuk memahami *apa* yang dibangun di Phase 3, *kenapa* dibangun, dan *bagaimana rasanya* dipakai, lengkap dengan analogi dan contoh kasus. Spesifikasi teknis yang mengikat tetap file `01`–`11` di folder ini.

---

## Gambaran besar: dari "satpam" menjadi "komite kredit"

**OSCAR hari ini** ibarat gedung yang dijaga satu satpam di pintu. Setiap pemohon datang, satpam mengecek daftar aturan, lalu hanya bisa bilang tiga hal: *"silakan masuk"* (APPROVE), *"maaf, tidak bisa"* (REJECT), atau *"tunggu, saya panggil atasan"* (MANUAL_REVIEW). Semua aturan ujungnya adalah **keputusan final**.

**OSCAR setelah Phase 3** ibarat **komite kredit** sungguhan:

- Ada **analis-analis spesialis** (rules) yang masing-masing menulis *penilaian* di catatan: "risiko agunan: TINGGI", "harga wajar kendaraan: 15 juta", "band usia kendaraan: TUA". Mereka **tidak memutuskan** — mereka menghasilkan **nilai**.
- Ada **ketua komite** (decision table / langkah akhir) yang membaca semua catatan itu dan **baru dia yang memutuskan**: approve, reject, atau review.
- Ada **denah alur rapat** (decision flow berbentuk graph) yang bisa **bercabang**: "kalau ada indikasi fraud, bawa dulu ke pemeriksaan mendalam; kalau bersih, jalur cepat" — dan kedua jalur bisa bertemu lagi di meja scoring.
- Semua orang bekerja dengan **formulir dan papan perencanaan visual**, bukan menulis kode/JSON.

Itulah inti Phase 3. Sekarang kita bedah satu per satu.

---

## 1. Rule Model v2 — aturan yang bisa "menghitung", bukan cuma "memvonis"

### Masalah sekarang
Setiap rule OSCAR bentuknya kaku: `JIKA kondisi terpenuhi → keputusan + kode alasan`. Padahal di dunia nyata, banyak kebijakan bentuknya **bertingkat** dan hasilnya **angka/kategori**, bukan vonis.

### Yang dibangun
Rule bisa punya **banyak cabang WHEN … THEN … dan satu ELSE** (persis pola CASE WHEN di iDecision), dan tiap cabang bisa menjalankan **lebih dari satu aksi**.

### Analogi: tarif parkir bertingkat
Papan tarif parkir tidak berbunyi "boleh parkir / tidak boleh parkir". Bunyinya:

> Jam pertama: Rp5.000 · Jam ke-2 s/d ke-4: Rp3.000/jam · Selebihnya: Rp2.000/jam

Itu adalah **satu aturan** dengan **banyak cabang** yang menghasilkan **angka** — bukan keputusan. Rule v2 memungkinkan analis menulis aturan seperti papan tarif ini.

### Contoh kasus (persis contoh iDecision "AR balance")
Bu Rani (Risk Policy Analyst) ingin menentukan **band harga kendaraan yang layak** berdasarkan saldo tabungan pemohon:

| Kondisi | Hasil |
|---|---|
| saldo > 50 juta | band harga = 20.000 |
| saldo > 10 juta | band harga = 15.000 |
| saldo > 5 juta | band harga = 10.000 |
| selain itu (ELSE) | band harga = 0 |

Di OSCAR lama ini **tidak bisa dibuat** (rule tidak bisa menghasilkan angka). Di Phase 3, Bu Rani membuat satu rule jenis **STATEMENT** dengan 3 cabang + ELSE, hasilnya ditulis ke output `outputs.vehicle_price_band`. Evaluasinya **first-match**: cabang dicek dari atas; yang pertama cocok, itulah yang dipakai — persis cara kita membaca papan tarif.

### Bonus: satu cabang bisa beberapa aksi
Contoh: "JIKA DTI > 40% → tulis `affordability_risk = HIGH` **DAN** tambahkan kode alasan DTI_NEAR_THRESHOLD". Dulu harus dua rule; sekarang satu.

---

## 2. Output Catalog — "kolom formulir resmi" yang boleh diisi rule

### Masalah sekarang
Kalau rule boleh menulis nilai, muncul pertanyaan: **menulis ke mana saja boleh?** Tanpa kontrol, analis A menulis `resiko_agunan`, analis B menulis `risk_agunan`, analis C menulis `collateralRisk` — tiga nama untuk satu hal, dan decision table jadi tidak tahu harus membaca yang mana.

### Yang dibangun
Katalog fitur (sudah ada sejak Phase 2 untuk *input*) diperluas dengan penanda **`writable`** — daftar resmi **output** yang boleh ditulis rule: `outputs.collateral_risk`, `outputs.eligible_limit`, dst. Rule hanya boleh menulis ke output yang terdaftar dan aktif; tipe datanya pun dijaga (output angka tidak bisa diisi teks).

### Analogi: formulir kantor pemerintah
Di formulir resmi, Anda hanya boleh menulis di **kotak yang disediakan**, dan tiap kotak sudah jelas formatnya (kotak tanggal ya diisi tanggal). Anda tidak boleh menggambar kotak baru di pinggir kertas. Output catalog = daftar kotak resmi itu. Petugas berikutnya (decision table) jadi selalu tahu di mana membaca nilai.

### Contoh kasus
Admin mendaftarkan `outputs.collateral_risk` (tipe STRING) dan `outputs.affordability_risk` (STRING) di katalog. Sejak itu:
- Rule apa pun boleh menulis ke keduanya (dan hasil tulisannya bisa dibaca rule/tabel setelahnya).
- Kalau ada yang typo `outputs.colateral_risk` → sistem menolak saat rule disimpan, bukan diam-diam bikin variabel liar.
- Nilai `outputs.*` juga muncul di trace, jadi auditor bisa melihat "angka 15.000 ini ditulis oleh rule mana, cabang ke berapa".

---

## 3. Rule Builder Baru — analis tidak pernah menyentuh JSON

### Masalah sekarang
Membuat rule sederhana sudah bisa lewat form, tapi **mengedit** rule = menghadapi JSON mentah. Kondisi hanya bisa satu grup datar (semua-AND atau semua-OR), nilai diketik bebas (bisa salah ketik `"MOTOR"` vs `MOTOR`), dan tidak ada pratinjau yang bisa dibaca manusia.

### Yang dibangun
1. **Grup bersarang (nested AND/OR)** — syarat kompleks bisa dibuat dengan tombol "Add Group".
2. **Pemilih fitur yang bisa dicari** — ketik "saldo", muncul daftar fitur cocok lengkap dengan tipe datanya.
3. **Operator & input yang "sadar tipe"** — fitur angka memunculkan operator `> >= < <=` dan kotak angka; fitur boolean cuma menawarkan benar/salah; fitur tanggal memunculkan kalender. Salah ketik jadi mustahil.
4. **Editor cabang CASE WHEN** — kartu per cabang, bisa diurut, plus bagian ELSE.
5. **Pratinjau manusiawi** — panel yang selalu menampilkan aturan dalam kalimat: *"JIKA saldo tabungan > 50.000.000 MAKA band harga = 20.000; SELAIN ITU = 0"*.
6. **Halaman detail builder-first** — mengedit rule lama juga lewat builder; JSON dipindah ke tab "Advanced" untuk yang membutuhkan.
7. **Form uji otomatis** — sistem membaca fitur yang dipakai rule lalu membuatkan form input uji coba (bukan menyuruh analis menulis JSON payload).
8. **Panel "Used by"** — sebelum mengubah/memensiunkan rule, terlihat rule set & strategy mana yang memakainya.

### Analogi: syarat beasiswa dengan kurung
Syarat beasiswa: *IPK > 3,5 **DAN** (aktif organisasi **ATAU** punya prestasi nasional)*. Tanpa grup bersarang, syarat berkurung seperti ini tidak bisa diekspresikan. Builder baru = bisa membuat "kurung" sebanyak yang dibutuhkan, dengan klik.

### Contoh kasus
Pak Dimas (analis non-teknis) mengedit rule DTI: ia klik rule di daftar → builder terbuka menampilkan kondisi dalam bentuk baris-baris terisi → ia mengubah angka 0.45 menjadi 0.42 lewat kotak angka → panel kanan langsung menampilkan kalimat aturan versi baru → ia klik "Run test", mengisi form uji (penghasilan, cicilan, dst.) → terlihat cabang mana yang match → simpan sebagai versi draft → ajukan approval. **Nol JSON dari awal sampai akhir.**

---

## 4. Decision Flow DAG — alur keputusan yang bisa bercabang

### Masalah sekarang
Strategy OSCAR = **rel kereta tunggal**: step 1 → 2 → 3 → … → selesai. Semua pemohon melewati stasiun yang sama, urutan yang sama. Tidak ada "kalau begini, lewat sini".

### Yang dibangun
Strategy menjadi **graph berarah (DAG)**: kumpulan node (langkah) yang dihubungkan panah, dengan node istimewa **CONDITION** yang punya dua panah keluar berlabel **TRUE / FALSE**. Jalur boleh **bertemu kembali** (rejoin), tapi tidak boleh berputar (tanpa loop) — supaya setiap eksekusi tetap deterministik dan bisa diaudit.

### Analogi: rel kereta vs jaringan jalan dengan persimpangan
- Lama = kereta: semua penumpang lewat stasiun yang sama.
- Baru = mobil dengan GPS: di persimpangan ada rambu *"JIKA skor risiko perangkat > 0.5 → belok ke jalur pemeriksaan ketat; JIKA TIDAK → jalur cepat"*. Dua jalur itu nanti bertemu lagi di gerbang tol yang sama (scoring), lalu ke tujuan akhir (keputusan). GPS (trace) merekam **persis jalan mana yang dilewati** mobil Anda.

### Contoh kasus
Alur baru LEASEBACK_MOTOR yang dirancang Bu Maya (Risk Manager):

```
START → Validasi → Hitung LTV/DTI → [CONDITION: device_risk_score > 0.5 ?]
                                        ├─ TRUE  → Rule Set FRAUD_DEEP  ┐
                                        └─ FALSE → Rule Set FRAUD_BASIC ┤
                                                                        ▼
                                                    Scorecard → Decision Table → END
```

Pemohon dengan perangkat mencurigakan menjalani 12 pemeriksaan fraud tambahan; pemohon normal cukup 4 — **tanpa memperlambat semua orang**. Di trace keputusan, auditor melihat: node `risk?` dievaluasi → hasil TRUE → jalur FRAUD_DEEP dilalui.

### Yang penting: strategy lama tidak rusak
Semua strategy yang sudah ada otomatis dikonversi menjadi graph lurus (START → step-step → END), dan **golden test** memastikan keputusan untuk payload contoh **identik** sebelum dan sesudah konversi. Sistem lama yang mengirim format `steps` lama juga tetap diterima.

---

## 5. Visual Flow Canvas — menggambar alur, bukan mengetik daftar

### Yang dibangun
Papan kanvas (seperti screenshot Design Flow iDecision): palet komponen di kiri (Validation, Calculation, Rule Set, Scorecard, Decision Table, Condition), tarik ke kanvas, hubungkan dengan panah, klik node untuk mengatur isinya (node Condition dibuka dengan condition builder yang sama seperti di rule). Versi draft bisa diedit; versi aktif tampil **read-only** (hanya bisa dilihat). Kalau graph-nya salah (ada loop, ada node yatim, node condition cuma punya satu panah), node/panah yang bermasalah menyala merah dengan daftar masalahnya.

### Analogi: denah evakuasi vs instruksi teks
Bandingkan membaca "keluar pintu, belok kiri, naik dua lantai, belok kanan…" dengan **melihat denah bergambar panah**. Isi informasinya sama; yang berubah adalah manusia langsung *melihat* strukturnya, salah sambung langsung kelihatan. Canvas = denahnya; eksekusi di mesin tetap sama persis.

### Contoh kasus
Dalam rapat komite kebijakan, Bu Maya membuka strategy versi draft di kanvas, menunjuk cabang fraud di layar, menggeser satu node Rule Set baru dari palet, menyambungkannya, klik Simpan → sistem memvalidasi → ia melampirkan hasil simulasi → submit approval → manajer lain (bukan dia — maker-checker tetap berlaku) menyetujui & mengaktifkan.

---

## 6. Expression Language + Preview SQL — "Free SQL" versi aman

### Kenapa bukan SQL beneran?
Di iDecision, rule diterjemahkan ke SQL karena engine mereka mengeksekusi **di dalam database**. OSCAR mengeksekusi rule **di memori aplikasi** — tidak ada SQL yang berjalan per keputusan. Menjalankan SQL bebas tulisan analis juga berbahaya: bisa mengintip data pemohon lain, hasil bisa tidak deterministik, dan aturan proyek (AGENTS.md) memang melarangnya.

### Yang dibangun
1. **Bahasa ekspresi aman** (khusus admin dulu, lewat izin `rule.author_expression`): menulis aturan sebagai **teks** —
   `CASE WHEN saving_account_balance > 50000000 THEN 20000 WHEN saving_account_balance > 10000000 THEN 15000 ELSE 0 END`
   atau formula: `monthly_income * 0.3 - existing_monthly_obligation`.
   Teks ini di-parse ke struktur terkontrol (hanya operator & fungsi yang di-whitelist: MIN, MAX, ROUND, ABS, COALESCE; identifier wajib fitur katalog) lalu dievaluasi mesin sendiri. **Tidak ada eval, tidak ada SQL yang dieksekusi.**
2. **Preview bergaya SQL untuk SEMUA rule** — rule buatan builder pun bisa dilihat dalam format `CASE WHEN … END` yang familiar, dengan banner tegas: *"Preview saja — OSCAR tidak pernah mengeksekusi SQL."*

### Analogi: ATM vs kasir bank
- **Expression language = ATM.** Anda bisa mengetik angka bebas dan memilih menu — sangat fleksibel — tapi mesin hanya mengerjakan operasi yang tombolnya memang ada. Tidak mungkin mengetik perintah "buka brankas".
- **Raw SQL = memberi orang asing kunci ruang arsip** dan berharap dia hanya membaca satu map.
- **Preview SQL = terjemahan tertulis** di layar ATM ("Anda akan menarik Rp500.000") — untuk dibaca dan dicek, bukan perintah tambahan.

### Contoh kasus
Admin (satu-satunya yang berizin) menulis formula cicilan maksimal: `ROUND(MIN(monthly_income * 0.3, outputs.eligible_limit / 12))`. Editor langsung memvalidasi (kalau ia mengetik fitur yang tak ada di katalog, muncul error di baris & kolomnya). Analis biasa yang mencoba membuat rule expression mendapat **403** — tapi tetap bisa *membaca* preview SQL dari rule mana pun untuk memahaminya.

---

## 7. Decision Table Grid Editor — matriks keputusan rasa spreadsheet

### Masalah sekarang
Decision table (mesinnya) sudah lengkap sejak MVP — tapi mengedit barisnya masih lewat JSON. Padahal justru tabel inilah "ketua komite" yang menggabungkan output para rule.

### Yang dibangun
Editor **grid seperti Excel**: kolom kondisi dipilih dari katalog (termasuk output rule seperti `outputs.collateral_risk`), kolom hasil (keputusan, limit, tenor, pricing, kode alasan), baris bisa ditambah/digandakan/diurut, sel berisi input sesuai tipe, dan **peringatan baris tumpang-tindih** dari backend muncul langsung di baris yang bermasalah.

### Analogi: papan tarif di loket
Seperti papan di loket imigrasi/kantor pajak: baris demi baris "kategori → tarif". Semua orang — termasuk yang bukan programmer — bisa membaca dan mengisinya. Bedanya, papan OSCAR mengecek sendiri kalau ada dua baris yang saling bertabrakan aturannya.

### Contoh kasus (inilah "pola modular" yang jadi inti Phase 3)
| `outputs.collateral_risk` | `outputs.affordability_risk` | Keputusan |
|---|---|---|
| HIGH | HIGH | REJECT |
| HIGH | * (apa pun) | MANUAL_REVIEW |
| * | HIGH | MANUAL_REVIEW |
| * | * | APPROVE |

Perhatikan: **rule tidak lagi memvonis**. Rule A hanya menulis `collateral_risk`, rule B hanya menulis `affordability_risk` — vonisnya lahir di tabel ini. Mau mengubah kebijakan "dua-duanya HIGH = REJECT" menjadi "= MANUAL_REVIEW"? Cukup edit **satu sel**, tanpa menyentuh rule mana pun.

---

## 8. Cerita utuh: perjalanan satu aplikasi setelah Phase 3

**Pak Budi** mengajukan lease-back motor Vario 2020, pinjaman 15 juta, penghasilan 8,5 juta.

1. **LOS mengirim aplikasi** ke `POST /v1/decisions` → OSCAR memuat **graph** strategy aktif.
2. **Validasi** kolom wajib ✓ → **Kalkulasi** menghitung LTV 0,83 & DTI 0,38.
3. **Node CONDITION** "device_risk_score > 0.5?" → nilai Pak Budi 0,12 → **FALSE** → jalur FRAUD_BASIC (jalur cepat).
4. **Rule set klasifikasi** berjalan: rule `VEHICLE_PRICE_BAND` (STATEMENT, 3 cabang) match di cabang ke-2 → menulis `outputs.vehicle_price_band = 15000`; rule lain menulis `outputs.collateral_risk = MEDIUM`.
5. **Scorecard** memetakan skor 684 → grade B.
6. **Decision table** (yang dibuat di grid editor) membaca grade B + `collateral_risk MEDIUM` + band harga → hasil **APPROVE_WITH_CONDITION**, limit 12,5 juta.
7. **Trace** merekam semuanya: jalur node yang dilalui (termasuk "condition → FALSE"), cabang rule yang match ("branch 2 of 3"), semua output yang ditulis, versi setiap konfigurasi. Auditor kapan pun bisa memutar ulang keputusan ini.
8. **Governance tidak berubah**: strategy yang dipakai tadi dulunya draft → disimulasikan (wajib) → diajukan analis → disetujui manajer yang berbeda (maker-checker) → diaktifkan → semua tercatat di audit log.

---

## 9. Yang sengaja TIDAK dibangun (dan alasannya)

| Tidak dibangun | Alasan singkat |
|---|---|
| Eksekusi raw SQL | Berbahaya (bisa akses data lain), melanggar aturan proyek, dan tidak cocok dengan mesin in-memory. Digantikan expression language + preview SQL |
| Cabang paralel / loop di flow | Merusak determinisme (urutan tulis output jadi ambigu) — padahal keputusan kredit wajib bisa direproduksi persis untuk audit |
| Rule templates, import/export massal, visualisasi dependency graph | Masuk **stretch backlog** — dikerjakan hanya setelah semua fitur inti stabil |
| Scope Phase 3 lama (fraud monitoring, champion/challenger, dst.) | Dihapus atas keputusan product owner (ADR-012) |

## 10. FAQ singkat

**T: Rule lama saya rusak tidak?**
J: Tidak. Bentuk lama (`condition` + `action`) tetap valid selamanya — di dalam mesin ia diperlakukan sebagai "CASE WHEN satu cabang". Ada test khusus (golden test) yang menjamin keputusan lama tetap identik.

**T: Siapa yang boleh apa?**
J: Sama seperti sekarang — analis membuat draft, manajer (orang berbeda) menyetujui & mengaktifkan, simulasi wajib dilampirkan sebelum aktivasi. Satu-satunya izin baru: menulis rule expression (admin dulu).

**T: Kalau saya lebih suka JSON, hilang?**
J: Tidak hilang — pindah ke tab "Advanced". Targetnya: *tidak ada yang terpaksa* memakai JSON, bukan melarangnya.

**T: Preview SQL itu bisa dijalankan?**
J: Tidak, murni tampilan untuk dibaca (ada banner peringatannya). OSCAR tidak pernah mengeksekusi SQL dari teks pengguna.
