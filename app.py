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


def extract_price_value(item):
    """Formats numeric dollar amounts safely from dicts, floats, ints, or strings."""
    if isinstance(item, dict):
        price = (
            item.get("unitPrice")
            or item.get("amount")
            or item.get("price")
            or item.get("rate")
        )
        comment = item.get("comment") or item.get("rateComment") or ""
        if price is not None and price != 0:
            formatted_price = (
                f"${price:,.0f}" if price == int(price) else f"${price:,.2f}"
            )
            return (
                f"{formatted_price} {comment}".strip()
                if comment
                else formatted_price
            )
        return comment if comment else "N/A"
    elif isinstance(item, (int, float)):
        return f"${item:,.0f}" if item == int(item) else f"${item:,.2f}"
    elif isinstance(item, str) and item.strip():
        return item.strip()
    return "N/A"


def extract_gallons_value(item):
    """Extracts raw numeric gallon requirements without dollar signs."""
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
        return item.get("comment", "N/A")
    elif isinstance(item, (int, float)):
        return f"{int(item)}" if item == int(item) else f"{item}"
    elif isinstance(item, str) and item.strip():
        return item.strip()
    return "N/A"


def extract_composite_fee(item):
    """
    Extracts base dollar amounts ($377) and combines them with hourly rate comments ('plus $31/hr')
    from any dictionary or list structure returned by Atlantic's API.
    """
    if not item:
        return "N/A"

    if isinstance(item, list):
        parts = []
        for sub in item:
            val = extract_composite_fee(sub)
            if val != "N/A":
                parts.append(val)
        return " ".join(parts) if parts else "N/A"

    if isinstance(item, dict):
        # 1. Look for base numeric price across common Atlantic keys
        base_price = (
            item.get("unitPrice")
            or item.get("amount")
            or item.get("price")
            or item.get("basePrice")
            or item.get("rate")
        )

        # 2. Look for rate text/comment
        comment = (
            item.get("rateComment")
            or item.get("comment")
            or item.get("description")
            or item.get("formattedRate")
            or item.get("value")
            or item.get("label")
            or ""
        )

        base_str = ""
        if base_price is not None and base_price != 0:
            base_str = (
                f"${base_price:,.0f}"
                if base_price == int(base_price)
                else f"${base_price:,.2f}"
            )

        if base_str and comment:
            if base_str in str(comment):
                return str(comment).strip()
            return f"{base_str} {comment}".strip()
        elif base_str:
            return base_str
        elif comment:
            return str(comment).strip()

        return "N/A"

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

            # Direct dictionary lookups covering all possible payload key variations
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
            hangar_raw = (
                data.get("hangar")
                or data.get("hangarFee")
                or data.get("Hangar")
                or data.get("hangarRate")
                or data.get("hangarFacility")
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
                "Airport Code": code,
                "Arrival Date": date_val,
                "Facility Fee": extract_price_value(facility_raw),
                "Gallons to Waive": extract_gallons_value(gallons_raw),
                "Hangar": extract_composite_fee(hangar_raw),
                "Security Fee": extract_price_value(security_raw),
                "Regular Parking": extract_composite_fee(parking_raw),
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