import streamlit as st
import google.generativeai as genai
import json
from PIL import Image
import io

# 1. Konfiguracija Gemini API-ja s tvojim ključem
API_KEY = "AQ.Ab8RN6IJcde0Xtw8qbWoJZ_eDelB_Wrdg35axbOcUMeTorFWgg"
genai.configure(api_key=API_KEY)

# Postavke stranice optimizirane za mobitele
st.set_page_config(page_title="Multi-Dućan Letak", layout="centered")
st.title("🛍️ Pametni Čitač Letaka")
st.caption("Učitaj letke iz različitih dućana, a AI će izvući i kategorizirati sve akcije!")

# Inicijalizacija baze podataka u memoriji aplikacije
if "sve_akcije" not in st.session_state:
    st.session_state.sve_akcije = []

# --- 1. DIO: UČITAVANJE LETAKA ---
st.subheader("1. Dodaj letak u bazu ➕")

naziv_ducana = st.text_input("Unesi naziv dućana (npr. Lidl, Konzum, Kaufland):")
uploaded_file = st.file_uploader("Učitaj sliku letka (JPG/PNG)", type=["jpg", "jpeg", "png"])

if st.button("Obradi letak pomoću AI 🧠"):
    if not naziv_ducana:
        st.error("Molimo te unesi naziv dućana prije obrade.")
    elif not uploaded_file:
        st.error("Molimo te učitaj sliku letka.")
    else:
        with st.spinner(f"Gemini AI analizira letak za {naziv_ducana}... Pričekaj trenutak."):
            try:
                # Otvaranje slike i priprema za Gemini
                image = Image.open(uploaded_file)
                
                # Uputa za AI (Prompt) - tražimo točan JSON format i kategorije
                prompt = f"""
                Pregledaj ovu sliku letka iz trgovine '{naziv_ducana}' i izvuci sve proizvode koji su na akciji, sniženju ili imaju posebnu ponudu.
                Razvrstaj ih u logičke kategorije kao što su: 'Mliječni proizvodi', 'Grickalice i slatkiši', 'Meso i riba', 'Voće i povrće', 'Pića', 'Pekara', 'Higijena i kućanstvo', 'Ostalo'.
                
                Vrati odgovor ISKLJUČIVO u ovom JSON formatu (nemoj pisati nikakav tekst prije ili poslije JSON-a, samo čisti JSON):
                {{
                  "Kategorija1": [
                     {{"proizvod": "Naziv artikla i gramaža", "cijena": "Cijena u €", "popust": "Postotak ili opis akcije"}}
                  ]
                }}
                Ako nema proizvoda za neku kategoriju, nemoj je uključivati.
                """
                
                # Pozivanje Gemini modela koji podržava analizu slika
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([prompt, image])
                
                # Čišćenje i parsiranje JSON odgovora od AI-ja
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                podaci_iz_letka = json.loads(clean_text)
                
                # Spremanje u lokalnu "bazu" u session_state
                brojac = 0
                for kategorija, proizvodi in podaci_iz_letka.items():
                    for p in proizvodi:
                        st.session_state.sve_akcije.append({
                            "Dućan": naziv_ducana.strip().capitalize(),
                            "Kategorija": kategorija,
                            "Proizvod": p.get("proizvod", "Nepoznato"),
                            "Cijena": p.get("cijena", "-"),
                            "Popust": p.get("popust", "-")
                        })
                        brojac += 1
                        
                st.success(f"Uspješno dodano {brojac} artikala iz trgovine {naziv_ducana}!")
                
            except Exception as e:
                st.error(f"Došlo je do pogreške prilikom obrade: {e}")
                st.info("Pokušaj ponovno ili provjeri je li slika čitljiva.")

# --- 2. DIO: FILTRIRANJE I PREGLED ---
if st.session_state.sve_akcije:
    st.markdown("---")
    st.subheader("2. Pretraži i usporedi akcije 🔎")
    
    # Izvlačenje opcija za filtere
    svi_ducani = sorted(list(set([p["Dućan"] for p in st.session_state.sve_akcije])))
    sve_kategorije = sorted(list(set([p["Kategorija"] for p in st.session_state.sve_akcije])))
    
    # Filtri prilagođeni ekranu mobitela (dva stupca)
    col1, col2 = st.columns(2)
    with col1:
        odabrani_ducan = st.selectbox("Trgovina:", ["Sve trgovine"] + svi_ducani)
    with col2:
        odabrana_kategorija = st.selectbox("Kategorija:", ["Sve kategorije"] + sve_kategorije)
        
    # Primjena filtera na podatke
    prikaz_podataka = st.session_state.sve_akcije
    if odabrani_ducan != "Sve trgovine":
        prikaz_podataka = [p for p in prikaz_podataka if p["Dućan"] == odabrani_ducan]
    if odabrana_kategorija != "Sve kategorije":
        prikaz_podataka = [p for p in prikaz_podataka if p["Kategorija"] == odabrana_kategorija]
        
    # Prikaz finalne tablice
    if prikaz_podataka:
        # Formatiramo tablicu za ljepši prikaz korisniku
        tablica_za_ekran = []
        for p in prikaz_podataka:
            tablica_za_ekran.append({
                "Dućan": p["Dućan"],
                "Kategorija": p["Kategorija"],
                "Proizvod": p["Proizvod"],
                "Cijena": p["Cijena"],
                "Popust": p["Popust"]
            })
        st.dataframe(tablica_za_ekran, use_container_width=True, hide_index=True)
        
        # Gumb za brisanje cijele liste ako želiš krenuti ispočetka
        if st.button("Očisti sve podatke 🗑️"):
            st.session_state.sve_akcije = []
            st.rerun()
    else:
        st.warning("Nema artikala za odabrane filtere.")