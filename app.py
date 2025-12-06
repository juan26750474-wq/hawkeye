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
from collections import Counter

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Analizador de Reputación JCPM", layout="centered")

# --- 2. ESTILOS CSS ---
st.markdown("""
<style>
    /* 1. Ocultar Menú hamburguesa y Pie de página */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 2. Ocultar la barra de herramientas superior derecha (Deploy, tres puntos, etc.) */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stDecoration"] {visibility: hidden !important;}
    
    /* 3. Estilos de la App */
    .noticia-buena { color: #2e7d32; font-weight: bold; background-color: #e8f5e9; padding: 2px 6px; border-radius: 4px; }
    .noticia-mala { color: #d32f2f; font-weight: bold; background-color: #ffebee; padding: 2px 6px; border-radius: 4px; }
    .noticia-neutra { color: #555; font-weight: bold; background-color: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
    .fuente-fecha { font-size: 0.9em; color: gray; }
    
    /* Caja de Análisis IA Dinámico */
    .analisis-ia {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 6px solid #ff4b4b;
        margin-bottom: 25px;
    }
    .analisis-titulo { font-weight: bold; font-size: 1.1em; margin-bottom: 10px; display: flex; align-items: center; }
</style>
""", unsafe_allow_html=True)

# --- 3. CARGA DE MOTORES ---
@st.cache_resource
def cargar_motores():
    return SentimentIntensityAnalyzer(), GoogleTranslator(source='auto', target='en')
analizador, traductor = cargar_motores()

# --- VARIABLES ---
STOP_WORDS = {"el", "la", "los", "las", "un", "una", "de", "del", "a", "en", "y", "o", "que", "por", "para", "con", "se", "su", "sus", "es", "al", "lo", "noticia", "news", "report", "the", "to", "in", "for", "on", "of", "and", "is", "ha", "han", "fue", "sus", "sobre", "este", "esta", "como", "pero", "sin", "mas", "año", "años", "gran", "desde", "hasta", "muy", "nos", "les", "esa", "ese", "eso", "porque", "está", "están", "ser", "parte", "todo", "hace", "donde", "quien", "ayer", "hoy", "mañana", "tras", "durante", "según", "entre", "millones", "ciento", "euros"}

DICCIONARIO_EXITO = ["dispara", "multiplica", "duplica", "récord", "lidera", "impulsa", "crece", "aumenta", "superávit", "éxito", "logro", "millonaria", "inversión", "skyrocket", "doubles", "record", "leads", "boosts", "grows", "profit", "success", "reducir", "bajar", "control", "sostenible", "avance", "sube", "acuerdo", "aprobado", "luz verde", "green light", "approved", "milestone"]

DICCIONARIO_FRACASO = [
    # Economía
    "desplome", "caída", "pérdidas", "cierra", "quiebra", "crisis", "ruina", "hundimiento", "recorte", "bankruptcy", "collapse",
    # Sanidad / Plagas
    "brote", "foco", "plaga", "virus", "bacteria", "infección", "contagio", "enfermedad", "hospitalizado", "outbreak", "virus", "infection",
    # Mortalidad
    "muertos", "muerte", "fallecidos", "víctimas", "sacrificio", "cadáveres", "dead", "death", "killed",
    # Restricciones / Legal
    "prohibición", "prohibido", "veto", "bloqueo", "restricción", "ilegal", "denuncia", "fraude", "multa", "sanción", "ban", "restriction", "illegal", "fine",
    # Clima / Desastres
    "sequía", "granizo", "inundación", "alerta", "emergencia", "drought", "flood", "emergency", "warning"
]

# --- 4. FUNCIONES LÓGICAS ---
def analizar_con_inteligencia(texto_original):
    try:
        texto_analisis = traductor.translate(texto_original)
        score_vader = analizador.polarity_scores(texto_analisis)['compound']
        score_norm = (score_vader + 1) / 2
        texto_low = texto_original.lower()
        
        # Prioridad 1: Detectar palabras de ALARMA (Fuerza nota baja)
        for p in DICCIONARIO_FRACASO:
            if p in texto_low: return min(score_norm, 0.20)
            
        # Prioridad 2: Detectar palabras de ÉXITO (Fuerza nota alta)
        for p in DICCIONARIO_EXITO:
            if p in texto_low: return max(score_norm, 0.85)
            
        return score_norm
    except: return 0.5

def limpiar_texto_profundo(texto):
    txt = html.unescape(texto)
    txt = re.sub(r'<[^>]+>', '', txt)
    return " ".join(txt.split())

