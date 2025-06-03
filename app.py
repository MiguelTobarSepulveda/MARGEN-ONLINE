import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="Consulta de Márgenes", layout="wide")

@st.cache_data
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)

    libro_ventas = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("LIBRO DE VENTAS").get_all_records())
    recetas = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("RECETAS DE PRODUCTOS").get_all_records())
    insumos = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("PRECIO DE INSUMOS").get_all_records())

    return libro_ventas, recetas, insumos

ventas, recetas, insumos = load_data()

ventas["MES"] = pd.to_datetime(ventas["FECHA"]).dt.strftime("%Y-%m")
recetas["CANTIDAD USADA"] = pd.to_numeric(recetas["CANTIDAD USADA"], errors="coerce")
insumos["FECHA"] = pd.to_datetime(insumos["FECHA"])
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
ventas_exp["COSTO UNITARIO"] = ventas_exp["CANTIDAD USADA"] * ventas_exp["PRECIO"]
ventas_exp["COSTO UNITARIO"] = ventas_exp["COSTO UNITARIO"].fillna(0)

costos_por_venta = ventas_exp.groupby("FACTURA", as_index=False).agg({
    "COSTO UNITARIO": "sum",
    "CANTIDAD": "first",
    "PRECIO UNITARIO": "first",
    "PRODUCTO": "first",
    "CLIENTE": "first",
    "MES": "first"
})
costos_por_venta["COSTO UNITARIO FINAL"] = costos_por_venta["COSTO UNITARIO"] / costos_por_venta["CANTIDAD"]
costos_por_venta["MARGEN %"] = (
    (costos_por_venta["PRECIO UNITARIO"] - costos_por_venta["COSTO UNITARIO FINAL"]) / 
    costos_por_venta["PRECIO UNITARIO"]
).fillna(0)

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

st.title("Márgenes por Cliente y Producto")
st.dataframe(df[[
    "MES", "CLIENTE", "PRODUCTO", "FACTURA", "CANTIDAD",
    "PRECIO UNITARIO", "COSTO UNITARIO FINAL", "MARGEN %"
]].sort_values(by=["MES", "CLIENTE", "FACTURA"]))