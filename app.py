import streamlit as st
import google.generativeai as genai
import json
import requests
import io

# 1. Konfiguracija Gemini API-ja iz sigurnih postavki
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API ključ nije pronađen u postavkama aplikacije!")
    
# Postavke stranice optimizirane za mobitele
st.set_page_config(page_title="Multi-Dućan Letak", layout="centered")
st.title("🛍️ Pametni Čitač Letaka (PDF & Slike)")
st.caption("Učitaj sliku, PDF ili zalijepi link na PDF letak. AI će izvući i kategorizirati sve akcije!")

# Inicijalizacija baze podataka u memoriji aplikacije
if "sve_akcije" not in st.session_state:
    st.session_state.sve_akcije = []

# --- 1. DIO: UČITAVANJE LETAKA ---
st.subheader("1. Dodaj letak u bazu ➕")

naziv_ducana = st.text_input("Unesi naziv dućana (npr. Lidl, Konzum, Kaufland):")

# Odabir načina unosa na mobitelu
izvor_unosa = st.radio("Odaberi način unosa letka:", ["Upload datoteke (Slika ili PDF)", "Zalijepi link (URL do PDF-a)"])

bytes_data = None
mime_type = None

if izvor_unosa == "Upload datoteke (Slika ili PDF)":
    uploaded_file = st.file_uploader("Učitaj letak (JPG, PNG ili PDF)", type=["jpg", "jpeg", "png", "pdf"])
    if uploaded_file:
        bytes_data = uploaded_file.read()
        mime_type = uploaded_file.type
else:
    pdf_url = st.text_input("Zalijepi direktan link na PDF letak:")
    if pdf_url and st.button("Preuzmi letak s linka 🌐"):
        with st.spinner("Preuzimanje PDF-a s interneta..."):
            try:
                response = requests.get(pdf_url, timeout=30)
                if response.status_code == 200:
                    bytes_data = response.content
                    mime_type = "application/pdf"
                    st.session_state["cached_pdf"] = (bytes_data, mime_type)
                    st.success("PDF uspješno preuzet s linka! Sada upiši ime dućana i klikni gumb 'Obradi letak' ispod.")
                else:
                    st.error(f"Nije moguće preuzeti PDF. Server je vratio grešku {response.status_code}")
            except Exception as e:
                st.error(f"Greška pri dohvaćanju linka: {e}")

if izvor_unosa == "Zalijepi link (URL do PDF-a)" and "cached_pdf" in st.session_state:
    bytes_data, mime_type = st.session_state["cached_pdf"]

# Gumb za pokretanje AI analize
if st.button("Obradi letak pomoću AI 🧠"):
    if not naziv_ducana:
        st.error("Molimo te unesi naziv dućana prije obrade.")
    elif bytes_data is None:
        st.error("Molimo te učitaj datoteku ili uspješno preuzmi PDF preko linka.")
    else:
        with st.spinner(f"Gemini AI analizira letak za {naziv_ducana}... Pričekaj trenutak."):
            try:
                # Precizne upute za AI
                prompt = """
                Pregledaj ovaj letak i izvuci sve proizvode koji su na akciji, sniženju ili imaju posebnu ponudu.
                Pregledaj sve dostupne stranice.
                Razvrstaj ih u logičke kategorije kao što su: 'Mliječni proizvodi', 'Grickalice i slatkiši', 'Meso i riba', 'Voće i povrće', 'Pića', 'Pekara', 'Higijena i kućanstvo', 'Ostalo'.
                
                Vrati odgovor ISKLJUČIVO u ovom JSON formatu. Nemoj pisati nikakav popratni tekst, uvod ili zaključak, samo čisti JSON:
                {
                  "Kategorija": [
                     {"proizvod": "Naziv artikla", "cijena": "Cijena", "popust": "Popust"}
                  ]
                }
                """
                
                file_part = {
                    "data": bytes_data,
                    "mime_type": mime_type
                }
                
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([prompt, file_part])
                
                # PAMETNO ČIŠĆENJE ODGOVORA (Uklanja ```json i slične oznake ako ih AI doda)
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    # Ukloni početni ```json ili ```
                    lines = raw_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_text = "\n".join(lines).strip()
                
                podaci_iz_letka = json.loads(raw_text)
                
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
                if "cached_pdf" in st.session_state:
                    del st.session_state["cached_pdf"]
                
            except json.JSONDecodeError:
                st.error("AI je vratio podatke u čudnom formatu koji ne možemo pročitati.")
                st.info("Pokušaj ponovno kliknuti na gumb 'Obradi letak pomoću AI' – AI često iz drugog pokušaja popravi format.")
            except Exception as e:
                st.error(f"Došlo je do pogreške prilikom obrade: {e}")

# --- 2. DIO: FILTRIRANJE I PREGLED ---
if st.session_state.sve_akcije:
    st.markdown("---")
    st.subheader("2. Pretraži i usporedi akcije 🔎")
    
    svi_ducani = sorted(list(set([p["Dućan"] for p in st.session_state.sve_akcije])))
    sve_kategorije = sorted(list(set([p["Kategorija"] for p in st.session_state.sve_akcije])))
    
    col1, col2 = st.columns(2)
    with col1:
        odabrani_ducan = st.selectbox("Trgovina:", ["Sve trgovine"] + svi_ducani)
    with col2:
        odabrana_kategorija = st.selectbox("Kategorija:", ["Sve kategorije"] + sve_kategorije)
        
    prikaz_podataka = st.session_state.sve_akcije
    if odabrani_ducan != "Sve trgovine":
        prikaz_podataka = [p for p in prikaz_podataka if p["Dućan"] == odabrani_ducan]
    if odabrana_kategorija != "Sve kategorije":
        prikaz_podataka = [p for p in prikaz_podataka if p["Kategorija"] == odabrana_kategorija]
        
    if prikaz_podataka:
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
        
        if st.button("Očisti sve podatke 🗑️"):
            st.session_state.sve_akcije = []
            st.rerun()
    else:
        st.warning("Nema artikala za odabrane filtere.")
