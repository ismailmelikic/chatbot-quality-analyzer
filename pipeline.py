"""
Pipeline Orkestrasyonu
-----------------------
DISARIDAN YUKLENEN herhangi bir log tablosunu bastan sona analiz eder.

`gercek_konu`, `sonuc_durumu` gibi ground truth kolonlari gercek bir chatbot
logunda YOKTUR; sistem onlara dayanamaz. Bu modul:
  - Zorunlu kolonlari kontrol eder, eksikse net hata verir
  - Eksik opsiyonel kolonlari makul varsayilanlarla doldurur
  - Basarisizligi etiketten degil, kural bazli olarak METINDEN tespit eder
  - Ground truth varsa ek olarak dogrulama (ARI/NMI) da hesaplar
"""

import json
import os

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    silhouette_score,
    adjusted_rand_score,
    normalized_mutual_info_score,
)

import kurallar
from diller import T

RANDOM_STATE = 42
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
K_ARALIGI = range(2, 13)
SILHOUETTE_ORNEK = 5000

# ---------------------------------------------------------------------
# Kolon sozlesmesi
# ---------------------------------------------------------------------
ZORUNLU = {
    "kullanici_mesaji": "Kullanicinin yazdigi mesaj — kumeleme bunun uzerinden yapilir.",
    "chatbot_cevabi": "Botun cevabi — basarisizlik tespiti bunun uzerinden yapilir.",
}

ONERILEN = {
    "oturum_id": "Konusma kimligi. Yoksa her satir ayri oturum sayilir.",
    "sira_no": "Oturum icindeki tur numarasi. Yoksa hepsi 1. tur sayilir.",
    "tarih": "Zaman damgasi. Yoksa Zaman Trendleri sekmesi devre disi kalir.",
}

DOGRULAMA = {
    "gercek_konu": "Varsa kumeleme kalitesi ARI/NMI ile olculur.",
    "belirsiz_mesaj": "Varsa belirsiz mesajlarin basarisizliga etkisi hesaplanir.",
    "sonuc_durumu": "Varsa kural bazli tespitin dogrulugu olculur.",
}


# ---------------------------------------------------------------------
# Otomatik bicim algilama
#
# NEDEN: Kimse loglarini bizim kolon adlarimizla tutmuyor. Gercek chatbot
# platformlari (Rasa, Dialogflow, Botpress, LangChain, OpenAI) logu
# "bir satir = tek mesaj + kim soyledi" seklinde yaziyor; bizim pipeline ise
# "bir satir = soru+cevap cifti" bekliyor. Kullaniciya CSV'sini elle
# duzenlettirmek yerine ikisini de kabul edip ceviriyoruz.
# ---------------------------------------------------------------------
KOLON_IPUCLARI = {
    "kullanici_mesaji": ["kullanici_mesaji", "instruction", "user_message", "query",
                         "question", "musteri_mesaji", "soru", "prompt", "input"],
    "chatbot_cevabi": ["chatbot_cevabi", "response", "answer", "reply", "bot_response",
                       "cevap", "output", "completion"],
    "oturum_id": ["oturum_id", "conversation_id", "session_id", "dialog_id", "dialogue_id",
                  "chat_id", "thread_id", "konusma_id", "conv_id"],
    "sira_no": ["sira_no", "turn", "turn_id", "turn_index", "turn_number", "sequence",
                "message_index", "sira"],
    "tarih": ["tarih", "date", "timestamp", "created_at", "datetime", "time", "zaman"],
}

# "Kim soyledi" kolonu olabilecek adlar ve deger sozlukleri.
ROL_KOLON_ADLARI = ["role", "sender", "speaker", "author", "author_role", "from",
                    "rol", "kim", "gonderen", "is_bot", "inbound"]
KULLANICI_ROLLERI = {"user", "customer", "human", "client", "consumer", "kullanici",
                     "musteri", "inbound", "in", "true", "1"}
BOT_ROLLERI = {"bot", "assistant", "agent", "system", "chatbot", "support", "company",
               "asistan", "destek", "outbound", "out", "false", "0"}
