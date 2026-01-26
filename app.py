import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import xlsxwriter

# --- ESTILOS VISUALES ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Analizador de Impedancia (EIS)", layout="wide", page_icon="⚡")
st.title("⚡ Analizador de Espectroscopía de Impedancia (EIS)")
st.markdown("---")

# --- NOTA TÉCNICA INICIAL ---
with st.expander("📘 NOTA TÉCNICA: ¿Cómo estamos procesando los datos?", expanded=False):
    st.markdown("""
    **1. Interpretación de Columnas:**
    Basado en tu archivo `6_V72.txt`, el código asume el formato:
    * `Columna 2`: Frecuencia (Hz)
    * `Columna 3`: Z' (Parte Real, Eje X del Nyquist)
    * `Columna 4`: -Z'' (Parte Imaginaria Negativa, Eje Y del Nyquist)
    * `Columna 6`: -Phase (Ángulo de fase)

    **2. Geometría de Nyquist:**
    El gráfico de Nyquist se fuerza a una **relación de aspecto 1:1**. 
    *¿Por qué?* Un semicírculo perfecto indica un circuito RC ideal. Si se ve "achatado" (deprimido), indica un elemento de fase constante (CPE) por rugosidad o inhomogeneidades. Si no mantenemos la escala 1:1, un círculo perfecto parecería una elipse errónea.

    **3. Estimación de Resistencias:**
    * **Rs (Serie):** Se toma el mínimo valor de Z' (típicamente a alta frecuencia).
    * **R_total (Baja Frecuencia):** Se toma el Z' a la frecuencia más baja registrada.
    * **Rct (Transferencia):** Aproximación simple: `R_total - Rs`.
    """)

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Configuración")
    # A veces los archivos tienen encabezados largos, permitimos saltar filas extra si es necesario
    skip_rows = st.number_input("Filas a saltar (Header)", value=0, min_value=0)
    
    st.header("2. Límites Visuales (Nyquist)")
    autoscale = st.checkbox("Auto-escala", value=True)
    if not autoscale:
        col1, col2 = st.columns(2)
        xmax = col1.number_input("Z' Max", value=100.0)
        ymax = col2.number_input("-Z'' Max", value=60.0)

# --- CARGA DE ARCHIVOS ---
st.subheader("Cargar Archivos de Impedancia (.txt / .csv)")
uploaded_files = st.file_uploader("Arrastra tus archivos de impedancia", type=["txt", "csv"], accept_multiple_files=True)

