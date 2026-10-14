from streamlit.testing.v1 import AppTest

import llm
from diller import T


def _panel():
    import dashboard
    dashboard._llm_paneli()


def test_bulunan_model_kutuya_hemen_yansir(monkeypatch):
    monkeypatch.setattr(llm, "calisan_model_bul", lambda ayar, *a, **k: (True, "bulunan/model"))
    monkeypatch.setattr(llm, "ayarlari_kaydet", lambda ayar: ayar)
    at = AppTest.from_function(_panel).run()
    dugme = [b for b in at.sidebar.button if b.label == T("calisan_model_bul")][0]
    at = dugme.click().run()
    kutu = [t for t in at.sidebar.text_input if t.label == T("model")][0]
    assert kutu.value == "bulunan/model"
    assert at.session_state["ayar"]["model"] == "bulunan/model"
    assert any("bulunan/model" in s.value for s in at.sidebar.success)


def test_anahtar_saglayici_degisince_tasinmaz():
    at = AppTest.from_function(_panel).run()
    sag = at.sidebar.selectbox[0]
    hf = [o for o in sag.options if "Hugging" in o][0]
    nv = [o for o in sag.options if "NVIDIA" in o][0]
    at = sag.select(hf).run()
    kutu = lambda: [t for t in at.sidebar.text_input if t.label == T("api_anahtari")][0]
    at = kutu().input("hf_token").run()
    at = at.sidebar.selectbox[0].select(nv).run()
    assert kutu().value == ""
    assert at.session_state["api_key"] == ""
    at = at.sidebar.selectbox[0].select(hf).run()
    assert kutu().value == "hf_token"
