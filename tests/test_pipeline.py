import json
import os

import numpy as np
import pandas as pd
import pytest

import pipeline


# ---------------------------------------------------------------------
# Bicim algilama
# ---------------------------------------------------------------------
def test_yaygin_kolon_adlari_eslenir():
    df = pd.DataFrame({"instruction": ["soru"], "response": ["cevap"],
                       "conversation_id": [1]})
    d, rapor = pipeline.hazirla(df)
    assert {"kullanici_mesaji", "chatbot_cevabi", "oturum_id"} <= set(d.columns)
    assert rapor["uzun_format"] is False


def test_rol_kolonlu_uzun_format_ciftlere_cevrilir():
    df = pd.DataFrame({
        "session_id": [1, 1, 1, 1, 2, 2],
        "role": ["assistant", "user", "user", "assistant", "user", "assistant"],
        "content": ["Merhaba!", "Faturam", "yüksek geldi", "Kontrol ediyorum",
                    "Modem", "Yeniden başlatın"],
    })
    d, rapor = pipeline.hazirla(df)
    assert rapor["uzun_format"] is True
    # Karsilama atlanir, ardisik kullanici mesajlari birlesir
    assert d["kullanici_mesaji"].tolist() == ["Faturam yüksek geldi", "Modem"]
    assert d["chatbot_cevabi"].tolist() == ["Kontrol ediyorum", "Yeniden başlatın"]


def test_is_bot_kolonu_ters_anlamli():
    # is_bot=True BOT demek (inbound=True ise kullanici demek)
    df = pd.DataFrame({"chat_id": [1, 1], "is_bot": [False, True],
                       "text": ["kullanici sorusu", "bot cevabi"]})
    d, _ = pipeline.hazirla(df)
    assert d.iloc[0]["kullanici_mesaji"] == "kullanici sorusu"
    assert d.iloc[0]["chatbot_cevabi"] == "bot cevabi"


def test_tur_numarasi_sayisal_siralanir():
    # Metin siralamasinda "10" < "2" olurdu
    tur = ["1", "2", "10", "11"]
    df = pd.DataFrame({"chat_id": [1] * 4, "turn": tur,
                       "role": ["user", "bot", "user", "bot"],
                       "text": ["ilk", "c1", "ikinci", "c2"]})
    d, _ = pipeline.hazirla(df.iloc[[2, 0, 3, 1]])
    assert d["kullanici_mesaji"].tolist() == ["ilk", "ikinci"]


# ---------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------
def _ham(**kolonlar):
    n = len(next(iter(kolonlar.values())))
    return pd.DataFrame({"kullanici_mesaji": ["m"] * n, "chatbot_cevabi": ["c"] * n,
                         **kolonlar})


def test_sira_no_yoksa_dosya_sirasi_kullanilir():
    df = pipeline.normalize(_ham(oturum_id=[1, 1, 2, 1]))
    assert df["sira_no"].tolist() == [1, 2, 1, 3]


def test_sira_no_sifirdan_baslasa_da_ilk_tur_1():
    df = pipeline.normalize(_ham(oturum_id=[1, 1, 2], sira_no=[0, 1, 0]))
    assert df["sira_no"].tolist() == [1, 2, 1]


def test_tekrarli_sira_no_tek_ilk_tur_uretir():
    df = pipeline.normalize(_ham(oturum_id=[1, 1, 1], sira_no=[1, 1, 2]))
    assert (df["sira_no"] == 1).sum() == 1


def test_bos_oturum_id_doldurulur():
    df = pipeline.normalize(_ham(oturum_id=[None, None]))
    assert df["oturum_id"].notna().all()
    assert df["oturum_id"].nunique() == 2


@pytest.mark.parametrize("deger, beklenen", [
    ("evet", "evet"), ("yes", "evet"), ("True", "evet"), (1, "evet"),
    ("hayir", "hayir"), ("no", "hayir"), (False, "hayir"), (0, "hayir"),
])
def test_belirsiz_mesaj_degerleri_birlesir(deger, beklenen):
    df = pipeline.normalize(_ham(belirsiz_mesaj=[deger]))
    assert df["belirsiz_mesaj"].iloc[0] == beklenen


# ---------------------------------------------------------------------
# Uctan uca (embedding modeli indirilmeden)
# ---------------------------------------------------------------------
KONULAR = {
    "fatura": ("Faturam neden yüksek geldi", "Faturanızı kontrol ettim, tutar doğru."),
    "modem": ("Modemim sürekli kopuyor", "Anlayamadım, tekrar ifade eder misiniz?"),
    "iptal": ("Aboneliğimi iptal etmek istiyorum", "Sizi müşteri temsilcimize aktarıyorum."),
}


def _sahte_embed(mesajlar, model=None, ilerleme=None):
    """Her konuya ayri bir eksen: KMeans konulari kusursuz ayirabilmeli."""
    rng = np.random.default_rng(0)
    eksen = {k: i for i, k in enumerate(KONULAR)}
    X = np.zeros((len(mesajlar), len(KONULAR)))
    for i, m in enumerate(mesajlar):
        konu = next(k for k, (soru, _) in KONULAR.items() if m.startswith(soru))
        X[i, eksen[konu]] = 1.0
    X += rng.normal(0, 0.01, X.shape)
    return X / np.linalg.norm(X, axis=1, keepdims=True)


@pytest.fixture
def ornek_log():
    satirlar = []
    for i in range(60):
        konu = list(KONULAR)[i % 3]
        soru, cevap = KONULAR[konu]
        satirlar.append({"session_id": i, "user_message": f"{soru} #{i}",
                         "bot_response": cevap, "gercek_konu": konu,
                         "timestamp": f"2026-0{1 + i % 3}-{1 + i % 28:02d}"})
    return pd.DataFrame(satirlar)


def test_uctan_uca_analiz(ornek_log, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "embed", _sahte_embed)
    # Onceki analizden kalan dosyalar silinmeli (iki veri seti karismasin)
    for eski in ("kume_isimleri.json", "llm_raporu_en.md"):
        (tmp_path / eski).write_text("{}")

    sonuc = pipeline.calistir(ornek_log, str(tmp_path))

    assert sonuc["oturum_sayisi"] == 60
    assert sonuc["kume_sayisi"] == 3
    assert sonuc["dogrulama"]["ari"] == 1.0
    assert not (tmp_path / "kume_isimleri.json").exists()
    assert not (tmp_path / "llm_raporu_en.md").exists()

    ozet = json.loads((tmp_path / "basarisizlik_ozet.json").read_text())
    # modem (fallback) ve iptal (devir) basarisiz: 40 / 60
    assert ozet["genel_basarisizlik_orani"] == pytest.approx(66.7)
    assert set(ozet["basarisiz_oturum_bitis_dagilimi"]) == {"fallback", "yetkiliye_yonlendirme"}
    for dosya in ("kumeleme_sonuclari.csv", "temsili_mesajlar.json", "trend_ozet.json"):
        assert os.path.exists(tmp_path / dosya)


def test_cok_az_konusma_net_hata_verir(ornek_log, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "embed", _sahte_embed)
    with pytest.raises(ValueError):
        pipeline.calistir(ornek_log.head(5), str(tmp_path))


def test_zorunlu_kolon_yoksa_net_hata_verir(tmp_path):
    with pytest.raises(ValueError):
        pipeline.calistir(pd.DataFrame({"x": range(20)}), str(tmp_path))
