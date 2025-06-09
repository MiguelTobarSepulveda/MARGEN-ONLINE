
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="Consulta de Márgenes", layout="wide")

@st.cache_data
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("MARGENES_AUTOMATIZADO")

    ventas = pd.DataFrame(sheet.worksheet("LIBRO DE VENTAS").get_all_records())
    recetas = pd.DataFrame(sheet.worksheet("RECETAS DE PRODUCTOS").get_all_records())
    insumos = pd.DataFrame(sheet.worksheet("PRECIO DE INSUMOS").get_all_records())

    return ventas, recetas, insumos

ventas, recetas, insumos = load_data()

# Convertir columnas clave a texto y limpiar espacios
ventas["CODIGO PRODUCTO"] = ventas["CODIGO PRODUCTO"].astype(str).str.strip()
recetas["CODIGO PRODUCTO"] = recetas["CODIGO PRODUCTO"].astype(str).str.strip()
insumos["CODIGO INSUMO"] = insumos["CODIGO INSUMO"].astype(str).str.strip()

# Convertir cantidades y precios
recetas["CANTIDAD"] = pd.to_numeric(recetas["CANTIDAD"], errors="coerce").fillna(0)
insumos["PRECIO"] = pd.to_numeric(insumos["PRECIO"], errors="coerce").fillna(0)
ventas["CANTIDAD PRODUCTO"] = pd.to_numeric(ventas["CANTIDAD PRODUCTO"], errors="coerce").fillna(0)
ventas["PRECIO UNITARIO"] = pd.to_numeric(ventas["PRECIO UNITARIO"], errors="coerce").fillna(0)

# Calcular costo unitario por receta
recetas = recetas.merge(insumos[["CODIGO INSUMO", "PRECIO"]], on="CODIGO INSUMO", how="left")
recetas["COSTO PARCIAL"] = recetas["CANTIDAD"] * recetas["PRECIO"]
costos_unitarios = recetas.groupby("CODIGO PRODUCTO", as_index=False)["COSTO PARCIAL"].sum()
costos_unitarios.rename(columns={"COSTO PARCIAL": "COSTO UNITARIO"}, inplace=True)

# Marcar productos con receta
costos_unitarios["TIENE COSTEO"] = True

# Unir con ventas
ventas = ventas.merge(costos_unitarios, on="CODIGO PRODUCTO", how="left")

# Rellenar productos sin receta
ventas["COSTO UNITARIO"] = ventas["COSTO UNITARIO"].fillna(0)
ventas["TIENE COSTEO"] = ventas["TIENE COSTEO"].fillna(False)

# Calcular margen
ventas["MARGEN %"] = 100 * (ventas["PRECIO UNITARIO"] - ventas["COSTO UNITARIO"]) / ventas["PRECIO UNITARIO"]
ventas["MARGEN %"] = ventas["MARGEN %"].round(4)

# Interfaz
st.sidebar.title("Filtros")
cliente_sel = st.sidebar.selectbox("Cliente", ["Todos"] + sorted(ventas["CLIENTE"].unique()))
producto_sel = st.sidebar.selectbox("Producto", ["Todos"] + sorted(ventas["NOMBRE PRODUCTO"].unique()))
mes_sel = st.sidebar.selectbox("Mes", ["Todos"] + sorted(ventas["MES"].unique()))

filtro = ventas.copy()
if cliente_sel != "Todos":
    filtro = filtro[filtro["CLIENTE"] == cliente_sel]
if producto_sel != "Todos":
    filtro = filtro[filtro["NOMBRE PRODUCTO"] == producto_sel]
if mes_sel != "Todos":
    filtro = filtro[filtro["MES"] == mes_sel]

st.title("Márgenes por Cliente y Producto")
st.dataframe(filtro[[
    "NOMBRE PRODUCTO", "NÚMERO", "CANTIDAD PRODUCTO", "PRECIO UNITARIO", "COSTO UNITARIO", "MARGEN %", "TIENE COSTEO"
]])
