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

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Analizador de Reputación", layout="centered")

# --- ESTILOS CSS (Para que quede bonito) ---
st.markdown("""
<style>
    .stExpander { border: 1px solid #ddd; border-radius: 5px; }
    .noticia-buena { color: #2e7d32; font-weight: bold; }
    .noticia-mala { color: #d32f2f; font-weight: bold; }
    .noticia-neutra { color: #555; font-weight: bold; }
    .fuente-fecha { font-size: 0.9em; color: #666; }
</style>
""", unsafe_allow_html=True)

# --- CARGA DE MOTORES ---
@st.cache_resource
def cargar_motores():
    analizador = SentimentIntensityAnalyzer()
    traductor = GoogleTranslator(source='auto', target='en')
    return analizador, traductor

analizador, traductor = cargar_motores()

# Listas de palabras clave
STOP_WORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "a", "en", "y", "o", "que", "por", "para", "con", "se", "su", "sus", "es", "al", "lo", "noticia", "news", "report", "the", "to", "in", "for", "on", "of"}
DICCIONARIO_EXITO = ["dispara", "multiplica", "duplica", "récord", "lidera", "impulsa", "crece", "aumenta", "superávit", "éxito", "logro", "millonaria", "inversión", "skyrocket", "doubles", "record", "leads", "boosts", "grows", "profit", "success", "reducir", "bajar", "control"]
DICCIONARIO_FRACASO = ["desplome", "caída", "pérdidas", "cierra", "quiebra", "crisis", "ruina", "hundimiento", "peor", "negativo", "recorte", "collapse", "fall", "drop", "loss", "bankruptcy"]

# --- FUNCIONES ---
def analizar_con_inteligencia(texto_original):
    try:
        texto_analisis = traductor.translate(texto_original)
        score_vader = analizador.polarity_scores(texto_analisis)['compound']
        score_norm = (score_vader + 1) / 2

        texto_low = texto_original.lower()
        for p in DICCIONARIO_EXITO:
            if p in texto_low: return max(score_norm, 0.85)
        for p in DICCIONARIO_FRACASO:
            if p in texto_low: return min(score_norm, 0.20)
        
        return score_norm
    except:
        return 0.5

def limpiar_html(texto):
    return html.unescape(texto).replace('<b>', '').replace('</b>', '').replace('...', '')

# --- INTERFAZ ---
st.title("🌍 Monitor de Inteligencia Global")
st.markdown("Analiza la reputación en tiempo real (Prensa Nacional e Internacional).")

with st.form("my_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        tema_es = st.text_input("✍️ Tema a analizar:", placeholder="Ej: Invernaderos Almería")
    with col2:
        periodo = st.selectbox("📅 Periodo:", ["24 Horas", "Semana", "Mes", "Año"])
    
    submitted = st.form_submit_button("🚀 EJECUTAR ANÁLISIS")

if submitted and tema_es:
    with st.spinner('Analizando satélites de noticias...'):
        
        # 1. TRADUCCIÓN
        try:
            tema_en = traductor.translate(tema_es)
            st.info(f"🔎 Rastreando: 🇪🇸 **{tema_es}** | 🌍 **{tema_en}**")
        except:
            tema_en = tema_es

        # 2. FECHAS
        ahora = datetime.now()
        dias_map = {"24 Horas": 1, "Semana": 7, "Mes": 30, "Año": 365}
        fecha_limite = ahora - timedelta(days=dias_map[periodo])

        # 3. MOTORES
        noticias_inter = []
        noticias_nac = []
        
        # INTERNACIONAL
        url_en = f"https://news.google.com/rss/search?q={urllib.parse.quote(tema_en)}&hl=en-US&gl=US&ceid=US:en"
        feed_en = feedparser.parse(url_en)
        for entry in feed_en.entries:
            if hasattr(entry, 'published_parsed'):
                fecha = datetime.fromtimestamp(mktime(entry.published_parsed))
                if fecha >= fecha_limite:
                    txt = limpiar_html(f"{entry.title}. {entry.description}")
                    if len(txt) > 10:
                        score = analizar_con_inteligencia(txt)
                        noticias_inter.append({"txt": txt, "fuente": entry.source.title if 'source' in entry else "Intl", "fecha": fecha, "score": score})

        # NACIONAL
        url_es = f"https://news.google.com/rss/search?q={urllib.parse.quote(tema_es)}&hl=es-419&gl=ES&ceid=ES:es-419"
        feed_es = feedparser.parse(url_es)
        for entry in feed_es.entries:
            if hasattr(entry, 'published_parsed'):
                fecha = datetime.fromtimestamp(mktime(entry.published_parsed))
                if fecha >= fecha_limite:
                    txt = limpiar_html(f"{entry.title}. {entry.description}")
                    if len(txt) > 10:
                        score = analizar_con_inteligencia(txt)
                        noticias_nac.append({"txt": txt, "fuente": entry.source.title if 'source' in entry else "Nac", "fecha": fecha, "score": score})

        # 4. RESULTADOS VISUALES
        if noticias_inter or noticias_nac:
            
            def calc_7(lista):
                if not lista: return 0
                prom = statistics.mean([x['score'] for x in lista])
                return round(1 + (prom * 6), 1)

            nota_int = calc_7(noticias_inter)
            nota_nac = calc_7(noticias_nac)
            nota_glob = calc_7(noticias_inter + noticias_nac)

            # MÉTRICAS
            col1, col2, col3 = st.columns(3)
            col1.metric("🇪🇸 Nacional", f"{nota_nac}/7")
            col2.metric("🌍 Internacional", f"{nota_int}/7")
            col3.metric("🌐 GLOBAL", f"{nota_glob}/7", delta="Positivo" if nota_glob>=5 else "Negativo")

            # LISTADO DETALLADO
            st.divider()
            st.subheader("📝 Detalle de Noticias")

            # Unimos y ordenamos
            todas = []
            for n in noticias_inter: todas.append({**n, "flag": "🌍"})
            for n in noticias_nac: todas.append({**n, "flag": "🇪🇸"})
            todas.sort(key=lambda x: x['fecha'], reverse=True)

            for n in todas:
                # LOGICA DE ETIQUETAS (LO QUE PEDISTE)
                score = n['score']
                if score > 0.65:
                    etiqueta = "🟢 BUENA"
                    clase_css = "noticia-buena"
                elif score < 0.4:
                    etiqueta = "🔴 MALA"
                    clase_css = "noticia-mala"
                else:
                    etiqueta = "⚪ NEUTRA"
                    clase_css = "noticia-neutra"

                # Formato de fecha y texto corto
                f_str = n['fecha'].strftime("%d/%m")
                # Recortamos texto a 120 caracteres para que no ocupe mucho
                texto_corto = (n['txt'][:120] + '...') if len(n['txt']) > 120 else n['txt']

                # VISUALIZACIÓN TIPO TARJETA
                with st.container():
                    # Línea 1: Metadatos y Valoración
                    st.markdown(f"""
                    <div style="margin-top: 10px;">
                        <span style="font-size:1.2em;">{n['flag']}</span> 
                        <span class="fuente-fecha">[{f_str}] <b>{n['fuente']}</b></span>
                        <span style="float:right;" class="{clase_css}">{etiqueta} ({score:.2f})</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Línea 2: El texto de la noticia
                    st.info(texto_corto)

        else:
            st.warning("No se encontraron noticias recientes.")
