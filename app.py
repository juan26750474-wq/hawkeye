import streamlit as st
import feedparser
import google.generativeai as genai
import urllib.parse
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
from time import mktime
import html
import re
import pandas as pd
import requests
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Strategic Intel Board", layout="wide", page_icon="🛡️")

# --- GESTIÓN DE SECRETOS ---
GEMINI_API_KEY = None
HORTI_API_SECRET = None
HORTI_API_URL = "https://horti.space/horti/informes/"

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    HORTI_API_SECRET = st.secrets["HORTI_API_SECRET"]
    genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    pass

# --- 2. CSS & DESIGN ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    .header-container {
        display: flex;
        align-items: center;
        background: linear-gradient(90deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .logo-img { font-size: 3rem; margin-right: 20px; }
    .header-text h1 {
        margin: 0;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700; font-size: 2rem; color: #ffffff;
        text-transform: uppercase; letter-spacing: 1px;
    }
    .header-text p { margin: 5px 0 0 0; font-size: 0.9rem; color: #a8c0ff; font-weight: 300; }
    .ia-report {
        background-color: #ffffff; padding: 25px; border-radius: 8px;
        border-left: 6px solid #2c5364; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        font-family: 'Segoe UI', sans-serif; font-size: 1rem; line-height: 1.6;
        color: #333; margin-bottom: 20px;
    }
    .custom-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        background-color: #f8f9fa; color: #6c757d;
        text-align: center; padding: 12px; font-size: 0.75em;
        border-top: 1px solid #e9ecef; z-index: 999; font-family: monospace;
    }
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .help-icon { cursor: help; color: #2c5364; font-size: 0.9rem; margin-left: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 3. LOGIC ---

def limpiar_html(texto):
    return html.unescape(re.sub(r'<[^>]+>', '', texto)).strip()

def obtener_noticias(tema, dias):
    mercados = {
        "🇪🇸 ES":      {"gl": "ES", "hl": "es-419", "lang": "es", "site": ""},
        "🇲🇦 MA":      {"gl": "MA", "hl": "ar",      "lang": "ar", "site": ""},
        "🇳🇱 NL":      {"gl": "NL", "hl": "nl",      "lang": "nl", "site": ""},
        "🇩🇪 DE":      {"gl": "DE", "hl": "de",      "lang": "de", "site": ""},
        "🇫🇷 FR":      {"gl": "FR", "hl": "fr",      "lang": "fr", "site": ""},
        "🇬🇧 UK":      {"gl": "GB", "hl": "en",      "lang": "en", "site": ""},
        "🔗 LINKEDIN":  {"gl": "US", "hl": "en",      "lang": "es", "site": "site:linkedin.com/posts"},
        "🐦 X/TWITTER": {"gl": "US", "hl": "en",      "lang": "es", "site": "site:x.com"},
        "👾 REDDIT":    {"gl": "US", "hl": "en",      "lang": "es", "site": "site:reddit.com"},
        "👥 FACEBOOK":  {"gl": "US", "hl": "en",      "lang": "es", "site": "site:facebook.com"}
    }
    fecha_limite = datetime.now() - timedelta(days=dias)
    lista_noticias = []
    progreso = st.progress(0)

    for i, (nombre_pais, params) in enumerate(mercados.items()):
        progreso.progress((i + 1) / len(mercados))
        try:
            query = tema
            if params['site']:
                query = f"{params['site']} \"{tema}\""
            elif params['lang'] != 'es':
                query = GoogleTranslator(source='es', target=params['lang']).translate(tema)
            q_enc = urllib.parse.quote(query) + (f"+when:{dias}d" if dias < 300 else "+when:1y")
            url = f"https://news.google.com/rss/search?q={q_enc}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    if dt >= fecha_limite:
                        tit_orig = limpiar_html(entry.title)
                        tit_es = tit_orig
                        if params['lang'] != 'es' or params['site'] != "":
                            tit_es = GoogleTranslator(source='auto', target='es').translate(tit_orig)
                        lista_noticias.append({
                            "Mercado": nombre_pais,
                            "Fuente": entry.source.title if hasattr(entry, 'source') else nombre_pais.split()[-1],
                            "Fecha": dt,
                            "Fecha_Texto": dt.strftime("%Y-%m-%d"),
                            "Titular": tit_es,
                            "Link": entry.link
                        })
        except:
            continue
    progreso.empty()
    return pd.DataFrame(lista_noticias)

def generar_sitrep(df_noticias, tema, rol):
    if df_noticias.empty: return "Sin datos para generar informe."
    if not GEMINI_API_KEY: return "API key no configurada."
    raw_text = ""
    df_sorted = df_noticias.sort_values(by="Fecha", ascending=False)
    for _, row in df_sorted.head(80).iterrows():
        raw_text += f"- [{row['Mercado']}] {row['Fuente']}: {row['Titular']}\n"
    hoy = datetime.now().strftime("%d de %B de %Y")
    prompt = f"""
    Eres ANALISTA DE INTELIGENCIA ESTRATÉGICA.
    FECHA: {hoy}.
    FOCO: "{tema}"
    PERFIL: "{rol}"
    SITREP (INFORME DE SITUACIÓN):
    Mezcla información de prensa sectorial con el pulso de las redes sociales (LinkedIn, X, etc.).
    NOTICIAS Y SEÑALES SOCIALES:
    {raw_text}
    INSTRUCCIONES:
    1. Redacta el SITREP en ESPAÑOL.
    2. Identifica si hay discrepancias entre la prensa oficial y lo que se dice en redes.
    3. Estilo ejecutivo y frío. Sin recomendaciones.
    SALIDA:
    3 párrafos de análisis.
    4. Nombra las fuentes clave conforme redactas el informe, incluyéndolas en el texto.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error IA: {str(e)}"

def df_a_json_serializable(df):
    """Convierte el DataFrame a lista de dicts serializable (sin Timestamps)"""
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "Mercado": row["Mercado"],
            "Fuente": row["Fuente"],
            "Fecha": row["Fecha_Texto"],
            "Titular": row["Titular"],
            "Link": row["Link"]
        })
    return rows

def publicar_informe(fecha_legible, foco, perfil, contenido, df_noticias):
    try:
        noticias_json = df_a_json_serializable(df_noticias)
        conteo = df_noticias['Mercado'].value_counts().reset_index()
        conteo.columns = ['Origen', 'Impactos']
        conteo_json = conteo.to_dict(orient='records')

        payload = {
            "secret": HORTI_API_SECRET,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "fecha_legible": fecha_legible,
            "foco": foco,
            "perfil": perfil,
            "contenido": contenido,
            "noticias": noticias_json,
            "conteo": conteo_json
        }
        r = requests.post(
            HORTI_API_URL + "guardar_informe.php",
            json=payload,
            timeout=15
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# --- 4. INTERFACE ---
st.markdown("""
<div class="header-container">
    <div class="logo-img">🛡️</div>
    <div class="header-text">
        <h1>STRATEGIC INTEL BOARD</h1>
        <p>Global Competitor & Market Monitoring Unit</p>
    </div>
</div>
""", unsafe_allow_html=True)

for key in ['sitrep', 'tema', 'rol', 'df', 'publicado', 'archivo_publicado']:
    if key not in st.session_state:
        st.session_state[key] = None

with st.form("main_form"):
    c1, c2, c3, c4 = st.columns([2, 4, 1.2, 1.2])
    with c1:
        st.markdown('**1. Foco de Análisis** <span class="help-icon" title=\'Palabra exacta: "Tomate cherry"\nOperador OR: Tomate OR Pepino\nExcluir palabras: Tomate -subasta\'>ℹ️</span>', unsafe_allow_html=True)
        tema = st.text_area("Foco", value="Tomate Exportación", height=85, label_visibility="collapsed")
    with c2:
        st.write("**2. Perfil Estratégico**")
        rol = st.text_area("Perfil", value="Productor Almería. Competencia Marruecos/Holanda.", height=85, label_visibility="collapsed")
    with c3:
        st.write("**3. Ventana**")
        st.write("")
        periodo_map = {"24 Horas": 1, "7 Días": 7, "30 Días": 30, "Trimestre": 90, "Semestre": 180, "Anual": 365}
        periodo_sel = st.selectbox("Tiempo", list(periodo_map.keys()), index=2, label_visibility="collapsed")
    with c4:
        st.write("")
        st.write("")
        btn_run = st.form_submit_button("ANALIZAR", type="primary", use_container_width=True)

if btn_run:
    st.session_state['publicado'] = False
    st.session_state['archivo_publicado'] = None
    df = obtener_noticias(tema, periodo_map[periodo_sel])
    st.session_state['df'] = df
    st.session_state['tema'] = tema
    st.session_state['rol'] = rol

    if not df.empty:
        col_datos, col_ia = st.columns([1, 2.5])
        with col_datos:
            st.markdown("### 📊 Señales")
            conteo = df['Mercado'].value_counts().reset_index()
            conteo.columns = ['Origen', 'Impactos']
            st.dataframe(conteo, hide_index=True, use_container_width=True)
        with col_ia:
            st.markdown("### ⚡ Estado de Situación")
            with st.spinner("Sincronizando Radar Social..."):
                sitrep = generar_sitrep(df, tema, rol)
            st.session_state['sitrep'] = sitrep
            st.markdown(f'<div class="ia-report">{sitrep}</div>', unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("📂 Inteligencia de Fuentes (Tabla)", expanded=False):
            st.dataframe(
                df[['Fecha', 'Mercado', 'Fuente', 'Titular', 'Link']],
                column_config={
                    "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY", width="small"),
                    "Mercado": st.column_config.TextColumn("Origen", width="small"),
                    "Fuente": st.column_config.TextColumn("Fuente", width="medium"),
                    "Titular": st.column_config.TextColumn("Titular", width="large"),
                    "Link": st.column_config.LinkColumn("Ref", display_text="Ver")
                },
                use_container_width=True, hide_index=True
            )
    else:
        st.info("Sin resultados en el radar.")

# --- EDITOR Y PUBLICACIÓN ---
if st.session_state.get('sitrep'):
    hoy = datetime.now().strftime("%d de %B de %Y")
    tema_actual = st.session_state.get('tema', '')
    rol_actual  = st.session_state.get('rol', '')
    df_actual   = st.session_state.get('df')

    st.markdown("---")
    st.markdown("### ✏️ Revisar y Publicar Informe")
    st.caption(f"📅 {hoy}  ·  🎯 {tema_actual}  ·  👤 {rol_actual}")

    informe_editado = st.text_area(
        "Edita el informe antes de publicarlo:",
        value=st.session_state['sitrep'],
        height=350,
        label_visibility="visible"
    )

    col_pub, col_estado = st.columns([1, 3])
    with col_pub:
        if st.button("📤 Publicar en horti.space", type="primary", use_container_width=True):
            with st.spinner("Publicando..."):
                resultado = publicar_informe(hoy, tema_actual, rol_actual, informe_editado, df_actual)
            if resultado.get('ok'):
                st.session_state['publicado'] = True
                st.session_state['archivo_publicado'] = resultado.get('archivo', '')
            else:
                st.error(f"❌ Error: {resultado.get('error', 'desconocido')}")

    with col_estado:
        if st.session_state.get('publicado'):
            archivo = st.session_state.get('archivo_publicado', '')
            url_informe = f"https://horti.space/horti/informes/{archivo}"
            st.success(f"✅ Publicado · [Ver informe]({url_informe})")

st.markdown("""
    <div class="custom-footer">
        Strategic Intelligence Unit · horti.space
    </div>
""", unsafe_allow_html=True)








































