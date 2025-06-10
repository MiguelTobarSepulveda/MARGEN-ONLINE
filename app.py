
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración de acceso a Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_credentials.json", scope)
client = gspread.authorize(creds)

# Cargar las hojas de cálculo
libro_ventas = pd.DataFrame(client.open("FORMATO PARA ARCHIVO GOOGLESHEETS").worksheet("LIBRO DE VENTAS").get_all_records())
recetas = pd.DataFrame(client.open("FORMATO PARA ARCHIVO GOOGLESHEETS").worksheet("RECETAS DE PRODUCTOS").get_all_records())
precios = pd.DataFrame(client.open("FORMATO PARA ARCHIVO GOOGLESHEETS").worksheet("PRECIO DE INSUMOS").get_all_records())

# Normalización de nombres
libro_ventas.columns = libro_ventas.columns.str.strip().str.upper()
recetas.columns = recetas.columns.str.strip().str.upper()
precios.columns = precios.columns.str.strip().str.upper()

# Limpieza de datos
for col in ["CODIGO DE PRODUCTO", "CODIGO INSUMO"]:
    if col in recetas.columns:
        recetas[col] = recetas[col].str.strip().str.upper()
    if col in libro_ventas.columns:
        libro_ventas[col] = libro_ventas[col].str.strip().str.upper()
    if col in precios.columns:
        precios[col] = precios[col].str.strip().str.upper()

# Convertir precios a numérico
precios["PRECIO"] = precios["PRECIO"].replace('[\$,]', '', regex=True).str.replace('.', '').str.replace(',', '.')
precios["PRECIO"] = pd.to_numeric(precios["PRECIO"], errors="coerce").fillna(0)

# Convertir cantidades
libro_ventas["CANTIDAD PRODUCTO"] = pd.to_numeric(libro_ventas["CANTIDAD PRODUCTO"], errors="coerce").fillna(0)
libro_ventas["NETO"] = pd.to_numeric(libro_ventas["NETO"], errors="coerce").fillna(0)
recetas["CANTIDAD"] = pd.to_numeric(recetas["CANTIDAD"], errors="coerce").fillna(0)

# Costo por insumo
recetas_precio = pd.merge(recetas, precios[["CODIGO INSUMO", "PRECIO"]], on="CODIGO INSUMO", how="left")
recetas_precio["COSTO UNITARIO"] = recetas_precio["CANTIDAD"] * recetas_precio["PRECIO"]

# Sumar costo por producto
costo_producto = recetas_precio.groupby("CODIGO DE PRODUCTO")["COSTO UNITARIO"].sum().reset_index()

# Merge con libro de ventas
ventas_merge = pd.merge(libro_ventas, costo_producto, on="CODIGO DE PRODUCTO", how="left")
ventas_merge["TIENE COSTEO"] = ventas_merge["COSTO UNITARIO"].notna()
ventas_merge["COSTO UNITARIO"] = ventas_merge["COSTO UNITARIO"].fillna(0)

# Calcular márgenes
ventas_merge["PRECIO UNITARIO"] = ventas_merge["NETO"] / ventas_merge["CANTIDAD PRODUCTO"]
ventas_merge["MARGEN %"] = 1 - (ventas_merge["COSTO UNITARIO"] / ventas_merge["PRECIO UNITARIO"])
ventas_merge["MARGEN %"] = ventas_merge["MARGEN %"].replace([float("inf"), -float("inf")], 0).fillna(0)
ventas_merge["TIENE COSTEO"] = ventas_merge["TIENE COSTEO"].map({True: "Sí", False: "No"})

# Interfaz Streamlit
st.sidebar.title("Filtros")
cliente_sel = st.sidebar.selectbox("Cliente", ["Todos"] + sorted(ventas_merge["CLIENTE"].dropna().unique().tolist()))
producto_sel = st.sidebar.selectbox("Producto", ["Todos"] + sorted(ventas_merge["NOMBRE DE PRODUCTO"].dropna().unique().tolist()))
mes_sel = st.sidebar.selectbox("Mes", ["Todos"] + sorted(ventas_merge["MES"].dropna().unique().tolist()))

filtro = ventas_merge.copy()
if cliente_sel != "Todos":
    filtro = filtro[filtro["CLIENTE"] == cliente_sel]
if producto_sel != "Todos":
    filtro = filtro[filtro["NOMBRE DE PRODUCTO"] == producto_sel]
if mes_sel != "Todos":
    filtro = filtro[filtro["MES"] == mes_sel]

st.title("Márgenes por Cliente y Producto")
st.dataframe(filtro[[
    "NOMBRE DE PRODUCTO", "NÚMERO", "CANTIDAD PRODUCTO", "PRECIO UNITARIO", 
    "COSTO UNITARIO", "MARGEN %", "TIENE COSTEO"
]])
