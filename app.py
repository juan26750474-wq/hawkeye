import streamlit as st
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from deep_translator import GoogleTranslator
import statistics
import urllib.parse
from datetime import datetime, timedelta
from time import mktime
import string
import html
import re

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Analizador de Reputación JCPM", layout="centered")

# --- 2. ESTILOS CSS ---
st.markdown("""
<style>
    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Etiquetas de colores */
    .noticia-buena { color: #2e7d32; font-weight: bold; background-color: #e8f5e9; padding: 2px 6px; border-radius: 4px; }
    .noticia-mala { color: #d32f2f; font-weight: bold; background-color: #ffebee; padding: 2px 6px; border-radius: 4px; }
    .noticia-neutra { color: #555; font-weight: bold; background-color: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
    .fuente-fecha { font-size: 0.9em; color: gray; }
</style>
""", unsafe_allow_html=True)

# --- 3. CARGA DE MOTORES ---
@st.cache_resource
def cargar_motores():
    analizador = SentimentIntensityAnalyzer()
    traductor = GoogleTranslator(source='auto', target='en')
    return analizador, traductor

analizador, traductor = cargar_motores()

# --- VARIABLES ---
STOP_WORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "a", "en", "y", "o", "que", "por", "para", "con", "se", "su", "sus", "es", "al", "lo", "noticia", "news", "report", "the", "to", "in", "for", "on", "of"}
DICCIONARIO_EXITO = ["dispara", "multiplica", "duplica", "récord", "lidera", "impulsa", "crece", "aumenta", "superávit", "éxito", "logro", "millonaria", "inversión", "skyrocket", "doubles", "record", "leads", "boosts", "grows", "profit", "success", "reducir", "bajar", "control", "sostenible", "avance", "sube", "acuerdo"]
DICCIONARIO_FRACASO = ["desplome", "caída", "pérdidas", "cierra", "quiebra", "crisis", "ruina", "hundimiento", "peor", "negativo", "recorte", "collapse", "fall", "drop", "loss", "bankruptcy", "dimisión", "protesta"]

# --- 4. FUNCIONES LÓGICAS ---
def analizar_con_inteligencia(texto_original):
    try:
        texto_analisis = traductor.translate(texto_original)
        score_vader = analizador.polarity_scores(texto_analisis)['compound']
        score_norm = (score_vader + 1) / 2 # Normalizar a 0-1

        texto_low = texto_original.lower()
        for p in DICCIONARIO_EXITO:
            if p in texto_low: return max(score_norm, 0.85)
        for p in DICCIONARIO_FRACASO:
            if p in texto_low: return min(score_norm, 0.20)
        
        return score_norm
    except:
        return 0.5

def limpiar_texto_profundo(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt)
    return " ".join(txt.split())

def obtener_clima_texto(nota):
    if nota >= 4.8: return "🟢 POSITIVO"
    elif nota <= 3.2: return "🔴 NEGATIVO"
    else: return "⚖️ NEUTRO"

# --- 5. INTERFAZ GRÁFICA ---
st.title("🌍 Monitor de Inteligencia Global")
st.markdown("Sistema avanzado para medir la **reputación** y el **sentimiento** de cualquier tema en prensa **Nacional** (España) e **Internacional** (Global) en tiempo real.")
st.caption("© JCPM - 2025")

# --- BLOQUE DE AYUDA (NUEVO) ---
with st.expander("ℹ️ Ayuda y Normas de Búsqueda"):
    st.markdown("""
    **Guía rápida para mejorar tus resultados:**
    * **Búsqueda Literal:** Usa comillas dobles `""` para buscar una frase exacta.
        * *Ejemplo:* `"Crisis del pepino"` buscará exactamente esa frase seguida.
    * **Palabras Clave:** Si no usas comillas, es mejor usar palabras sueltas clave.
        * *Ejemplo:* `Invernaderos Almería` funciona mejor que `Cómo están los invernaderos de Almería`.
    * **Traducción Automática:** El sistema traducirá tu búsqueda al inglés automáticamente manteniendo el criterio de las comillas.
    """)

with st.form("my_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        tema_es = st.text_input("✍️ Tema a analizar:", placeholder="Ej: \"Plan Hidrológico\"")
    with col2:
        periodo = st.selectbox("📅 Periodo:", ["24 Horas", "Semana", "Mes", "Año"])
    
    submitted = st.form_submit_button("🚀 EJECUTAR ANÁLISIS")

