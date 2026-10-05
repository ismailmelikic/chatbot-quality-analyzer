"""
Dil katmani (i18n)
------------------
Panelin butun kullanici metinleri burada. `T("anahtar")` secili dildeki
karsiligi dondurur; secim `st.session_state["dil"]` icinde tutulur.

Yeni dil eklemek: her sozluge o dilin kodunu ("de", "fr"…) ekleyin ve
DILLER'e yazin. Eksik anahtar kalirsa Turkce'ye duser, panel cokmez.

NOT: Basarisizlik tespiti kaliplari burada DEGIL, `kurallar.py` icinde —
onlar arayuz metni degil, analiz mantigi. Panel dilini Ingilizce yapmak
Turkce loglari analiz etmeyi engellemez; ikisi bagimsizdir.
"""

VARSAYILAN = "tr"
DILLER = {"tr": "Türkçe", "en": "English"}

M = {
    # --- genel ---
    "baslik":         {"tr": "Chatbot Konuşma Kalitesi Analiz Paneli",
                       "en": "Chatbot Conversation Quality Panel"},
    "dil":            {"tr": "Dil", "en": "Language"},
    "oturum":         {"tr": "oturum", "en": "sessions"},
    "basarisiz":      {"tr": "başarısız", "en": "failed"},

    # --- yan panel: veri kaynagi ---
    "veri_kaynagi":   {"tr": "Veri kaynağı", "en": "Data source"},
    "yukle_baslik":   {"tr": "📁 Loglarınızı yükleyin", "en": "📁 Upload your logs"},
    "yukle_aciklama": {"tr": "Dosyanızı yükleyin; sistem kümelemeyi, başarısızlık "
                             "tespitini ve trend analizini sıfırdan çalıştırır.",
                       "en": "Upload your file; the system runs clustering, failure "
                             "detection and trend analysis from scratch."},
    "yukle_yardim":   {"tr": """<b>Kolon adlarını değiştirmenize gerek yok.</b> Sistem yaygın
            adlandırmaları (<code>instruction</code>/<code>response</code>,
            <code>role</code>/<code>content</code>, <code>sender</code>/<code>text</code>…)
            otomatik tanır.<br><br>
            <b>Desteklenen biçimler</b><br>
            Satır başına soru-cevap çifti, ya da satır başına tek mesaj +
            rol kolonu (Rasa, Dialogflow, LangChain tarzı) — ikincisi otomatik
            çiftlere dönüştürülür.<br><br>
            <b>Varsa kullanılır</b><br>
            <code>oturum_id</code> · <code>sira_no</code> · <code>tarih</code><br><br>
            <b>Ground truth (opsiyonel)</b><br>
            <code>gercek_konu</code> · <code>sonuc_durumu</code> · <code>belirsiz_mesaj</code>
            — varsa doğruluk ölçülür, yoksa analiz yine çalışır.""",
                       "en": """<b>No need to rename your columns.</b> The system
            auto-detects common namings (<code>instruction</code>/<code>response</code>,
            <code>role</code>/<code>content</code>, <code>sender</code>/<code>text</code>…).<br><br>
            <b>Supported layouts</b><br>
            One question-answer pair per row, or one message per row plus a role
            column (Rasa, Dialogflow, LangChain style) — the latter is converted
            into pairs automatically.<br><br>
            <b>Used when present</b><br>
            <code>oturum_id</code> · <code>sira_no</code> · <code>tarih</code><br><br>
            <b>Ground truth (optional)</b><br>
            <code>gercek_konu</code> · <code>sonuc_durumu</code> · <code>belirsiz_mesaj</code>
            — accuracy is measured when present; the analysis runs either way."""},
    "yukleyici":      {"tr": "Log dosyası (CSV / JSON / JSONL)",
                       "en": "Log file (CSV / JSON / JSONL)"},

    # --- yukleme akisi ---
    "dosya_okunamadi": {"tr": "Dosya okunamadı: {}", "en": "Could not read file: {}"},
    "satir_kolon":    {"tr": "**{}** satır, **{}** kolon",
                       "en": "**{}** rows, **{}** columns"},
    "uzun_format":    {"tr": "Mesaj bazlı log algılandı (`{rol}` / `{metin}`) — "
                             "{once} mesaj, {sonra} soru-cevap çiftine dönüştürüldü.",
                       "en": "Message-level log detected (`{rol}` / `{metin}`) — "
                             "{once} messages converted into {sonra} question-answer pairs."},
    "eslesen_kolonlar": {"tr": "Otomatik eşleşen kolonlar: ",
                         "en": "Auto-matched columns: "},
    "kolon_bulunamadi": {"tr": "Şu kolonlar otomatik bulunamadı: ",
                         "en": "These columns could not be detected: "},
    "kolon_sec_uyari": {"tr": ". Dosyanızdaki karşılığını seçin:",
                        "en": ". Pick the matching column from your file:"},
    "sec":            {"tr": "— seç —", "en": "— select —"},
    "ayni_kolon":     {"tr": "Kullanıcı mesajı ve bot cevabı için farklı kolonlar seçin.",
                       "en": "Pick different columns for the user message and the bot reply."},
    "sag_yerel":      {"tr": "Yerel / Özel (Ollama, vLLM, kurum içi)",
                       "en": "Local / Custom (Ollama, vLLM, on-prem)"},
    "hangi_kolon":    {"tr": "`{}` hangi kolon?", "en": "Which column is `{}`?"},
    "tarih_ipucu":    {"tr": "`tarih` kolonu eklersen Zaman Trendleri sekmesi de açılır.",
                       "en": "Add a `tarih` (date) column to unlock the Time Trends tab."},
    "gt_bulundu":     {"tr": "Ground truth kolonu bulundu — kümeleme doğruluğu da ölçülecek.",
                       "en": "Ground truth column found — clustering accuracy will also be measured."},
    "analizi_calistir": {"tr": "Analizi çalıştır", "en": "Run analysis"},
    "basliyor":       {"tr": "Başlıyor...", "en": "Starting..."},
    "analiz_basarisiz": {"tr": "Analiz başarısız: {}", "en": "Analysis failed: {}"},
    "analiz_tamam":   {"tr": "Tamamlandı — {} oturum, {} küme bulundu.",
                       "en": "Done — {} sessions, {} clusters found."},

    # --- LLM ayarlari ---
    "llm_ayarlari":   {"tr": "LLM ayarları", "en": "LLM settings"},
    "saglayici_model": {"tr": "⚙️ Sağlayıcı ve model", "en": "⚙️ Provider and model"},
    "saglayici":      {"tr": "Sağlayıcı", "en": "Provider"},
    "base_url_sabit": {"tr": "Sağlayıcı tarafından otomatik belirlenir, değiştirilemez.",
                       "en": "Set automatically by the provider; not editable."},
    "model":          {"tr": "Model", "en": "Model"},
    "onerilen":       {"tr": "Önerilen: ", "en": "Suggested: "},
    "api_anahtari":   {"tr": "API anahtarı", "en": "API key"},
    "anahtar_bos":    {"tr": "boşsa {} kullanılır", "en": "falls back to {} when empty"},
    "anahtar_panel":  {"tr": "🔑 Panelden girilen anahtar kullanılacak (diske yazılmaz).",
                       "en": "🔑 Using the key entered here (never written to disk)."},
    "anahtar_ortam":  {"tr": "🔑 `{}` ortam değişkeni bulundu.",
                       "en": "🔑 Found the `{}` environment variable."},
    "anahtar_yok":    {"tr": "⚠️ Anahtar yok. Rapor üretilemez, diğer sekmeler çalışır.",
                       "en": "⚠️ No key. Report generation is unavailable; other tabs work."},
    "ucretsiz_anahtar": {"tr": "Ücretsiz anahtar: {}", "en": "Free key: {}"},
    "test_et":        {"tr": "Test et", "en": "Test"},
    "baglaniliyor":   {"tr": "Bağlanılıyor...", "en": "Connecting..."},
    "kaydet":         {"tr": "Kaydet", "en": "Save"},
    "kaydedildi":     {"tr": "Kaydedildi (anahtar hariç).", "en": "Saved (key excluded)."},
    "model_listesi_getir": {"tr": "Güncel model listesini getir",
                            "en": "Fetch current model list"},
    "liste_aliniyor": {"tr": "Sağlayıcıdan liste alınıyor...",
                       "en": "Fetching list from provider..."},
    "calisan_model_bul": {"tr": "Çalışan modeli otomatik bul",
                          "en": "Auto-find a working model"},
    "model_bulundu":  {"tr": "Çalışan model bulundu ve kaydedildi:\n\n**{}**",
                       "en": "Working model found and saved:\n\n**{}**"},
    "model_sayisi":   {"tr": "{} model bulundu.", "en": "{} models found."},
    "listeden_sec":   {"tr": "Listeden seç", "en": "Select from list"},
    "bu_modeli_kullan": {"tr": "Bu modeli kullan", "en": "Use this model"},

    # --- KPI kartlari ---
    "kpi_oturum":     {"tr": "Toplam oturum", "en": "Total sessions"},
    "kpi_oturum_not": {"tr": "analiz edilen konuşma", "en": "conversations analyzed"},
    "kpi_oran":       {"tr": "Başarısızlık oranı", "en": "Failure rate"},
    "kpi_oran_not":   {"tr": "kural bazlı tespit", "en": "rule-based detection"},
    "kpi_kume":       {"tr": "Konu kümesi", "en": "Topic clusters"},
    "kpi_kume_not":   {"tr": "algoritma buldu", "en": "found by the algorithm"},
    "kpi_belirsiz":   {"tr": "Belirsiz mesaj", "en": "Ambiguous messages"},
    "kpi_belirsiz_not": {"tr": "toplamın %{}’i", "en": "{}% of all"},

    # --- sekme adlari ---
    "sekme_kumeler":  {"tr": "Konu Kümeleri", "en": "Topic Clusters"},
    "sekme_basarisizlik": {"tr": "Başarısızlık Analizi", "en": "Failure Analysis"},
    "sekme_trend":    {"tr": "Zaman Trendleri", "en": "Time Trends"},
    "sekme_rapor":    {"tr": "Yönetim Raporu", "en": "Executive Report"},

    # --- kumeler sekmesi ---
    "kumeler_baslik": {"tr": "#### Otomatik keşfedilen konu kümeleri",
                       "en": "#### Automatically discovered topic clusters"},
    "kumeler_aciklama": {"tr": "Algoritma konu etiketlerini <b>görmeden</b>, sadece "
                               "mesaj metinlerinin anlamsal benzerliğinden bu grupları "
                               "buldu. Küme sayısı elle verilmedi — silhouette skoru seçti.",
                         "en": "The algorithm found these groups <b>without seeing</b> any "
                               "topic labels, purely from the semantic similarity of the "
                               "message texts. The cluster count was not set by hand — "
                               "the silhouette score chose it."},
    "isimlendir_btn": {"tr": "Kümeleri LLM ile isimlendir", "en": "Name clusters with an LLM"},
    "isimlendir_not": {"tr": "Kümeler şu an numarayla gösteriliyor. LLM her kümenin "
                             "merkezine en yakın mesajlara bakıp başlık üretir.",
                       "en": "Clusters are currently shown by number. The LLM reads the "
                             "messages closest to each cluster centre and writes a title."},
    "kume":           {"tr": "Küme {}", "en": "Cluster {}"},
    "harita_not":     {"tr": "Her nokta bir konuşma. Yakın noktalar anlamca benzer mesajlar.",
                       "en": "Each dot is a conversation. Nearby dots are semantically similar."},
    "kume_basina":    {"tr": "Küme başına oturum", "en": "Sessions per cluster"},
    "toplam_oturum":  {"tr": "Toplam **{}** oturum", "en": "**{}** sessions in total"},
    "dogruluk_baslik": {"tr": "#### Kümeleme doğruluğu", "en": "#### Clustering accuracy"},
    "dogruluk_aciklama": {"tr": "Ground truth kolonu veride mevcut olduğu için kümelemenin "
                                "gerçek konularla ne kadar örtüştüğü ölçülebiliyor. Bu "
                                "kolonlar modele <b>verilmedi</b>, sadece sonradan karşılaştırıldı.",
                          "en": "Because the data contains a ground-truth column, we can "
                                "measure how well the clustering matches the real topics. "
                                "These columns were <b>never given</b> to the model; they "
                                "were only compared afterwards."},
    "ari_yardim":     {"tr": "Adjusted Rand Index — 1.0 mükemmel eşleşme",
                       "en": "Adjusted Rand Index — 1.0 is a perfect match"},
    "secilen_k":      {"tr": "Seçilen k", "en": "Chosen k"},
    "tablo_kume":     {"tr": "Küme", "en": "Cluster"},
    "tablo_baskin":   {"tr": "Baskın gerçek konu", "en": "Dominant true topic"},
    "tablo_saflik":   {"tr": "Saflık %", "en": "Purity %"},
    "tablo_oturum":   {"tr": "Oturum", "en": "Sessions"},

    # --- basarisizlik sekmesi ---
    "basarisizlik_baslik": {"tr": "#### Nerede başarısız oluyor?",
                            "en": "#### Where is it failing?"},
    "basarisizlik_aciklama": {"tr": "Başarısızlık, bot cevabının metninden <b>kural bazlı</b> "
                                    "tespit ediliyor: pes etme kalıpları (“anlayamadım”), "
                                    "insana devir (“temsilciye aktarıyorum”) ve kullanıcının "
                                    "aynı şeyi tekrar sorması.",
                              "en": "Failure is detected <b>by rules</b> from the bot's own "
                                    "reply text: giving-up phrases (“I don't understand”), "
                                    "handover to a human (“transferring you to an agent”) "
                                    "and the user having to repeat the question."},
    "kural_uymuyor":  {"tr": "**Kural seti bu loga uymuyor.** {} cevabın hiçbirinde bilinen "
                             "bir başarısızlık kalıbı bulunamadı — bu, botun hiç başarısız "
                             "olmadığı anlamına **gelmez**. Muhtemelen log Türkçe/İngilizce "
                             "dışında bir dilde ya da çok farklı bir üslupta. Aşağıdaki "
                             "oranları geçerli sayma; `kurallar.py` içindeki kalıp "
                             "listelerine o dilin ifadelerini ekleyin.",
                       "en": "**The rule set does not fit this log.** None of the {} replies "
                             "matched a known failure pattern — this does **not** mean the "
                             "bot never failed. The log is probably in a language other than "
                             "Turkish/English, or in a very different style. Do not treat the "
                             "rates below as valid; add that language's phrases to the "
                             "pattern lists in `kurallar.py`."},
    "kumeye_gore":    {"tr": "Kümeye göre başarısızlık oranı", "en": "Failure rate by cluster"},
    "kumeye_gore_not": {"tr": "Üretimde kullanılacak görünüm — konu etiketi gerektirmez.",
                        "en": "The production view — requires no topic labels."},
    "konuya_gore":    {"tr": "Gerçek konuya göre (doğrulama)",
                       "en": "By true topic (validation)"},
    "konuya_gore_not": {"tr": "Soldaki grafikle aynı sıralamayı vermesi yöntemin "
                              "çalıştığını gösterir.",
                        "en": "Matching the ranking of the left-hand chart shows the "
                              "method works."},
    "bitis_fallback": {"tr": "Anlamadı (fallback)", "en": "Did not understand (fallback)"},
    "bitis_devir":    {"tr": "İnsana devretti", "en": "Handed over to a human"},
    "bitis_tekrar":   {"tr": "Kullanıcı tekrar sordu", "en": "User asked again"},
    "bitis_baslik":   {"tr": "Başarısız oturumlar nasıl bitiyor",
                       "en": "How failed sessions end"},
    "belirsiz_evet":  {"tr": "Belirsiz mesaj", "en": "Ambiguous message"},
    "belirsiz_hayir": {"tr": "Net mesaj", "en": "Clear message"},
    "belirsiz_baslik": {"tr": "Belirsiz mesajların etkisi",
                        "en": "Impact of ambiguous messages"},
    "belirsiz_not":   {"tr": "Kasten belirsiz yazılmış mesajlarda başarısızlık belirgin "
                             "yükseliyor.",
                       "en": "Failure rises noticeably on deliberately ambiguous messages."},
    "kural_dogruluk_baslik": {"tr": "#### Kural bazlı tespitin doğruluğu",
                              "en": "#### Accuracy of the rule-based detection"},
    "ikili_ayrim":    {"tr": "Başarılı/başarısız ayrımı", "en": "Success/failure split"},
    "dort_sinif":     {"tr": "Dört sınıfın tamamı", "en": "All four classes"},
    "kural_dogruluk_aciklama": {"tr": "Veride <code>sonuc_durumu</code> etiketi olduğu için "
                                      "kuralların bu etiketi ne kadar geri üretebildiği "
                                      "ölçüldü. Sentetik veride yüksek çıkması beklenir "
                                      "(mesajlar sabit şablonlardan üretildi); gerçek "
                                      "loglarda daha düşük olacaktır.",
                                "en": "Since the data carries a <code>sonuc_durumu</code> "
                                      "label, we measured how well the rules reproduce it. "
                                      "A high score is expected on synthetic data (messages "
                                      "came from fixed templates); real logs will score lower."},

    # --- trend sekmesi ---
    "trend_baslik":   {"tr": "#### Zaman içinde ne değişti?",
                       "en": "#### What changed over time?"},
    "haftalik_hacim": {"tr": "Haftalık konuşma hacmi", "en": "Weekly conversation volume"},
    "haftalik_oran":  {"tr": "Haftalık başarısızlık oranı", "en": "Weekly failure rate"},
    "hacim_patlamasi": {"tr": "Hacim patlaması — {}", "en": "Volume spike — {}"},
    "hacim_aciklama": {"tr": "<b>{hafta}</b> haftasında hacim <b>{hacim}</b>’e çıkmış "
                             "(diğer haftalar ort. {ort}){oran} Kırmızı çubuk zirve haftası.",
                       "en": "Volume peaked at <b>{hacim}</b> in week <b>{hafta}</b> "
                             "(other weeks avg. {ort}){oran} The red bar marks the peak week."},
    "hacim_oran_tr":  {"tr": ", başarısızlık <b>%{}</b>.", "en": ", failure rate <b>{}%</b>."},
    "aylar_arasi":    {"tr": "Aylar arası bozulma", "en": "Month-over-month degradation"},
    "aylar_aciklama": {"tr": "Kademeli bozulmalar hafta bazında gürültüye karışıyor, "
                             "aylık kırılımda net görünüyor.",
                       "en": "Gradual degradation gets lost in weekly noise but is clear "
                             "in the monthly breakdown."},
    "aylik_oran":     {"tr": "Aylık başarısızlık oranı", "en": "Monthly failure rate"},

    # --- rapor sekmesi ---
    "rapor_baslik":   {"tr": "#### Yönetim raporu", "en": "#### Executive report"},
    "rapor_aciklama": {"tr": "Bu metni LLM yazdı — ama ham konuşmaları görmedi. Prompt’a "
                             "sadece yukarıdaki <b>sayısal özetler</b> gönderiliyor. Bu hem "
                             "müşteri mesajlarının dışarı çıkmasını engelliyor hem de "
                             "halüsinasyon riskini azaltıyor.",
                       "en": "An LLM wrote this text — but it never saw the raw conversations. "
                             "Only the <b>numeric summaries</b> above are sent in the prompt. "
                             "That keeps customer messages from leaving your machine and "
                             "lowers the risk of hallucination."},
    "rapor_uret_btn": {"tr": "Raporu yeniden üret", "en": "Regenerate report"},
    "rapor_yok":      {"tr": "Henüz rapor üretilmedi. Yukarıdaki düğmeye basın "
                             "(sol panelden API anahtarı girilmiş olmalı).",
                       "en": "No report yet. Press the button above "
                             "(an API key must be set in the sidebar)."},
    "rapor_yaziyor":  {"tr": "{} rapor yazıyor...", "en": "{} is writing the report..."},
    "rapor_uretilemedi": {"tr": "Rapor üretilemedi: {}", "en": "Could not generate report: {}"},
    "isim_uretiyor":  {"tr": "{} küme isimleri üretiyor...",
                       "en": "{} is generating cluster names..."},
    "isimlendirme_basarisiz": {"tr": "İsimlendirme başarısız: {}",
                               "en": "Naming failed: {}"},
    "anahtar_gerekli": {"tr": "API anahtarı yok. Sol panelden **LLM ayarları** bölümüne girin.",
                        "en": "No API key. Open **LLM settings** in the sidebar."},
    "temsili_yok":    {"tr": "`temsili_mesajlar.json` bulunamadı — analiz yeniden çalıştırılmalı.",
                       "en": "`temsili_mesajlar.json` not found — rerun the analysis."},

    # --- bos ekran ---
    "bos_aciklama":   {"tr": "Chatbot konuşma loglarınızı yükleyin; sistem konu kümelerini "
                             "otomatik keşfeder, başarısız konuşmaları tespit eder, zaman "
                             "trendlerini çıkarır ve bulguları yönetim raporuna çevirir.",
                       "en": "Upload your chatbot conversation logs; the system discovers "
                             "topic clusters automatically, detects failed conversations, "
                             "extracts time trends and turns the findings into an "
                             "executive report."},
    "bos_basla":      {"tr": "##### Başlamak için", "en": "##### Getting started"},
    "bos_adimlar":    {"tr": "1. Sol panelden log dosyanızı yükleyin (CSV / JSON / JSONL)\n"
                             "2. **Analizi çalıştır**'a basın\n"
                             "3. Sonuçlar burada görünür",
                       "en": "1. Upload your log file from the sidebar (CSV / JSON / JSONL)\n"
                             "2. Press **Run analysis**\n"
                             "3. Results appear here"},
    "bos_dosya":      {"tr": "##### Dosyanız nasıl olmalı", "en": "##### What your file needs"},
    "bos_dosya_metin": {"tr": "Kolon adlarını değiştirmenize **gerek yok** — yaygın "
                              "adlandırmalar (`instruction`/`response`, `role`/`content`, "
                              "`sender`/`text`) otomatik tanınır.\n\nSatır başına soru-cevap "
                              "çifti ya da satır başına tek mesaj + rol kolonu, ikisi de olur.",
                        "en": "**No need** to rename columns — common namings "
                              "(`instruction`/`response`, `role`/`content`, `sender`/`text`) "
                              "are detected automatically.\n\nOne question-answer pair per "
                              "row, or one message per row plus a role column — either works."},
    "bos_ornek":      {"tr": "Hemen denemek için depodaki `ornek_musteri_loglari.csv` "
                             "dosyasını yükleyebilirsiniz.",
                       "en": "To try it right away, upload `ornek_musteri_loglari.csv` "
                             "from this repository."},

    # --- ilerleme mesajlari (pipeline / llm) ---
    "ilr_hazirla":    {"tr": "Veri hazırlanıyor...", "en": "Preparing data..."},
    "ilr_model_yukle": {"tr": "Embedding modeli yükleniyor (ilk seferde ~470 MB iner)...",
                        "en": "Loading the embedding model (~470 MB download on first run)..."},
    "ilr_vektor":     {"tr": "{} mesaj vektöre çevriliyor...",
                       "en": "Embedding {} messages..."},
    "ilr_k_ara":      {"tr": "En uygun küme sayısı aranıyor...",
                       "en": "Searching for the best number of clusters..."},
    "ilr_k_tarama":   {"tr": "K taraması: k={}", "en": "Scanning k={}"},
    "ilr_kumele":     {"tr": "k={} ile kümeleniyor...", "en": "Clustering with k={}..."},
    "ilr_harita":     {"tr": "Harita için boyut indirgeme...",
                       "en": "Reducing dimensions for the map..."},
    "ilr_analiz":     {"tr": "Başarısızlık ve trend analizi...",
                       "en": "Analyzing failures and trends..."},
    "ilr_kaydet":     {"tr": "Sonuçlar kaydediliyor...", "en": "Saving results..."},
    "ilr_tamam":      {"tr": "Tamamlandı.", "en": "Done."},
    "ilr_deneniyor":  {"tr": "Deneniyor: {}", "en": "Trying: {}"},

    # --- hata mesajlari (pipeline / llm) ---
    "hata_zorunlu_kolon": {"tr": "Zorunlu kolon(lar) bulunamadı: {}. Kullanıcı mesajı ve bot "
                                 "cevabı kolonları otomatik tespit edilemedi; panelden elle "
                                 "eşleştirebilirsiniz.",
                           "en": "Required column(s) not found: {}. The user message and bot "
                                 "reply columns could not be detected; you can map them in "
                                 "the panel."},
    "hata_az_mesaj":  {"tr": "Kümeleme için çok az konuşma var ({}). En az 10 gerekli.",
                       "en": "Too few conversations to cluster ({}). At least 10 are needed."},
    "hata_kumelenemedi": {"tr": "Mesajlar kümelenemedi: hepsi aynı ya da boş görünüyor. "
                                "Farklı mesajlar içeren bir dosya deneyin.",
                          "en": "Messages could not be clustered: they all look identical "
                                "or empty. Try a file with varied messages."},
    "hata_anahtar_bozuk": {"tr": "API anahtarı geçersiz: içinde kullanılabilir karakter yok. "
                                 "Kopyalarken bozulmuş olabilir, elle yeniden yazın.",
                           "en": "Invalid API key: it contains no usable characters. It may "
                                 "have been corrupted while copying; type it again."},
    "hata_bos_cevap": {"tr": "Model boş cevap döndü. 'Reasoning' modellerinde düşünme aşaması "
                             "token payını tüketmiş olabilir - başka bir model seçin.",
                       "en": "The model returned an empty answer. With 'reasoning' models the "
                             "thinking phase may use up the token budget - pick another model."},
    "baglanti_ok":    {"tr": "Bağlantı başarılı. Model yanıt verdi: “{}”",
                       "en": "Connection OK. The model replied: “{}”"},
    "hata_bos_liste": {"tr": "Sağlayıcı boş liste döndürdü.",
                       "en": "The provider returned an empty list."},
    "hata_isim_json": {"tr": "Model geçerli JSON döndürmedi: {}",
                       "en": "The model did not return valid JSON: {}"},
    "hata_isim_gecersiz": {"tr": "Model geçerli bir küme ismi döndürmedi.",
                           "en": "The model did not return any valid cluster name."},
    "hata_401":       {"tr": "API anahtarı reddedildi (401 Unauthorized).\n\nBu bir model "
                             "sorunu değil — anahtarın kendisi geçersiz. Muhtemel sebepler:\n"
                             "• Anahtar eksik/hatalı yapıştırıldı\n"
                             "• Anahtarın süresi doldu ya da iptal edildi\n"
                             "• Ücretsiz kredi limiti bitti\n\n"
                             "Sağlayıcının sitesinden yeni bir anahtar üretip tekrar deneyin.",
                       "en": "The API key was rejected (401 Unauthorized).\n\nThis is not a "
                             "model problem — the key itself is invalid. Likely causes:\n"
                             "• The key was pasted incompletely or incorrectly\n"
                             "• The key expired or was revoked\n"
                             "• The free credit limit ran out\n\n"
                             "Create a new key on the provider's site and try again."},
    "hata_model_yok": {"tr": "Denenen modellerin hiçbiri cevap vermedi:",
                       "en": "None of the tried models answered:"},
    "anahtar_gerekmez": {"tr": "Yerel sunucu anahtar istemiyor; boş bırakabilirsiniz.",
                         "en": "Local servers need no key; you can leave it empty."},
    "ollama_ipucu":   {"tr": "Ollama varsayılan adresi `http://localhost:11434/v1`. Önce "
                             "bir model indirin: `ollama pull llama3.1`",
                       "en": "Ollama's default address is `http://localhost:11434/v1`. "
                             "Pull a model first: `ollama pull llama3.1`"},
    "rapor_baska_dilde": {"tr": "Bu analiz için yalnızca İngilizce rapor var. Türkçe "
                                "raporu yukarıdaki düğmeyle üretebilirsiniz.",
                          "en": "There is only a Turkish report for this analysis. Generate "
                                "the English one with the button above."},
}


def mevcut_dil():
    """Streamlit oturumundaki secili dil. Streamlit yoksa varsayilana duser."""
    try:
        import streamlit as st
        # Streamlit disinda (test, komut satiri) session_state'e dokunmak
        # her cagrida uyari basiyor; once calisan bir oturum var mi bak.
        if not st.runtime.exists():
            return VARSAYILAN
        return st.session_state.get("dil", VARSAYILAN)
    except Exception:
        return VARSAYILAN


def T(anahtar, dil=None):
    """Secili dildeki metni dondurur. Anahtar ya da dil eksikse Turkce'ye duser."""
    kayit = M.get(anahtar)
    if kayit is None:
        return anahtar
    return kayit.get(dil or mevcut_dil()) or kayit.get(VARSAYILAN, anahtar)
