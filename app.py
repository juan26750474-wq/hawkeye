import streamlit as st
import feedparser
import google.generativeai as genai
import urllib.parse
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
from time import mktime
import html
import re
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Strategic Intel Board", layout="wide", page_icon="📡")

# ⚠️ TU CLAVE AQUÍ
GEMINI_API_KEY = "AIzaSyC8bQvMCvWCAYIwihZx2w1HgkMBDMl_n5E"

if GEMINI_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Error de API: {e}")

# --- 2. ESTILOS ---
st.markdown("""
<style>
    .metric-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        background-color: white;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-number { font-size: 24px; font-weight: bold; color: #0066cc; }
    .metric-label { font-size: 13px; color: #666; font-weight: 500; text-transform: uppercase; }
    
    .ia-report {
        background-color: #fcfcfc;
        padding: 25px;
        border-radius: 8px;
        border: 1px solid #eee;
        border-left: 5px solid #28a745; /* Verde Estratégico */
        font-family: 'Segoe UI', sans-serif;
    }
    .ia-report h3 { color: #2e7d32; margin-top: 20px; font-size: 1.1em; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
    .ia-report h2 { font-size: 1.3em; color: #333; }
    .ia-report strong { color: #000; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES ---

def limpiar_html(texto):
    return html.unescape(re.sub(r'<[^>]+>', '', texto)).strip()

def obtener_noticias(tema, dias):
    mercados = {
        "🇪🇸 España":   {"gl": "ES", "hl": "es-419", "lang": "es"},
        "🇲🇦 Marruecos": {"gl": "MA", "hl": "fr",     "lang": "fr"}, 
        "🇳🇱 Holanda":   {"gl": "NL", "hl": "nl",     "lang": "nl"},
        "🇩🇪 Alemania":  {"gl": "DE", "hl": "de",     "lang": "de"},
        "🇫🇷 Francia":   {"gl": "FR", "hl": "fr",     "lang": "fr"},
        "🇬🇧 UK/Intl":   {"gl": "GB", "hl": "en",     "lang": "en"}
    }

    fecha_limite = datetime.now() - timedelta(days=dias)
    lista_noticias = []
    
    progreso_texto = st.empty()
    barra_progreso = st.progress(0)
    total_mercados = len(mercados)
    
    for i, (nombre_pais, params) in enumerate(mercados.items()):
        progreso_texto.text(f"📡 Rastreando {nombre_pais}...")
        barra_progreso.progress((i + 1) / total_mercados)
        
        try:
            query = tema
            if params['lang'] != 'es':
                query = GoogleTranslator(source='es', target=params['lang']).translate(tema)
            
            # Filtro de fecha en Google (when:Xd)
            q_enc = urllib.parse.quote(query) + (f"+when:{dias}d" if dias < 300 else "+when:1y")
            url = f"https://news.google.com/rss/search?q={q_enc}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
            
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    if dt >= fecha_limite:
                        tit_orig = limpiar_html(entry.title)
                        tit_es = tit_orig
                        if params['lang'] != 'es':
                            tit_es = GoogleTranslator(source=params['lang'], target='es').translate(tit_orig)
                        
                        lista_noticias.append({
                            "pais": nombre_pais,
                            "fuente": entry.source.title,
                            "fecha": dt,
                            "fecha_str": dt.strftime("%Y-%m-%d"),
                            "titulo_es": tit_es,
                            "link": entry.link
                        })
        except Exception:
            continue
            
    progreso_texto.empty()
    barra_progreso.empty()
    return pd.DataFrame(lista_noticias)

def consultar_cerebro_digital(df_noticias, tema, rol):
    if df_noticias.empty: return "Falta información."

    # Contexto para la IA
    raw_text = ""
    # Enviamos hasta 50 titulares para que tenga de donde escoger
    for _, row in df_noticias.head(50).iterrows():
        raw_text += f"- [{row['pais']}] {row['fuente']}: {row['titulo_es']}\n"
    
    # Fecha actual real para evitar errores de predicción temporal
    hoy = datetime.now().strftime("%d de %B de %Y")

    prompt = f"""
    Eres un ANALISTA DE INTELIGENCIA ESTRATÉGICA.
    FECHA ACTUAL: {hoy}. (Toda previsión debe partir de esta fecha hacia el futuro).
    
    PERFIL USUARIO: "{rol}"
    OBJETIVO: "{tema}"
    
    NOTICIAS BRUTAS DISPONIBLES:
    {raw_text}
    
    ---
    INSTRUCCIONES CRÍTICAS:
    1. **SELECCIÓN INTELIGENTE:** Ignora las noticias irrelevantes o repetitivas. Usa solo las que aporten valor estratégico real.
    2. **CERO INTRODUCCIONES:** No saludes. No digas "A continuación presento...". Empieza directo con el primer punto.
    3. **PREVISIÓN FUTURA:** Si la noticia es de hoy, proyéctala. Nunca hables de años pasados como "previsión".
    
    ESTRUCTURA OBLIGATORIA DEL INFORME:
    
    ### ⚡ Situación Actual (Resumen Ejecutivo)
    (Sintetiza qué está pasando ahora mismo en los mercados clave. Cita fuentes específicas).
    
    ### 🔮 Previsión a 3 Meses (Táctico)
    (Decisiones inmediatas: precios, stock, ventas. ¿Qué va a pasar en el corto plazo?)
    
    ### 🚀 Previsión a 6 Meses (Estratégico)
    (Tendencias de la próxima campaña/semestre. Cambios en competencia).
    
    ### 🔭 Visión a 1 Año (Largo Plazo)
    (Cambios estructurales, regulatorios o tecnológicos que afectarán al negocio).
    
    ### 🎯 Acción Recomendada
    (Una frase directa en imperativo).
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error IA: {str(e)}"

# --- 4. INTERFAZ ---

st.title("🛡️ Centro de Inteligencia Competitiva")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Parámetros")
    
    with st.form("formulario_inteligencia"):
        st.subheader("1. Foco")
        tema = st.text_input("Tema / Producto", value="Tomate Exportación")
        
        st.subheader("2. Contexto de Negocio")
        rol = st.text_area("Define tu rol y duda", 
                           value="Productor en Almería. ¿Cómo afectará la producción de Marruecos y Holanda a mis precios esta campaña?",
                           height=100)
        
        st.subheader("3. Horizonte de Búsqueda")
        # Por defecto 30 días para tener perspectiva
        periodo_map = {"24 Horas": 1, "7 Días": 7, "30 Días": 30, "90 Días": 90}
        periodo_sel = st.selectbox("Rastreo hacia atrás:", list(periodo_map.keys()), index=2)
        
        btn_run = st.form_submit_button("🚀 GENERAR ESTRATEGIA", type="primary")

    dias = periodo_map[periodo_sel]

# --- LÓGICA PRINCIPAL ---

if btn_run:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Configura la API KEY.")
        st.stop()

    df = obtener_noticias(tema, dias)

    if not df.empty:
        # --- MÉTRICAS ---
        st.markdown("### 📊 Panel de Fuentes")
        
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5]) # Ajuste ancho columnas
        
        c1.markdown(f'<div class="metric-container"><div class="metric-number">{len(df)}</div><div class="metric-label">Noticias</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-container"><div class="metric-number">{df["pais"].nunique()}</div><div class="metric-label">Mercados</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-container"><div class="metric-number">{df["fuente"].nunique()}</div><div class="metric-label">Medios</div></div>', unsafe_allow_html=True)
        
        with c4:
            # Gráfico Pequeño y limpio
            counts = df['pais'].value_counts()
            st.bar_chart(counts, height=80, color="#0066cc")

        # --- INFORME ---
        st.markdown("---")
        st.subheader("🧠 Análisis de Escenarios Futuros")
        
        with st.spinner("La IA está cruzando datos y proyectando escenarios..."):
            analisis = consultar_cerebro_digital(df, tema, rol)
            
        st.markdown(f'<div class="ia-report">{analisis}</div>', unsafe_allow_html=True)

        # --- EVIDENCIAS ---
        with st.expander("🔎 Auditoría de Fuentes (Clic para desplegar)", expanded=False):
            st.dataframe(
                df[['fecha_str', 'pais', 'fuente', 'titulo_es', 'link']],
                column_config={
                    "link": st.column_config.LinkColumn("Leer Original"),
                    "titulo_es": "Titular Detectado",
                    "pais": "Mercado Origen"
                },
                use_container_width=True,
                hide_index=True
            )

    else:
        st.warning(f"No se detectaron señales relevantes sobre '{tema}' en el periodo seleccionado.")























