import datetime
import pandas as pd
import requests
import streamlit as st

# Streamlit Page Config
st.set_page_config(
    page_title="Atlantic Aviation Fee Scraper", page_icon="✈", layout="wide"
)

st.title("✈️ Atlantic Aviation Lear 75 Detailed Fee Scraper")
st.write(
    "Direct API scraper targeting Atlantic Aviation's Umbraco backend endpoint for ABQ and TUL airports."
)

# Filtered list of airports (ABQ & TUL only)
AIRPORT_CODES = [
    "ABQ",
    "TUL",
]

# Sidebar Parameters
st.sidebar.header("Scraper Parameters")
make_model_id = st.sidebar.text_input("Lear 75 Model ID", "971")
target_date = st.sidebar.date_input("Arrival Date", datetime.date.today())
date_str = target_date.strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.atlanticaviation.com/locations/ABQ#tripplanning",
}


def extract_string_val(item):
    """Safely extracts and cleans string values from any JSON data type."""
    if item is None:
        return "N/A"

    if isinstance(item, str):
        val = item.strip()
        return val if val else "N/A"

    if isinstance(item, (int, float)):
        return f"${item:,.0f}" if item == int(item) else f"${item:,.2f}"

    if isinstance(item, list):
        parts = []
        for sub in item:
            res = extract_string_val(sub)
            if res != "N/A" and res not in parts:
                parts.append(res)
        return " ".join(parts) if parts else "N/A"

    if isinstance(item, dict):
        base_price = (
            item.get("unitPrice")
            or item.get("amount")
            or item.get("price")
            or item.get("basePrice")
            or item.get("rate")
        )

        comment = (
            item.get("rateComment")
            or item.get("comment")
            or item.get("description")
            or item.get("formattedRate")
            or item.get("value")
            or item.get("text")
            or ""
        )

        base_str = ""
        if base_price is not None and base_price != 0:
            base_str = (
                f"${base_price:,.0f}"
                if base_price == int(base_price)
                else f"${base_price:,.2f}"
            )

        comment_str = str(comment).strip()

        if base_str and comment_str:
            if base_str in comment_str:
                return comment_str
            return f"{base_str} {comment_str}".strip()
        elif base_str:
            return base_str
        elif comment_str:
            return comment_str

        # Fallback to recursively extract all values in dict if primary keys miss
        collected = []
        for v in item.values():
            extracted = extract_string_val(v)
            if extracted != "N/A" and extracted not in collected:
                collected.append(extracted)
        if collected:
            return " ".join(collected)

    return "N/A"


def extract_gallons_string(item):
    """Extracts required gallons as a clean string without dollar formatting."""
    if isinstance(item, dict):
        gallons = (
            item.get("unitPrice")
            or item.get("amount")
            or item.get("gallons")
            or item.get("value")
            or item.get("rate")
        )
        if gallons is not None:
            return f"{int(gallons)}" if gallons == int(gallons) else f"{gallons}"
        return extract_string_val(item.get("comment"))
    elif isinstance(item, (int, float)):
        return f"{int(item)}" if item == int(item) else f"{item}"
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
                    "Airport Code": str(code),
                    "Arrival Date": str(date_val),
                    "Facility Fee": "Not Available",
                    "Gallons to Waive": "N/A",
                    "Hangar": "N/A",
                    "Security Fee": "N/A",
                    "Regular Parking": "N/A",
                }

            # Inspect payload keys across all potential casing/naming conventions
            facility_raw = (
                data.get("facilityFee")
                or data.get("FacilityFee")
                or data.get("facility")
            )
            gallons_raw = (
                data.get("gallonsNeededToWaiveFacilityFee")
                or data.get("gallonsToWaive")
                or data.get("WaiveGallons")
                or data.get("gallonsNeeded")
            )

            # Expanded key lookups specifically for hangar payloads
            hangar_raw = (
                data.get("hangar")
                or data.get("hangarFee")
                or data.get("Hangar")
                or data.get("hangarRate")
                or data.get("hangarFacility")
                or data.get("hangarFees")
            )

            security_raw = (
                data.get("securityFee")
                or data.get("SecurityFee")
                or data.get("security")
            )
            parking_raw = (
                data.get("regularParking")
                or data.get("RegularParking")
                or data.get("parkingFee")
                or data.get("parking")
                or data.get("overnightParking")
            )

            return {
                "Airport Code": str(code),
                "Arrival Date": str(date_val),
                "Facility Fee": extract_string_val(facility_raw),
                "Gallons to Waive": extract_gallons_string(gallons_raw),
                "Hangar": extract_string_val(hangar_raw),
                "Security Fee": extract_string_val(security_raw),
                "Regular Parking": extract_string_val(parking_raw),
            }
        else:
            return {
                "Airport Code": str(code),
                "Arrival Date": str(date_val),
                "Facility Fee": f"HTTP {response.status_code}",
                "Gallons to Waive": "N/A",
                "Hangar": "N/A",
                "Security Fee": "N/A",
                "Regular Parking": "N/A",
            }

    except Exception as e:
        return {
            "Airport Code": str(code),
            "Arrival Date": str(date_val),
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

    # Explicitly cast entire DataFrame to string type to avoid Streamlit column inference issues
    df = pd.DataFrame(results).astype(str)

    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Rates CSV",
        data=csv_bytes,
        file_name=f"atlantic_lear75_rates_{target_date}.csv",
        mime="text/csv",
    )