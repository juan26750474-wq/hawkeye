import streamlit as st
import feedparser
import google.generativeai as genai # Librería oficial de Google
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

# ⚠️ PEGA AQUÍ TU CLAVE DE GOOGLE AI STUDIO ⚠️
GEMINI_API_KEY = "AIzaSyC8bQvMCvWCAYIwihZx2w1HgkMBDMl_n5E" 

# Configuración de la librería de Google
try:
    genai.configure(api_key=GEMINI_API_KEY)
except:
    pass

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

# --- 3. CARGA DE MOTORES ---
@st.cache_resource
def cargar_motores():
    return SentimentIntensityAnalyzer()
analizador = cargar_motores()

# --- 4. FUNCIONES DE LÓGICA E IA ---

def consultar_gemini(lista_noticias, tema):
    """Genera el resumen usando la librería oficial de Google (más estable)"""
    if not lista_noticias:
        return "No hay noticias suficientes para generar un informe."

    # Preparamos los datos
    datos_contexto = ""
    for n in lista_noticias[:25]:
        datos_contexto += f"- [{n['fecha_str']}] ({n['pais']}) {n['fuente']}: {n['titulo']} (Sentimiento: {n['score']:.2f})\n"

    prompt = f"""
    Eres un Analista de Inteligencia. Analiza: "{tema}".
    
    NOTICIAS:
    {datos_contexto}
    
    INSTRUCCIONES:
    1. Resumen Ejecutivo (Crisis, Éxito o Estabilidad).
    2. Diferencias por países.
    3. Hechos clave.
    4. Previsión corto plazo.
    """

    try:
        # Usamos 'gemini-1.5-flash' que es el nombre estándar en la librería oficial
        # Si falla, el código probará automáticamente con 'gemini-pro'
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Intento de respaldo si falla el modelo Flash
        try:
            model_backup = genai.GenerativeModel('gemini-pro')
            response = model_backup.generate_content(prompt)
            return response.text
        except Exception as e2:
            return f"⚠️ Error conectando con IA: {str(e)}. Verifica tu API KEY."

def limpiar_texto(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt)
    return " ".join(txt.split())

def obtener_sentimiento(texto_traducido_en):
    score = analizador.polarity_scores(texto_traducido_en)['compound']
    return (score + 1) / 2

# --- 5. INTERFAZ Y BÚSQUEDA ---

st.title("🌍 Radar de Inteligencia Global")

# Inicializamos variable segura
todas_noticias = []

with st.form("search_form"):
    col1, col2 = st.columns([3, 1])
    with col1: 
        tema_busqueda = st.text_input("Objetivo de Inteligencia:", placeholder="Ej: Energía Solar...")
    with col2: 
        periodo = st.selectbox("Ventana de Tiempo:", ["24 Horas", "7 Días", "30 Días", "1 Año"])
    
    btn_buscar = st.form_submit_button("🚀 EJECUTAR ANÁLISIS")

