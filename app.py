import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Márgenes por Cliente y Producto", layout="wide")

@st.cache_data
def load_data_from_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("MARGENES_AUTOMATIZADO")

    ventas = pd.DataFrame(sheet.worksheet("LIBRO DE VENTAS").get_all_records())
    recetas = pd.DataFrame(sheet.worksheet("RECETAS DE PRODUCTOS").get_all_records())
    insumos = pd.DataFrame(sheet.worksheet("PRECIO DE INSUMOS").get_all_records())

    return ventas, recetas, insumos

ventas, recetas, insumos = load_data_from_sheets()

# Normalización
recetas["CODIGO INSUMO"] = recetas["CODIGO INSUMO"].str.strip().str.upper()
recetas["CODIGO DE PRODUCTO"] = recetas["CODIGO DE PRODUCTO"].str.strip().str.upper()
insumos["CODIGO INSUMO"] = insumos["CODIGO INSUMO"].str.strip().str.upper()
ventas["CODIGO DE PRODUCTO"] = ventas["CODIGO DE PRODUCTO"].str.strip().str.upper()

# Asegurar tipos numéricos
ventas["CANTIDAD PRODUCTO"] = pd.to_numeric(ventas["CANTIDAD PRODUCTO"], errors="coerce").fillna(0)
ventas["NETO"] = pd.to_numeric(ventas["NETO"], errors="coerce").fillna(0)
recetas["CANTIDAD"] = pd.to_numeric(recetas["CANTIDAD"], errors="coerce").fillna(0)
insumos["PRECIO"] = pd.to_numeric(insumos["PRECIO"], errors="coerce").fillna(0)

# Calcular el costo por unidad para cada producto
recetas_insumos = pd.merge(recetas, insumos, on="CODIGO INSUMO", how="left")
recetas_insumos["COSTO PARCIAL"] = recetas_insumos["CANTIDAD"] * recetas_insumos["PRECIO"]
costo_unitario = recetas_insumos.groupby("CODIGO DE PRODUCTO")["COSTO PARCIAL"].sum().reset_index()
costo_unitario.columns = ["CODIGO DE PRODUCTO", "COSTO UNITARIO"]

# Marcar productos sin receta
productos_con_receta = set(costo_unitario["CODIGO DE PRODUCTO"])
ventas["SIN RECETA"] = ~ventas["CODIGO DE PRODUCTO"].isin(productos_con_receta)

# Unir con ventas
ventas_costos = pd.merge(ventas, costo_unitario, on="CODIGO DE PRODUCTO", how="left")
ventas_costos["COSTO UNITARIO"] = ventas_costos["COSTO UNITARIO"].fillna(0)

# Calcular margen
ventas_costos["PRECIO UNITARIO"] = ventas_costos["NETO"] / ventas_costos["CANTIDAD PRODUCTO"]
ventas_costos["MARGEN %"] = 1 - (ventas_costos["COSTO UNITARIO"] / ventas_costos["PRECIO UNITARIO"])
ventas_costos["MARGEN %"] = ventas_costos["MARGEN %"].replace([float("inf"), -float("inf")], 1).fillna(1)

# Filtros UI
cliente_sel = st.sidebar.selectbox("Cliente", ["Todos"] + sorted(ventas_costos["CLIENTE"].unique()))
producto_sel = st.sidebar.selectbox("Producto", ["Todos"] + sorted(ventas_costos["NOMBRE DE PRODUCTO"].unique()))
mes_sel = st.sidebar.selectbox("Mes", ["Todos"] + sorted(ventas_costos["MES"].unique()))

df_filtrado = ventas_costos.copy()
if cliente_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"] == cliente_sel]
if producto_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["NOMBRE DE PRODUCTO"] == producto_sel]
if mes_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["MES"] == mes_sel]

st.markdown("## Márgenes por Cliente y Producto")
st.dataframe(df_filtrado[[
    "NOMBRE DE PRODUCTO", "NÚMERO", "CANTIDAD PRODUCTO", "PRECIO UNITARIO",
    "COSTO UNITARIO", "MARGEN %", "SIN RECETA"
]])