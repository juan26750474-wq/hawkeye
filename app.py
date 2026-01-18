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
st.set_page_config(page_title="Global Intel AI", layout="centered")

# ⚠️ IMPORTANTE: Pon aquí tu API KEY de Google Gemini
# Lo ideal es usar st.secrets, pero para este ejemplo la ponemos en variable
GEMINI_API_KEY = "PON_AQUI_TU_API_KEY_DE_GOOGLE" 

# --- 2. ESTILOS CSS (Mantenemos tu estilo visual) ---
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

# Instanciamos traductores para no saturar
traductor_es = GoogleTranslator(source='auto', target='es')
traductor_en = GoogleTranslator(source='auto', target='en')

# --- 4. FUNCIONES DE LÓGICA E IA ---

def consultar_gemini(lista_noticias, tema):
    """Genera el resumen usando la API de Gemini (Google)"""
    if not lista_noticias:
        return "No hay noticias suficientes para generar un informe de inteligencia."

    # Preparamos los datos para el prompt (limitamos a las 25 más recientes para no saturar tokens)
    datos_contexto = ""
    for n in lista_noticias[:25]:
        datos_contexto += f"- [{n['fecha_str']}] ({n['pais']}) {n['fuente']}: {n['titulo']} (Sentimiento: {n['score']:.2f})\n"

    prompt = f"""
    Actúa como un Analista de Inteligencia Corporativa y Reputación Senior.
    Estás analizando la presencia mediática del tema: "{tema}".
    
    A continuación tienes las últimas noticias detectadas en prensa internacional (España, Francia, Alemania, Países Árabes, UK/USA):
    
    {datos_contexto}
    
    INSTRUCCIONES PARA EL INFORME:
    1. **Resumen Ejecutivo:** Sintetiza en un párrafo denso la situación actual. ¿Es crisis, éxito o estabilidad?
    2. **Análisis por Regiones:** Destaca si hay diferencias entre lo que se dice en Europa vs Mundo Árabe o Angloparlante.
    3. **Hechos Clave:** Menciona los 2-3 eventos concretos que están moviendo la métrica.
    4. **Conclusión y Previsión:** Basado en la tendencia, ¿qué se espera para los próximos días?
    
    El tono debe ser profesional, periodístico y directo. Usa formato Markdown (negritas, listas).
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"Error en API Gemini: {response.text}"
    except Exception as e:
        return f"Error de conexión con IA: {str(e)}"

def limpiar_texto(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt)
    return " ".join(txt.split())

def obtener_sentimiento(texto_traducido_en):
    # VADER funciona mejor en inglés
    score = analizador.polarity_scores(texto_traducido_en)['compound']
    # Normalizar de -1...1 a 0...1 para facilitar visualización
    return (score + 1) / 2

# --- 5. INTERFAZ PRINCIPAL ---

st.title("🌍 Radar de Inteligencia Global 360º")
st.markdown("Monitorización de reputación en **Español, Inglés, Francés, Alemán y Árabe** con análisis de IA Generativa.")

with st.form("search_form"):
    col1, col2 = st.columns([3, 1])
    with col1: 
        tema_busqueda = st.text_input("Objetivo de Inteligencia:", placeholder="Ej: Energía Solar, Crisis Bancaria, Nombre Empresa...")
    with col2: 
        periodo = st.selectbox("Ventana de Tiempo:", ["24h", "7 Días", "30 Días"])
    
    btn_buscar = st.form_submit_button("🚀 EJECUTAR ANÁLISIS")

if btn_buscar and tema_busqueda:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Error de Configuración: Debes introducir tu API KEY de Google Gemini en el código.")
    else:
        with st.status("📡 Iniciando barrido de satélites informativos...", expanded=True) as status:
            
            # 1. Configuración de idiomas y regiones
            # Estructura: Código: (Sufijo Google News, Código idioma traducción)
            regiones = {
                "ES": {"gl": "ES", "hl": "es-419", "lang_code": "es", "flag": "🇪🇸"},
                "US/UK": {"gl": "US", "hl": "en-US", "lang_code": "en", "flag": "🇬🇧"},
                "FR": {"gl": "FR", "hl": "fr-FR", "lang_code": "fr", "flag": "🇫🇷"},
                "DE": {"gl": "DE", "hl": "de-DE", "lang_code": "de", "flag": "🇩🇪"},
                "AR": {"gl": "SA", "hl": "ar", "lang_code": "ar", "flag": "🇸🇦"} # Arabia Saudí como proxy de mundo árabe
            }

            # 2. Definir fecha límite
            dias = 1 if periodo == "24h" else 7 if periodo == "7 Días" else 30
            fecha_limite = datetime.now() - timedelta(days=dias)

            todas_noticias = []
            
            # 3. Bucle de búsqueda multilingüe
            for region, params in regiones.items():
                st.write(f"Escaneando fuentes en {params['flag']} {region}...")
                
                # A. Traducir el término de búsqueda al idioma destino (si no es el mismo)
                try:
                    query_traducida = tema_busqueda
                    if params['lang_code'] != 'es':
                        # Usamos el traductor para buscar "Agricultura" en alemán como "Landwirtschaft"
                        query_traducida = GoogleTranslator(source='auto', target=params['lang_code']).translate(tema_busqueda)
                except:
                    query_traducida = tema_busqueda # Fallback

                # B. Construir URL RSS Google News
                url_rss = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_traducida)}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
                
                # C. Descargar y procesar
                feed = feedparser.parse(url_rss)
                
                for entry in feed.entries:
                    if hasattr(entry, 'published_parsed'):
                        fecha_pub = datetime.fromtimestamp(mktime(entry.published_parsed))
                        if fecha_pub >= fecha_limite:
                            try:
                                # Texto original
                                txt_original = limpiar_texto(f"{entry.title}. {entry.description}")
                                
                                # Traducción para Análisis (a Inglés para VADER) y Visualización (a Español)
                                # Para optimizar, si es ES ya lo tenemos, si no, traducimos.
                                if params['lang_code'] == 'es':
                                    txt_es = txt_original
                                    txt_en = GoogleTranslator(source='es', target='en').translate(txt_original)
                                else:
                                    # Traducimos a español para que el usuario entienda
                                    txt_es = GoogleTranslator(source=params['lang_code'], target='es').translate(txt_original)
                                    # Traducimos a inglés para el motor de sentimiento
                                    txt_en = GoogleTranslator(source=params['lang_code'], target='en').translate(txt_original)
                                
                                score = obtener_sentimiento(txt_en)
                                
                                todas_noticias.append({
                                    "titulo": txt_es, # Guardamos en español para la IA y el usuario
                                    "original": txt_original,
                                    "fuente": entry.source.title if 'source' in entry else "Google News",
                                    "pais": params['flag'],
                                    "fecha": fecha_pub,
                                    "fecha_str": fecha_pub.strftime('%Y-%m-%d'),
                                    "score": score,
                                    "link": getattr(entry, 'link', '#')
                                })
                            except Exception as e:
                                continue # Saltar errores de traducción puntuales

            status.update(label="✅ Análisis completado", state="complete", expanded=False)

    # --- 6. VISUALIZACIÓN DE RESULTADOS ---
    
    if todas_noticias:
        # Calcular media global
        scores = [n['score'] for n in todas_noticias]
        media_score = statistics.mean(scores)
        
        # Mapear nota 0-1 a escala 0-7 (como pedías en tu código original)
        nota_final = 1 + (media_score * 6)
        
        # Determinar color
        if nota_final >= 5: color_nota = "green"
        elif nota_final <= 2.5: color_nota = "red"
        else: color_nota = "orange"

        st.divider()
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(f"<h2 style='text-align: center; color: {color_nota}'>Reputación Global: {nota_final:.1f} / 7.0</h2>", unsafe_allow_html=True)
            st.progress(media_score)

        # --- SECCIÓN IA (GEMINI) ---
        st.markdown(f"""
        <div class="analisis-ia">
            <div class="analisis-titulo">🧠 Informe de Inteligencia Artificial (Gemini)</div>
            {consultar_gemini(todas_noticias, tema_busqueda)}
            <br><small style="color:gray">Informe generado automáticamente analizando {len(todas_noticias)} impactos en 5 idiomas.</small>
        </div>
        """, unsafe_allow_html=True)

        # --- LISTADO DE NOTICIAS ---
        st.subheader(f"🗞️ Desglose de Noticias ({len(todas_noticias)})")
        
        # Ordenar por fecha más reciente
        todas_noticias.sort(key=lambda x: x['fecha'], reverse=True)

        for n in todas_noticias:
            # Etiquetas visuales
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
                    # Expandible para ver texto original si fue traducido
                    if n['pais'] != "🇪🇸":
                        with st.expander("Ver texto original"):
                            st.caption(n['original'])
                with col_b:
                    st.markdown(f'<div class="{css_class}" style="text-align:center; font-size:0.8em;">{label}<br>{n["score"]:.2f}</div>', unsafe_allow_html=True)
                
                st.markdown("---")
    else:
        st.warning("No se encontraron noticias relevantes en el periodo seleccionado.")













