import streamlit as st
import feedparser
import google.generativeai as genai
import urllib.parse
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
from time import mktime
import html
import re
import statistics

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Analizador Global 360", layout="centered")

# ⚠️ PON AQUÍ TU NUEVA CLAVE (NO LA QUE BORRASTE)
GEMINI_API_KEY = "AIzaSyC8bQvMCvWCAYIwihZx2w1HgkMBDMl_n5E"

# Configuración segura de la librería
if GEMINI_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Error configurando API: {e}")

# --- 2. ESTILOS CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    
    .noticia-buena { color: #2e7d32; font-weight: bold; background-color: #e8f5e9; padding: 2px 6px; border-radius: 4px; }
    .noticia-mala { color: #d32f2f; font-weight: bold; background-color: #ffebee; padding: 2px 6px; border-radius: 4px; }
    .noticia-neutra { color: #555; font-weight: bold; background-color: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
    .fuente-fecha { font-size: 0.8em; color: gray; }
    .tag-lang { font-size: 0.8em; font-weight: bold; padding: 1px 4px; border: 1px solid #ddd; border-radius: 3px; margin-right: 5px;}
    
    .analisis-ia {
        background-color: #f8f9fa;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 30px;
    }
    .analisis-titulo { color: #1565c0; font-weight: bold; font-size: 1.2em; margin-bottom: 15px; border-bottom: 2px solid #1565c0; padding-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 3. MOTORES ---
@st.cache_resource
def cargar_motores():
    return SentimentIntensityAnalyzer()
analizador = cargar_motores()

# --- 4. LÓGICA IA ---
def consultar_gemini(lista_noticias, tema):
    """Genera el resumen usando Gemini Pro (Modelo más estable)"""
    if not lista_noticias:
        return "Faltan datos para el análisis."

    # Contexto
    datos_contexto = ""
    for n in lista_noticias[:20]:
        datos_contexto += f"- {n['fecha_str']} ({n['pais']}): {n['titulo']}\n"

    prompt = f"""
    Eres un Analista de Inteligencia. Analiza: "{tema}".
    
    TITULARES DETECTADOS:
    {datos_contexto}
    
    INSTRUCCIONES:
    1. Resumen de situación (Crisis/Estabilidad).
    2. Diferencias por región.
    3. Conclusión breve.
    """

    try:
        # INTENTO 1: Usar el modelo estándar 'gemini-pro' (Más compatible que Flash)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Si falla, devolvemos el error exacto para verlo en pantalla
        return f"⚠️ Error IA: {str(e)}"

def limpiar_texto(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt)
    return " ".join(txt.split())

def obtener_sentimiento(texto_traducido_en):
    score = analizador.polarity_scores(texto_traducido_en)['compound']
    return (score + 1) / 2

# --- 5. INTERFAZ ---
st.title("🌍 Radar Global 360º")

todas_noticias = []

with st.form("search_form"):
    col1, col2 = st.columns([3, 1])
    with col1: 
        tema_busqueda = st.text_input("Objetivo:", placeholder="Ej: Bitcoin, Elecciones EEUU...")
    with col2: 
        periodo = st.selectbox("Tiempo:", ["24 Horas", "7 Días", "30 Días", "1 Año"])
    btn_buscar = st.form_submit_button("🚀 EJECUTAR")

if btn_buscar and tema_busqueda:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Falta la API KEY en el código.")
        st.stop()
    
    with st.status("📡 Escaneando fuentes...", expanded=True) as status:
        regiones = {
            "ES": {"gl": "ES", "hl": "es-419", "lang_code": "es", "flag": "🇪🇸"},
            "UK": {"gl": "GB", "hl": "en-GB", "lang_code": "en", "flag": "🇬🇧"},
            "USA": {"gl": "US", "hl": "en-US", "lang_code": "en", "flag": "🇺🇸"},
            "FR": {"gl": "FR", "hl": "fr-FR", "lang_code": "fr", "flag": "🇫🇷"},
        }

        if periodo == "24 Horas": dias = 1
        elif periodo == "7 Días": dias = 7
        elif periodo == "30 Días": dias = 30
        else: dias = 365 
        
        fecha_limite = datetime.now() - timedelta(days=dias)

        for region, params in regiones.items():
            st.write(f"Leyendo {params['flag']}...")
            try:
                q = tema_busqueda
                if params['lang_code'] != 'es':
                    q = GoogleTranslator(source='auto', target=params['lang_code']).translate(tema_busqueda)
                
                q_enc = urllib.parse.quote(q)
                if dias == 365: q_enc += "+when:1y"
                
                url = f"https://news.google.com/rss/search?q={q_enc}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
                
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if hasattr(entry, 'published_parsed'):
                        dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                        if dt >= fecha_limite:
                            try:
                                txt_orig = limpiar_texto(entry.title)
                                if params['lang_code'] == 'es':
                                    txt_es = txt_orig
                                    txt_en = GoogleTranslator(source='es', target='en').translate(txt_orig)
                                else:
                                    txt_es = GoogleTranslator(source=params['lang_code'], target='es').translate(txt_orig)
                                    txt_en = GoogleTranslator(source=params['lang_code'], target='en').translate(txt_orig)
                                
                                todas_noticias.append({
                                    "titulo": txt_es,
                                    "original": txt_orig,
                                    "fuente": entry.source.title if 'source' in entry else "Google",
                                    "pais": params['flag'],
                                    "fecha": dt,
                                    "fecha_str": dt.strftime('%d/%m/%Y'),
                                    "score": obtener_sentimiento(txt_en)
                                })
                            except: pass
            except: pass
        status.update(label="✅ Listo", state="complete", expanded=False)

# --- 6. RESULTADOS ---
if todas_noticias:
    scores = [n['score'] for n in todas_noticias]
    media = statistics.mean(scores)
    nota = 1 + (media * 6)
    color = "green" if nota >= 5 else "red" if nota <= 2.5 else "orange"

    st.divider()
    st.markdown(f"<h2 style='text-align:center; color:{color}'>Reputación: {nota:.1f}/7.0</h2>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="analisis-ia">
        <div class="analisis-titulo">🧠 Análisis Gemini</div>
        {consultar_gemini(todas_noticias, tema_busqueda)}
    </div>
    """, unsafe_allow_html=True)

    st.subheader(f"Noticias ({len(todas_noticias)})")
    todas_noticias.sort(key=lambda x: x['fecha'], reverse=True)
    
    for n in todas_noticias:
        colA, colB = st.columns([0.85, 0.15])
        with colA:
            st.write(f"**{n['pais']} | {n['fuente']}**: {n['titulo']}")
        with colB:
            st.write(f"Sc: {n['score']:.2f}")
        st.divider()
elif btn_buscar:
    st.warning("No se encontraron noticias.")


