# --- AJUSTE DE BAREMOS GLOBALES (1-7) ---
def obtener_clima_texto(nota):
    if nota >= 4.5: return "🟢 POSITIVO"  # Bajado de 4.8 para ser menos exigente
    elif nota <= 2.9: return "🔴 NEGATIVO" # Bajado de 3.2 para ser menos pesimista
    else: return "⚖️ NEUTRO"

# --- GENERADOR DINÁMICO ---
def generar_resumen_dinamico(todas_las_noticias, nota_global, termino_busqueda):
    if not todas_las_noticias: return "No hay datos suficientes."
    
    total = len(todas_las_noticias)
    
    # 1. Filtro de palabras prohibidas (búsqueda)
    busqueda_limpia = termino_busqueda.lower().replace('"', '').replace("'", "")
    palabras_busqueda = set(busqueda_limpia.split())
    
    # 2. Extraer Trending Topics
    texto_completo = " ".join([n['txt'] for n in todas_las_noticias]).lower()
    texto_completo = re.sub(r'[^\w\s]', '', texto_completo) 
    palabras = texto_completo.split()
    
    palabras_clave = [
        p for p in palabras 
        if p not in STOP_WORDS 
        and p not in palabras_busqueda 
        and len(p) > 4
    ]
    
    conteo = Counter(palabras_clave)
    top_3 = conteo.most_common(3)
    
    conceptos_str = ""
    if top_3:
        conceptos_str = ", ".join([f"**'{p[0].upper()}'**" for p in top_3])
    else:
        conceptos_str = "temas generales"

    # 3. Métricas (Ajustadas a los nuevos umbrales)
    # Umbral Positivo: > 0.60
    # Umbral Negativo: < 0.30
    pos = sum(1 for n in todas_las_noticias if n['score'] > 0.60)
    neg = sum(1 for n in todas_las_noticias if n['score'] < 0.30)
    
    # 4. Redacción
    mensaje = f"Se han analizado **{total} impactos mediáticos**. "
    
    if nota_global >= 5.5:
        mensaje += "El escenario es **altamente favorable**. La prensa destaca logros y avances significativos. "
    elif nota_global >= 4.5:
        mensaje += "El clima general es **positivo**, aunque con matices. "
    elif nota_global <= 2.5:
        mensaje += "Se detecta una **crisis de reputación severa**. El tono mediático es hostil. "
    elif nota_global <= 3.5:
        mensaje += "El entorno es **crítico**. Existen focos de negatividad que requieren atención. "
    else:
        mensaje += "La situación es de **estabilidad y cautela**. "
        
    mensaje += f"Al margen de la búsqueda principal, la conversación pública gira en torno a conceptos como {conceptos_str}. "
    
    if neg == 0 and pos > 0:
        mensaje += "Es destacable la **ausencia total de noticias negativas** en este periodo."
    elif neg > pos:
        mensaje += f"⚠️ **Atención:** El volumen de noticias negativas ({neg}) supera al de positivas ({pos}), lo que indica una tendencia a la baja."
    elif pos > neg:
        mensaje += f"La solidez del tema se confirma con **{pos} noticias positivas**."
    else:
        mensaje += "Existe una **polarización exacta** entre noticias positivas y negativas."
        
    return mensaje

# --- 5. INTERFAZ GRÁFICA ---
st.title("🌍 Monitor de Inteligencia Global")
st.markdown("Sistema avanzado para medir la **reputación** y el **sentimiento** de cualquier tema en prensa **Nacional** (España) e **Internacional** (Global) en tiempo real.")
st.caption("© JCPM - 2025")

# --- BOTÓN DE ENLACE EN LA BARRA LATERAL ---
with st.sidebar:
    st.header("Sobre nosotros")
    st.write("Herramienta desarrollada para el análisis de inteligencia corporativa.")
    st.link_button("🌐 Visitar Aprendidos.es", "https://www.aprendidos.es/")

with st.expander("ℹ️ Ayuda y Normas de Búsqueda"):
    st.markdown("""
    **Guía rápida:**
    * **Literal:** Usa comillas `""` (ej: `"Crisis del pepino"`) para buscar la frase exacta.
    * **General:** Sin comillas busca palabras clave relacionadas.
    """)

with st.form("my_form"):
    col1, col2 = st.columns([3, 1])
    with col1: tema_es = st.text_input("✍️ Tema a analizar:", placeholder="Ej: Agricultura Almería")
    with col2: periodo = st.selectbox("📅 Periodo:", ["24 Horas", "Semana", "Mes", "Año"])
    submitted = st.form_submit_button("🚀 EJECUTAR ANÁLISIS")

