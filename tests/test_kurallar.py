import pandas as pd
import pytest

import kurallar
from kurallar import cevap_sinifla


@pytest.mark.parametrize("cevap", [
    "Ne demek istediğinizi anlayamadım, tekrar ifade eder misiniz?",
    "Üzgünüm, bu konuda yardımcı olamıyorum.",
    "I'm not sure I follow, could you rephrase?",
    "Sorry, I don't understand your question.",
    "I can't help with that request.",
])
def test_fallback(cevap):
    assert cevap_sinifla(cevap) == "fallback"


def test_buyuk_I_ingilizce_kalibi_bozmuyor():
    # tr_kucult "I"yi "ı" yapiyor; kaliplar iki bicimde de aranmali
    assert cevap_sinifla("I'M NOT SURE WHAT YOU MEAN") == "fallback"


@pytest.mark.parametrize("cevap", [
    "Sizi müşteri temsilcimize aktarıyorum.",
    "Konuyu yetkili birime yönlendiriyorum.",
    "I'm transferring you to a human agent now.",
    "Let me connect you with our support team.",
])
def test_insana_devir(cevap):
    assert cevap_sinifla(cevap) == "yetkiliye_yonlendirme"


@pytest.mark.parametrize("cevap", [
    # Devir fiili var ama insan hedefi yok -> basarili
    "Sizi uygun kampanyalara yönlendiriyorum.",
    "I'm redirecting you to our latest offers.",
    # Insan hedefi var ama devir yok -> basarili
    "Teknisyenimiz yarın sizi arayacak, temsilci notunu ekledim.",
])
def test_tek_parca_devir_sayilmaz(cevap):
    assert cevap_sinifla(cevap) == "basarili"


def test_ingilizce_detay_istemek_bilerek_fallback_degil():
    # Olculdu: bu kalip Ingilizcede rutin netlestirme, orani sisiriyordu
    assert cevap_sinifla("Could you provide more details about the error?") == "basarili"


def test_ikinci_turda_fallback_tekrarli_soru():
    assert cevap_sinifla("Anlayamadım.", sira_no=1) == "fallback"
    assert cevap_sinifla("Anlayamadım.", sira_no=2) == "tekrarli_soru"


def test_kapsama_baska_dilde_uyarir():
    df = pd.DataFrame({"chatbot_cevabi": ["Ich habe das nicht verstanden."] * 30})
    assert kurallar.kapsama(df)["kural_uymuyor"] is True


def test_kapsama_kucuk_logda_uyarmaz():
    df = pd.DataFrame({"chatbot_cevabi": ["Ich habe das nicht verstanden."] * 29})
    assert kurallar.kapsama(df)["kural_uymuyor"] is False


def test_ornek_veride_etiketi_geri_uretir():
    """Sentetik verideki sonuc_durumu etiketi kurallarla birebir uretilmeli."""
    df = pd.read_csv("telekom_chatbot_loglari.csv")
    sonuc = kurallar.dogrula(df)
    assert sonuc["ikili_dogruluk"] == 100.0
    assert sonuc["tam_eslesme_orani"] == 100.0