METIN_KOLON_ADLARI = ["text", "message", "content", "utterance", "mesaj", "body", "value"]


def _ad_esle(kolonlar):
    """Yaygin isimlendirmeleri bizim kolon adlarimiza cevirir. {eski: yeni}."""
    kucuk = {str(k).lower().strip(): k for k in kolonlar}
    esleme = {}
    for hedef, ipuclari in KOLON_IPUCLARI.items():
        if hedef in kucuk:
            continue
        for ipucu in ipuclari:
            if ipucu in kucuk and kucuk[ipucu] not in esleme:
                esleme[kucuk[ipucu]] = hedef
                break
    return esleme


# Bu kolonlarda "true" BOT demek; genel sozlukte ise true = kullanici
# (inbound=true gibi). Ayni degerin anlami kolona gore tersine donuyor.
TERS_ROL_KOLONLARI = {"is_bot"}


def _rol_kolonu_bul(df):
    """Degerleri 'user'/'bot' gibi gorunen bir kolon var mi? (kolon_adi, harita)."""
    for kolon in df.columns:
        ad = str(kolon).lower().strip()
        if ad not in ROL_KOLON_ADLARI:
            continue
        degerler = {str(d).lower().strip() for d in df[kolon].dropna().unique()}
        if not degerler or len(degerler) > 6:
            continue
        harita = {}
        for d in degerler:
            if d in KULLANICI_ROLLERI:
                harita[d] = "kullanici"
            elif d in BOT_ROLLERI:
                harita[d] = "bot"
        if ad in TERS_ROL_KOLONLARI:
            harita = {d: ("bot" if r == "kullanici" else "kullanici")
                      for d, r in harita.items()}
        # Her iki taraf da temsil edilmeli, yoksa bu bir rol kolonu degil.
        if set(harita.values()) == {"kullanici", "bot"}:
            return kolon, harita
    return None, None


def _metin_kolonu_bul(df, disinda=()):
    for aday in METIN_KOLON_ADLARI:
        for kolon in df.columns:
            if kolon in disinda:
                continue
            if str(kolon).lower().strip() == aday:
                return kolon
    return None


def uzun_formati_cevir(df, rol_kolonu, harita, metin_kolonu):
    """'Bir satir = tek mesaj' formatini 'bir satir = soru+cevap cifti'ne cevirir.

    Ardisik ayni taraf mesajlari birlestirilir (kullanici ust uste 2 mesaj
    yazmis olabilir). Kullanici mesajindan once gelen bot karsilama mesajlari
    atlanir - degerlendirilecek bir soru yoktur.
    """
    d = df.copy()
    d["_rol"] = d[rol_kolonu].astype(str).str.lower().str.strip().map(harita)
    d = d[d["_rol"].notna()]

    if "oturum_id" not in d.columns:
        d["oturum_id"] = "otr_00000"
    if "sira_no" in d.columns:
        # Metin olarak siralanirsa "10" < "2" olur; sayiya cevirip sirala
        d["_sira"] = pd.to_numeric(d["sira_no"], errors="coerce")
        d = d.sort_values(["oturum_id", "_sira"], kind="stable")
    elif "tarih" in d.columns:
        d = d.sort_values(["oturum_id", "tarih"], kind="stable")
    else:
        d = d.sort_values("oturum_id", kind="stable")

    satirlar = []
    for oturum, grup in d.groupby("oturum_id", sort=False):
        soru, tarih, sira = [], None, 0
        for _, r in grup.iterrows():
            metin = str(r[metin_kolonu]) if pd.notna(r[metin_kolonu]) else ""
            if r["_rol"] == "kullanici":
                soru.append(metin)
                if tarih is None and "tarih" in grup.columns:
                    tarih = r["tarih"]
            elif soru:  # bot cevabi, ama once bir soru gelmis olmali
                sira += 1
                kayit = {"oturum_id": oturum, "sira_no": sira,
                         "kullanici_mesaji": " ".join(soru), "chatbot_cevabi": metin}
                if tarih is not None:
                    kayit["tarih"] = tarih
                satirlar.append(kayit)
                soru, tarih = [], None
        if soru:  # bot hic cevaplamadan oturum bitmis
            sira += 1
            kayit = {"oturum_id": oturum, "sira_no": sira,
                     "kullanici_mesaji": " ".join(soru), "chatbot_cevabi": ""}
            if tarih is not None:
                kayit["tarih"] = tarih
            satirlar.append(kayit)

    return pd.DataFrame(satirlar)


