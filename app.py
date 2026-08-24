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
    **1. Interpretación de Columnas (Actualizada):**
    Basado en tu nuevo formato de archivo, el código asume:
    * `Columna 0`: Z' (Parte Real, Eje X del Nyquist)
    * `Columna 1`: -Z'' (Parte Imaginaria Negativa, Eje Y del Nyquist)
    * `Columna 5`: -Phase (Ángulo de fase)
    * `Columna 6`: Frecuencia (Hz)

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
    skip_rows = st.number_input("Filas a saltar (Header)", value=0, min_value=0)
    
    st.header("2. Límites Visuales (Nyquist)")
    autoscale = st.checkbox("Auto-escala", value=True)
    if not autoscale:
        col1, col2 = st.columns(2)
        xmax = col1.number_input("Z' Max", value=100.0)
        ymax = col2.number_input("-Z'' Max", value=60.0)
        
    st.header("3. Procesamiento Visual")
    normalizar_rs = st.checkbox("Normalizar origen (Restar Rs)", value=False, help="Resta el valor de Rs a toda la curva para que inicie en Z' = 0. Ideal para comparar diámetros (Rct).")

# --- CARGA DE ARCHIVOS ---
st.subheader("Cargar Archivos de Impedancia (.txt / .csv)")
uploaded_files = st.file_uploader("Arrastra tus archivos de impedancia", type=["txt", "csv"], accept_multiple_files=True)

if uploaded_files:
    resultados_lista = []
    datos_para_excel = {}
    
    fig_nyquist = go.Figure()
    fig_bode = make_subplots(specs=[[{"secondary_y": True}]])

    for uploaded_file in uploaded_files:
        try:
            # --- LECTURA DE DATOS ---
            df = pd.read_csv(uploaded_file, sep=';', skiprows=skip_rows, encoding='latin-1', engine='python')
            df.columns = df.columns.str.strip()
            
            # --- EXTRACCIÓN DE VARIABLES ---
            z_real = df.iloc[:, 0].values     # Z' (Real) - Columna 0
            z_img_neg = df.iloc[:, 1].values  # -Z'' (Imaginario Negativo) - Columna 1
            z_mag = df.iloc[:, 4].values      # Z (Magnitud) - Columna 4
            phase = df.iloc[:, 5].values      # -Phase (Fase) - Columna 5
            freq = df.iloc[:, 6].values       # Frecuencia - Columna 6

            nombre = uploaded_file.name

            # --- ANÁLISIS FÍSICO RÁPIDO ---
            idx_rs = np.argmin(z_real) 
            val_Rs = z_real[idx_rs]
            
            idx_low_freq = np.argmin(freq) 
            val_R_total = z_real[idx_low_freq]

            val_Rct = val_R_total - val_Rs
            
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

            datos_para_excel[nombre] = {
                'Freq': freq,
                'Z_real': z_real,
                'Z_img_neg': z_img_neg,
                'Phase': phase
            }

            # --- NORMALIZACIÓN CONDICIONAL ---
            z_real_plot = z_real - val_Rs if normalizar_rs else z_real
            nombre_legend = f"{nombre} (Norm)" if normalizar_rs else nombre

            # --- PLOT NYQUIST ---
            fig_nyquist.add_trace(go.Scatter(
                x=z_real_plot, 
                y=z_img_neg, 
                mode='lines+markers', 
                name=nombre_legend,
                marker=dict(size=5)
            ))

            # --- PLOT BODE ---
            fig_bode.add_trace(go.Scatter(
                x=freq, y=phase, mode='lines', name=f"Phase {nombre}",
                line=dict(dash='dot')
            ), secondary_y=False)

        except Exception as e:
            st.error(f"Error procesando {uploaded_file.name}. Verifica el formato. Detalle: {e}")

    # --- MOSTRAR RESULTADOS ---
    st.subheader("📊 Parámetros Electroquímicos Estimados")
    df_res = pd.DataFrame(resultados_lista)
    st.dataframe(df_res, use_container_width=True)

    col_graph1, col_graph2 = st.columns(2)

    with col_graph1:
        titulo_nyquist = "d. Diagrama de Nyquist (-Z'' vs Z') [Normalizado]" if normalizar_rs else "d. Diagrama de Nyquist (-Z'' vs Z')"
        st.subheader(titulo_nyquist)
        
        layout_args = dict(
            xaxis_title="Z' (Re) [Ω]" if not normalizar_rs else "Z' - Rs (Re) [Ω]",
            yaxis_title="-Z'' (Im) [Ω]",
            template="plotly_white",
            height=550,
            yaxis=dict(
                scaleanchor="x",
                scaleratio=1,
            )
        )
        
        if not autoscale:
            layout_args['xaxis_range'] = [0, xmax]
            layout_args['yaxis_range'] = [0, ymax]
            
        fig_nyquist.update_layout(**layout_args)
        fig_nyquist.add_hline(y=0, line_width=1, line_color="black")
        
        st.plotly_chart(fig_nyquist, use_container_width=True)

    with col_graph2:
        st.subheader("📈 Diagrama de Bode (Fase vs Frecuencia)")
        fig_bode.update_layout(
            xaxis_title="Frecuencia (Hz)",
            yaxis_title="Fase (-°)",
            xaxis_type="log", 
            template="plotly_white",
            height=550
        )
        st.plotly_chart(fig_bode, use_container_width=True)

    # --- EXPORTACIÓN A EXCEL (CON GRÁFICAS) ---
    st.subheader("💾 Exportar Reporte de Impedancia")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_res.to_excel(writer, sheet_name='Parametros', index=False)
        ws_res = writer.sheets['Parametros']
        ws_res.set_column('A:E', 18)
        
        df_raw = pd.DataFrame()
        for k, v in datos_para_excel.items():
            df_raw[f"Freq_{k}"] = pd.Series(v['Freq'])
            # Exportamos los datos crudos siempre por seguridad científica
            df_raw[f"Z_Re_{k}"] = pd.Series(v['Z_real']) 
            df_raw[f"Z_Im_{k}"] = pd.Series(v['Z_img_neg'])
        
        df_raw.to_excel(writer, sheet_name='Datos_EIS', index=False)
        
        workbook = writer.book
        chart_nyquist = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        
        num_filas = len(df_raw)
        
        for i, nombre in enumerate(datos_para_excel.keys()):
            col_offset = i * 3
            col_z_re = col_offset + 1
            col_z_im = col_offset + 2
            
            chart_nyquist.add_series({
                'name':       nombre,
                'categories': ['Datos_EIS', 1, col_z_re, num_filas, col_z_re], 
                'values':     ['Datos_EIS', 1, col_z_im, num_filas, col_z_im], 
                'line':       {'width': 1.5},
                'marker':     {'type': 'circle', 'size': 5}
            })
            
        chart_nyquist.set_title({'name': 'Diagrama de Nyquist (Datos Crudos)'})
        chart_nyquist.set_x_axis({'name': "Z' (Ohm)", 'major_gridlines': {'visible': True}})
        chart_nyquist.set_y_axis({'name': "-Z'' (Ohm)", 'major_gridlines': {'visible': True}})
        
        ws_res.insert_chart('G2', chart_nyquist, {'x_scale': 1.5, 'y_scale': 1.5})

    st.download_button(
        label="Descargar Reporte EIS (.xlsx)",
        data=buffer.getvalue(),
        file_name="Reporte_Impedancia.xlsx",
        mime="application/vnd.ms-excel"
    )

else:
    st.info("👆 Carga tu archivo .txt de impedancia (formato ;).")
