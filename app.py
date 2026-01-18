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

# ⚠️ TU CLAVE DE GOOGLE AQUÍ
GEMINI_API_KEY = "AIzaSyC8bQvMCvWCAYIwihZx2w1HgkMBDMl_n5E"

if GEMINI_API_KEY.startswith("AIza"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"Error de API: {e}")

# --- 2. ESTILOS ---
st.markdown("""
<style>
    /* Tarjetas de métricas */
    .metric-container {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        background-color: white;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-number { font-size: 28px; font-weight: bold; color: #0066cc; }
    .metric-label { font-size: 14px; color: #666; font-weight: 500; text-transform: uppercase; }
    
    /* Informe IA */
    .ia-report {
        background-color: #f8f9fa;
        padding: 30px;
        border-radius: 10px;
        border-left: 5px solid #0066cc;
        margin-top: 20px;
        margin-bottom: 30px;
        font-family: 'Segoe UI', sans-serif;
    }
    .ia-report h3 { color: #004488; margin-top: 20px; }
    .ia-report li { margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES ---

def limpiar_html(texto):
    return html.unescape(re.sub(r'<[^>]+>', '', texto)).strip()

def obtener_noticias(tema, dias):
    # Configuración de mercados competidores/objetivo
    # Estructura: "Nombre": {"código_país", "código_idioma_google", "idioma_traductor"}
    mercados = {
        "🇪🇸 España":   {"gl": "ES", "hl": "es-419", "lang": "es"},
        "🇲🇦 Marruecos": {"gl": "MA", "hl": "fr",     "lang": "fr"}, # Prensa de negocios suele ser en francés
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
        progreso_texto.text(f"📡 Escaneando satélites en {nombre_pais}...")
        barra_progreso.progress((i + 1) / total_mercados)
        
        try:
            # 1. Traducir el tema al idioma del país destino
            query = tema
            if params['lang'] != 'es':
                query = GoogleTranslator(source='es', target=params['lang']).translate(tema)
            
            # 2. Construir URL RSS Google News
            # Usamos 'when:Xd' para filtrar mejor por fecha en la query
            q_enc = urllib.parse.quote(query) + (f"+when:{dias}d" if dias < 300 else "+when:1y")
            
            url = f"https://news.google.com/rss/search?q={q_enc}&hl={params['hl']}&gl={params['gl']}&ceid={params['gl']}:{params['hl']}"
            
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    if dt >= fecha_limite:
                        # Limpieza y traducción del titular para el usuario
                        tit_orig = limpiar_html(entry.title)
                        tit_es = tit_orig
                        if params['lang'] != 'es':
                            tit_es = GoogleTranslator(source=params['lang'], target='es').translate(tit_orig)
                        
                        lista_noticias.append({
                            "pais": nombre_pais,
                            "idioma_origen": params['lang'].upper(),
                            "fuente": entry.source.title,
                            "fecha": dt,
                            "fecha_str": dt.strftime("%Y-%m-%d"),
                            "titulo_es": tit_es,
                            "titulo_orig": tit_orig,
                            "link": entry.link
                        })
        except Exception:
            continue
            
    progreso_texto.empty()
    barra_progreso.empty()
    return pd.DataFrame(lista_noticias)

def consultar_cerebro_digital(df_noticias, tema, rol):
    if df_noticias.empty: return "No hay datos para analizar."

    # Preparamos la información cruda para la IA (País + Fuente + Titular)
    # Seleccionamos las 35 más recientes para dar buen contexto
    raw_text = ""
    for _, row in df_noticias.head(35).iterrows():
        raw_text += f"- [{row['pais']}] {row['fuente']}: {row['titulo_es']}\n"

    prompt = f"""
    Eres un CONSULTOR DE ESTRATEGIA DE NEGOCIO.
    
    PERFIL DEL CLIENTE (ROL): "{rol}"
    OBJETIVO DE ANÁLISIS: "{tema}"
    
    NOTICIAS DETECTADAS (MERCADO):
    {raw_text}
    
    --- INSTRUCCIONES ---
    Genera un INFORME ESTRATÉGICO útil para tomar decisiones.
    No pierdas tiempo saludando. Ve directo al grano.
    
    ESTRUCTURA REQUERIDA:
    
    ### ⚡ ANÁLISIS DE SITUACIÓN (Lo que está pasando)
    (Resume la situación cruzando datos de los diferentes países. Cita explícitamente: "Como indican los medios marroquíes..." o "La prensa holandesa señala...").

    ### 📅 HORIZONTES DE DECISIÓN
    
    **1. Corto Plazo (Esta semana/mes)**
    * **Acción sugerida:** ¿Qué debe hacer el cliente YA? (Subir precios, aguantar stock, vender rápido...)
    * **Por qué:** Justifícalo con una noticia leída.
    
    **2. Medio Plazo (Próxima campaña/trimestre)**
    * **Tendencia:** ¿El mercado sube, baja o se estanca?
    * **Ojo a:** Riesgos regulatorios o de competencia detectados.
    
    **3. Largo Plazo (Estrategia)**
    * **Visión:** Cambios estructurales (clima, leyes, tecnología).
    
    ### 🎯 CONCLUSIÓN FINAL
    (Una frase lapidaria de recomendación).
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en el análisis IA: {str(e)}"

# --- 4. INTERFAZ ---

st.title("🛡️ Centro de Inteligencia Competitiva")
st.markdown("Monitorización en tiempo real de competidores internacionales para la toma de decisiones.")

# --- BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.header("🎯 Objetivo")
    tema = st.text_input("Tema / Producto", value="Tomate")
    
    st.header("👤 Tu Perfil")
    rol = st.text_area("Contexto para la IA", 
                       value="Soy gerente de una exportadora agrícola en Almería. Necesito saber si Marruecos tiene problemas de plagas o clima para anticipar mis precios de venta a supermercados europeos.",
                       height=150)
    
    st.header("⏳ Periodo")
    periodo_map = {"24 Horas": 1, "3 Días": 3, "7 Días": 7, "30 Días": 30}
    periodo_sel = st.selectbox("Ventana de análisis", list(periodo_map.keys()), index=2)
    dias = periodo_map[periodo_sel]
    
    btn_run = st.form_submit_button("🚀 EJECUTAR INTELIGENCIA") if 'form_submit_button' in dir(st) else st.button("🚀 EJECUTAR INTELIGENCIA", type="primary")

# --- LÓGICA PRINCIPAL ---

if btn_run:
    if "PON_AQUI" in GEMINI_API_KEY:
        st.error("⚠️ Error: Configura la API KEY en el código.")
        st.stop()

    # 1. OBTENCIÓN DE DATOS (PYTHON PURO)
    df = obtener_noticias(tema, dias)

    if not df.empty:
        # --- SECCIÓN 1: DATOS DUROS (ESTADÍSTICAS REALES) ---
        st.markdown("### 📊 Radiografía de Fuentes (Datos Reales)")
        
        # Cálculos directos con Pandas
        total_noticias = len(df)
        paises_unicos = df['pais'].nunique()
        fuentes_unicas = df['fuente'].nunique()
        
        # Mostrar métricas principales
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="metric-container"><div class="metric-number">{total_noticias}</div><div class="metric-label">Noticias Analizadas</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-container"><div class="metric-number">{paises_unicos}</div><div class="metric-label">Países Detectados</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-container"><div class="metric-number">{fuentes_unicas}</div><div class="metric-label">Fuentes/Diarios</div></div>', unsafe_allow_html=True)
        
        # Desglose por País (Gráfico de barras simple usando Streamlit)
        with c4:
            st.caption("Distribución por Mercado")
            conteo_pais = df['pais'].value_counts()
            st.bar_chart(conteo_pais, color="#0066cc", height=100)

        # --- SECCIÓN 2: INTELIGENCIA ESTRATÉGICA (IA) ---
        st.markdown("---")
        st.subheader("🧠 Informe de Decisión Estratégica")
        
        with st.spinner("Analizando implicaciones para tu negocio..."):
            analisis = consultar_cerebro_digital(df, tema, rol)
            
        st.markdown(f'<div class="ia-report">{analisis}</div>', unsafe_allow_html=True)

        # --- SECCIÓN 3: EVIDENCIAS (TABLA DE DATOS) ---
        st.subheader("📂 Evidencias y Fuentes Originales")
        
        # Mostramos la tabla interactiva
        st.dataframe(
            df[['fecha_str', 'pais', 'fuente', 'titulo_es', 'link']],
            column_config={
                "fecha_str": "Fecha",
                "pais": "Mercado",
                "fuente": "Medio",
                "titulo_es": "Titular (Traducido)",
                "link": st.column_config.LinkColumn("Enlace Original")
            },
            hide_index=True,
            use_container_width=True
        )

    else:
        st.warning(f"No se encontraron noticias sobre '{tema}' en los últimos {dias} días en los mercados seleccionados.")





















