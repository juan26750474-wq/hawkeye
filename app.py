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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Analizador de Reputación", layout="centered")

# --- ESTILOS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .noticia-buena { color: #2e7d32; font-weight: bold; background-color: #e8f5e9; padding: 2px 6px; border-radius: 4px; }
    .noticia-mala { color: #d32f2f; font-weight: bold; background-color: #ffebee; padding: 2px 6px; border-radius: 4px; }
    .noticia-neutra { color: #555; font-weight: bold; background-color: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
    .fuente-fecha { font-size: 0.9em; color: gray; }
</style>
""", unsafe_allow_html=True)

# --- MOTORES ---
@st.cache_resource
def cargar_motores():
    return SentimentIntensityAnalyzer(), GoogleTranslator(source='auto', target='en')
analizador, traductor = cargar_motores()

# --- VARIABLES ---
STOP_WORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "a", "en", "y", "o", "que", "por", "para", "con", "se", "su", "sus", "es", "al", "lo", "noticia"}
DICCIONARIO_EXITO = ["dispara", "multiplica", "duplica", "récord", "lidera", "impulsa", "crece", "aumenta", "superávit", "éxito", "logro", "millonaria", "inversión", "skyrocket", "doubles", "record", "leads", "boosts", "grows", "profit", "success", "reducir", "bajar", "control", "sostenible", "avance", "sube"]
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
    except: return 0.5

def limpiar_texto_profundo(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt) # Borra todo el HTML
    return " ".join(txt.split())

def obtener_clima_texto(nota):
    if nota >= 4.8: return "🟢 POSITIVO"
    elif nota <= 3.2: return "🔴 NEGATIVO"
    else: return "⚖️ NEUTRO"

# --- INTERFAZ ---
st.title("🌍 Monitor de Inteligencia Global")
with st.form("my_form"):
    col1, col2 = st.columns([3, 1])
    with col1: tema_es = st.text_input("✍️ Tema:", placeholder="Ej: Invernaderos Almería")
    with col2: periodo = st.selectbox("📅 Periodo:", ["24 Horas", "Semana", "Mes", "Año"])
    submitted = st.form_submit_button("🚀 EJECUTAR")

if submitted and tema_es:
    with st.spinner('Analizando...'):
        try: tema_en = traductor.translate(tema_es)
        except: tema_en = tema_es
        st.info(f"🔎 Rastreando: 🇪🇸 {tema_es} | 🌍 {tema_en}")
        
        ahora = datetime.now()
        dias_map = {"24 Horas": 1, "Semana": 7, "Mes": 30, "Año": 365}
        fecha_limite = ahora - timedelta(days=dias_map[periodo])
        
        noticias_inter, noticias_nac = [], []
        
        for lang, query, lista, flag, src_name in [("en-US", tema_en, noticias_inter, "🌍", "Intl"), ("es-419", tema_es, noticias_nac, "🇪🇸", "Nac")]:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl={lang}&gl={lang[-2:]}&ceid={lang[-2:]}:{lang}"
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    fecha = datetime.fromtimestamp(mktime(entry.published_parsed))
                    if fecha >= fecha_limite:
                        raw = f"{entry.title}. {entry.description}"
                        txt = limpiar_texto_profundo(raw) # LIMPIEZA TOTAL
                        link = getattr(entry, 'link', '#')
                        if len(txt) > 10:
                            score = analizar_con_inteligencia(txt)
                            lista.append({"txt": txt, "fuente": entry.source.title if 'source' in entry else src_name, "fecha": fecha, "score": score, "link": link})

        if noticias_inter or noticias_nac:
            def calc_7(lista):
                if not lista: return 0
                prom = statistics.mean([x['score'] for x in lista])
                return round(1 + (prom * 6), 1)

            nota_nac = calc_7(noticias_nac)
            nota_int = calc_7(noticias_inter)
            nota_glob = calc_7(noticias_inter + noticias_nac)

            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("🇪🇸 Nacional", f"{nota_nac}/7"); c1.caption(f"**{obtener_clima_texto(nota_nac)}**")
            c2.metric("🌍 Internacional", f"{nota_int}/7"); c2.caption(f"**{obtener_clima_texto(nota_int)}**")
            c3.metric("🌐 GLOBAL", f"{nota_glob}/7"); c3.caption(f"**{obtener_clima_texto(nota_glob)}**")
            st.divider()

            st.subheader("📝 Detalle de Noticias")
            todas = [{"flag": "🌍", **n} for n in noticias_inter] + [{"flag": "🇪🇸", **n} for n in noticias_nac]
            todas.sort(key=lambda x: x['fecha'], reverse=True)

            for n in todas:
                score = n['score']
                if score > 0.65: lbl, css = "BUENA", "noticia-buena"
                elif score < 0.4: lbl, css = "MALA", "noticia-mala"
                else: lbl, css = "NEUTRA", "noticia-neutra"
                
                txt_corto = (n['txt'][:200] + '...') if len(n['txt']) > 200 else n['txt']

                with st.container():
                    st.markdown(f"""
                    <div style="margin-bottom:5px; display:flex; justify-content:space-between;">
                        <div><span style="font-size:1.2em;">{n['flag']}</span> <span class="fuente-fecha">[{n['fecha'].strftime('%d/%m')}] <b>{n['fuente']}</b></span></div>
                        <span class="{css}">{lbl} ({score:.2f})</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.info(txt_corto)
                    # BOTÓN OFICIAL DE STREAMLIT (GRIS, LIMPIO, FUNCIONA SIEMPRE)
                    st.link_button("🔗 Leer noticia completa", n['link'])
                    st.markdown("---")
        else:
            st.warning("No hay noticias.")




