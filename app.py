import streamlit as st
import feedparser
import requests
import json
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

# ⚠️ ¡PEGA AQUÍ TU CLAVE DE GOOGLE AI STUDIO! ⚠️
GEMINI_API_KEY = "PON_AQUI_TU_API_KEY_REAL" 

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
    
    /* Caja Informe IA */
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
    """Genera el resumen usando la API de Gemini con el modelo corregido"""
    if not lista_noticias:
        return "No hay noticias suficientes para generar un informe."

    # Preparamos los datos (máx 30 noticias para no saturar)
    datos_contexto = ""
    for n in lista_noticias[:30]:
        datos_contexto += f"- [{n['fecha_str']}] ({n['pais']}) {n['fuente']}: {n['titulo']} (Sentimiento: {n['score']:.2f})\n"

    prompt = f"""
    Actúa como un Analista de Inteligencia Corporativa Senior.
    Estás analizando la presencia mediática del tema: "{tema}".
    
    DATOS (Últimos impactos detectados):
    {datos_contexto}
    
    INSTRUCCIONES PARA EL INFORME:
    1. **Resumen Ejecutivo:** Sintetiza en un párrafo denso la situación (Crisis, Éxito o Estabilidad).
    2. **Análisis Geopolítico:** Destaca diferencias de opinión entre regiones (Europa, Mundo Árabe, Anglo).
    3. **Temas Clave:** Menciona los eventos concretos que mueven la métrica.
    4. **Conclusión:** Previsión de tendencia a corto plazo.
    
    Usa formato Markdown limpio.
    """

    # URL ACTUALIZADA: Usamos 'gemini-1.5-flash-latest' que es más estable
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ Error API ({response.status_code}): {response.text}"
    except Exception as e:
        return f"⚠️ Error de conexión: {str(e)}"

def limpiar_texto(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt)
    return " ".join(txt.split())

def obtener_sentimiento(texto_traducido_en):
    score = analizador.polarity_scores(texto_traducido_en)['compound']
    # Normalizar -1 a 1  -->  0 a 1
    return (score + 1) / 2

# --- 5. INTERFAZ Y BÚSQUEDA ---

st.title("🌍 Radar de Inteligencia Global 360º")
st.markdown("Monitorización en **Español, Inglés, Francés, Alemán y Árabe**.")

# Inicializamos variable segura
todas_noticias = []

with st.form("search_form"):
    col1, col2 = st.columns([3, 1])
    with col1: 
        tema_busqueda = st.text_input("Objetivo de Inteligencia:", placeholder="Ej: Energía Solar, Crisis Bancaria...")
    with col2: 
        # AÑADIDA OPCIÓN 1 AÑO
        periodo = st.selectbox("Ventana de Tiempo:", ["24 Horas", "7 Días", "30 Días", "1 Año"])
    
    btn_buscar = st.form_submit_button("🚀 EJECUTAR ANÁLISIS")

if btn_buscar and tema_busqueda:
    # Verificación API KEY
    if "PON_AQUI" in GEMINI_API_KEY or len(GEMINI_API_KEY) < 10:
        st.error("⚠️ ERROR: Falta la API KEY de Google Gemini en la línea 19 del código.")
        st.stop()
    
    with st.status("📡 Escaneando satélites informativos...", expanded=True) as status:
        
        # 1. Configuración Regional
        regiones = {
            "ES": {"gl": "ES", "hl": "es-419", "lang_code": "es", "flag": "🇪🇸"},
            "US/UK": {"gl": "US", "hl": "en-US", "lang_code": "en", "flag": "🇬🇧"},
            "FR": {"gl": "FR", "hl": "fr-FR", "lang_code": "fr", "flag": "🇫🇷"},
            "DE": {"gl": "DE", "hl": "de-DE", "lang_code": "de", "flag": "🇩🇪"},
            "AR": {"gl": "SA", "hl": "ar", "lang_code": "ar", "flag": "🇸🇦"} 
        }

        # 2. Configuración Fechas
        if periodo == "24 Horas": dias = 1
        elif periodo == "7 Días": dias = 7
        elif periodo == "30 Días": dias = 30
        else: dias = 365 # Lógica para 1 Año
        
        fecha_limite = datetime.now() - timedelta(days=dias)

        # 3. Bucle de Búsqueda
        for region, params in regiones.items():
            st.write(f"Rastreando medios en {params['flag']} {region}...")
            
            # Traducir término de búsqueda
            try:
                query_traducida = tema_busqueda
                if params['lang_code'] != 'es':
                    query_traducida = GoogleTranslator(source='auto', target=params['lang_code']).translate(tema_busqueda)
            except:
                query_traducida = tema_busqueda 

            # RSS URL (Se añade 'when:1y' al query si es 1 año para forzar a Google a buscar más atrás)
            q_param = urllib.parse.quote(query_traducida)
            if dias == 365: q_param += "+when:1y" 
            
            url_rss = f"https://news.google.com/rss/search?q={q_param}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
            
            try:
                feed = feedparser.parse(url_rss)
                for entry in feed.entries:
                    if hasattr(entry, 'published_parsed'):
                        fecha_pub = datetime.fromtimestamp(mktime(entry.published_parsed))
                        
                        # Filtro de fecha estricto
                        if fecha_pub >= fecha_limite:
                            try:
                                txt_original = limpiar_texto(f"{entry.title}. {entry.description}")
                                
                                # Traducciones
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
            except Exception as e:
                st.error(f"Error en región {region}: {e}")

        status.update(label="✅ Análisis completado", state="complete", expanded=False)

# --- 6. RESULTADOS ---

if todas_noticias:
    scores = [n['score'] for n in todas_noticias]
    media_score = statistics.mean(scores)
    nota_final = 1 + (media_score * 6) # Escala 1-7
    
    if nota_final >= 5: color_nota = "green"
    elif nota_final <= 2.5: color_nota = "red"
    else: color_nota = "orange"

    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"<h2 style='text-align: center; color: {color_nota}'>Reputación Global: {nota_final:.1f} / 7.0</h2>", unsafe_allow_html=True)
        st.progress(media_score)

    # --- INFORME IA ---
    st.markdown(f"""
    <div class="analisis-ia">
        <div class="analisis-titulo">🧠 Informe de Inteligencia Artificial (Gemini)</div>
        {consultar_gemini(todas_noticias, tema_busqueda)}
        <br><small style="color:gray">Informe generado sobre {len(todas_noticias)} noticias en 5 idiomas.</small>
    </div>
    """, unsafe_allow_html=True)

    # --- LISTADO ---
    st.subheader(f"🗞️ Noticias Detectadas ({len(todas_noticias)})")
    
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
                <span class="tag-lang">{n['pais']}</span> 
                <span class="fuente-fecha">{n['fuente']} | {n['fecha_str']}</span>
                """, unsafe_allow_html=True)
                if n['pais'] != "🇪🇸":
                    with st.expander("Ver texto original"):
                        st.caption(n['original'])
            with col_b:
                st.markdown(f'<div class="{css_class}" style="text-align:center; font-size:0.8em;">{label}<br>{n["score"]:.2f}</div>', unsafe_allow_html=True)
            st.markdown("---")
            
elif btn_buscar:
    st.warning("No se encontraron noticias. Intenta con un término más general.")















