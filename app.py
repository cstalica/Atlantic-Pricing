import datetime
import re
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# Streamlit Page Config
st.set_page_config(
    page_title="Atlantic Aviation Fee Scraper", page_icon="✈️", layout="wide"
)

st.title("✈️ Atlantic Aviation Lear 75 Detailed Fee Scraper")
st.write(
    "Extracts Facility Fee, Waive Gallons, Hangar, Security Fee, and Regular Parking for each airport."
)

AIRPORT_CODES = [
    "ABQ",
    "ADS",
    "AGC",
    "ANC",
    "ANE",
    "APC",
    "ASE",
    "AUS",
    "BAF",
    "BCT",
    "BDA",
    "BDL",
    "BDR",
    "BED",
    "BFL",
    "BHM",
    "BNA",
    "BUR",
    "CHS",
    "CLE",
    "CPR",
    "CRP",
    "DAL",
    "DJT",
    "DTS",
    "ELM",
    "ELP",
    "EUG",
    "FAI",
    "FAT",
    "FMN",
    "FRG",
    "FXE",
    "GCM",
    "GPI",
    "HDN",
    "HNL",
    "HOU",
    "HPNE",
    "HPNW",
    "HYA",
    "IAD",
    "IAH",
    "ILG",
    "ITO",
    "JAN",
    "JZI",
    "KOA",
    "LAS",
    "LAX",
    "LGB",
    "LIH",
    "LIT",
    "LNK",
    "LNY",
    "MCO",
    "MDW",
    "MKC",
    "MMU",
    "MSY",
    "MTJ",
    "OGG",
    "OKC",
    "OMA",
    "OPF",
    "ORH",
    "ORL",
    "OXC",
    "PDK",
    "PDX",
    "PHF",
    "PHL",
    "PIT",
    "PLS",
    "PNE",
    "PSP",
    "PVD",
    "PWA",
    "PWK",
    "RDU",
    "RIL",
    "RNO",
    "SAF",
    "SBA",
    "SBN",
    "SCK",
    "SDF",
    "SDL",
    "SGJ",
    "SJC",
    "SKF",
    "SLC",
    "SMO",
    "SRQ",
    "SUA",
    "SUN",
    "SWF",
    "SXM",
    "TEB",
    "TRM",
    "TUL",
    "TUS",
    "UAO",
    "UES",
    "6N5",
]

# Sidebar Parameters
st.sidebar.header("Scraper Parameters")
aircraft_model = st.sidebar.text_input("Aircraft Make & Model", "Lear 75")
target_date = st.sidebar.date_input("Arrival Date", datetime.date.today())
date_str = target_date.strftime("%m/%d/%Y")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def parse_fee(soup, title):
    """Finds a fee header by text and extracts the corresponding value below it."""
    try:
        # Locate header matching fee name
        header = soup.find(
            lambda tag: tag.name in ["h3", "h4", "div", "strong", "b", "p"]
            and title.lower() in tag.text.strip().lower()
        )
        if header:
            # Extract text from the adjacent or parent elements
            sibling = header.find_next_sibling()
            if sibling:
                return sibling.text.strip()
            parent = header.parent
            text = parent.text.replace(header.text, "").strip()
            return text if text else "N/A"
    except Exception:
        pass
    return "N/A"


def fetch_airport_fees(code, aircraft, date_val):
    url = f"https://www.atlanticaviation.com/locations/{code}#tripplanning"
    params = {"aircraft": aircraft, "date": date_val}

    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")

            return {
                "Airport Code": code,
                "Aircraft": aircraft,
                "Arrival Date": date_val,
                "Facility Fee": parse_fee(soup, "Facility Fee"),
                "Gallons to Waive": parse_fee(
                    soup, "Gallons Needed to Waive"
                ),
                "Hangar": parse_fee(soup, "Hangar"),
                "Security Fee": parse_fee(soup, "Security Fee"),
                "Regular Parking": parse_fee(soup, "Regular Parking"),
                "URL": url,
            }
        else:
            return {
                "Airport Code": code,
                "Aircraft": aircraft,
                "Arrival Date": date_val,
                "Facility Fee": f"HTTP {res.status_code}",
                "Gallons to Waive": "N/A",
                "Hangar": "N/A",
                "Security Fee": "N/A",
                "Regular Parking": "N/A",
                "URL": url,
            }
    except Exception as e:
        return {
            "Airport Code": code,
            "Aircraft": aircraft,
            "Arrival Date": date_val,
            "Facility Fee": f"Error: {str(e)}",
            "Gallons to Waive": "N/A",
            "Hangar": "N/A",
            "Security Fee": "N/A",
            "Regular Parking": "N/A",
            "URL": url,
        }


if st.button("🚀 Fetch Fee Data"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(AIRPORT_CODES)
    for idx, code in enumerate(AIRPORT_CODES):
        status_text.text(
            f"Fetching {code} ({idx + 1}/{total}) for {aircraft_model}..."
        )
        data = fetch_airport_fees(code, aircraft_model, date_str)
        results.append(data)
        progress_bar.progress((idx + 1) / total)

    status_text.success("Complete!")
    df = pd.DataFrame(results)

    # Display dataset
    st.dataframe(df, use_container_width=True)

    # Download CSV
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Detailed CSV",
        data=csv_bytes,
        file_name=f"atlantic_aviation_fees_{aircraft_model.replace(' ', '_')}_{target_date}.csv",
        mime="text/csv",
    )