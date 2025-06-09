
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

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

# Normalizar códigos
recetas["CÓDIGO INSUMO"] = recetas["CÓDIGO INSUMO"].str.strip().str.upper()
insumos["CÓDIGO INSUMO"] = insumos["CÓDIGO INSUMO"].str.strip().str.upper()
ventas["CÓDIGO PRODUCTO"] = ventas["CÓDIGO PRODUCTO"].str.strip().str.upper()
recetas["CÓDIGO PRODUCTO"] = recetas["CÓDIGO PRODUCTO"].str.strip().str.upper()

# Convertir numéricos
ventas["CANTIDAD PRODUCTO"] = pd.to_numeric(ventas["CANTIDAD PRODUCTO"], errors="coerce").fillna(0)
insumos["PRECIO UNITARIO"] = pd.to_numeric(insumos["PRECIO UNITARIO"], errors="coerce").fillna(0)
recetas["CANTIDAD"] = pd.to_numeric(recetas["CANTIDAD"], errors="coerce").fillna(0)

# Calcular costo unitario de receta
recetas = recetas.merge(insumos[["CÓDIGO INSUMO", "PRECIO UNITARIO"]], how="left", on="CÓDIGO INSUMO")
recetas["COSTO PARCIAL"] = recetas["CANTIDAD"] * recetas["PRECIO UNITARIO"]

# Sumar costos parciales por código producto
costo_unitario = recetas.groupby(["CÓDIGO PRODUCTO", "MES"])["COSTO PARCIAL"].sum().reset_index()
costo_unitario = costo_unitario.rename(columns={"COSTO PARCIAL": "COSTO UNITARIO"})

# Unir con ventas
ventas_exp = ventas.merge(costo_unitario, how="left", on=["CÓDIGO PRODUCTO", "MES"])

# Costo 0 si no hay receta
ventas_exp["COSTO UNITARIO"] = ventas_exp["COSTO UNITARIO"].fillna(0)

# Calcular margen
ventas_exp["MARGEN %"] = 1 - (ventas_exp["COSTO UNITARIO"] / ventas_exp["PRECIO UNITARIO"])
ventas_exp["MARGEN %"] = ventas_exp["MARGEN %"].replace([float("inf"), -float("inf")], 0).fillna(0)

# Columna SIN COSTEO
ventas_exp["SIN COSTEO"] = ventas_exp["COSTO UNITARIO"].apply(lambda x: "SI" if x == 0 else "NO")

# Filtros
st.sidebar.header("Filtros")
clientes = ["Todos"] + sorted(ventas_exp["CLIENTE"].dropna().unique().tolist())
cliente_sel = st.sidebar.selectbox("Cliente", clientes)

productos = ["Todos"] + sorted(ventas_exp["NOMBRE DE PRODUCTO"].dropna().unique().tolist())
producto_sel = st.sidebar.selectbox("Producto", productos)

meses = ["Todos"] + sorted(ventas_exp["MES"].dropna().unique().tolist())
mes_sel = st.sidebar.selectbox("Mes", meses)

# Aplicar filtros
df = ventas_exp.copy()
if cliente_sel != "Todos":
    df = df[df["CLIENTE"] == cliente_sel]
if producto_sel != "Todos":
    df = df[df["NOMBRE DE PRODUCTO"] == producto_sel]
if mes_sel != "Todos":
    df = df[df["MES"] == mes_sel]

# Mostrar resultados
st.markdown("## Márgenes por Cliente y Producto")
st.dataframe(df[[
    "NOMBRE DE PRODUCTO", "NÚMERO", "CANTIDAD PRODUCTO", "PRECIO UNITARIO",
    "COSTO UNITARIO", "MARGEN %", "SIN COSTEO"
]])