def hazirla(df):
    """Herhangi bir log tablosunu pipeline'in bekledigi bicime getirir.

    (df, rapor) doner. rapor: kullaniciya "senin dosyanda sunu gordum" demek
    icin - sessizce donusturup kullaniciyi karanlikta birakmiyoruz.
    """
    rapor = {"ad_eslemesi": {}, "uzun_format": False, "satir_once": len(df)}
    d = df.copy()

    if d.columns.duplicated().any():
        d = d.loc[:, ~d.columns.duplicated()]

    esleme = _ad_esle(d.columns)
    if esleme:
        d = d.rename(columns=esleme)
        rapor["ad_eslemesi"] = esleme

    eksik = [k for k in ZORUNLU if k not in d.columns]
    if eksik:
        rol_kolonu, harita = _rol_kolonu_bul(d)
        metin_kolonu = _metin_kolonu_bul(d, disinda=(rol_kolonu,)) if rol_kolonu else None
        if rol_kolonu and metin_kolonu:
            d = uzun_formati_cevir(d, rol_kolonu, harita, metin_kolonu)
            rapor.update({"uzun_format": True, "rol_kolonu": rol_kolonu,
                          "metin_kolonu": metin_kolonu})

    rapor["satir_sonra"] = len(d)
    return d, rapor


def sema_kontrol(df):
    """Yuklenen CSV'nin kolonlarini denetler. Hicbir sey yazmaz, sadece rapor doner."""
    kolonlar = set(df.columns)
    return {
        "eksik_zorunlu": [k for k in ZORUNLU if k not in kolonlar],
        "eksik_onerilen": [k for k in ONERILEN if k not in kolonlar],
        "mevcut_dogrulama": [k for k in DOGRULAMA if k in kolonlar],
        "satir_sayisi": len(df),
        "kolonlar": sorted(kolonlar),
    }


def normalize(df):
    """Eksik opsiyonel kolonlari makul varsayilanlarla doldurur."""
    df = df.copy()

    # Ayni ada sahip iki kolon varsa df["x"] Series yerine DataFrame doner ve
    # ilerideki .tolist()/.fillna() cagrilari cig AttributeError ile cokerdi.
    # Disaridan gelen CSV'lerde tekrarli baslik siklikla goruluyor; ilkini tut.
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated()]

    # DIKKAT: kolonun VARLIGI yetmiyor, dolu olmasi da gerekiyor. oturum_id
    # tamamen bos gelirse groupby("oturum_id") butun satirlari dusuruyor ve
    # hata cok ilerideki bir agregasyonda "string dtype" olarak patliyordu.
    if "oturum_id" not in df.columns:
        df["oturum_id"] = [f"otr_{i:05d}" for i in range(len(df))]
    else:
        bos = df["oturum_id"].isna()
        if bos.any():
            # Kolon tamamen bossa dtype float olur; string atamayi reddediyor.
            df["oturum_id"] = df["oturum_id"].astype(object)
            df.loc[bos, "oturum_id"] = [f"otr_{i:05d}" for i in np.where(bos)[0]]

    # sira_no her oturumda 1'den baslayan, tekrarsiz bir sira olmali. Kumeleme
    # sira_no==1 satirlarini aliyor; kolon yoksa (her satir 1 olur), 0'dan
    # basliyorsa (turn_index) ya da tekrar ediyorsa oturumlar ya kumelemeden
    # dusuyor ya da birden fazla "ilk tur" ile sayimlar sisiyordu. Oturum
    # icindeki sira korunarak yeniden numaralandiriliyor; esitlikte dosya
    # sirasi gecerli.
    if "sira_no" in df.columns:
        sira = pd.to_numeric(df["sira_no"], errors="coerce").fillna(0)
    else:
        sira = pd.Series(0, index=df.index)
    df["sira_no"] = sira.groupby(df["oturum_id"]).rank(method="first").astype(int)

    if "tarih" in df.columns:
        df["tarih"] = pd.to_datetime(df["tarih"], errors="coerce")
        if df["tarih"].isna().all():
            df = df.drop(columns=["tarih"])

    for kolon in ("kullanici_mesaji", "chatbot_cevabi"):
        df[kolon] = df[kolon].fillna("").astype(str)

    if "belirsiz_mesaj" in df.columns:
        df["belirsiz_mesaj"] = df["belirsiz_mesaj"].map(_evet_hayir)

    return df


