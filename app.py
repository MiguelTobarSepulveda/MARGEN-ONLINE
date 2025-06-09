
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
    insumos_hist = pd.DataFrame(sheet.worksheet("PRECIO DE INSUMOS").get_all_records())

    return ventas, recetas, insumos_hist

ventas, recetas, insumos_hist = load_data_from_sheets()

# Asegurar formato correcto
ventas["CANTIDAD"] = pd.to_numeric(ventas["CANTIDAD"], errors="coerce").fillna(0)
ventas["PRECIO UNITARIO"] = pd.to_numeric(ventas["PRECIO UNITARIO"], errors="coerce").fillna(0)
insumos_hist["PRECIO INSUMO"] = pd.to_numeric(insumos_hist["PRECIO INSUMO"], errors="coerce").fillna(0)
recetas["CANTIDAD"] = pd.to_numeric(recetas["CANTIDAD"], errors="coerce").fillna(0)

# Calcular costo unitario por receta
recetas_insumos = pd.merge(recetas, insumos_hist, how="left", on=["CÓDIGO INSUMO", "MES"])
recetas_insumos["COSTO TOTAL"] = recetas_insumos["CANTIDAD"] * recetas_insumos["PRECIO INSUMO"]
costos_unitarios = recetas_insumos.groupby(["CÓDIGO PRODUCTO", "MES"], as_index=False)["COSTO TOTAL"].sum()
costos_unitarios.rename(columns={"COSTO TOTAL": "COSTO UNITARIO"}, inplace=True)

# Unir ventas con costos
ventas_costos = pd.merge(ventas, costos_unitarios, how="left", on=["CÓDIGO PRODUCTO", "MES"])
ventas_costos["COSTO UNITARIO"] = ventas_costos["COSTO UNITARIO"].fillna(0)
ventas_costos["MARGEN %"] = 1 - (ventas_costos["COSTO UNITARIO"] / ventas_costos["PRECIO UNITARIO"])
ventas_costos["MARGEN %"] = ventas_costos["MARGEN %"].fillna(1)
ventas_costos["SIN COSTEO"] = ventas_costos["COSTO UNITARIO"].apply(lambda x: "SI" if x == 0 else "NO")

# Interfaz
st.sidebar.header("Filtros")
clientes = ["Todos"] + sorted(ventas_costos["CLIENTE"].unique())
productos = ["Todos"] + sorted(ventas_costos["NOMBRE DE PRODUCTO"].unique())
meses = ["Todos"] + sorted(ventas_costos["MES"].unique())

cliente_sel = st.sidebar.selectbox("Cliente", clientes)
producto_sel = st.sidebar.selectbox("Producto", productos)
mes_sel = st.sidebar.selectbox("Mes", meses)

df_filtrado = ventas_costos.copy()
if cliente_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"] == cliente_sel]
if producto_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["NOMBRE DE PRODUCTO"] == producto_sel]
if mes_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["MES"] == mes_sel]

st.markdown("## Márgenes por Cliente y Producto")
st.dataframe(df_filtrado.reset_index(drop=True))
