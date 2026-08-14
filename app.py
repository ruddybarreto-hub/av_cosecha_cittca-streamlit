import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Avance de Cosecha", page_icon="🌱", layout="wide")
st.title("🌱 Avance de Cosecha")
st.caption("Seguimiento de cosecha por propiedad")

def preparar_datos(df):
    df = df.copy()
    if pd.api.types.is_numeric_dtype(df["fc"]):
        df["fc"] = pd.to_datetime(df["fc"], unit="D", origin="1899-12-30", errors="coerce")
    else:
        df["fc"] = pd.to_datetime(df["fc"], errors="coerce")
    return df

def calcular_resumen_propiedades(df):
    resumen = (
        df[df["estado"].isin(["Cosechado", "Sincosecha"])]
        .groupby(["unidad_01", "unidad_02", "estado"])["area"]
        .sum().unstack(fill_value=0).reset_index()
    )
    for col in ["Cosechado", "Sincosecha"]:
        if col not in resumen.columns:
            resumen[col] = 0
    resumen["Ha evaluables"] = resumen["Cosechado"] + resumen["Sincosecha"]
    resumen["Avance %"] = (resumen["Cosechado"] / resumen["Ha evaluables"] * 100).fillna(0)
    return resumen

def calcular_avance_semanal(df):
    return (
        df[df["estado"] == "Cosechado"]
        .groupby(["unidad_01", "unidad_02", "fci", "fc"])["area"]
        .sum().reset_index().sort_values(["unidad_02", "fci"])
    )

def calcular_acumulado(avance):
    avance = avance.copy()
    avance["ha_acumuladas"] = avance.groupby("unidad_02")["area"].cumsum()
    return avance

def calcular_porcentaje_avance(avance, resumen):
    avance = avance.merge(resumen[["unidad_02", "Ha evaluables"]], on="unidad_02", how="left")
    avance["avance_%"] = (avance["ha_acumuladas"] / avance["Ha evaluables"] * 100).fillna(0)
    return avance

def procesar_datos(df):
    df = preparar_datos(df)
    resumen = calcular_resumen_propiedades(df)
    avance = calcular_avance_semanal(df)
    avance = calcular_acumulado(avance)
    avance = calcular_porcentaje_avance(avance, resumen)
    return df, resumen, avance

archivo = Path("avance_cosecha.xlsx")
if not archivo.exists():
    st.error("No se encontró 'avance_cosecha.xlsx'. Colócalo junto a app.py.")
    st.stop()

try:
    df_original = pd.read_excel(archivo)
    df, resumen, avance = procesar_datos(df_original)
except Exception as e:
    st.error("No se pudo procesar el Excel.")
    st.exception(e)
    st.stop()

total_cosechado = resumen["Cosechado"].sum()
total_sin = resumen["Sincosecha"].sum()
total_eval = resumen["Ha evaluables"].sum()
avance_general = total_cosechado / total_eval * 100 if total_eval else 0

st.subheader("Resumen general")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ha cosechadas", f"{total_cosechado:,.2f}")
c2.metric("Ha sin cosecha", f"{total_sin:,.2f}")
c3.metric("Ha evaluables", f"{total_eval:,.2f}")
c4.metric("Avance", f"{avance_general:.2f}%")

st.subheader("Análisis por propiedad")
propiedades = ["Todas"] + sorted(resumen["unidad_02"].dropna().astype(str).unique())
seleccion = st.selectbox("Selecciona una propiedad", propiedades)

if seleccion == "Todas":
    resumen_f = resumen.copy()
    avance_f = avance.copy()
else:
    resumen_f = resumen[resumen["unidad_02"].astype(str) == seleccion].copy()
    avance_f = avance[avance["unidad_02"].astype(str) == seleccion].copy()

if seleccion != "Todas" and not resumen_f.empty:
    fila = resumen_f.iloc[0]
    st.markdown(f"### {seleccion}")
    a, b, c, d = st.columns(4)
    a.metric("Cosechado", f"{fila['Cosechado']:,.2f} ha")
    b.metric("Sin cosecha", f"{fila['Sincosecha']:,.2f} ha")
    c.metric("Ha evaluables", f"{fila['Ha evaluables']:,.2f} ha")
    d.metric("Avance", f"{fila['Avance %']:.2f}%")

if not avance_f.empty:
    st.subheader("📈 Evolución del avance")
    st.line_chart(avance_f.sort_values("fc").set_index("fc")["avance_%"])
    st.subheader("📊 Hectáreas cosechadas por FCI")
    st.bar_chart(avance_f.sort_values("fci").set_index("fci")["area"])
    st.subheader("📈 Hectáreas acumuladas")
    st.line_chart(avance_f.sort_values("fci").set_index("fci")["ha_acumuladas"])

st.subheader("📋 Resumen por propiedad")
tabla = resumen_f[["unidad_01","unidad_02","Cosechado","Sincosecha","Ha evaluables","Avance %"]].rename(columns={
    "unidad_01":"Código propiedad", "unidad_02":"Propiedad",
    "Cosechado":"Ha cosechadas", "Sincosecha":"Ha sin cosecha"
})
st.dataframe(tabla, use_container_width=True, hide_index=True)

if not avance_f.empty:
    st.subheader("📅 Avance semanal")
    tabla_a = avance_f[["unidad_01","unidad_02","fci","fc","area","ha_acumuladas","Ha evaluables","avance_%"]].rename(columns={
        "unidad_01":"Código propiedad", "unidad_02":"Propiedad", "fci":"FCI",
        "fc":"Fecha cosecha", "area":"Ha nuevas", "ha_acumuladas":"Ha acumuladas",
        "avance_%":"Avance %"
    })
    st.dataframe(tabla_a, use_container_width=True, hide_index=True)

st.caption(f"Registros procesados: {len(df):,} | Propiedades: {resumen['unidad_02'].nunique():,}")
