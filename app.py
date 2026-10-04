import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Atlantic Aviation Rates Scraper", page_icon="✈️", layout="wide"
)

st.title("✈️ Atlantic Aviation Lear 75 Direct API Scraper")

# Complete list of Atlantic Aviation airport codes
AIRPORT_CODES = [
    "CRP",
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
    "Referer": "https://www.atlanticaviation.com/",
}


def fetch_airport_fees(code, model_id, date_val):
    api_url = "https://www.atlanticaviation.com/umbraco/api/FacilityLookup/Get"
    params = {
        "aiportCode": code,  # Note the spelling in Atlantic's endpoint parameter name
        "makeModelid": model_id,
        "arrivalDate": date_val,
    }

    try:
        response = requests.get(
            api_url, params=params, headers=HEADERS, timeout=10
        )
        if response.status_code == 200:
            data = response.json()

            # Map the returned JSON keys safely (handles missing fields gracefully)
            return {
                "Airport Code": code,
                "Arrival Date": date_val,
                "Facility Fee": data.get("facilityFee")
                or data.get("FacilityFee")
                or "N/A",
                "Gallons to Waive": data.get("gallonsNeededToWaiveFacilityFee")
                or data.get("WaiveGallons")
                or "N/A",
                "Hangar": data.get("hangar") or data.get("Hangar") or "N/A",
                "Security Fee": data.get("securityFee")
                or data.get("SecurityFee")
                or "N/A",
                "Regular Parking": data.get("regularParking")
                or data.get("RegularParking")
                or "N/A",
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

    status_text.success("Complete!")
    df = pd.DataFrame(results)

    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Rates CSV",
        data=csv_bytes,
        file_name=f"atlantic_lear75_rates_{target_date}.csv",
        mime="text/csv",
    )