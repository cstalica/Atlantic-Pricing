import datetime
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# Configure Streamlit Page
st.set_page_config(
    page_title="Atlantic Aviation Pricing Scraper",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ Atlantic Aviation Lear 75 Rate Scraper")
st.write(
    "Automated tool to fetch trip planning rates for a Lear 75 across all Atlantic Aviation FBO locations."
)

# List of Atlantic Aviation ICAO / IATA location codes
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

# Sidebar inputs
st.sidebar.header("Scraper Parameters")
aircraft_model = st.sidebar.text_input("Aircraft Make & Model", "Lear 75")
target_date = st.sidebar.date_input("Arrival Date", datetime.date.today())

date_str = target_date.strftime("%m/%d/%Y")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_location_pricing(code, aircraft, date_val):
    """Query individual Atlantic Aviation location page for pricing data."""
    url = f"https://www.atlanticaviation.com/locations/{code}#tripplanning"
    params = {"aircraft": aircraft, "date": date_val}

    try:
        response = requests.get(
            url, headers=HEADERS, params=params, timeout=10
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract pricing elements if dynamically rendered server-side
            price_elem = soup.find("div", class_="pricing-details") or soup.find(
                "span", class_="rate"
            )
            rate = price_elem.text.strip() if price_elem else "N/A"

            return {
                "Airport Code": code,
                "Aircraft": aircraft,
                "Arrival Date": date_val,
                "Rate / Status": rate,
                "URL": url,
            }
        else:
            return {
                "Airport Code": code,
                "Aircraft": aircraft,
                "Arrival Date": date_val,
                "Rate / Status": f"HTTP {response.status_code}",
                "URL": url,
            }
    except Exception as e:
        return {
            "Airport Code": code,
            "Aircraft": aircraft,
            "Arrival Date": date_val,
            "Rate / Status": f"Error: {str(e)}",
            "URL": url,
        }


if st.button("🚀 Fetch Pricing Data"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_airports = len(AIRPORT_CODES)

    for idx, code in enumerate(AIRPORT_CODES):
        status_text.text(
            f"Fetching {code} ({idx + 1}/{total_airports}) for {aircraft_model}..."
        )
        data = fetch_location_pricing(code, aircraft_model, date_str)
        results.append(data)
        progress_bar.progress((idx + 1) / total_airports)

    status_text.success("Scraping completed!")

    df = pd.DataFrame(results)

    # Display results table
    st.dataframe(df, use_container_width=True)

    # Download CSV button
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv_data,
        file_name=f"atlantic_aviation_{aircraft_model.replace(' ', '_')}_{target_date}.csv",
        mime="text/csv",
    )