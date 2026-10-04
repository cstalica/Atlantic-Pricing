import datetime
import pandas as pd
import requests
import streamlit as st

# Configure Streamlit Page
st.set_page_config(
    page_title="Atlantic Aviation Rates Scraper", page_icon="✈️", layout="wide"
)

st.title("✈️ Atlantic Aviation Lear 75 Fee Scraper")
st.write(
    "Direct API scraper targeting Atlantic Aviation's Umbraco backend endpoint for Lear 75 pricing."
)

# Complete list of 107 Atlantic Aviation airport codes
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
st.sidebar.header("Parameters")
make_model_id = st.sidebar.text_input("Lear 75 Model ID", "971")
target_date = st.sidebar.date_input("Arrival Date", datetime.date.today())
date_str = target_date.strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.atlanticaviation.com/locations/",
}


def extract_price_value(item):
    """Safely extracts unitPrice, amount, price, or text comments from returned JSON objects."""
    if isinstance(item, dict):
        price = item.get("unitPrice") or item.get("amount") or item.get("price")
        comment = item.get("comment", "")
        if price is not None:
            return f"${price:,.0f}" if price == int(price) else f"${price:,.2f}"
        return comment if comment else "N/A"
    elif isinstance(item, (int, float)):
        return f"${item:,.0f}" if item == int(item) else f"${item:,.2f}"
    elif isinstance(item, str) and item.strip():
        return item.strip()
    return "N/A"


def fetch_airport_fees(code, model_id, date_val):
    api_url = "https://www.atlanticaviation.com/umbraco/api/FacilityLookup/Get"
    params = {
        "aiportCode": code,
        "makeModelid": model_id,
        "arrivalDate": date_val,
    }

    try:
        response = requests.get(
            api_url, params=params, headers=HEADERS, timeout=10
        )

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                return {
                    "Airport Code": code,
                    "Arrival Date": date_val,
                    "Facility Fee": "Not Available",
                    "Gallons to Waive": "N/A",
                    "Hangar": "N/A",
                    "Security Fee": "N/A",
                    "Regular Parking": "N/A",
                }

            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            if not isinstance(data, dict):
                return {
                    "Airport Code": code,
                    "Arrival Date": date_val,
                    "Facility Fee": "Not Available",
                    "Gallons to Waive": "N/A",
                    "Hangar": "N/A",
                    "Security Fee": "N/A",
                    "Regular Parking": "N/A",
                }

            # Parse individual fee attributes
            facility_fee = extract_price_value(
                data.get("facilityFee") or data.get("FacilityFee")
            )

            gallons = (
                data.get("gallonsNeededToWaiveFacilityFee")
                or data.get("gallonsToWaive")
                or data.get("WaiveGallons")
            )
            gallons_str = f"{gallons}" if gallons is not None else "N/A"

            hangar_fee = extract_price_value(
                data.get("hangar") or data.get("Hangar")
            )
            security_fee = extract_price_value(
                data.get("securityFee") or data.get("SecurityFee")
            )
            parking_fee = extract_price_value(
                data.get("regularParking") or data.get("RegularParking")
            )

            return {
                "Airport Code": code,
                "Arrival Date": date_val,
                "Facility Fee": facility_fee,
                "Gallons to Waive": gallons_str,
                "Hangar": hangar_fee,
                "Security Fee": security_fee,
                "Regular Parking": parking_fee,
            }
        else:
            return {
                "Airport Code": code,
                "Arrival Date": date_val,
                "Facility Fee": f"HTTP {response.status_code}",
                "Gallons to Waive": "N/A",
                "Hangar": "N/A",
                "Security Fee": "N/A",
                "Regular Parking": "N/A",
            }

    except Exception as e:
        return {
            "Airport Code": code,
            "Arrival Date": date_val,
            "Facility Fee": f"Error: {str(e)}",
            "Gallons to Waive": "N/A",
            "Hangar": "N/A",
            "Security Fee": "N/A",
            "Regular Parking": "N/A",
        }


if st.button("🚀 Fetch Fee Data"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(AIRPORT_CODES)
    for idx, code in enumerate(AIRPORT_CODES):
        status_text.text(f"Fetching {code} ({idx + 1}/{total})...")
        fee_data = fetch_airport_fees(code, make_model_id, date_str)
        results.append(fee_data)
        progress_bar.progress((idx + 1) / total)

    status_text.success("Scraping completed!")
    df = pd.DataFrame(results)

    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Rates CSV",
        data=csv_bytes,
        file_name=f"atlantic_lear75_rates_{target_date}.csv",
        mime="text/csv",
    )