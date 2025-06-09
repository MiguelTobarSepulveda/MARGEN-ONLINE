
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Consulta de Márgenes", layout="wide")

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

# Limpiar claves
ventas["CODIGO DE PRODUCTO"] = ventas["CODIGO DE PRODUCTO"].str.strip()
recetas["CODIGO DE PRODUCTO"] = recetas["CODIGO DE PRODUCTO"].str.strip()
recetas["CODIGO DE INSUMO"] = recetas["CODIGO DE INSUMO"].str.strip()
insumos["CODIGO DE INSUMO"] = insumos["CODIGO DE INSUMO"].str.strip()

# Convertir columnas a numéricas
recetas["CANTIDAD"] = pd.to_numeric(recetas["CANTIDAD"], errors="coerce").fillna(0)
insumos["PRECIO UNITARIO"] = pd.to_numeric(insumos["PRECIO UNITARIO"], errors="coerce").fillna(0)
ventas["CANTIDAD PRODUCTO"] = pd.to_numeric(ventas["CANTIDAD PRODUCTO"], errors="coerce").fillna(0)
ventas["NETO"] = pd.to_numeric(ventas["NETO"], errors="coerce").fillna(0)

# Unir recetas con precios de insumos
recetas_insumos = recetas.merge(insumos, on="CODIGO DE INSUMO", how="left")
recetas_insumos["COSTO INSUMO"] = recetas_insumos["CANTIDAD"] * recetas_insumos["PRECIO UNITARIO"]

# Calcular costo unitario por producto
costos = recetas_insumos.groupby("CODIGO DE PRODUCTO").agg(COSTO_UNITARIO=("COSTO INSUMO", "sum")).reset_index()

# Unir ventas con costos
ventas_costeadas = ventas.merge(costos, on="CODIGO DE PRODUCTO", how="left")

# Si no hay receta, costo = 0
ventas_costeadas["COSTO UNITARIO"] = ventas_costeadas["COSTO UNITARIO"].fillna(0)
ventas_costeadas["COSTO TOTAL"] = ventas_costeadas["CANTIDAD PRODUCTO"] * ventas_costeadas["COSTO UNITARIO"]

# Cálculo de margen
ventas_costeadas["MARGEN %"] = (
    (ventas_costeadas["NETO"] - ventas_costeadas["COSTO TOTAL"]) / ventas_costeadas["NETO"]
).fillna(1)

# Marcar productos sin costeo
ventas_costeadas["SIN COSTEO"] = ventas_costeadas["COSTO UNITARIO"].apply(lambda x: "SI" if x == 0 else "NO")

# Filtros
st.sidebar.title("Filtros")
clientes = ["Todos"] + sorted(ventas_costeadas["CLIENTE"].dropna().unique().tolist())
cliente_sel = st.sidebar.selectbox("Cliente", clientes)

productos = ["Todos"] + sorted(ventas_costeadas["NOMBRE DE PRODUCTO"].dropna().unique().tolist())
producto_sel = st.sidebar.selectbox("Producto", productos)

meses = ["Todos"] + sorted(ventas_costeadas["MES"].dropna().unique().tolist())
mes_sel = st.sidebar.selectbox("Mes", meses)

df = ventas_costeadas.copy()
if cliente_sel != "Todos":
    df = df[df["CLIENTE"] == cliente_sel]
if producto_sel != "Todos":
    df = df[df["NOMBRE DE PRODUCTO"] == producto_sel]
if mes_sel != "Todos":
    df = df[df["MES"] == mes_sel]

# Mostrar resultado
st.title("Márgenes por Cliente y Producto")
st.dataframe(df[[
    "CLIENTE", "NOMBRE DE PRODUCTO", "NÚMERO", "CANTIDAD PRODUCTO",
    "PRECIO UNITARIO", "COSTO UNITARIO", "COSTO TOTAL", "NETO", "MARGEN %", "SIN COSTEO"
]])