if uploaded_files:
    resultados_lista = []
    datos_para_excel = {}
    
    # Preparamos figuras
    # 1. Nyquist
    fig_nyquist = go.Figure()
    # 2. Bode (Doble eje Y: Magnitud y Fase)
    fig_bode = make_subplots(specs=[[{"secondary_y": True}]])

    for uploaded_file in uploaded_files:
        try:
            # --- LECTURA DE DATOS (CRÍTICO: SEPARADOR ;) ---
            # Tu archivo usa ';' y codificación que soporta el símbolo Ohm (latin-1 o utf-8)
            df = pd.read_csv(uploaded_file, sep=';', skiprows=skip_rows, encoding='latin-1', engine='python')
            
            # Limpieza básica de nombres de columnas (quitar espacios y símbolos raros)
            df.columns = df.columns.str.strip()
            
            # --- EXTRACCIÓN DE VARIABLES (POR POSICIÓN PARA SEGURIDAD) ---
            # Asumimos la estructura de tu archivo 6_V72.txt
            # Index | Freq | Z' | -Z'' | Z | -Phase | Time
            
            freq = df.iloc[:, 1].values  # Frecuencia
            z_real = df.iloc[:, 2].values # Z' (Real)
            z_img_neg = df.iloc[:, 3].values # -Z'' (Imaginario Negativo)
            z_mag = df.iloc[:, 4].values  # Magnitud Z
            phase = df.iloc[:, 5].values  # Fase (negativa en tu archivo)

            nombre = uploaded_file.name

            # --- ANÁLISIS FÍSICO RÁPIDO ---
            # 1. Rs (Resistencia Serie): Intercepto a alta frecuencia (Z' mínimo)
            idx_rs = np.argmin(z_real) # Buscamos el Z' más pequeño (lado izquierdo del arco)
            val_Rs = z_real[idx_rs]
            
            # 2. R_total (Resistencia Total): Intercepto a baja frecuencia
            # Normalmente es el último punto si la frecuencia baja al final
            idx_low_freq = np.argmin(freq) 
            val_R_total = z_real[idx_low_freq]

            # 3. Rct (Estimado)
            val_Rct = val_R_total - val_Rs
            
            # 4. Frecuencia Característica (Punto más alto del arco)
            # Donde -Z'' es máximo
            idx_top = np.argmax(z_img_neg)
            freq_peak = freq[idx_top]
            phase_peak = phase[idx_top]

            resultados_lista.append({
                "Archivo": nombre,
                "Rs (Ω) [High Freq]": round(val_Rs, 2),
                "Rct_est (Ω) [Diameter]": round(val_Rct, 2),
                "Freq Peak (Hz)": round(freq_peak, 2),
                "Max Phase (°)": round(phase_peak, 2)
            })

            # Guardar para Excel
            datos_para_excel[nombre] = {
                'Freq': freq,
                'Z_real': z_real,
                'Z_img_neg': z_img_neg,
                'Phase': phase
            }

            # --- PLOT NYQUIST ---
            fig_nyquist.add_trace(go.Scatter(
                x=z_real, 
                y=z_img_neg, 
                mode='lines+markers', 
                name=nombre,
                marker=dict(size=5)
            ))

            # --- PLOT BODE ---
            # Fase (Eje izquierdo)
            fig_bode.add_trace(go.Scatter(
                x=freq, y=phase, mode='lines', name=f"Phase {nombre}",
                line=dict(dash='dot')
            ), secondary_y=False)
            
            # Magnitud (Eje derecho - Opcional, o solo graficamos fase para limpieza)
            # Para no saturar, grafiquemos solo Fase vs Frecuencia en este ejemplo, 
            # o Zreal vs Freq. Vamos a graficar Fase que es lo más diagnóstico.

        except Exception as e:
            st.error(f"Error procesando {uploaded_file.name}. Verifica que sea formato ';' y columnas estándar. Detalle: {e}")

    # --- MOSTRAR RESULTADOS ---
    
    # 1. Tabla de Parámetros
    st.subheader("📊 Parámetros Electroquímicos Estimados")
    df_res = pd.DataFrame(resultados_lista)
    st.dataframe(df_res, use_container_width=True)

    # 2. Gráficos
    col_graph1, col_graph2 = st.columns(2)

    with col_graph1:
        st.subheader("d. Diagrama de Nyquist (-Z'' vs Z')")
        
        layout_args = dict(
            xaxis_title="Z' (Re) [Ω]",
            yaxis_title="-Z'' (Im) [Ω]",
            template="plotly_white",
            height=550,
            # ESTO ES CRUCIAL PARA NYQUIST: ESCALA 1:1
            yaxis=dict(
                scaleanchor="x",
                scaleratio=1,
            )
        )
        
        if not autoscale:
            layout_args['xaxis_range'] = [0, xmax]
            layout_args['yaxis_range'] = [0, ymax]
            
        fig_nyquist.update_layout(**layout_args)
        # Línea cero
        fig_nyquist.add_hline(y=0, line_width=1, line_color="black")
        
        st.plotly_chart(fig_nyquist, use_container_width=True)

    with col_graph2:
        st.subheader("📈 Diagrama de Bode (Fase vs Frecuencia)")
        fig_bode.update_layout(
            xaxis_title="Frecuencia (Hz)",
            yaxis_title="Fase (-°)",
            xaxis_type="log", # Bode siempre es log en X
            template="plotly_white",
            height=550
        )
        st.plotly_chart(fig_bode, use_container_width=True)

    # --- EXPORTACIÓN A EXCEL (CON GRÁFICAS) ---
    st.subheader("💾 Exportar Reporte de Impedancia")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # 1. Hoja Resultados
        df_res.to_excel(writer, sheet_name='Parametros', index=False)
        ws_res = writer.sheets['Parametros']
        ws_res.set_column('A:E', 18)
        
        # 2. Hoja Datos Crudos
        df_raw = pd.DataFrame()
        for k, v in datos_para_excel.items():
            df_raw[f"Freq_{k}"] = pd.Series(v['Freq'])
            df_raw[f"Z_Re_{k}"] = pd.Series(v['Z_real'])
            df_raw[f"Z_Im_{k}"] = pd.Series(v['Z_img_neg'])
        
        df_raw.to_excel(writer, sheet_name='Datos_EIS', index=False)
        
        # 3. GRÁFICA EXCEL NATIVA (NYQUIST)
        workbook = writer.book
        chart_nyquist = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        
        num_filas = len(df_raw)
        
        # Iterar archivos para agregar series
        # Estructura en hoja 'Datos_EIS': Freq(0), Z'(1), -Z''(2)  |  Freq(3), Z'(4), -Z''(5)...
        for i, nombre in enumerate(datos_para_excel.keys()):
            col_offset = i * 3
            col_z_re = col_offset + 1
            col_z_im = col_offset + 2
            
            chart_nyquist.add_series({
                'name':       nombre,
                'categories': ['Datos_EIS', 1, col_z_re, num_filas, col_z_re], # X: Z'
                'values':     ['Datos_EIS', 1, col_z_im, num_filas, col_z_im], # Y: -Z''
                'line':       {'width': 1.5},
                'marker':     {'type': 'circle', 'size': 5}
            })
            
        chart_nyquist.set_title({'name': 'Diagrama de Nyquist'})
        chart_nyquist.set_x_axis({'name': "Z' (Ohm)", 'major_gridlines': {'visible': True}})
        chart_nyquist.set_y_axis({'name': "-Z'' (Ohm)", 'major_gridlines': {'visible': True}})
        
        # Insertar gráfico en hoja Parametros
        ws_res.insert_chart('G2', chart_nyquist, {'x_scale': 1.5, 'y_scale': 1.5})

    st.download_button(
        label="Descargar Reporte EIS (.xlsx)",
        data=buffer.getvalue(),
        file_name="Reporte_Impedancia.xlsx",
        mime="application/vnd.ms-excel"
    )

else:
    st.info("👆 Carga tu archivo .txt de impedancia (formato ;).")