EVET = {"evet", "e", "yes", "y", "true", "1", "1.0"}
HAYIR = {"hayir", "hayır", "h", "no", "n", "false", "0", "0.0"}


def _evet_hayir(deger):
    """belirsiz_mesaj farkli loglarda yes/no, True/False, 1/0 gelebiliyor.
    Panel ve rapor "evet"/"hayir" bekliyor; aksi halde "yes" belirsiz
    sayilmiyordu."""
    if pd.isna(deger):
        return None
    d = str(deger).strip().lower()
    if d in EVET:
        return "evet"
    if d in HAYIR:
        return "hayir"
    return d


# ---------------------------------------------------------------------
# Kumeleme
# ---------------------------------------------------------------------
def embed(mesajlar, model=None, ilerleme=None):
    from sentence_transformers import SentenceTransformer

    if model is None:
        if ilerleme:
            ilerleme(0.10, T("ilr_model_yukle"))
        model = SentenceTransformer(MODEL_NAME)

    if ilerleme:
        ilerleme(0.25, T("ilr_vektor").format(len(mesajlar)))

    metinler = [kurallar_temizle(m) for m in mesajlar]
    return model.encode(metinler, batch_size=32, show_progress_bar=False,
                        normalize_embeddings=True)


def kurallar_temizle(metin):
    """Hafif temizlik. Stopword atma / stemming YAPILMAZ — embedding modeli
    baglami zaten anliyor, Turkce stemming anlam kaybettirir."""
    s = str(metin).strip()
    for ch in "?!.,":
        s = s.replace(ch, " ")
    return " ".join(s.split())


def k_sec(X, k_araligi=K_ARALIGI, ilerleme=None):
    """K'yi metrik secer, elle verilmez. Silhouette en yuksek olan kazanir."""
    n = len(X)
    gecerli = [k for k in k_araligi if k < n]
    sonuclar = []
    for i, k in enumerate(gecerli):
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        etiket = km.fit_predict(X)
        # Butun mesajlar ayni (ya da bos) ise embedding'ler de ayni oluyor,
        # KMeans tek etiket uretiyor ve silhouette_score cig bir sklearn
        # hatasi firlatiyor. Bu k'yi atla, asagida topluca ele aliniyor.
        if len(set(etiket)) < 2:
            continue
        sonuclar.append({
            "k": k,
            # Silhouette O(n^2) bellek istiyor; buyuk loglarda ornekleyerek hesapla
            "silhouette": float(silhouette_score(
                X, etiket, metric="cosine",
                sample_size=min(n, SILHOUETTE_ORNEK), random_state=RANDOM_STATE)),
            "inertia": float(km.inertia_),
        })
        if ilerleme:
            ilerleme(0.40 + 0.25 * (i + 1) / len(gecerli), T("ilr_k_tarama").format(k))

    if not sonuclar:
        raise ValueError(T("hata_kumelenemedi"))

    df_k = pd.DataFrame(sonuclar)
    return int(df_k.loc[df_k["silhouette"].idxmax(), "k"]), df_k


def haritala(X, ilerleme=None):
    """2 boyuta indirger. UMAP varsa UMAP, yoksa PCA."""
    if ilerleme:
        ilerleme(0.75, T("ilr_harita"))
    try:
        import umap
        n = len(X)
        reducer = umap.UMAP(n_neighbors=min(15, max(2, n - 1)), min_dist=0.1,
                            metric="cosine", random_state=RANDOM_STATE)
        return reducer.fit_transform(X), "UMAP"
    except Exception:
        from sklearn.decomposition import PCA
        return PCA(n_components=2, random_state=RANDOM_STATE).fit_transform(X), "PCA"


