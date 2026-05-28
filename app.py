import base64
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st


# ======================
# Streamlit setup
# ======================
st.set_page_config(page_title="Spiermassa Calculator")
st.title("Spiermassa Berekening")

# ======================
# Bestanden
# ======================
APP_DIR = Path(__file__).parent
gegevens_bestand = APP_DIR / "gegevens.csv"
metingen_bestand = APP_DIR / "metingen.csv"

basis = None

if gegevens_bestand.exists():
    basis = pd.read_csv(gegevens_bestand)
else:
    st.warning(
        "Kan gegevens.csv niet vinden. Je kunt de calculator wel gebruiken zonder SAMU nummer."
    )

# ======================
# SAMU/ID optioneel gebruiken
# ======================
gebruik_samu = False
persoon = None
id_keuze = ""

if basis is not None and "ID" in basis.columns:
    gebruik_samu = st.checkbox("Gegevens ophalen met SAMU nummer / ID", value=True)

    if gebruik_samu:
        id_keuze = st.selectbox("Selecteer SAMU nummer / ID", basis["ID"])
        persoon = basis[basis["ID"] == id_keuze].iloc[0]
else:
    st.info("Vul de gegevens handmatig in.")

# ======================
# Lengte input
# ======================
if persoon is not None and "lnght" in basis.columns and not pd.isna(persoon["lnght"]):
    default_lnght = float(persoon["lnght"])
else:
    default_lnght = 170.0

lnght = st.number_input(
    "Lengte (cm)",
    min_value=50.0,
    max_value=250.0,
    step=0.1,
    value=default_lnght,
)

# ======================
# Geslacht input
# ======================
geslacht_opties = ["Man", "Vrouw"]
default_geslacht_index = 0

if persoon is not None and "sex_janssen_modified" in basis.columns:
    sex_uit_csv = persoon["sex_janssen_modified"]

    if pd.isna(sex_uit_csv):
        st.warning("Geslacht ontbreekt voor dit SAMU nummer / ID. Kies hieronder:")
    else:
        default_geslacht_index = 0 if int(sex_uit_csv) == 1 else 1

geslacht_txt = st.selectbox("Geslacht", geslacht_opties, index=default_geslacht_index)
sex_janssen_modified = 1 if geslacht_txt == "Man" else 0

st.write(f"**Geselecteerde lengte:** {lnght} cm")
st.write(f"**Geselecteerd geslacht:** {geslacht_txt}")

# ======================
# Gewicht & Resistentie
# ======================
wght = st.number_input(
    "Gewicht (kg)",
    min_value=30.0,
    max_value=200.0,
    step=0.1,
)

bia_res = st.number_input(
    "Resistentie",
    min_value=1.0,
    max_value=1000.0,
    step=1.0,
)

# ======================
# Berekening
# ======================
def bereken_spiermassa(lnght, wght, bia_res, sex_janssen_modified):
    try:
        spiermassa = (
            (
                0.827
                + (0.19 * (lnght**2 / bia_res))
                + (2.101 * sex_janssen_modified)
                + (0.079 * wght)
            )
            / ((lnght**2) / 10000)
        )
        return spiermassa
    except ZeroDivisionError:
        return None


def sla_meting_lokaal_op(nieuwe_meting):
    nieuwe_rij = pd.DataFrame([nieuwe_meting])

    if metingen_bestand.exists():
        bestaande_metingen = pd.read_csv(metingen_bestand)
        alle_metingen = pd.concat([bestaande_metingen, nieuwe_rij], ignore_index=True)
    else:
        alle_metingen = nieuwe_rij

    alle_metingen.to_csv(metingen_bestand, index=False)
    return alle_metingen


def github_config_is_aanwezig():
    return all(
        sleutel in st.secrets
        for sleutel in ["GITHUB_TOKEN", "GITHUB_REPO", "GITHUB_BRANCH", "GITHUB_METINGEN_PAD"]
    )


def sla_metingen_op_in_github(df_metingen):
    if not github_config_is_aanwezig():
        st.warning(
            "De meting is lokaal opgeslagen, maar niet in GitHub. "
            "Controleer je Streamlit secrets."
        )
        return

    github_token = st.secrets["GITHUB_TOKEN"]
    github_repo = st.secrets["GITHUB_REPO"]
    github_branch = st.secrets["GITHUB_BRANCH"]
    github_pad = st.secrets["GITHUB_METINGEN_PAD"]

    encoded_pad = quote(github_pad, safe="/")
    url = f"https://api.github.com/repos/{github_repo}/contents/{encoded_pad}"

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    bestaand_bestand = requests.get(
        url,
        headers=headers,
        params={"ref": github_branch},
        timeout=20,
    )

    sha = None

    if bestaand_bestand.status_code == 200:
        sha = bestaand_bestand.json()["sha"]
    elif bestaand_bestand.status_code != 404:
        st.error(f"GitHub bestand ophalen mislukt: {bestaand_bestand.text}")
        return

    csv_tekst = df_metingen.to_csv(index=False)
    inhoud_base64 = base64.b64encode(csv_tekst.encode("utf-8")).decode("utf-8")

    data = {
        "message": f"Meting opgeslagen op {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": inhoud_base64,
        "branch": github_branch,
    }

    if sha is not None:
        data["sha"] = sha

    resultaat = requests.put(url, headers=headers, json=data, timeout=20)

    if resultaat.status_code in [200, 201]:
        st.success("Meting is opgeslagen in GitHub.")
    else:
        st.error(f"Opslaan in GitHub mislukt: {resultaat.text}")


# ======================
# Resultaat + opslaan
# ======================
if wght > 0 and bia_res > 0:
    spiermassa = bereken_spiermassa(lnght, wght, bia_res, sex_janssen_modified)

    if spiermassa is None:
        st.error("Fout in berekening: Resistentie mag niet nul zijn.")
    else:
        st.success(f"Spiermassa: {spiermassa:.2f} kg")

        if st.button("Opslaan"):
            nieuwe_meting = {
                "ID": id_keuze if gebruik_samu else "",
                "Gender": geslacht_txt,
                "Lengte_cm": lnght,
                "Gewicht_kg": wght,
                "Resistentie": bia_res,
                "Spiermassa": round(spiermassa, 2),
                "Datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            df_metingen = sla_meting_lokaal_op(nieuwe_meting)
            st.info("Meting lokaal opgeslagen.")
            sla_metingen_op_in_github(df_metingen)

# ======================
# Bekijk alle metingen
# ======================
if metingen_bestand.exists():
    st.subheader("Alle opgeslagen metingen")
    df_metingen = pd.read_csv(metingen_bestand)
    st.dataframe(df_metingen)

    st.download_button(
        "Download metingen als CSV",
        data=df_metingen.to_csv(index=False).encode("utf-8"),
        file_name="metingen.csv",
        mime="text/csv",
    )
