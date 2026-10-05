"""
Chatbot Konusma Kalitesi Analiz Paneli
--------------------------------------
Calistirma:  streamlit run dashboard.py   (ya da start.command / start.bat)

Kullanicinin yukledigi log dosyasi uzerinde pipeline'i bastan calistirir
(embedding + kumeleme + kural bazli tespit + trend) ve sonuclari gosterir.
Cikti `yuklenen_analiz/` altinda tutulur; panel acildiginda orada hazir bir
analiz varsa onu okur, yoksa karsilama ekrani gosterir.
"""

import html
import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import llm
from diller import DILLER, T

st.set_page_config(
    page_title="Chatbot Quality Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

YUKLENEN_KLASOR = "yuklenen_analiz"

# ---------------------------------------------------------------------
# Palet — dataviz kilavuzundaki dogrulanmis kategorik sira.
# Sira SABIT: bir kume her zaman ayni rengi alir, filtre degisince
# renkler yeniden dagitilmaz.
# ---------------------------------------------------------------------
def _koyu_mu():
    try:
        return (st.get_option("theme.base") or "light") == "dark"
    except Exception:
        return False


KOYU = _koyu_mu()

PALET = (["#3987e5", "#d95926", "#199e70", "#c98500",
          "#d55181", "#008300", "#9085e9", "#e66767"] if KOYU else
         ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"])

MUREKKEP      = "#ffffff"  if KOYU else "#0b0b0b"
MUREKKEP_IKI  = "#c3c2b7"  if KOYU else "#52514e"
SOLUK         = "#898781"
IZGARA        = "#2c2c2a"  if KOYU else "#e1e0d9"
YUZEY         = "#1a1a19"  if KOYU else "#fcfcfb"

KRITIK = "#d03b3b"   # status: critical — sadece basarisizlik icin
IYI    = "#0ca30c"   # status: good

CSS = f"""
<style>
  .block-container {{ padding-top: 2.2rem; max-width: 1400px; }}
  #MainMenu, footer {{ visibility: hidden; }}

  .baslik   {{ font-size: 1.9rem; font-weight: 650; letter-spacing: -0.02em;
               margin: 0 0 .15rem 0; color: {MUREKKEP}; }}
  .altbilgi {{ font-size: .88rem; color: {SOLUK}; margin: 0 0 1.4rem 0; }}

  .kpi-satir {{ display: flex; gap: .75rem; margin-bottom: 1.6rem; flex-wrap: wrap; }}
  .kpi {{ flex: 1 1 160px; background: {YUZEY}; border: 1px solid {IZGARA};
          border-radius: 10px; padding: .85rem 1rem; }}
  .kpi-etiket {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .06em;
                 color: {SOLUK}; margin-bottom: .3rem; }}
  .kpi-deger  {{ font-size: 1.75rem; font-weight: 620; line-height: 1.1;
                 color: {MUREKKEP}; }}
  .kpi-not    {{ font-size: .72rem; color: {SOLUK}; margin-top: .2rem; }}

  section[data-testid="stSidebar"] {{ border-right: 1px solid {IZGARA}; }}
  section[data-testid="stSidebar"] h3 {{ font-size: .82rem !important;
      text-transform: uppercase; letter-spacing: .06em; color: {SOLUK} !important;
      margin-top: 1.1rem !important; }}

  .stTabs [data-baseweb="tab-list"] {{ gap: .3rem; }}
  .stTabs [data-baseweb="tab"] {{ padding: .5rem 1rem; }}

  .aciklama {{ font-size: .82rem; color: {SOLUK}; line-height: 1.5;
               border-left: 2px solid {IZGARA}; padding-left: .7rem; margin: .2rem 0 1rem 0; }}
</style>
"""


def duzen(fig, yukseklik=340, baslik=None, sag_bosluk=8):
    """Tum grafiklere ayni iskeleti uygular: recessive izgara, sade eksen.

    sag_bosluk: textposition="outside" kullanan yatay barlarda etiketin
    kirpilmamasi icin sag margin'i buyutmek gerekiyor."""
    if baslik:
        fig.update_layout(title=dict(text=baslik, font=dict(size=14, color=MUREKKEP),
                                     x=0, xanchor="left"))
    fig.update_layout(
        height=yukseklik,
        margin=dict(l=8, r=sag_bosluk, t=38 if baslik else 12, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, -apple-system, sans-serif",
                  size=12, color=MUREKKEP_IKI),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(size=11)),
        hoverlabel=dict(font_size=12),
    )
    # automargin: uzun kume isimleri sol margin'e sigmayinca plotly yeri kendisi
    # buyutsun, yoksa etiketler kirpilir.
    fig.update_xaxes(showgrid=False, linecolor=IZGARA, automargin=True,
                     tickfont=dict(color=SOLUK, size=11))
    fig.update_yaxes(gridcolor=IZGARA, zeroline=False, linecolor="rgba(0,0,0,0)",
                     automargin=True, tickfont=dict(color=SOLUK, size=11))
    return fig


# ---------------------------------------------------------------------
# Veri yukleme
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _json_oku(yol, _damga):
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def _csv_oku(yol, _damga):
    return pd.read_csv(yol) if os.path.exists(yol) else None


@st.cache_data(show_spinner=False)
def _metin_oku(yol, _damga):
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _damga(klasor):
    """Klasordeki dosyalar degisince cache bozulsun diye."""
    try:
        return max((os.path.getmtime(os.path.join(klasor, d))
                    for d in os.listdir(klasor)), default=0)
    except OSError:
        return 0


def veri_seti_yukle(klasor):
    d = _damga(klasor)
    y = lambda ad: os.path.join(klasor, ad)
    return {
        "kumeler":      _csv_oku(y("kumeleme_sonuclari.csv"), d),
        "basarisizlik": _json_oku(y("basarisizlik_ozet.json"), d),
        "trend":        _json_oku(y("trend_ozet.json"), d),
        "isimler":      _dil_isimleri(_json_oku(y("kume_isimleri.json"), d)),
        "dogrulama":    _json_oku(y("dogrulama.json"), d),
        "raporlar":     _raporlari_oku(klasor, d),
        "klasor":       klasor,
    }


def _rapor_yolu(klasor, dil):
    return os.path.join(klasor, f"llm_raporu_{dil}.md")


def _raporlari_oku(klasor, damga):
    """{dil: metin}. Rapor dil bazinda ayri dosyada tutulur; dil degisince
    diger dilin raporu gosterilmez. Eski tek dosya (llm_raporu.md) varsa
    dili sabit baslik sablonundan anlasilir."""
    raporlar = {}
    for dil in DILLER:
        metin = _metin_oku(_rapor_yolu(klasor, dil), damga)
        if metin:
            raporlar[dil] = metin
    eski = _metin_oku(os.path.join(klasor, "llm_raporu.md"), damga)
    if eski:
        dil = "en" if "## Executive Summary" in eski else "tr"
        raporlar.setdefault(dil, eski)
    return raporlar


def _isim_dosyasi(ham):
    """kume_isimleri.json dil bazinda tutulur: {"tr": {...}, "en": {...}}.
    i18n oncesi duz format ({"0": "..."}) Turkce uretilmisti, "tr" sayilir."""
    if not ham:
        return {}
    if all(k in DILLER for k in ham):
        return ham
    return {"tr": ham}


def _dil_isimleri(ham):
    # Panel dilinde isim yoksa bos doner -> isimlendirme butonu yeniden cikar
    return dict(_isim_dosyasi(ham).get(st.session_state.get("dil", "tr"), {}))


def kume_adi(no, isimler):
    """Grafiklerde kullanilacak kume adi - HTML kacisli.

    Isimler LLM'den, LLM'in girdisi de yuklenen logdan geliyor. Plotly etiket
    ve hover metinlerinde <a>, <b> gibi etiketleri yorumladigi icin kacislanmazsa
    logdaki bir metin grafikte calisan bir baglantiya donusebilir."""
    return html.escape(str(isimler.get(str(no), T("kume").format(no))))


def _kacis(seri):
    """Kullanici verisini Plotly metnine guvenle koymak icin."""
    return [html.escape(str(v)) for v in seri]


def _tr_mi():
    return st.session_state.get("dil", "tr") == "tr"


def yuzde(v):
    """Turkcede isaret basta (%29.0), Ingilizcede sonda (29.0%)."""
    return f"%{v}" if _tr_mi() else f"{v}%"


def sayi(n):
    """Binlik ayirici: Turkcede nokta (1.234), Ingilizcede virgul (1,234)."""
    metin = f"{n:,}"
    return metin.replace(",", ".") if _tr_mi() else metin


def kume_rengi(no):
    return PALET[int(no) % len(PALET)]


# ---------------------------------------------------------------------
# Yan panel
# ---------------------------------------------------------------------
def yan_panel():
    sb = st.sidebar

    # Dil secici en ustte: kullanici once dili secsin, sonra geri kalani okusun.
    # Ilk acilista ?lang=en adres parametresi varsayilan dili belirler.
    kodlar = list(DILLER)
    if "dil" not in st.session_state and st.query_params.get("lang") in DILLER:
        st.session_state["dil"] = st.query_params["lang"]
    sb.radio(T("dil"), kodlar, key="dil", horizontal=True,
             format_func=lambda k: DILLER[k])

    sb.markdown("### " + T("veri_kaynagi"))

    with sb.expander(T("yukle_baslik"), expanded=True):
        st.caption(T("yukle_aciklama"))
        st.markdown(
            f'''<div class="aciklama">{T("yukle_yardim")}</div>''',
            unsafe_allow_html=True)

        dosya = st.file_uploader(T("yukleyici"),
                                 type=["csv", "json", "jsonl"],
                                 label_visibility="collapsed")
        if dosya is not None:
            _yukleme_akisi(dosya)

    _llm_paneli()
    return YUKLENEN_KLASOR


def _dosya_oku(dosya):
    """CSV, JSON ve JSONL kabul eder - chatbot platformlarinin cogu JSON yaziyor."""
    ad = (dosya.name or "").lower()
    if ad.endswith(".jsonl"):
        return pd.read_json(dosya, lines=True)
    if ad.endswith(".json"):
        return pd.json_normalize(json.load(dosya))
    return pd.read_csv(dosya)


def _yukleme_akisi(dosya):
    import pipeline

    try:
        ham = _dosya_oku(dosya)
    except Exception as e:
        st.error(T("dosya_okunamadi").format(e))
        return

    satir_once = len(ham)

    # Once otomatik bicim algilama: kolon adlari ve "bir satir = tek mesaj"
    # formati burada cevriliyor. Elle eslestirme sadece bu basarisiz olursa.
    try:
        ham, bicim = pipeline.hazirla(ham)
        kontrol = pipeline.sema_kontrol(ham)
    except Exception as e:
        st.error(T("dosya_okunamadi").format(e))
        return

    st.write(T("satir_kolon").format(satir_once, len(kontrol["kolonlar"])))

    if bicim["uzun_format"]:
        st.info(T("uzun_format").format(
            rol=bicim["rol_kolonu"], metin=bicim["metin_kolonu"],
            once=satir_once, sonra=bicim["satir_sonra"]))
    if bicim["ad_eslemesi"]:
        st.caption(T("eslesen_kolonlar") + ", ".join(
            f"`{k}` → `{v}`" for k, v in bicim["ad_eslemesi"].items()))

    if kontrol["eksik_zorunlu"]:
        st.warning(
            T("kolon_bulunamadi") +
            ", ".join(f"`{k}`" for k in kontrol["eksik_zorunlu"]) +
            T("kolon_sec_uyari")
        )
        secenekler = [T("sec")] + list(ham.columns)
        esleme = {}
        for hedef in kontrol["eksik_zorunlu"]:
            esleme[hedef] = st.selectbox(T("hangi_kolon").format(hedef), secenekler,
                                          key=f"esle_{hedef}")
        if any(v == T("sec") for v in esleme.values()):
            return
        # Ayni kolon iki hedefe secilirse yeniden adlandirma tekrarli kolon
        # uretir ve biri sessizce kaybolur.
        if len(set(esleme.values())) < len(esleme):
            st.error(T("ayni_kolon"))
            return
        ham = ham.rename(columns={kaynak: hedef for hedef, kaynak in esleme.items()})
        kontrol = pipeline.sema_kontrol(ham)

    # Opsiyonel kolonlarin yoklugu bir sorun degil - sistem zaten onlarsiz
    # calisiyor. "Eksik" diye uyarmak yerine sadece neyin acilacagini soyle.
    if "tarih" in kontrol["eksik_onerilen"]:
        st.caption(T("tarih_ipucu"))
    if kontrol["mevcut_dogrulama"]:
        st.caption(T("gt_bulundu"))

    if st.button(T("analizi_calistir"), type="primary", width="stretch"):
        cubuk = st.progress(0.0, T("basliyor"))
        try:
            sonuc = pipeline.calistir(
                ham, YUKLENEN_KLASOR,
                ilerleme=lambda o, m: cubuk.progress(min(o, 1.0), m),
            )
        except Exception as e:
            cubuk.empty()
            st.error(T("analiz_basarisiz").format(e))
            return
        cubuk.empty()
        st.success(T("analiz_tamam").format(
            sonuc["oturum_sayisi"], sonuc["kume_sayisi"]))
        st.cache_data.clear()
        st.rerun()


def _saglayici_adi(anahtar):
    """llm.SAGLAYICILAR anahtarlari ayarlar.json'a yaziliyor, o yuzden
    degistirilmiyor; ekranda panel dilinde gosteriliyor."""
    if "Yerel" in anahtar:
        return T("sag_yerel")
    return anahtar.replace(" (ucretsiz)", "")


def _llm_paneli():
    sb = st.sidebar
    sb.markdown("### " + T("llm_ayarlari"))

    ayar = st.session_state.setdefault("ayar", llm.ayarlari_yukle())

    with sb.expander(T("saglayici_model"), expanded=False):
        # key VERILMEZSE Streamlit, secili degeri her seferinde disaridan
        # (ayar["saglayici"]) yeniden hesapliyor - ama bu blok o degeri hemen
        # asagida kendisi de guncelliyor. Sonuc: tiklama bir tur gecikmeli
        # isleniyor (once tikla, degismez; tekrar tikla, degisir). key=
        # verince Streamlit ilk cizimden sonra widget'in KENDI durumuna
        # guveniyor, index sadece ilk acilista kullaniliyor.
        saglayicilar = list(llm.SAGLAYICILAR)
        mevcut = ayar.get("saglayici", saglayicilar[0])
        idx = saglayicilar.index(mevcut) if mevcut in saglayicilar else 0
        yeni_sag = st.selectbox(T("saglayici"), saglayicilar, index=idx,
                                # Dil anahtarda: Streamlit secili kutunun etiketini
                                # ilk cizimde donduruyor, dil degisince yenilensin
                                key="saglayici_secim_" + st.session_state.get("dil", "tr"),
                                format_func=_saglayici_adi)

        bilgi = llm.SAGLAYICILAR[yeni_sag]
        if yeni_sag != ayar.get("saglayici"):
            ayar["saglayici"] = yeni_sag
            ayar["base_url"] = bilgi["base_url"]
            ayar["model"] = bilgi["modeller"][0]

        # Bilinen saglayicilarda (NVIDIA, Hugging Face, OpenAI) Base URL
        # sabittir - kullanici degistiremesin, yanlislikla bozmasin. Sadece
        # "Yerel / Ozel" secenegi editable kalir, cunku orada adres kisiye
        # ozel (kendi Ollama portu ya da kurum ici sunucu).
        yerel_mi = "Yerel" in yeni_sag
        if yerel_mi:
            ayar["base_url"] = st.text_input("Base URL", ayar["base_url"])
            st.caption(T("ollama_ipucu"))
        else:
            st.text_input("Base URL", ayar["base_url"], disabled=True)
            st.caption(T("base_url_sabit"))

        ayar["model"] = st.text_input(T("model"), ayar["model"])
        st.caption(T("onerilen") + " · ".join(f"`{m}`" for m in bilgi["modeller"][:3]))

        anahtar = st.text_input(
            T("api_anahtari"), type="password",
            value=st.session_state.get("api_key", ""),
            placeholder=T("anahtar_bos").format(bilgi["anahtar_degiskeni"]),
        )
        st.session_state["api_key"] = anahtar

        cevre = llm.anahtar_bul(ayar, None)
        if anahtar:
            st.caption(T("anahtar_panel"))
        elif llm.anahtar_gerekmez(ayar):
            st.caption(T("anahtar_gerekmez"))
        elif cevre:
            st.caption(T("anahtar_ortam").format(bilgi["anahtar_degiskeni"]))
        else:
            st.caption(T("anahtar_yok"))
            if bilgi["anahtar_adresi"]:
                st.caption(T("ucretsiz_anahtar").format(bilgi["anahtar_adresi"]))

        # Spinner/sonuc mesajlari her turda var olan sabit yer tutuculara
        # yaziliyor. Aksi halde yeni eklenen eleman alttaki dugmeleri bir
        # sira kaydiriyor ve Streamlit rerun sirasinda eski dugmeleri bir an
        # yenileriyle birlikte gosteriyordu (ust uste iki "Test" dugmesi).
        c1, c2 = st.columns(2)
        test_bas = c1.button(T("test_et"), width="stretch")
        kaydet_bas = c2.button(T("kaydet"), width="stretch")
        durum = st.empty()
        if test_bas:
            with durum.container(), st.spinner(T("baglaniliyor")):
                ok, mesaj = llm.baglanti_testi(ayar, anahtar or None)
            (durum.success if ok else durum.error)(mesaj)
        if kaydet_bas:
            llm.ayarlari_kaydet(ayar)
            durum.success(T("kaydedildi"))

        # NIM'in ucretsiz katalogu sik degisiyor; sabit model adina guvenmek
        # yerine saglayicinin O ANKI gercek listesini cekip gosteriyoruz.
        # DIKKAT: Secim kutusu ve "kullan" dugmesi, listeyi getiren dugmenin
        # ICINE yazilamaz. Streamlit'te bir dugme yalnizca basildigi rerun'da
        # True doner; ikinci dugmeye basilinca distaki False olur, blok komple
        # kaybolur ve ic tiklama hic islenmez. Bu yuzden liste session_state'e
        # alinip blok disariya cikarildi.
        liste_bas = st.button(T("model_listesi_getir"), width="stretch")
        liste_durum = st.empty()
        if liste_bas:
            with liste_durum.container(), st.spinner(T("liste_aliniyor")):
                ok, sonuc = llm.mevcut_modelleri_listele(ayar, anahtar or None)
            if ok:
                st.session_state["model_listesi"] = sonuc
                st.session_state.pop("model_listesi_hata", None)
            else:
                st.session_state.pop("model_listesi", None)
                st.session_state["model_listesi_hata"] = sonuc

        if st.session_state.get("model_listesi_hata"):
            liste_durum.error(st.session_state["model_listesi_hata"])

        # Listede gorunmek, hesapta KULLANILABILIR olmak demek degil —
        # cagirinca 404 "Not found for account" gelebiliyor. Tek tek denemek
        # yerine otomatik tarayip ilk calisani seciyoruz.
        bul_bas = st.button(T("calisan_model_bul"), type="primary", width="stretch")
        bul_durum = st.empty()
        if bul_bas:
            cubuk = bul_durum.progress(0.0, T("basliyor"))
            ok, sonuc = llm.calisan_model_bul(
                ayar, anahtar or None,
                ilerleme=lambda o, m: cubuk.progress(min(o, 1.0), m))
            if ok:
                ayar["model"] = sonuc
                st.session_state["ayar"] = ayar
                llm.ayarlari_kaydet(ayar)
                bul_durum.success(T("model_bulundu").format(sonuc))
            else:
                bul_durum.error(sonuc)

        liste = st.session_state.get("model_listesi")
        if liste:
            st.caption(T("model_sayisi").format(len(liste)))
            varsayilan = liste.index(ayar["model"]) if ayar["model"] in liste else 0
            secim = st.selectbox(T("listeden_sec"), liste, index=varsayilan,
                                 key="model_listesi_secim")
            if st.button(T("bu_modeli_kullan"), key="model_sec_uygula", width="stretch"):
                ayar["model"] = secim
                st.session_state["ayar"] = ayar
                llm.ayarlari_kaydet(ayar)
                # Yukaridaki "Model" kutusu bu satirdan ONCE ciziliyor (kod
                # sirasinda daha yukarida). st.rerun() olmadan degisiklik
                # ekrana bu turda yansimiyor, bir sonraki etkilesimi bekliyor.
                st.rerun()

        st.session_state["ayar"] = ayar


# ---------------------------------------------------------------------
# Sekmeler
# ---------------------------------------------------------------------
def sekme_kumeler(veri):
    df, isimler = veri["kumeler"], veri["isimler"]
    dog = veri["dogrulama"]

    st.markdown(T("kumeler_baslik"))
    st.markdown(f'<div class="aciklama">{T("kumeler_aciklama")}</div>',
                unsafe_allow_html=True)

    # Kumelerin LLM ismi yoksa (ornegin yeni yuklenen veri) isimlendirme teklif et
    if not isimler:
        u1, u2 = st.columns([1.1, 3])
        with u1:
            if st.button(T("isimlendir_btn"), width="stretch"):
                _kumeleri_isimlendir(veri)
        with u2:
            st.caption(T("isimlendir_not"))

    sol, sag = st.columns([2, 1.15])

    with sol:
        fig = go.Figure()
        for no in sorted(df["kume"].unique()):
            alt = df[df["kume"] == no]
            # Scattergl WebGL gerektiriyor; GPU'su zayif makinelerde
            # "WebGL is not supported" yaziyor. 620 nokta icin normal
            # Scatter yeterli ve her yerde calisiyor.
            fig.add_trace(go.Scatter(
                x=alt["umap_x"], y=alt["umap_y"], mode="markers",
                name=kume_adi(no, isimler),
                marker=dict(size=7, color=kume_rengi(no), opacity=.75,
                            line=dict(width=0)),
                customdata=[[m] for m in _kacis(alt["kullanici_mesaji"])],
                hovertemplate="%{customdata[0]}<extra>%{fullData.name}</extra>",
            ))
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        st.plotly_chart(duzen(fig, 480), width="stretch")
        st.caption(T("harita_not"))

    with sag:
        sayim = df["kume"].value_counts().sort_values(ascending=True)
        fig = go.Figure(go.Bar(
            x=sayim.values,
            y=[kume_adi(n, isimler) for n in sayim.index],
            orientation="h",
            marker=dict(color=[kume_rengi(n) for n in sayim.index],
                        cornerradius=4),
            text=sayim.values, textposition="outside",
            textfont=dict(color=MUREKKEP_IKI, size=11),
            hovertemplate="%{y}: %{x} " + T("oturum") + "<extra></extra>",
        ))
        fig.update_xaxes(showgrid=False, showticklabels=False,
                         range=[0, sayim.max() * 1.45])
        st.plotly_chart(duzen(fig, 480, T("kume_basina"), sag_bosluk=52),
                        width="stretch")
        st.caption(T("toplam_oturum").format(int(sayim.sum())))

    if dog and "ari" in dog:
        st.divider()
        st.markdown(T("dogruluk_baslik"))
        st.markdown(f'<div class="aciklama">{T("dogruluk_aciklama")}</div>',
                    unsafe_allow_html=True)
        k = st.columns(3)
        k[0].metric("ARI", dog["ari"], help=T("ari_yardim"))
        k[1].metric("NMI", dog["nmi"], help="Normalized Mutual Information")
        k[2].metric(T("secilen_k"), dog.get("secilen_k", "—"))

        if dog.get("kume_saflik"):
            saf = pd.DataFrame(dog["kume_saflik"])
            # st.dataframe HTML yorumlamaz; kacissiz ham isim kullanilir
            saf[T("tablo_kume")] = saf["kume"].map(
                lambda n: isimler.get(str(n), T("kume").format(n)))
            st.dataframe(
                saf[[T("tablo_kume"), "baskin_konu", "saflik", "n"]].rename(columns={
                    "baskin_konu": T("tablo_baskin"),
                    "saflik": T("tablo_saflik"), "n": T("tablo_oturum")}),
                width="stretch", hide_index=True)


def sekme_basarisizlik(veri):
    oz, isimler = veri["basarisizlik"], veri["isimler"]
    dog = veri["dogrulama"]

    st.markdown(T("basarisizlik_baslik"))
    st.markdown(f'<div class="aciklama">{T("basarisizlik_aciklama")}</div>',
                unsafe_allow_html=True)

    # Kural seti bu logun diline uymuyorsa asagidaki her sayi 0 cikar.
    # Sessizce "hic sorun yok" demek yerine bunu acikca soyluyoruz.
    kapsama = oz.get("kural_kapsamasi") or {}
    if kapsama.get("kural_uymuyor"):
        st.error(T("kural_uymuyor").format(kapsama["satir"]))

    # Ground truth yoksa ikinci grafik zaten yok. Yarim genislikte bir grafigin
    # yanina "su kolon yok" kutusu koymak veriyi kusurlu gosteriyor; onun
    # yerine tek grafigi tam genislikte veriyoruz.
    dogrulama_var = bool(oz.get("konu_bazli"))
    if dogrulama_var:
        sol, sag = st.columns(2)
    else:
        sol, sag = st.container(), None

    with sol:
        kb = pd.DataFrame(oz["kume_bazli"]).sort_values("basarisizlik_orani")
        fig = go.Figure(go.Bar(
            x=kb["basarisizlik_orani"],
            y=[kume_adi(n, isimler) for n in kb["kume"]],
            orientation="h",
            marker=dict(color=[kume_rengi(n) for n in kb["kume"]], cornerradius=4),
            text=[yuzde(v) for v in kb["basarisizlik_orani"]],
            textposition="outside", textfont=dict(color=MUREKKEP_IKI, size=11),
            customdata=kb[["oturum_sayisi"]],
            hovertemplate="%{y}<br>%{x}% " + T("basarisiz") + " · %{customdata[0]} "
                          + T("oturum") + "<extra></extra>",
        ))
        fig.update_xaxes(showgrid=False, showticklabels=False,
                         range=[0, kb["basarisizlik_orani"].max() * 1.32])
        st.plotly_chart(duzen(fig, 330, T("kumeye_gore"), sag_bosluk=44),
                        width="stretch")
        st.caption(T("kumeye_gore_not"))

    if dogrulama_var:
        with sag:
            kt = pd.DataFrame(oz["konu_bazli"]).sort_values("basarisizlik_orani")
            fig = go.Figure(go.Bar(
                x=kt["basarisizlik_orani"], y=_kacis(kt["gercek_konu"]), orientation="h",
                marker=dict(color=PALET[0], cornerradius=4),
                text=[yuzde(v) for v in kt["basarisizlik_orani"]],
                textposition="outside", textfont=dict(color=MUREKKEP_IKI, size=11),
                customdata=kt[["oturum_sayisi"]],
                hovertemplate="%{y}<br>%{x}% · %{customdata[0]} " + T("oturum")
                              + "<extra></extra>",
            ))
            fig.update_xaxes(showgrid=False, showticklabels=False,
                             range=[0, kt["basarisizlik_orani"].max() * 1.32])
            st.plotly_chart(duzen(fig, 330, T("konuya_gore"),
                                  sag_bosluk=44), width="stretch")
            st.caption(T("konuya_gore_not"))

    st.divider()
    alt_sol, alt_sag = st.columns(2)

    with alt_sol:
        bitis = oz.get("basarisiz_oturum_bitis_dagilimi", {})
        if bitis:
            etiket = {"fallback": T("bitis_fallback"),
                      "yetkiliye_yonlendirme": T("bitis_devir"),
                      "tekrarli_soru": T("bitis_tekrar")}
            # Renk bitis TURUNE sabit bagli, siraya gore degil — filtre/veri
            # degisince ayni durum ayni rengi korusun.
            renk = {"fallback": KRITIK,
                    "yetkiliye_yonlendirme": PALET[3],
                    "tekrarli_soru": PALET[1]}
            # Yatay barda plotly ilk ogeyi EN ALTA koyar; en buyugun ustte
            # gorunmesi icin artan siralamak gerekiyor.
            sirali = sorted(bitis.items(), key=lambda x: x[1])
            fig = go.Figure(go.Bar(
                x=[v for _, v in sirali],
                y=[etiket.get(k, k) for k, _ in sirali],
                orientation="h",
                marker=dict(color=[renk.get(k, PALET[0]) for k, _ in sirali],
                            cornerradius=4),
                text=[v for _, v in sirali], textposition="outside",
                textfont=dict(color=MUREKKEP_IKI, size=11),
                hovertemplate="%{y}: %{x} " + T("oturum") + "<extra></extra>",
            ))
            fig.update_xaxes(showgrid=False, showticklabels=False,
                             range=[0, max(bitis.values()) * 1.30])
            st.plotly_chart(duzen(fig, 260, T("bitis_baslik"),
                                  sag_bosluk=44), width="stretch")

    with alt_sag:
        if oz.get("belirsiz_mesaj_etkisi"):
            be = pd.DataFrame(oz["belirsiz_mesaj_etkisi"])
            ad = {"evet": T("belirsiz_evet"), "hayir": T("belirsiz_hayir")}
            fig = go.Figure(go.Bar(
                x=[ad.get(v, v) for v in be["belirsiz_mesaj"]],
                y=be["basarisizlik_orani"],
                marker=dict(color=[KRITIK if v == "evet" else PALET[0]
                                   for v in be["belirsiz_mesaj"]], cornerradius=4),
                text=[yuzde(v) for v in be["basarisizlik_orani"]],
                textposition="outside", textfont=dict(color=MUREKKEP_IKI, size=11),
                hovertemplate="%{x}: %{y}% " + T("basarisiz") + "<extra></extra>",
            ))
            fig.update_yaxes(range=[0, be["basarisizlik_orani"].max() * 1.3])
            st.plotly_chart(duzen(fig, 260, T("belirsiz_baslik")),
                            width="stretch")
            st.caption(T("belirsiz_not"))

    if dog and "kural_ikili_dogruluk" in dog:
        st.divider()
        st.markdown(T("kural_dogruluk_baslik"))
        c = st.columns(2)
        c[0].metric(T("ikili_ayrim"), yuzde(dog['kural_ikili_dogruluk']))
        c[1].metric(T("dort_sinif"), yuzde(dog['kural_tam_dogruluk']))
        st.markdown(f'<div class="aciklama">{T("kural_dogruluk_aciklama")}</div>',
                    unsafe_allow_html=True)


def sekme_trend(veri):
    trend, isimler = veri["trend"], veri["isimler"]
    if not trend:   # main() trend yoksa bu sekmeyi zaten olusturmuyor
        return

    st.markdown(T("trend_baslik"))

    hg = pd.DataFrame(trend["haftalik_genel"])

    # DIKKAT: hacim ve oran tek grafikte cift eksene KONMAZ.
    # Iki ayri panel, ayni x ekseni — karsilastirma bozulmadan okunur.
    fig = go.Figure(go.Bar(
        x=hg["hafta"], y=hg["oturum_sayisi"],
        marker=dict(color=PALET[0], cornerradius=4),
        hovertemplate="%{x}<br>%{y} " + T("oturum") + "<extra></extra>",
    ))
    st.plotly_chart(duzen(fig, 220, T("haftalik_hacim")), width="stretch")

    fig = go.Figure(go.Scatter(
        x=hg["hafta"], y=hg["basarisizlik_orani"], mode="lines+markers",
        line=dict(color=KRITIK, width=2), marker=dict(size=8),
        hovertemplate="%{x}<br>%{y}% " + T("basarisiz") + "<extra></extra>",
    ))
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(duzen(fig, 220, T("haftalik_oran")), width="stretch")

    st.divider()
    sol, sag = st.columns(2)

    with sol:
        hp = trend.get("hacim_patlamasi")
        if hp and hp.get("detay"):
            ad = hp.get("etiket") or kume_adi(hp.get("kume"), isimler)
            d = pd.DataFrame(hp["detay"])
            renkler = [KRITIK if h == hp["zirve_hafta"] else PALET[2] for h in d["hafta"]]
            fig = go.Figure(go.Bar(
                x=d["hafta"], y=d["oturum_sayisi"],
                marker=dict(color=renkler, cornerradius=4),
                customdata=d[["basarisizlik_orani"]],
                hovertemplate="%{x}<br>%{y} " + T("oturum") + " · %{customdata[0]}% "
                              + T("basarisiz") + "<extra></extra>",
            ))
            st.plotly_chart(duzen(fig, 280, T("hacim_patlamasi").format(ad)),
                            width="stretch")
            oran_metni = (T("hacim_oran_tr").format(hp["zirve_basarisizlik"])
                          if hp.get("zirve_basarisizlik") is not None else ".")
            st.markdown(
                '<div class="aciklama">' + T("hacim_aciklama").format(
                    hafta=hp["zirve_hafta"], hacim=hp["zirve_hacim"],
                    ort=hp["diger_haftalar_ortalama"], oran=oran_metni)
                + '</div>', unsafe_allow_html=True)

    with sag:
        konu_aylik = trend.get("konu_aylik") or {}
        if konu_aylik:
            fig = go.Figure()
            for i, (ad, seri) in enumerate(konu_aylik.items()):
                s = pd.DataFrame(seri)
                fig.add_trace(go.Scatter(
                    x=[str(a) for a in s["ay"]], y=s["basarisizlik_orani"],
                    mode="lines+markers", name=ad,
                    line=dict(color=PALET[i % len(PALET)], width=2),
                    marker=dict(size=9),
                    hovertemplate="%{x}: %{y}%<extra>" + ad + "</extra>",
                ))
            fig.update_xaxes(type="category")
            fig.update_yaxes(ticksuffix="%")
            st.plotly_chart(duzen(fig, 280, T("aylar_arasi")), width="stretch")
            st.markdown(f'<div class="aciklama">{T("aylar_aciklama")}</div>',
                        unsafe_allow_html=True)
        elif trend.get("aylik_genel"):
            ag = pd.DataFrame(trend["aylik_genel"])
            fig = go.Figure(go.Scatter(
                x=[str(a) for a in ag["ay"]], y=ag["basarisizlik_orani"],
                mode="lines+markers", line=dict(color=KRITIK, width=2),
                marker=dict(size=9),
                hovertemplate="%{x}: %{y}%<extra></extra>",
            ))
            fig.update_xaxes(type="category")
            fig.update_yaxes(ticksuffix="%")
            st.plotly_chart(duzen(fig, 280, T("aylik_oran")), width="stretch")


def sekme_rapor(veri):
    st.markdown(T("rapor_baslik"))
    st.markdown(f'<div class="aciklama">{T("rapor_aciklama")}</div>',
                unsafe_allow_html=True)

    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button(T("rapor_uret_btn"), type="primary", width="stretch"):
            _rapor_uret(veri)

    rapor = veri["raporlar"].get(st.session_state.get("dil", "tr"))
    if rapor:
        st.markdown("---")
        # Diskteki rapor eski surumden ya da elle duzenlenmis olabilir; her
        # gosterimde de temizlenir.
        st.markdown(llm.guvenli_markdown(rapor))
    elif veri["raporlar"]:
        st.info(T("rapor_baska_dilde"))
    else:
        st.info(T("rapor_yok"))


def _kumeleri_isimlendir(veri):
    """Temsili mesajlari LLM'e gonderip kume basliklari uretir.
    Sonuc kume_isimleri.json'a panel dili altinda yazilir; panel her
    acilista LLM'e sormaz."""
    ayar = st.session_state.get("ayar", llm.ayarlari_yukle())
    anahtar = st.session_state.get("api_key") or None

    if not llm.anahtar_bul(ayar, anahtar):
        st.error(T("anahtar_gerekli"))
        return

    yol = os.path.join(veri["klasor"], "temsili_mesajlar.json")
    if not os.path.exists(yol):
        st.error(T("temsili_yok"))
        return

    with open(yol, encoding="utf-8") as f:
        temsili = json.load(f)

    try:
        with st.spinner(T("isim_uretiyor").format(ayar["model"])):
            isimler = llm.kumeleri_isimlendir(
                temsili, ayar, oturum_anahtari=anahtar,
                dil=st.session_state.get("dil", "tr"))
    except Exception as e:
        st.error(T("isimlendirme_basarisiz").format(llm.hata_metni(e)))
        return

    # LLM ayni ismi iki kumeye verebiliyor (gecmiste oldu) - tekrarlari ayristir
    gorulen = {}
    for k in sorted(isimler, key=lambda x: int(x)):
        ad = str(isimler[k]).strip()
        if ad in gorulen:
            gorulen[ad] += 1
            ad = f"{ad} ({gorulen[ad]})"
        else:
            gorulen[ad] = 1
        isimler[k] = ad

    # Diger dillerdeki isimler korunur; dil degistirince tekrar LLM'e gerek yok
    dosya = os.path.join(veri["klasor"], "kume_isimleri.json")
    tum = {}
    if os.path.exists(dosya):
        with open(dosya, encoding="utf-8") as f:
            tum = _isim_dosyasi(json.load(f))
    tum[st.session_state.get("dil", "tr")] = isimler
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(tum, f, ensure_ascii=False, indent=2)

    st.cache_data.clear()
    st.rerun()


def _rapor_uret(veri):
    ayar = st.session_state.get("ayar", llm.ayarlari_yukle())
    anahtar = st.session_state.get("api_key") or None

    if not llm.anahtar_bul(ayar, anahtar):
        st.error(T("anahtar_gerekli"))
        return

    df = veri["kumeler"]
    donem = "-"
    if df is not None and "tarih" in df.columns:
        t = pd.to_datetime(df["tarih"], errors="coerce").dropna()
        if len(t):
            donem = f"{t.min():%Y-%m-%d} / {t.max():%Y-%m-%d}"

    try:
        with st.spinner(T("rapor_yaziyor").format(ayar["model"])):
            metin = llm.rapor_uret(
                veri["basarisizlik"], veri["trend"], veri["isimler"], ayar,
                oturum_anahtari=anahtar, donem=donem,
                oturum_sayisi=len(df) if df is not None else "-",
                dil=st.session_state.get("dil", "tr"))
    except Exception as e:
        st.error(T("rapor_uretilemedi").format(llm.hata_metni(e)))
        return

    dil = st.session_state.get("dil", "tr")
    with open(_rapor_yolu(veri["klasor"], dil), "w", encoding="utf-8") as f:
        f.write(metin)
    st.cache_data.clear()
    st.rerun()


# ---------------------------------------------------------------------
def _bos_ekran():
    """Henuz analiz yokken gorunen karsilama. Hata degil - normal baslangic."""
    st.markdown(f'<div class="baslik">{T("baslik")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="aciklama">{T("bos_aciklama")}</div>',
                unsafe_allow_html=True)

    sol, sag = st.columns(2)
    with sol:
        st.markdown(T("bos_basla"))
        st.markdown(T("bos_adimlar"))
    with sag:
        st.markdown(T("bos_dosya"))
        st.markdown(T("bos_dosya_metin"))

    if os.path.exists("ornek_musteri_loglari.csv"):
        st.caption(T("bos_ornek"))


def main():
    st.markdown(CSS, unsafe_allow_html=True)
    klasor = yan_panel()
    veri = veri_seti_yukle(klasor)

    if veri["kumeler"] is None or veri["basarisizlik"] is None:
        _bos_ekran()
        return

    df = veri["kumeler"]
    oz = veri["basarisizlik"]

    st.markdown(f'<div class="baslik">{T("baslik")}</div>', unsafe_allow_html=True)

    donem = ""
    if "tarih" in df.columns:
        t = pd.to_datetime(df["tarih"], errors="coerce").dropna()
        if len(t):
            bicim = "%d.%m.%Y" if _tr_mi() else "%b %d, %Y"
            donem = f"{t.min():{bicim}} – {t.max():{bicim}}"
    if donem:
        st.markdown(f'<div class="altbilgi">{donem}</div>', unsafe_allow_html=True)

    belirsiz = int((df["belirsiz_mesaj"] == "evet").sum()) if "belirsiz_mesaj" in df.columns else None
    kartlar = [
        (T("kpi_oturum"), sayi(len(df)), T("kpi_oturum_not")),
        (T("kpi_oran"), yuzde(oz['genel_basarisizlik_orani']), T("kpi_oran_not")),
        (T("kpi_kume"), str(df["kume"].nunique()), T("kpi_kume_not")),
    ]
    if belirsiz is not None:
        kartlar.append((T("kpi_belirsiz"), str(belirsiz),
                        T("kpi_belirsiz_not").format(belirsiz * 100 // len(df))))

    st.markdown(
        '<div class="kpi-satir">' + "".join(
            f'<div class="kpi"><div class="kpi-etiket">{e}</div>'
            f'<div class="kpi-deger">{d}</div><div class="kpi-not">{n}</div></div>'
            for e, d, n in kartlar) + '</div>',
        unsafe_allow_html=True)

    # Trend sekmesi sadece tarih verisi varsa. Her zaman acik tutup icine
    # "tarih kolonu yok" yazmak, calismayan bir sekme gibi duruyor.
    basliklar = [T("sekme_kumeler"), T("sekme_basarisizlik")]
    ciz = [sekme_kumeler, sekme_basarisizlik]
    if veri.get("trend"):
        basliklar.append(T("sekme_trend"))
        ciz.append(sekme_trend)
    basliklar.append(T("sekme_rapor"))
    ciz.append(sekme_rapor)

    for sekme, fn in zip(st.tabs(basliklar), ciz):
        with sekme:
            fn(veri)


if __name__ == "__main__":
    main()