def temsili_mesajlar(X, etiketler, mesajlar, merkezler, n=12):
    """Her kumenin merkezine en yakin n mesaj — LLM'e isim sordurmak icin."""
    secim = {}
    for c in sorted(set(etiketler)):
        idx = np.where(etiketler == c)[0]
        benzerlik = X[idx] @ merkezler[c]
        en_yakin = idx[np.argsort(-benzerlik)[:n]]
        secim[str(c)] = [mesajlar[i] for i in en_yakin]
    return secim


# ---------------------------------------------------------------------
# Agregasyonlar
# ---------------------------------------------------------------------
def _oran_tablosu(gruplu):
    t = gruplu.agg(["mean", "count"]).rename(
        columns={"mean": "basarisizlik_orani", "count": "oturum_sayisi"})
    t["basarisizlik_orani"] = (t["basarisizlik_orani"] * 100).round(1)
    return t.sort_values("basarisizlik_orani", ascending=False)


def basarisizlik_ozeti(oturum, gt_var):
    ozet = {
        "genel_basarisizlik_orani": round(oturum["basarisiz"].mean() * 100, 1),
        "kume_bazli": _oran_tablosu(
            oturum.dropna(subset=["kume"]).groupby("kume")["basarisiz"]
        ).reset_index().to_dict(orient="records"),
        "basarisiz_oturum_bitis_dagilimi": {
            k: int(v) for k, v in
            oturum[oturum["basarisiz"]]["son_durum"].value_counts().items()
        },
    }

    if gt_var.get("gercek_konu"):
        ozet["konu_bazli"] = _oran_tablosu(
            oturum.groupby("gercek_konu")["basarisiz"]
        ).reset_index().to_dict(orient="records")

    if gt_var.get("belirsiz_mesaj"):
        ozet["belirsiz_mesaj_etkisi"] = _oran_tablosu(
            oturum.groupby("belirsiz_mesaj")["basarisiz"]
        ).reset_index().to_dict(orient="records")

    return ozet


def trend_ozeti(oturum):
    """Zaman analizi. `tarih` yoksa None doner."""
    if "tarih" not in oturum.columns or oturum["tarih"].isna().all():
        return None

    o = oturum.dropna(subset=["tarih"]).copy()
    o["hafta"] = o["tarih"].dt.to_period("W").apply(lambda p: p.start_time)

    haftalik = _hafta_agregasyon(o)
    ozet = {
        "haftalik_genel": [
            {"hafta": str(h.date()), **r.to_dict()} for h, r in haftalik.iterrows()
        ]
    }

    # En cok oturum ureten kumede hacim patlamasi var mi (olay tespiti)
    if o["kume"].notna().any():
        buyuk_kume = o["kume"].value_counts().idxmax()
        alt = o[o["kume"] == buyuk_kume]
        alt_haftalik = _hafta_agregasyon(alt)
        if len(alt_haftalik) > 1:
            zirve = alt_haftalik["oturum_sayisi"].idxmax()
            ozet["hacim_patlamasi"] = {
                "kume": int(buyuk_kume),
                "zirve_hafta": str(zirve.date()),
                "zirve_hacim": int(alt_haftalik.loc[zirve, "oturum_sayisi"]),
                "diger_haftalar_ortalama": round(
                    float(alt_haftalik["oturum_sayisi"].drop(zirve).mean()), 1),
                "zirve_basarisizlik": float(alt_haftalik.loc[zirve, "basarisizlik_orani"]),
                "detay": [
                    {"hafta": str(h.date()), **r.to_dict()}
                    for h, r in alt_haftalik.iterrows()
                ],
            }

    # Aylik kirilim — kademeli bozulmalar burada gorunur
    o["ay"] = o["tarih"].dt.to_period("M")
    aylik = o.groupby("ay")["basarisiz"].agg(["mean", "count"])
    ozet["aylik_genel"] = [
        {"ay": str(ay), "basarisizlik_orani": round(r["mean"] * 100, 1),
         "oturum_sayisi": int(r["count"])}
        for ay, r in aylik.iterrows()
    ]

    # Her kume icin aylik seri — hangi konunun bozulduğu buradan gorunur
    if o["kume"].notna().any():
        kume_aylik = o.groupby(["kume", "ay"])["basarisiz"].agg(["mean", "count"])
        ozet["kume_aylik"] = [
            {"kume": int(k), "ay": str(ay),
             "basarisizlik_orani": round(r["mean"] * 100, 1),
             "oturum_sayisi": int(r["count"])}
            for (k, ay), r in kume_aylik.iterrows()
        ]

    return ozet


