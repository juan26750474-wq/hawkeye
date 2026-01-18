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

# --- 1. CONFIGURACIÓN Y API KEY ---
st.set_page_config(page_title="Analizador Global 360", layout="centered")

# ⚠️⚠️⚠️ PON AQUÍ TU NUEVA CLAVE (La que creaste tras borrar la anterior) ⚠️⚠️⚠️
GEMINI_API_KEY = "AIzaSyC8bQvMCvWCAYIwihZx2w1HgkMBDMl_n5E" 

# Configuración de la librería de Google
if GEMINI_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Error de configuración API: {e}")

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

# --- 3. MOTORES DE ANÁLISIS ---
@st.cache_resource
def cargar_motores():
    return SentimentIntensityAnalyzer()
analizador = cargar_motores()

# --- 4. FUNCIONES LÓGICAS E IA ---

def consultar_gemini(lista_noticias, tema):
    """Genera el resumen usando el modelo gemini-2.5-flash confirmado"""
    if not lista_noticias:
        return "Faltan datos para el análisis."

    # Contexto (limitado a 20 noticias para no saturar tokens)
    datos_contexto = ""
    for n in lista_noticias[:20]:
        datos_contexto += f"- {n['fecha_str']} ({n['pais']}): {n['titulo']}\n"

    prompt = f"""
    Eres un Analista de Inteligencia Corporativa.
    Analiza la presencia mediática de: "{tema}".
    
    TITULARES RECIENTES:
    {datos_contexto}
    
    INSTRUCCIONES:
    1. **Resumen Ejecutivo:** ¿La tendencia es positiva, negativa o neutra?
    2. **Análisis Geopolítico:** Diferencias clave entre regiones (Europa, EEUU, etc).
    3. **Conclusión:** Previsión a corto plazo.
    """

    try:
        # Usamos el modelo que vimos en tu lista de cuotas
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error IA: {str(e)}. (Verifica que no has superado las 5 consultas por minuto)."

def limpiar_texto(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt)
    return " ".join(txt.split())

def obtener_sentimiento(texto_traducido_en):
    score = analizador.polarity_scores(texto_traducido_en)['compound']
    # Normalizar -1 a 1  -->  0 a 1
    return (score + 1) / 2

# --- 5. INTERFAZ Y BÚSQUEDA ---

st.title("🌍 Radar de Inteligencia Global")

todas_noticias = []

with st.form("search_form"):
    col1, col2 = st.columns([3, 1])
    with col1: 
        tema_busqueda = st.text_input("Objetivo:", placeholder="Ej: Energías Renovables, Elecciones...")
    with col2: 
        periodo = st.selectbox("Ventana:", ["24 Horas", "7 Días", "30 Días", "1 Año"])
    
    btn_buscar = st.form_submit_button("🚀 EJECUTAR ANÁLISIS")

if btn_buscar and tema_busqueda:
    if "PON_AQUI" in GEMINI_API_KEY or len(GEMINI_API_KEY) < 10:
        st.error("⚠️ Error: Debes pegar tu nueva API KEY en la línea 17 del código.")
        st.stop()
    
    with st.status("📡 Escaneando fuentes globales...", expanded=True) as status:
        
        # Configuración de regiones
        regiones = {
            "ES": {"gl": "ES", "hl": "es-419", "lang_code": "es", "flag": "🇪🇸"},
            "USA": {"gl": "US", "hl": "en-US", "lang_code": "en", "flag": "🇺🇸"},
            "UK": {"gl": "GB", "hl": "en-GB", "lang_code": "en", "flag": "🇬🇧"},
            "FR": {"gl": "FR", "hl": "fr-FR", "lang_code": "fr", "flag": "🇫🇷"},
            "DE": {"gl": "DE", "hl": "de-DE", "lang_code": "de", "flag": "🇩🇪"},
        }

        # Configuración de fechas
        if periodo == "24 Horas": dias = 1
        elif periodo == "7 Días": dias = 7
        elif periodo == "30 Días": dias = 30
        else: dias = 365 
        
        fecha_limite = datetime.now() - timedelta(days=dias)

        for region, params in regiones.items():
            st.write(f"Analizando {params['flag']}...")
            try:
                # Traducción de la búsqueda
                q = tema_busqueda
                if params['lang_code'] != 'es':
                    q = GoogleTranslator(source='auto', target=params['lang_code']).translate(tema_busqueda)
                
                # Construcción URL RSS
                q_enc = urllib.parse.quote(q)
                if dias == 365: q_enc += "+when:1y" # Comando especial para Google News
                
                url = f"https://news.google.com/rss/search?q={q_enc}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
                
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if hasattr(entry, 'published_parsed'):
                        dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                        
                        if dt >= fecha_limite:
                            try:
                                txt_orig = limpiar_texto(f"{entry.title}")
                                
                                # Traducción para análisis
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
        
        status.update(label="✅ Análisis finalizado", state="complete", expanded=False)

# --- 6. VISUALIZACIÓN DE RESULTADOS ---

if todas_noticias:
    scores = [n['score'] for n in todas_noticias]
    media = statistics.mean(scores)
    nota = 1 + (media * 6)
    
    if nota >= 5: color = "green"
    elif nota <= 2.5: color = "red"
    else: color = "orange"

    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"<h2 style='text-align: center; color: {color}'>Reputación: {nota:.1f} / 7.0</h2>", unsafe_allow_html=True)
        st.progress(media)

    # Informe Gemini
    st.markdown(f"""
    <div class="analisis-ia">
        <div class="analisis-titulo">🧠 Análisis Estratégico (Gemini 2.5)</div>
        {consultar_gemini(todas_noticias, tema_busqueda)}
        <br><small style="color:gray">Basado en {len(todas_noticias)} impactos informativos.</small>
    </div>
    """, unsafe_allow_html=True)

    # Listado de Noticias
    st.subheader(f"🗞️ Desglose de Noticias ({len(todas_noticias)})")
    todas_noticias.sort(key=lambda x: x['fecha'], reverse=True)

    for n in todas_noticias:
        if n['score'] > 0.6: css, lbl = "noticia-buena", "POSITIVO"
        elif n['score'] < 0.4: css, lbl = "noticia-mala", "NEGATIVO"
        else: css, lbl = "noticia-neutra", "NEUTRO"

        with st.container():
            colA, colB = st.columns([0.85, 0.15])
            with colA:
                st.markdown(f"**{n['titulo']}**")
                st.markdown(f"<span class='tag-lang'>{n['pais']}</span> <span class='fuente-fecha'>{n['fuente']} - {n['fecha_str']}</span>", unsafe_allow_html=True)
                if n['pais'] != "🇪🇸":
                    with st.expander("Ver original"):
                        st.caption(n['original'])
            with colB:
                st.markdown(f"<div class='{css}' style='text-align:center; font-size:0.8em'>{lbl}<br>{n['score']:.2f}</div>", unsafe_allow_html=True)
            st.markdown("---")
            
elif btn_buscar:
    st.warning("No se encontraron noticias recientes. Intenta cambiar el término de búsqueda.")



