if btn_buscar and tema_busqueda:
    if "PON_AQUI" in GEMINI_API_KEY or len(GEMINI_API_KEY) < 10:
        st.error("⚠️ ERROR: Falta la API KEY de Google Gemini en la línea 17.")
        st.stop()
    
    with st.status("📡 Rastreando noticias internacionales...", expanded=True) as status:
        
        regiones = {
            "ES": {"gl": "ES", "hl": "es-419", "lang_code": "es", "flag": "🇪🇸"},
            "US/UK": {"gl": "US", "hl": "en-US", "lang_code": "en", "flag": "🇬🇧"},
            "FR": {"gl": "FR", "hl": "fr-FR", "lang_code": "fr", "flag": "🇫🇷"},
            "DE": {"gl": "DE", "hl": "de-DE", "lang_code": "de", "flag": "🇩🇪"},
            "AR": {"gl": "SA", "hl": "ar", "lang_code": "ar", "flag": "🇸🇦"} 
        }

        if periodo == "24 Horas": dias = 1
        elif periodo == "7 Días": dias = 7
        elif periodo == "30 Días": dias = 30
        else: dias = 365 
        
        fecha_limite = datetime.now() - timedelta(days=dias)

        for region, params in regiones.items():
            st.write(f"Analizando {params['flag']}...")
            
            try:
                query_traducida = tema_busqueda
                if params['lang_code'] != 'es':
                    query_traducida = GoogleTranslator(source='auto', target=params['lang_code']).translate(tema_busqueda)
            except:
                query_traducida = tema_busqueda 

            # Parametros para buscar hasta 1 año atrás si es necesario
            q_param = urllib.parse.quote(query_traducida)
            if dias == 365: q_param += "+when:1y"
            
            url_rss = f"https://news.google.com/rss/search?q={q_param}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
            
            try:
                feed = feedparser.parse(url_rss)
                for entry in feed.entries:
                    if hasattr(entry, 'published_parsed'):
                        fecha_pub = datetime.fromtimestamp(mktime(entry.published_parsed))
                        
                        if fecha_pub >= fecha_limite:
                            try:
                                txt_original = limpiar_texto(f"{entry.title}. {entry.description}")
                                
                                if params['lang_code'] == 'es':
                                    txt_es = txt_original
                                    txt_en = GoogleTranslator(source='es', target='en').translate(txt_original)
                                else:
                                    txt_es = GoogleTranslator(source=params['lang_code'], target='es').translate(txt_original)
                                    txt_en = GoogleTranslator(source=params['lang_code'], target='en').translate(txt_original)
                                
                                score = obtener_sentimiento(txt_en)
                                
                                todas_noticias.append({
                                    "titulo": txt_es,
                                    "original": txt_original,
                                    "fuente": entry.source.title if 'source' in entry else "Google News",
                                    "pais": params['flag'],
                                    "fecha": fecha_pub,
                                    "fecha_str": fecha_pub.strftime('%d/%m/%Y'),
                                    "score": score,
                                    "link": getattr(entry, 'link', '#')
                                })
                            except Exception:
                                continue
            except Exception:
                continue

        status.update(label="✅ Finalizado", state="complete", expanded=False)

# --- 6. VISUALIZACIÓN ---

if todas_noticias:
    scores = [n['score'] for n in todas_noticias]
    media_score = statistics.mean(scores)
    nota_final = 1 + (media_score * 6)
    
    if nota_final >= 5: color_nota = "green"
    elif nota_final <= 2.5: color_nota = "red"
    else: color_nota = "orange"

    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"<h2 style='text-align: center; color: {color_nota}'>Reputación: {nota_final:.1f} / 7.0</h2>", unsafe_allow_html=True)
        st.progress(media_score)

    st.markdown(f"""
    <div class="analisis-ia">
        <div class="analisis-titulo">🧠 Informe Inteligente (Gemini)</div>
        {consultar_gemini(todas_noticias, tema_busqueda)}
        <br><small style="color:gray">Basado en {len(todas_noticias)} noticias.</small>
    </div>
    """, unsafe_allow_html=True)

    st.subheader(f"🗞️ Noticias ({len(todas_noticias)})")
    todas_noticias.sort(key=lambda x: x['fecha'], reverse=True)

    for n in todas_noticias:
        if n['score'] > 0.6: css_class, label = "noticia-buena", "POSITIVO"
        elif n['score'] < 0.4: css_class, label = "noticia-mala", "NEGATIVO"
        else: css_class, label = "noticia-neutra", "NEUTRO"

        with st.container():
            col_a, col_b = st.columns([0.85, 0.15])
            with col_a:
                st.markdown(f"""
                <span style="font-size:1.1em; font-weight:bold;">{n['titulo']}</span><br>
                <span class="tag-lang">{n['pais']}</span> <span class="fuente-fecha">{n['fuente']} | {n['fecha_str']}</span>
                """, unsafe_allow_html=True)
                if n['pais'] != "🇪🇸":
                    with st.expander("Ver original"):
                        st.caption(n['original'])
            with col_b:
                st.markdown(f'<div class="{css_class}" style="text-align:center; font-size:0.8em;">{label}<br>{n["score"]:.2f}</div>', unsafe_allow_html=True)
            st.markdown("---")
            
elif btn_buscar:
    st.warning("No se encontraron noticias. Prueba otro término.")

















