"""
Kural Bazli Basarisizlik Tespiti
---------------------------------
Bir chatbot cevabinin basarili olup olmadigini SADECE cevap metninden anlar.

Neden onemli: Gercek chatbot loglarinda `sonuc_durumu` diye hazir bir etiket
YOKTUR. Sentetik veri setimizde var, ama o etiketi kullanan bir sistem gercek
loglara uygulanamaz. Bu modul etiketi metinden yeniden uretir; boylece pipeline
etiketsiz loglarda da calisir.

Sentetik veri uzerinde bu kurallarin `sonuc_durumu` etiketini ne kadar
dogru geri urettigi `dogrula()` ile olculur.
"""

import re

# ---------------------------------------------------------------------
# Turkce kucuk harf. Python'un .lower() metodu "I" ve "İ" harflerini bozar:
#   "İSTANBUL".lower() -> "i̇stanbul"  (araya birlesik nokta giriyor)
# ---------------------------------------------------------------------
def tr_kucult(s):
    return str(s).replace("İ", "i").replace("I", "ı").lower()


# ---------------------------------------------------------------------
# Kalip sozlukleri
#
# Bunlar "anahtar kelime" degil, chatbot'un pes etme/aktarma kaliplaridir.
# Yeni bir chatbot'a uyarlarken degistirilmesi gereken tek yer burasidir.
# ---------------------------------------------------------------------

# Bot anlamadi / islemi yapamadi
#
# Kaliplar DILE OZELDIR. Turkce ve Ingilizce setleri birlikte tutuluyor:
# bir chatbot ikisini ayni cevapta karistirmadigi icin yanlis pozitif riski
# yok, buna karsilik dil tespitine hic gerek kalmiyor. Baska bir dil icin
# calisilacaksa buraya o dilin kaliplari eklenir - `kapsama()` hic eslesme
# olmadigini soyluyorsa eksik olan tam da budur.
FALLBACK_KALIPLARI = [
    # --- Turkce ---
    r"anlay[ae]mad",          # anlayamadım, anlayamadı
    r"anlamad[ıi]m",          # anlamadım
    r"i[şs]leyemiyorum",      # işleyemiyorum
    r"yard[ıi]mc[ıi] olam",   # yardımcı olamıyorum
    r"tekrar ifade",          # tekrar ifade eder misiniz
    r"yeniden yaz",           # yeniden yazar mısınız
    r"farkl[ıi] bir [şs]ekilde",
    r"daha detay",
    r"detay verebilir",
    r"ne demek istedi",
    r"emin de[ğg]ilim",
    r"bilgim yok",
    # --- Ingilizce ---
    r"(?:do not|don't|didn't|did not) understand",
    r"(?:didn't|did not) (?:quite )?catch",
    r"could you (?:please )?(?:rephrase|clarify|repeat)",
    r"(?:rephrase|clarify) (?:your|that)",
    r"(?:i'm|i am) not sure",
    r"(?:do not|don't) have (?:that|this|enough) information",
    r"(?:unable|not able) to (?:help|assist)",
    r"(?:can't|cannot) (?:help|assist)",
    r"what do you mean",
    # NOT: Turkcedeki "daha detay" / "detay verebilir" karsiligi olan
    # "provide more details" BILEREK yok. Turkcede bu kalip pes etmeyle
    # birlikte geliyor (tespitlerin %12'si), Ingilizcede ise rutin bir
    # netlestirme sorusu - olcum yapildi: tek basina tespitlerin %76'sini
    # uretip orani %1.8'den %7.2'ye sisiriyordu. Ayni cumle iki dilde ayni
    # seyi ifade etmiyor; kural seti zaten dile ozel.
]

# Bot insana devrediyor.
#
# DIKKAT: "yonlendiriyorum" / "aktariyorum" gibi fiiller TEK BASINA yeterli
# degil. Denendi ve yanlis pozitif verdi:
#   "Sizi uygun kampanyalara yonlendiriyorum..."      -> satis, basarili
#   "Randevunuzu olusturdum, teknisyen sizi arayacak" -> randevu, basarili
# Bu yuzden kural iki parcali: bir DEVIR FIILI ve ayni cevapta bir INSAN
# HEDEFI birlikte gecmeli. "teknisyen" ve "teknik ekip" bilerek disarida -
# onlar sahaya gonderilen kisiler, chatbot'un pes ettigi anlamina gelmez.
INSAN_HEDEFI_KALIPLARI = [
    # --- Turkce ---
    r"temsilci",
    r"uzman[ıi]m[ıi]z",
    r"yetkili",
    r"ilgili birim",
    r"m[üu][şs]teri hizmetleri",
    r"canl[ıi] destek",
    r"dan[ıi][şs]man",
    # --- Ingilizce --- ("technician"/"engineer" bilerek yok: onlar da sahaya
    # gonderilen kisiler, bot'un pes ettigi anlamina gelmez.
    r"representative",
    r"(?:human|live) agent",
    r"customer (?:service|support)",
    r"support team",
    r"live chat",
    r"specialist",
    r"supervisor",
]

DEVIR_FIILI_KALIPLARI = [
    # --- Turkce ---
    r"aktar[ıi]yorum",
    r"y[öo]nlendiriyorum",
    r"ba[ğg]l[ıi]yorum",
    r"devrediyorum",
    r"ge[çc]iriyorum",
    # --- Ingilizce ---
    r"transfer(?:ring)? you",
    r"connect(?:ing)? you",
    r"put(?:ting)? you through",
    r"forward(?:ing)? (?:you|your)",
    r"escalat",
    r"redirect(?:ing)? you",
    r"hand(?:ing)? (?:you )?over",
]

