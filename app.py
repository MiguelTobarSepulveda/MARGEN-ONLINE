import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.set_page_config(page_title="Márgenes por Cliente y Producto", layout="wide")

@st.cache_data
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_credentials.json", scope)
    client = gspread.authorize(creds)

    # Reemplaza con el nombre exacto de tu archivo de Google Sheets
    sheet = client.open("MARGENES_AUTOMATIZADO")
    ventas = pd.DataFrame(sheet.worksheet("LIBRO DE VENTAS").get_all_records())
    recetas = pd.DataFrame(sheet.worksheet("RECETAS DE PRODUCTOS").get_all_records())
    insumos = pd.DataFrame(sheet.worksheet("PRECIO DE INSUMOS").get_all_records())
    return ventas, recetas, insumos

ventas, recetas, insumos = load_data()

ventas["MES"] = pd.to_datetime(ventas["FECHA"], errors="coerce").dt.strftime("%Y-%m")
insumos["FECHA"] = pd.to_datetime(insumos["FECHA"], errors="coerce")
insumos["MES"] = insumos["FECHA"].dt.strftime("%Y-%m")

ventas_exp = ventas.merge(recetas, on="CODIGO PRODUCTO", how="left")

ultimos_precios = (
    insumos.sort_values("FECHA")
    .groupby(["CODIGO INSUMO", "MES"], as_index=False)
    .last()
)

ventas_exp = ventas_exp.merge(
    ultimos_precios[["CODIGO INSUMO", "MES", "PRECIO"]],
    on=["CODIGO INSUMO", "MES"],
    how="left"
)

ventas_exp["CANTIDAD INSUMO"] = pd.to_numeric(ventas_exp["CANTIDAD"], errors="coerce")
ventas_exp["COSTO UNITARIO"] = ventas_exp["CANTIDAD INSUMO"] * ventas_exp["PRECIO"]
ventas_exp["COSTO UNITARIO"] = ventas_exp["COSTO UNITARIO"].fillna(0)

costos = ventas_exp.groupby(["NÚMERO"], as_index=False).agg({
    "COSTO UNITARIO": "sum",
    "CANTIDAD_x": "first",
    "PRECIO UNITARIO": "first",
    "NOMBRE DE PRODUCTO": "first",
    "CLIENTE": "first",
    "MES": "first",
    "CODIGO PRODUCTO": "first"
})

costos["COSTO UNITARIO FINAL"] = costos["COSTO UNITARIO"] / costos["CANTIDAD_x"]
costos["MARGEN %"] = (
    (costos["PRECIO UNITARIO"] - costos["COSTO UNITARIO FINAL"]) /
    costos["PRECIO UNITARIO"]
).fillna(0)

st.sidebar.header("Filtros")
cliente_sel = st.sidebar.selectbox("Cliente", ["Todos"] + sorted(costos["CLIENTE"].dropna().unique()))
producto_sel = st.sidebar.selectbox("Producto", ["Todos"] + sorted(costos["NOMBRE DE PRODUCTO"].dropna().unique()))
mes_sel = st.sidebar.selectbox("Mes", ["Todos"] + sorted(costos["MES"].dropna().unique()))

df = costos.copy()
if cliente_sel != "Todos":
    df = df[df["CLIENTE"] == cliente_sel]
if producto_sel != "Todos":
    df = df[df["NOMBRE DE PRODUCTO"] == producto_sel]
if mes_sel != "Todos":
    df = df[df["MES"] == mes_sel]

st.title("Márgenes por Cliente y Producto")
st.dataframe(df[[
    "MES", "CLIENTE", "NOMBRE DE PRODUCTO", "NÚMERO", "CANTIDAD_x",
    "PRECIO UNITARIO", "COSTO UNITARIO FINAL", "MARGEN %"
]].rename(columns={"NÚMERO": "FACTURA", "CANTIDAD_x": "CANTIDAD"}))