if submitted and tema_es:
    with st.spinner('Escaneando satélites de noticias...'):
        
        # A. TRADUCCIÓN INTELIGENTE (Detecta si hay comillas)
        try:
            # 1. Detectamos si el usuario quiere búsqueda literal
            es_literal = '"' in tema_es
            
            # 2. Traducimos el texto limpio (sin comillas para que el traductor no falle)
            texto_limpio = tema_es.replace('"', '')
            tema_en_raw = traductor.translate(texto_limpio)
            
            # 3. Si era literal, volvemos a poner comillas en inglés
            if es_literal:
                tema_en = f'"{tema_en_raw}"'
            else:
                tema_en = tema_en_raw
                
            st.info(f"🔎 Rastreando objetivos: 🇪🇸 **{tema_es}** | 🌍 **{tema_en}**")
        except:
            tema_en = tema_es

        # B. FECHAS
        ahora = datetime.now()
        dias_map = {"24 Horas": 1, "Semana": 7, "Mes": 30, "Año": 365}
        fecha_limite = ahora - timedelta(days=dias_map[periodo])

        # C. BÚSQUEDA RSS
        noticias_inter = []
        noticias_nac = []
        
        # --- MOTOR INTERNACIONAL ---
        url_en = f"https://news.google.com/rss/search?q={urllib.parse.quote(tema_en)}&hl=en-US&gl=US&ceid=US:en"
        feed_en = feedparser.parse(url_en)
        for entry in feed_en.entries:
            if hasattr(entry, 'published_parsed'):
                fecha = datetime.fromtimestamp(mktime(entry.published_parsed))
                if fecha >= fecha_limite:
                    raw = f"{entry.title}. {entry.description}"
                    txt = limpiar_texto_profundo(raw)
                    link = getattr(entry, 'link', '#')
                    
                    if len(txt) > 10:
                        score = analizar_con_inteligencia(txt)
                        noticias_inter.append({"txt": txt, "fuente": entry.source.title if 'source' in entry else "Intl", "fecha": fecha, "score": score, "link": link})

        # --- MOTOR NACIONAL ---
        url_es = f"https://news.google.com/rss/search?q={urllib.parse.quote(tema_es)}&hl=es-419&gl=ES&ceid=ES:es-419"
        feed_es = feedparser.parse(url_es)
        for entry in feed_es.entries:
            if hasattr(entry, 'published_parsed'):
                fecha = datetime.fromtimestamp(mktime(entry.published_parsed))
                if fecha >= fecha_limite:
                    raw = f"{entry.title}. {entry.description}"
                    txt = limpiar_texto_profundo(raw)
                    link = getattr(entry, 'link', '#')
                    
                    if len(txt) > 10:
                        score = analizar_con_inteligencia(txt)
                        noticias_nac.append({"txt": txt, "fuente": entry.source.title if 'source' in entry else "Nac", "fecha": fecha, "score": score, "link": link})

        # D. RESULTADOS
        if noticias_inter or noticias_nac:
            
            def calc_7(lista):
                if not lista: return 0
                prom = statistics.mean([x['score'] for x in lista])
                return round(1 + (prom * 6), 1)

            nota_int = calc_7(noticias_inter)
            nota_nac = calc_7(noticias_nac)
            nota_glob = calc_7(noticias_inter + noticias_nac)

            # --- MÉTRICAS ---
            st.divider()
            txt_nac = obtener_clima_texto(nota_nac)
            txt_int = obtener_clima_texto(nota_int)
            txt_glob = obtener_clima_texto(nota_glob)

            col1, col2, col3 = st.columns(3)
            col1.metric("🇪🇸 Nacional", f"{nota_nac}/7")
            col1.caption(f"**{txt_nac}**")
            col2.metric("🌍 Internacional", f"{nota_int}/7")
            col2.caption(f"**{txt_int}**")
            col3.metric("🌐 GLOBAL", f"{nota_glob}/7")
            col3.caption(f"**{txt_glob}**")

            st.divider()

            # --- LISTADO ---
            st.subheader("📝 Detalle de Noticias")

            todas = []
            for n in noticias_inter: todas.append({**n, "flag": "🌍"})
            for n in noticias_nac: todas.append({**n, "flag": "🇪🇸"})
            todas.sort(key=lambda x: x['fecha'], reverse=True)

            for n in todas:
                score = n['score']
                if score > 0.65:
                    etiqueta = "BUENA"
                    clase_css = "noticia-buena"
                elif score < 0.4:
                    etiqueta = "MALA"
                    clase_css = "noticia-mala"
                else:
                    etiqueta = "NEUTRA"
                    clase_css = "noticia-neutra"

                f_str = n['fecha'].strftime("%d/%m")
                texto_corto = (n['txt'][:180] + '...') if len(n['txt']) > 180 else n['txt']

                with st.container():
                    st.markdown(f"""
                    <div style="margin-bottom: 5px; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <span style="font-size:1.2em;">{n['flag']}</span> 
                            <span class="fuente-fecha">[{f_str}] <b>{n['fuente']}</b></span>
                        </div>
                        <span class="{clase_css}">{etiqueta} ({score:.2f})</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.info(texto_corto)
                    st.link_button("🔗 Leer noticia completa", n['link'])
                    st.markdown("---")

        else:
            st.warning("No se encontraron noticias recientes que coincidan con el análisis.")