FALLBACK_RE = re.compile("|".join(FALLBACK_KALIPLARI))
INSAN_HEDEFI_RE = re.compile("|".join(INSAN_HEDEFI_KALIPLARI))
DEVIR_FIILI_RE = re.compile("|".join(DEVIR_FIILI_KALIPLARI))


def _bicimler(cevap):
    """Metnin iki kucuk harf bicimi: Turkce kurali ve duz .lower().

    NEDEN IKISI: tr_kucult buyuk "I"yi "ı" yapiyor (Turkce icin dogru), ama
    bu Ingilizce metni bozuyor - "I'm not sure" -> "ı'm not sure" olunca
    hicbir Ingilizce kalip tutmuyordu. Kaliplari her iki bicimde de arayarak
    iki dil de dogru calisiyor; kaliplara tek tek [iı] yazmaktan guvenli.
    """
    s = str(cevap)
    return (tr_kucult(s), s.lower())


def _herhangi(kalip_re, bicimler):
    return any(kalip_re.search(b) for b in bicimler)


def cevap_sinifla(cevap, sira_no=1):
    """Tek bir bot cevabini siniflar.

    sira_no > 1 ise kullanici ayni seyi tekrar sormak zorunda kalmis demektir;
    ayni fallback metni ilk turda 'fallback', ikinci turda 'tekrarli_soru'dur.
    """
    bicimler = _bicimler(cevap)

    if _herhangi(INSAN_HEDEFI_RE, bicimler) and _herhangi(DEVIR_FIILI_RE, bicimler):
        return "yetkiliye_yonlendirme"
    if _herhangi(FALLBACK_RE, bicimler):
        return "tekrarli_soru" if sira_no and sira_no > 1 else "fallback"
    return "basarili"


def durum_ata(df, cevap_kolonu="chatbot_cevabi", sira_kolonu="sira_no"):
    """DataFrame'e `tespit_durum` kolonu ekler."""
    df = df.copy()
    sira = df[sira_kolonu] if sira_kolonu in df.columns else 1
    if isinstance(sira, int):
        df["tespit_durum"] = [cevap_sinifla(c, 1) for c in df[cevap_kolonu]]
    else:
        df["tespit_durum"] = [
            cevap_sinifla(c, s) for c, s in zip(df[cevap_kolonu], sira)
        ]
    return df


def kapsama(df, cevap_kolonu="chatbot_cevabi"):
    """Kural setinin bu loga ne kadar degdigini olcer.

    NEDEN: Kaliplar dile ozel. Baska dilde (ya da cok farkli uslupta) bir
    chatbot logunda hicbiri eslesmez ve sistem "basarisizlik %0" diye
    guven verici ama YANLIS bir sonuc uretir - hata da vermez. Bu fonksiyon
    o sessiz basarisizligi gorunur kilar: hic eslesme yoksa sorun logda
    degil, kural setinin o dili tanimamasindadir.
    """
    d = durum_ata(df, cevap_kolonu=cevap_kolonu)
    n = len(d)
    eslesen = int((d["tespit_durum"] != "basarili").sum())
    return {
        "satir": n,
        "eslesen": eslesen,
        "oran": round(eslesen / n * 100, 1) if n else 0.0,
        # Anlamli buyuklukte bir logda tek bir kalip bile tutmadiysa kural
        # setinin bu veriye uymadigini varsayiyoruz.
        "kural_uymuyor": bool(n >= 30 and eslesen == 0),
    }


def dogrula(df):
    """Kurallarin `sonuc_durumu` etiketini ne kadar dogru geri urettigini olcer.
    Sadece etiket varsa anlamli - gercek loglarda cagrilmaz."""
    if "sonuc_durumu" not in df.columns:
        return None

    import pandas as pd
    df = durum_ata(df)
    dogru = (df["tespit_durum"] == df["sonuc_durumu"])

    # Asil onemli soru: "basarili mi degil mi" ikili ayrimi tutuyor mu?
    ikili_gercek = df["sonuc_durumu"] != "basarili"
    ikili_tespit = df["tespit_durum"] != "basarili"
    ikili_dogru = (ikili_gercek == ikili_tespit)

    return {
        "satir_sayisi": len(df),
        "tam_eslesme_orani": round(dogru.mean() * 100, 1),
        "ikili_dogruluk": round(ikili_dogru.mean() * 100, 1),
        "karisiklik_matrisi": pd.crosstab(
            df["sonuc_durumu"], df["tespit_durum"]
        ),
    }


if __name__ == "__main__":
    import pandas as pd
    df = pd.read_csv("telekom_chatbot_loglari.csv")
    sonuc = dogrula(df)
    print("=" * 72)
    print("KURAL BAZLI TESPIT - DOGRULAMA (sentetik etikete karsi)")
    print("=" * 72)
    print(f"Satir sayisi            : {sonuc['satir_sayisi']}")
    print(f"Tam siniflama dogrulugu : %{sonuc['tam_eslesme_orani']}")
    print(f"Basarili/basarisiz ayrimi: %{sonuc['ikili_dogruluk']}")
    print("\nKarisiklik matrisi (satir=etiket, sutun=kuralin tespiti):")
    print(sonuc["karisiklik_matrisi"].to_string())
