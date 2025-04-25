import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
import numpy as np

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

# Mostrar animación de la planta con p5.js
st.subheader("🌱 Estado de la Planta según la Humedad")

# Obtener el último valor de humedad
latest_humidity = hum_df["humidity"].iloc[-1] if not hum_df.empty else 0

# Incluir animación HTML con p5.js
plant_animation = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Planta Interactiva</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.4.0/p5.js"></script>
    <script>
        let humidity = {latest_humidity}; // Valor de humedad obtenido
        let plantHeight = map(humidity, 0, 100, 100, 300);
        let leafSize = map(humidity, 0, 100, 30, 80);       
        let leafAngle = map(humidity, 0, 100, 0, PI / 4);  // Ángulo de las hojas
        let leafColor = color(34, 139, 34); // Color verde de las hojas

        function setup() {{
            createCanvas(400, 400);
            noStroke();
        }}

        function draw() {{
            background(255);

            // Dibujar el suelo
            fill(139, 69, 19);
            rect(0, height - 50, width, 50);

            // Dibujar el tallo
            fill(34, 139, 34); // Color verde
            rect(width / 2 - 10, height - 50 - plantHeight, 20, plantHeight);

            // Hojas con ángulo de rotación
            fill(leafColor);
            push();
            translate(width / 2 - leafSize / 2, height - 50 - plantHeight / 2);
            rotate(leafAngle);
            ellipse(0, 0, leafSize, leafSize);
            pop();
            push();
            translate(width / 2 + leafSize / 2, height - 50 - plantHeight / 2);
            rotate(-leafAngle);
            ellipse(0, 0, leafSize, leafSize);
            pop();

            // Cambiar color de la planta dependiendo de la humedad
            if (humidity > 60) {{
                fill(0, 128, 0);  // Verde oscuro (alta humedad)
            }} else if (humidity > 30) {{
                fill(85, 107, 47); // Verde oliva (media humedad)
            }} else {{
                fill(169, 169, 169); // Gris (baja humedad)
            }}
            ellipse(width / 2, height - 50 - plantHeight / 2, leafSize, leafSize);
        }}
    </script>
</head>
<body>
    <div id="sketch-holder"></div>
</body>
</html>
"""

# Mostrar la animación en el app
st.components.v1.html(plant_animation, height=400)