def _hafta_agregasyon(o):
    h = o.groupby("hafta").agg(
        oturum_sayisi=("basarisiz", "size"),
        basarisizlik_orani=("basarisiz", "mean"),
    )
    h["basarisizlik_orani"] = (h["basarisizlik_orani"] * 100).round(1)
    return h


# ---------------------------------------------------------------------
# ANA AKIS
# ---------------------------------------------------------------------
def calistir(df, cikti_klasoru, model=None, ilerleme=None):
    """Ham log DataFrame'ini alir, tum analizi yapar, cikti_klasoru'ne yazar.

    ilerleme: ilerleme(oran: float, mesaj: str) seklinde opsiyonel callback.
    """
    def bildir(oran, mesaj):
        if ilerleme:
            ilerleme(oran, mesaj)

    # Once bicimi otomatik tani: farkli kolon adlari ve "bir satir = tek mesaj"
    # formati burada cevriliyor. Zaten dogru formattaki veride etkisi yok.
    df, bicim = hazirla(df)

    kontrol = sema_kontrol(df)
    if kontrol["eksik_zorunlu"]:
        raise ValueError(T("hata_zorunlu_kolon").format(
            ", ".join(kontrol["eksik_zorunlu"])))

    os.makedirs(cikti_klasoru, exist_ok=True)
    bildir(0.05, T("ilr_hazirla"))
    df = normalize(df)

    gt_var = {k: (k in df.columns) for k in DOGRULAMA}

    # --- 1) Kural bazli basarisizlik tespiti (etiket KULLANILMAZ) ---
    df = kurallar.durum_ata(df)

    # Kural seti bu logun diline uyuyor mu? Uymuyorsa asagidaki butun
    # basarisizlik sayilari 0 cikar - sessizce yanlis rapor vermemek icin
    # bunu sonuca tasiyip panelde uyariya ceviriyoruz.
    kapsama = kurallar.kapsama(df)

    # --- 2) Kumeleme: sadece ilk tur mesajlari ---
    ilk_tur = df[df["sira_no"] == 1].copy().reset_index(drop=True)
    if len(ilk_tur) < 10:
        raise ValueError(T("hata_az_mesaj").format(len(ilk_tur)))

    mesajlar = ilk_tur["kullanici_mesaji"].tolist()
    X = embed(mesajlar, model=model, ilerleme=ilerleme)

    bildir(0.40, T("ilr_k_ara"))
    en_iyi_k, df_k = k_sec(X, ilerleme=ilerleme)

    bildir(0.68, T("ilr_kumele").format(en_iyi_k))
    km = KMeans(n_clusters=en_iyi_k, random_state=RANDOM_STATE, n_init=10)
    etiketler = km.fit_predict(X)

    koordinat, yontem = haritala(X, ilerleme=ilerleme)
    ilk_tur["kume"] = etiketler
    ilk_tur["umap_x"] = koordinat[:, 0]
    ilk_tur["umap_y"] = koordinat[:, 1]

    # --- 3) Oturum seviyesine indir ---
    bildir(0.85, T("ilr_analiz"))
    grup = df.groupby("oturum_id")
    oturum = pd.DataFrame({
        "basarisiz": grup["tespit_durum"].apply(lambda s: (s != "basarili").any()),
        "son_durum": grup["tespit_durum"].last(),
    }).reset_index()

    if "tarih" in df.columns:
        ilk_tarih = df[df["sira_no"] == 1].set_index("oturum_id")["tarih"]
        oturum["tarih"] = oturum["oturum_id"].map(ilk_tarih)

    for kolon in ("gercek_konu", "belirsiz_mesaj"):
        if gt_var[kolon]:
            oturum[kolon] = oturum["oturum_id"].map(grup[kolon].first())

    oturum = oturum.merge(ilk_tur[["oturum_id", "kume"]], on="oturum_id", how="left")

    # --- 4) Agregasyonlar ---
    basarisizlik = basarisizlik_ozeti(oturum, gt_var)
    trend = trend_ozeti(oturum)

    # --- 5) Dogrulama (ground truth varsa) ---
    dogrulama = {"yontem": yontem, "secilen_k": en_iyi_k}

    if gt_var["gercek_konu"]:
        # Bos hucreler NaN (float) olarak gelir; metinle karisinca sklearn
        # siralama hatasi veriyor. Hepsini metne cevir.
        gercek = ilk_tur["gercek_konu"].fillna("-").astype(str).values
        dogrulama["ari"] = round(float(adjusted_rand_score(gercek, etiketler)), 3)
        dogrulama["nmi"] = round(float(normalized_mutual_info_score(gercek, etiketler)), 3)
        ct = pd.crosstab(pd.Series(gercek, name="gercek_konu"),
                         pd.Series(etiketler, name="kume"))
        dogrulama["kume_saflik"] = [
            {"kume": int(c), "baskin_konu": str(ct[c].idxmax()),
             "saflik": round(float(ct[c].max() / ct[c].sum()) * 100, 1),
             "n": int(ct[c].sum())}
            for c in ct.columns
        ]

    if gt_var["sonuc_durumu"]:
        kural_sonuc = kurallar.dogrula(df)
        dogrulama["kural_tam_dogruluk"] = kural_sonuc["tam_eslesme_orani"]
        dogrulama["kural_ikili_dogruluk"] = kural_sonuc["ikili_dogruluk"]

    # --- 6) Diske yaz ---
    bildir(0.95, T("ilr_kaydet"))
    yol = lambda ad: os.path.join(cikti_klasoru, ad)

    # Onceki analizden kalan dosyalari temizle. NEDEN: her cikti her calismada
    # yeniden yazilmiyor - trend_ozet.json sadece tarih kolonu varsa,
    # kume_isimleri.json ve llm_raporu.md ise ayri adimlarda uretiliyor.
    # Temizlemezsek A veri setini analiz edip sonra B'yi analiz eden biri,
    # B'nin kumelerinin yaninda A'nin trend grafigini ve rapor metnini
    # gorur - sessizce iki veri seti karisir.
    for eski in ("trend_ozet.json", "kume_isimleri.json", "llm_raporu.md",
                 "llm_raporu_tr.md", "llm_raporu_en.md"):
        p = yol(eski)
        if os.path.exists(p):
            os.remove(p)

    ilk_tur.to_csv(yol("kumeleme_sonuclari.csv"), index=False, encoding="utf-8-sig")
    df_k.to_csv(yol("k_secim_metrikleri.csv"), index=False)
    np.save(yol("embeddings.npy"), X)

    basarisizlik["kural_kapsamasi"] = kapsama
    _json_yaz(yol("basarisizlik_ozet.json"), basarisizlik)
    _json_yaz(yol("dogrulama.json"), dogrulama)
    _json_yaz(yol("temsili_mesajlar.json"),
              temsili_mesajlar(X, etiketler, mesajlar, km.cluster_centers_))
    if trend:
        _json_yaz(yol("trend_ozet.json"), trend)

    bildir(1.0, T("ilr_tamam"))
    return {
        "cikti_klasoru": cikti_klasoru,
        "oturum_sayisi": len(oturum),
        "kume_sayisi": en_iyi_k,
        "dogrulama": dogrulama,
        "trend_var": trend is not None,
        "ground_truth": gt_var,
        "kural_kapsamasi": kapsama,
    }


def _json_yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
