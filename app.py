import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Márgenes por Cliente y Producto", layout="wide")

# Conexión con Google Sheets usando archivo local
@st.cache_data
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_credentials.json", scope)
    client = gspread.authorize(creds)

    ventas = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("LIBRO DE VENTAS").get_all_records())
    recetas = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("RECETAS DE PRODUCTOS").get_all_records())
    insumos = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("PRECIO DE INSUMOS").get_all_records())

    return ventas, recetas, insumos

ventas, recetas, insumos = load_data()

# --- BLOQUE DE CRUCE SEGURO POR CÓDIGO DE PRODUCTO ---

ventas["MES"] = pd.to_datetime(ventas["FECHA"], errors="coerce").dt.strftime("%Y-%m")
recetas["CANTIDAD USADA"] = pd.to_numeric(recetas["CANTIDAD USADA"], errors="coerce")
insumos["FECHA"] = pd.to_datetime(insumos["FECHA"], errors="coerce")
insumos["MES"] = insumos["FECHA"].dt.strftime("%Y-%m")

ventas_exp = ventas.merge(recetas, on="CÓDIGO PRODUCTO", how="left")

ultimos_precios = (
    insumos.sort_values("FECHA")
    .groupby(["CÓDIGO INSUMO", "MES"], as_index=False)
    .last()
)

ventas_exp = ventas_exp.merge(
    ultimos_precios[["CÓDIGO INSUMO", "MES", "PRECIO"]],
    on=["CÓDIGO INSUMO", "MES"],
    how="left"
)

ventas_exp["COSTO UNITARIO"] = ventas_exp["CANTIDAD USADA"] * ventas_exp["PRECIO"]
ventas_exp["COSTO UNITARIO"] = ventas_exp["COSTO UNITARIO"].fillna(0)

costos_por_venta = ventas_exp.groupby("NRO FACTURA", as_index=False).agg({
    "COSTO UNITARIO": "sum",
    "CANTIDAD": "first",
    "PRECIO UNITARIO": "first",
    "PRODUCTO": "first",
    "CLIENTE": "first",
    "MES": "first",
    "CÓDIGO PRODUCTO": "first"
})

costos_por_venta["COSTO UNITARIO FINAL"] = costos_por_venta["COSTO UNITARIO"] / costos_por_venta["CANTIDAD"]
costos_por_venta["MARGEN %"] = (
    (costos_por_venta["PRECIO UNITARIO"] - costos_por_venta["COSTO UNITARIO FINAL"]) /
    costos_por_venta["PRECIO UNITARIO"]
).fillna(0)

todos_los_productos = ventas[["CÓDIGO PRODUCTO", "PRODUCTO"]].drop_duplicates()
costos_por_venta = todos_los_productos.merge(costos_por_venta, on="CÓDIGO PRODUCTO", how="left")

costos_por_venta["COSTO UNITARIO FINAL"] = costos_por_venta["COSTO UNITARIO FINAL"].fillna(0)
costos_por_venta["MARGEN %"] = costos_por_venta["MARGEN %"].fillna(0)

# Filtros
st.sidebar.header("Filtros")
cliente_sel = st.sidebar.selectbox("Cliente", ["Todos"] + sorted(costos_por_venta["CLIENTE"].dropna().unique().tolist()))
producto_sel = st.sidebar.selectbox("Producto", ["Todos"] + sorted(costos_por_venta["PRODUCTO"].dropna().unique().tolist()))
mes_sel = st.sidebar.selectbox("Mes", ["Todos"] + sorted(costos_por_venta["MES"].dropna().unique().tolist()))

df = costos_por_venta.copy()
if cliente_sel != "Todos":
    df = df[df["CLIENTE"] == cliente_sel]
if producto_sel != "Todos":
    df = df[df["PRODUCTO"] == producto_sel]
if mes_sel != "Todos":
    df = df[df["MES"] == mes_sel]

# Mostrar resultados
st.title("Márgenes por Cliente y Producto")
st.dataframe(df[[
    "MES", "CLIENTE", "PRODUCTO", "NRO FACTURA", "CANTIDAD",
    "PRECIO UNITARIO", "COSTO UNITARIO FINAL", "MARGEN %"
]].sort_values(by=["MES", "CLIENTE", "NRO FACTURA"]))