if submitted and tema_es:
    with st.spinner('Escaneando satélites de noticias...'):
        
        # A. TRADUCCIÓN
        try:
            es_literal = '"' in tema_es
            texto_limpio = tema_es.replace('"', '')
            tema_en_raw = traductor.translate(texto_limpio)
            tema_en = f'"{tema_en_raw}"' if es_literal else tema_en_raw
            st.info(f"🔎 Rastreando: 🇪🇸 **{tema_es}** | 🌍 **{tema_en}**")
        except: tema_en = tema_es

        # B. FECHAS
        ahora = datetime.now()
        dias_map = {"24 Horas": 1, "Semana": 7, "Mes": 30, "Año": 365}
        fecha_limite = ahora - timedelta(days=dias_map[periodo])

        # C. BÚSQUEDA
        noticias_inter, noticias_nac = [], []
        
        # INTERNACIONAL
        feed_en = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(tema_en)}&hl=en-US&gl=US&ceid=US:en")
        for entry in feed_en.entries:
            if hasattr(entry, 'published_parsed') and datetime.fromtimestamp(mktime(entry.published_parsed)) >= fecha_limite:
                txt = limpiar_texto_profundo(f"{entry.title}. {entry.description}")
                if len(txt) > 10:
                    noticias_inter.append({"txt": txt, "fuente": entry.source.title if 'source' in entry else "Intl", "fecha": datetime.fromtimestamp(mktime(entry.published_parsed)), "score": analizar_con_inteligencia(txt), "link": getattr(entry, 'link', '#')})

        # NACIONAL
        feed_es = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(tema_es)}&hl=es-419&gl=ES&ceid=ES:es-419")
        for entry in feed_es.entries:
            if hasattr(entry, 'published_parsed') and datetime.fromtimestamp(mktime(entry.published_parsed)) >= fecha_limite:
                txt = limpiar_texto_profundo(f"{entry.title}. {entry.description}")
                if len(txt) > 10:
                    noticias_nac.append({"txt": txt, "fuente": entry.source.title if 'source' in entry else "Nac", "fecha": datetime.fromtimestamp(mktime(entry.published_parsed)), "score": analizar_con_inteligencia(txt), "link": getattr(entry, 'link', '#')})

        # D. RESULTADOS
        if noticias_inter or noticias_nac:
            def calc_7(lista):
                if not lista: return 0
                return round(1 + (statistics.mean([x['score'] for x in lista]) * 6), 1)

            nota_int = calc_7(noticias_inter)
            nota_nac = calc_7(noticias_nac)
            nota_glob = calc_7(noticias_inter + noticias_nac)

            # --- MÉTRICAS ---
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("🇪🇸 Nacional", f"{nota_nac}/7"); c1.caption(f"**{obtener_clima_texto(nota_nac)}**")
            c2.metric("🌍 Internacional", f"{nota_int}/7"); c2.caption(f"**{obtener_clima_texto(nota_int)}**")
            c3.metric("🌐 GLOBAL", f"{nota_glob}/7"); c3.caption(f"**{obtener_clima_texto(nota_glob)}**")
            
            # --- ANÁLISIS DINÁMICO ---
            todas = [{"flag": "🌍", **n} for n in noticias_inter] + [{"flag": "🇪🇸", **n} for n in noticias_nac]
            resumen_ia = generar_resumen_dinamico(todas, nota_glob, tema_es)
            
            st.markdown(f"""
            <div class="analisis-ia">
                <div class="analisis-titulo">🤖 Análisis de Inteligencia Artificial</div>
                {resumen_ia}
            </div>
            """, unsafe_allow_html=True)

            st.divider()

            # --- LISTADO ---
            st.subheader(f"📝 Detalle de Noticias ({len(todas)})")
            todas.sort(key=lambda x: x['fecha'], reverse=True)

            for n in todas:
                score = n['score']
                
                # --- NUEVOS UMBRALES SUAVIZADOS ---
                # > 0.60 Buena | < 0.30 Mala
                if score > 0.60: 
                    lbl, css = "BUENA", "noticia-buena"
                elif score < 0.30: 
                    lbl, css = "MALA", "noticia-mala"
                else: 
                    lbl, css = "NEUTRA", "noticia-neutra"
                
                txt_corto = (n['txt'][:400] + '...') if len(n['txt']) > 400 else n['txt']

                with st.container():
                    st.markdown(f"""
                    <div style="margin-bottom: 5px; display: flex; align-items: center; justify-content: space-between;">
                        <div><span style="font-size:1.2em;">{n['flag']}</span> <span class="fuente-fecha">[{n['fecha'].strftime('%d/%m')}] <b>{n['fuente']}</b></span></div>
                        <span class="{css}">{lbl} ({score:.2f})</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.info(txt_corto)
                    st.link_button("🔗 Leer noticia completa", n['link'])
                    st.markdown("---")
        else:
            st.warning("No se encontraron noticias recientes.")












