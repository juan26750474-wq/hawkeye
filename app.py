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

# --- CONFIGURACIÓN DE LA PÁGINA WEB ---
st.set_page_config(page_title="Analizador Global de Reputación", layout="wide")

# --- CARGA DE MOTORES (CON CACHÉ PARA QUE VAYA RÁPIDO) ---
@st.cache_resource
def cargar_motores():
    # Usamos VADER para todo (con traducción) por ser más robusto
    analizador = SentimentIntensityAnalyzer()
    traductor = GoogleTranslator(source='auto', target='en')
    return analizador, traductor

analizador, traductor = cargar_motores()

STOP_WORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "a", "en", "y", "o", "que", "por", "para", "con", "se", "su", "sus", "es", "al", "lo", "noticia", "news", "report", "the", "to", "in", "for", "on", "of"}

DICCIONARIO_EXITO = ["dispara", "multiplica", "duplica", "récord", "lidera", "impulsa", "crece", "aumenta", "superávit", "éxito", "logro", "millonaria", "inversión", "skyrocket", "doubles", "record", "leads", "boosts", "grows", "profit", "success"]
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

# --- INTERFAZ GRÁFICA (LO QUE SE VE EN LA WEB) ---
st.title("🌍 Monitor de Inteligencia: Nacional vs Internacional")
st.markdown("Analiza la reputación de cualquier tema en prensa **Española** y **Mundial** al mismo tiempo.")

# COLUMNAS PARA LOS CONTROLES
col1, col2 = st.columns([3, 1])
with col1:
    tema_es = st.text_input("✍️ Tema a analizar:", placeholder="Ej: Agricultura Almería")
with col2:
    periodo = st.selectbox("📅 Periodo:", ["24 Horas", "Semana", "Mes", "Año"])

# BOTÓN DE ACCIÓN
if st.button("🚀 EJECUTAR ANÁLISIS"):
    if not tema_es:
        st.warning("Por favor, escribe un tema.")
    else:
        with st.spinner('Rastreando satélites de noticias... (Esto puede tardar unos segundos)'):
            
            # 1. TRADUCCIÓN
            try:
                tema_en = traductor.translate(tema_es)
                st.info(f"🔎 Búsqueda Dual: 🇪🇸 **{tema_es}** | 🌍 **{tema_en}**")
            except:
                tema_en = tema_es

            # 2. FECHAS
            ahora = datetime.now()
            dias_map = {"24 Horas": 1, "Semana": 7, "Mes": 30, "Año": 365}
            fecha_limite = ahora - timedelta(days=dias_map[periodo])

            # 3. MOTORES DE BÚSQUEDA
            noticias_inter = []
            noticias_nac = []
            
            # --- INTERNACIONAL ---
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

            # --- NACIONAL ---
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

            # 4. RESULTADOS
            if noticias_inter or noticias_nac:
                
                # Cálculos
                def calc_7(lista):
                    if not lista: return 0
                    prom = statistics.mean([x['score'] for x in lista])
                    return round(1 + (prom * 6), 1)

                nota_int = calc_7(noticias_inter)
                nota_nac = calc_7(noticias_nac)
                nota_glob = calc_7(noticias_inter + noticias_nac)

                # --- MOSTRAR MÉTRICAS ---
                st.divider()
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("🇪🇸 Nota España", f"{nota_nac}/7", delta_color="normal")
                kpi2.metric("🌍 Nota Mundo", f"{nota_int}/7", delta_color="normal")
                kpi3.metric("🌐 GLOBAL", f"{nota_glob}/7")

                # Clima
                if nota_glob >= 5: st.success(f"✅ CLIMA GLOBAL: POSITIVO ({nota_glob})")
                elif nota_glob <= 3: st.error(f"❌ CLIMA GLOBAL: NEGATIVO ({nota_glob})")
                else: st.warning(f"⚖️ CLIMA GLOBAL: NEUTRO ({nota_glob})")

                # --- LISTADO DE NOTICIAS ---
                st.subheader("📝 Detalle de Noticias")
                
                # Unimos y ordenamos
                todas = []
                for n in noticias_inter: todas.append({**n, "flag": "🌍"})
                for n in noticias_nac: todas.append({**n, "flag": "🇪🇸"})
                todas.sort(key=lambda x: x['fecha'], reverse=True)

                for n in todas:
                    # Colorines para la nota
                    color = "green" if n['score'] > 0.6 else ("red" if n['score'] < 0.4 else "gray")
                    
                    with st.expander(f"{n['flag']} [{n['fecha'].strftime('%d/%m')}] {n['fuente']} | Nota: {n['score']:.2f}"):
                        st.write(f"**Titular:** {n['txt']}")
                        if n['score'] > 0.8: st.caption("🔥 Noticia muy positiva detectada")
                        if n['score'] < 0.2: st.caption("🚨 Noticia muy negativa detectada")

            else:
                st.error("No se encontraron noticias en este periodo.")