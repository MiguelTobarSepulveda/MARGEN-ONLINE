
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración de la página
st.set_page_config(page_title="Consulta de Márgenes", layout="wide")

# Conexión a Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_credentials.json", scope)
client = gspread.authorize(creds)

# Cargar hojas
ventas = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("LIBRO DE VENTAS").get_all_records())
recetas = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("RECETAS DE PRODUCTOS").get_all_records())
insumos = pd.DataFrame(client.open("MARGENES_AUTOMATIZADO").worksheet("PRECIO DE INSUMOS").get_all_records())

# Limpiar encabezados
ventas.columns = ventas.columns.str.strip()
recetas.columns = recetas.columns.str.strip()
insumos.columns = insumos.columns.str.strip()

# Normalizar claves
ventas["CODIGO DE PRODUCTO"] = ventas["CODIGO DE PRODUCTO"].str.strip()
recetas["CODIGO DE PRODUCTO"] = recetas["CODIGO DE PRODUCTO"].str.strip()
recetas["CODIGO INSUMO"] = recetas["CODIGO INSUMO"].str.strip()
insumos["CODIGO INSUMO"] = insumos["CODIGO INSUMO"].str.strip()

# Convertir columnas numéricas
ventas["CANTIDAD PRODUCTO"] = pd.to_numeric(ventas["CANTIDAD PRODUCTO"], errors="coerce").fillna(0)
ventas["NETO"] = pd.to_numeric(ventas["NETO"], errors="coerce").fillna(0)
recetas["CANTIDAD"] = pd.to_numeric(recetas["CANTIDAD"], errors="coerce").fillna(0)
insumos["PRECIO"] = pd.to_numeric(insumos["PRECIO"], errors="coerce").fillna(0)

# Calcular costo unitario
recetas_insumos = pd.merge(recetas, insumos, on="CODIGO INSUMO", how="left")
recetas_insumos["COSTO PARCIAL"] = recetas_insumos["CANTIDAD"] * recetas_insumos["PRECIO"]
costo_unitario = recetas_insumos.groupby("CODIGO DE PRODUCTO")["COSTO PARCIAL"].sum().reset_index()
costo_unitario.rename(columns={"COSTO PARCIAL": "COSTO UNITARIO"}, inplace=True)

# Agregar costeo a ventas
ventas_merge = pd.merge(ventas, costo_unitario, on="CODIGO DE PRODUCTO", how="left")
ventas_merge["COSTO UNITARIO"] = ventas_merge["COSTO UNITARIO"].fillna(0)
ventas_merge["TIENE COSTEO"] = ventas_merge["COSTO UNITARIO"].apply(lambda x: "Sí" if x > 0 else "No")

# Cálculo del margen
ventas_merge["PRECIO UNITARIO"] = ventas_merge["NETO"] / ventas_merge["CANTIDAD PRODUCTO"]
ventas_merge["MARGEN %"] = 1 - (ventas_merge["COSTO UNITARIO"] / ventas_merge["PRECIO UNITARIO"])
ventas_merge["MARGEN %"] = ventas_merge["MARGEN %"].round(4)

# Interfaz Streamlit
st.sidebar.title("Filtros")

cliente_sel = st.sidebar.selectbox("Cliente", ["Todos"] + sorted(ventas_merge["CLIENTE"].unique()))
producto_sel = st.sidebar.selectbox("Producto", ["Todos"] + sorted(ventas_merge["NOMBRE DE PRODUCTO"].unique()))
mes_sel = st.sidebar.selectbox("Mes", ["Todos"] + sorted(ventas_merge["MES"].unique()))

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
