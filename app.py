import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
import numpy as np
import streamlit.components.v1 as components

# Configuración desde archivo local
from config import INFLUX_URL, INFLUX_TOKEN, ORG, BUCKET

# Función para consultar múltiples campos de un mismo measurement
def query_accelerometer_data(range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    import "math"
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "accelerometer" and r["_field"] == "ax" or r["_field"] == "ay" or r["_field"] == "az")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query_data_frame(query)
    if result.empty:
        return pd.DataFrame()

    # Renombrar y calcular magnitud
    result = result.rename(columns={"_time": "time"})
    result["accel_magnitude"] = np.sqrt(result["ax"]**2 + result["ay"]**2 + result["az"]**2)
    result["time"] = pd.to_datetime(result["time"])
    return result[["time", "accel_magnitude"]]

# Función para consultar datos del giroscopio (gx, gy, gz)
def query_gyroscope_data(range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "gyroscope" and (r["_field"] == "gx" or r["_field"] == "gy" or r["_field"] == "gz"))
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query_data_frame(query)
    if result.empty:
        return pd.DataFrame()

    result = result.rename(columns={"_time": "time"})
    result["time"] = pd.to_datetime(result["time"])
    return result[["time", "gx", "gy", "gz"]]

# Consulta simple de un solo campo
def query_data(measurement, field, range_minutes=60):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=ORG)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{BUCKET}")
      |> range(start: -{range_minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "{measurement}" and r["_field"] == "{field}")
      |> sort(columns: ["_time"])
    '''

    result = query_api.query(query)
    data = []

    for table in result:
        for record in table.records:
            data.append({"time": record.get_time(), field: record.get_value()})

    df = pd.DataFrame(data)
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
    return df

# Función para mostrar la animación de la planta
def show_flower_animation(humidity):
    flower_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Animación Planta Realista</title>
        <style>
            .flower-container {{
                position: relative;
                width: 120px;
                height: 150px;
                margin: auto;
            }}
            .stem {{
                width: 15px;
                height: 200px;
                background-color: #2d6a4f;
                position: absolute;
                top: 100px;
                left: 50%;
                margin-left: -7.5px;
                z-index: 0;
            }}
            .petal {{
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background-color: #ff6f61;
                position: absolute;
                transform-origin: center center;
                transition: all 1s ease;
            }}
            .petal1 {{
                top: 20px;
                left: 20px;
                transform: rotate(-45deg);
            }}
            .petal2 {{
                top: 20px;
                left: 40px;
                transform: rotate(45deg);
            }}
            .petal3 {{
                top: 20px;
                left: 60px;
                transform: rotate(135deg);
            }}
            .petal4 {{
                top: 20px;
                left: 80px;
                transform: rotate(-135deg);
            }}
            .flower-closed .petal {{
                transform: rotate(0deg);
                width: 0;
                height: 0;
                opacity: 0;
            }}
            .flower-open .petal {{
                transform: rotate(0deg);
                width: 60px;
                height: 60px;
                opacity: 1;
            }}
            .flower-center {{
                width: 30px;
                height: 30px;
                background-color: #ffcc00;
                border-radius: 50%;
                position: absolute;
                top: 45px;
                left: 45px;
                z-index: 1;
            }}
        </style>
    </head>
    <body>
        <div class="flower-container">
            <div class="stem"></div>
            <div id="flower" class="flower-closed">
                <div class="petal petal1"></div>
                <div class="petal petal2"></div>
                <div class="petal petal3"></div>
                <div class="petal petal4"></div>
                <div class="flower-center"></div>
            </div>
        </div>
        <script>
            function updateFlower(humidity) {{
                const flower = document.getElementById('flower');
                if (humidity < 40) {{
                    flower.classList.remove('flower-open');
                    flower.classList.add('flower-closed');
                }} else if (humidity >= 40 && humidity < 80) {{
                    flower.classList.remove('flower-closed');
                    flower.classList.add('flower-open');
                }} else {{
                    flower.classList.remove('flower-closed');
                    flower.classList.add('flower-open');
                }}
            }}

            window.onload = function() {{
                updateFlower({humidity});
            }}
        </script>
    </body>
    </html>
    """
    components.html(flower_html, height=400)

# Configuración de la app
st.set_page_config(page_title="🌿 Koru – Jardín Inteligente", layout="wide")
st.title("🌿 Koru – Jardín Inteligente para la Calma")
st.markdown("Monitorea en tiempo real los datos de tu planta: temperatura, humedad y movimiento.")

# Selector de tiempo
range_minutes = st.slider("Selecciona el rango de tiempo (en minutos):", 10, 180, 60)

# Consultas
temp_df = query_data("airSensor", "temperature", range_minutes)
hum_df = query_data("airSensor", "humidity", range_minutes)
mov_df = query_accelerometer_data(range_minutes)
gyro_df = query_gyroscope_data(range_minutes)

# Visualización
col1, col2 = st.columns(2)

with col1:
    st.subheader("🌡️ Temperatura (°C)")
    if not temp_df.empty:
        st.plotly_chart(px.line(temp_df, x="time", y="temperature", title="Temperatura"), use_container_width=True)
    else:
        st.info("Sin datos de temperatura en este rango.")

with col2:
    st.subheader("💧 Humedad (%)")
    if not hum_df.empty:
        st.plotly_chart(px.line(hum_df, x="time", y="humidity", title="Humedad"), use_container_width=True)
        # Mostrar la animación de la planta según la humedad
        latest_humidity = hum_df["humidity"].iloc[-1]
        show_flower_animation(latest_humidity)
    else:
        st.info("Sin datos de humedad en este rango.")

st.subheader("📈 Movimiento (magnitud del acelerómetro)")
if not mov_df.empty:
    st.plotly_chart(px.line(mov_df, x="time", y="accel_magnitude", title="Movimiento"), use_container_width=True)
else:
    st.info("Sin datos de movimiento en este rango.")

# Gráfico de orientación (Giroscopio)
st.subheader("🌀 Orientación (Giroscopio)")
if not gyro_df.empty:
    fig = px.line(gyro_df, x="time", y=["gx", "gy", "gz"], title="Orientación (gx, gy, gz)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sin datos del giroscopio en este rango.")
