import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ======================
# Streamlit setup
# ======================
st.set_page_config(page_title="Spiermassa Calculator")
st.title("Spiermassa Berekening")

# ======================
# CSV inladen
# ======================
bestand = "gegevens.csv"

if not os.path.exists(bestand):
    st.error(f"Kan bestand niet vinden: {bestand}. Zorg dat het in dezelfde map staat als app.py.")
    st.stop()

basis = pd.read_csv(bestand)

# ======================
# ID selecteren
# ======================
id_keuze = st.selectbox("Selecteer ID", basis["ID"])
persoon = basis[basis["ID"] == id_keuze].iloc[0]

# ======================
# Lengte input
# ======================
default_lengte = None if pd.isna(persoon["lnght"]) else float(persoon["lnght"])

lnght = st.number_input(
    "Lengte (cm)",
    min_value=50.0,
    max_value=250.0,
    step=0.1,
    value=default_lengte
)

# ======================
# Geslacht input
# ======================
opties = ["", "Man", "Vrouw"]

if not pd.isna(persoon["sex_janssen_modified"]):
    sex_val = int(persoon["sex_janssen_modified"])
    default_index = 1 if sex_val == 1 else 2
else:
    default_index = 0

geslacht_txt = st.selectbox(
    "Geslacht",
    opties,
    index=default_index
)

if geslacht_txt == "Man":
    sex_janssen_modified = 1
elif geslacht_txt == "Vrouw":
    sex_janssen_modified = 0
else:
    sex_janssen_modified = None

st.write(f"**Geselecteerde lengte:** {lnght if lnght else 'Niet ingevuld'}")
st.write(f"**Geselecteerd geslacht:** {geslacht_txt if geslacht_txt else 'Niet ingevuld'}")

# ======================
# Gewicht & Resistentie
# ======================
wght = st.number_input(
    "Gewicht (kg)",
    min_value=30.0,
    max_value=200.0,
    step=0.1,
    value=None
)

bia_res = st.number_input(
    "Resistentie",
    min_value=1.0,
    max_value=1000.0,
    step=1.0,
    value=None
)

# ======================
# Berekeningsfunctie
# ======================
def bereken_spiermassa(lnght, wght, bia_res, sex):
    try:
        spiermassa = (
            (0.827 + (0.19 * (lnght**2 / bia_res)) + (2.101 * sex) + (0.079 * wght))
            / ((lnght**2) / 10000)
        )
        return spiermassa
    except ZeroDivisionError:
        return None

# ======================
# Berekening
# ======================
if None not in (lnght, wght, bia_res, sex_janssen_modified):

    spiermassa = bereken_spiermassa(lnght, wght, bia_res, sex_janssen_modified)

    if spiermassa is None:
        st.error("Fout in berekening: Resistentie mag niet nul zijn.")
    else:
        st.success(f"Spiermassa: {spiermassa:.2f} kg")

        # ======================
        # Opslaan
        # ======================
        if st.button("Opslaan"):

            nieuwe_rij = pd.DataFrame([{
                "ID": id_keuze,
                "Gender": geslacht_txt,
                "Lengte_cm": lnght,
                "Gewicht_kg": wght,
                "Resistentie": bia_res,
                "Spiermassa": spiermassa,
                "Datum": datetime.now()
            }])

            if os.path.exists("metingen.csv"):
                oud = pd.read_csv("metingen.csv")
                nieuwe_rij = pd.concat([oud, nieuwe_rij], ignore_index=True)

            nieuwe_rij.to_csv("metingen.csv", index=False)
            st.info("Meting opgeslagen ✔")

# ======================
# Bekijk metingen
# ======================
if os.path.exists("metingen.csv"):
    st.subheader("Alle opgeslagen metingen")
    df_metingen = pd.read_csv("metingen.csv")
    st.dataframe(df_metingen)

