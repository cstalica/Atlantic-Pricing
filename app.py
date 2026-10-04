import datetime
import pandas as pd
import requests
import streamlit as st

# Streamlit Page Configuration
st.set_page_config(
    page_title="Atlantic Aviation Fee Scraper",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Atlantic Aviation Lear 75 Detailed Fee Scraper")
st.write(
    "Direct API scraper targeting Atlantic Aviation's Umbraco backend endpoint for ABQ and TUL airports."
)

# Target Airports
AIRPORT_CODES = ["ABQ", "TUL"]

# Sidebar Parameters
st.sidebar.header("Scraper Parameters")
make_model_id = st.sidebar.text_input("Lear 75 Model ID", "971")
target_date = st.sidebar.date_input("Arrival Date", datetime.date.today())
date_str = target_date.strftime("%Y-%m-%d")

show_raw_json = st.sidebar.checkbox("Show Raw JSON Payload for Debugging", value=False)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.atlanticaviation.com/locations/ABQ",
}


def parse_fee_payload(item):
    """
    Recursively parses primitives, dicts, or lists from Atlantic's payload.
    Combines base numeric prices ($377) with rate comments ('plus $31/hr').
    """
    if item is None:
        return "N/A"

    if isinstance(item, str):
        val = item.strip()
        return val if val else "N/A"

    if isinstance(item, (int, float)):
        return f"${item:,.0f}" if item == int(item) else f"${item:,.2f}"

    if isinstance(item, list):
        parsed_items = [parse_fee_payload(sub) for sub in item]
        valid_items = [p for p in parsed_items if p != "N/A"]
        return " ".join(valid_items) if valid_items else "N/A"

    if isinstance(item, dict):
        base_price = (
            item.get("unitPrice")
            or item.get("amount")
            or item.get("price")
            or item.get("basePrice")
            or item.get("rate")
            or item.get("value")
        )

        comment = (
            item.get("rateComment")
            or item.get("comment")
            or item.get("description")
            or item.get("formattedRate")
            or item.get("text")
            or ""
        )

        base_str = ""
        if isinstance(base_price, (int, float)) and base_price != 0:
            base_str = f"${base_price:,.0f}" if base_price == int(base_price) else f"${base_price:,.2f}"
        elif isinstance(base_price, str) and base_price.strip():
            base_str = base_price.strip()

        comment_str = str(comment).strip()

        if base_str and comment_str:
            if base_str in comment_str:
                return comment_str
            return f"{base_str} {comment_str}".strip()
        elif base_str:
            return base_str
        elif comment_str:
            return comment_str

        # Fallback recursive extraction across all dict values if specific keys are missing
        collected = []
        for v in item.values():
            extracted = parse_fee_payload(v)
            if extracted != "N/A" and extracted not in collected:
                collected.append(extracted)
        if collected:
            return " ".join(collected)

    return "N/A"


def extract_gallons_string(item):
    """Extracts gallons required without adding currency formatting ($)."""
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
        return parse_fee_payload(item.get("comment"))
    elif isinstance(item, (int, float)):
        return f"{int(item)}" if item == int(item) else f"{item}"
    elif isinstance(item, str) and item.strip():
        return item.strip()
    return "N/A"


def find_key_recursive(data, target_substrings):
    """
    Traverses the JSON structure recursively to find any key containing target keywords
    (e.g., 'hangar', 'facility', 'parking', 'security').
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if any(sub.lower() in key.lower() for sub in target_substrings):
                res = parse_fee_payload(value)
                if res != "N/A":
                    return res
            res = find_key_recursive(value, target_substrings)
            if res != "N/A":
                return res
    elif isinstance(data, list):
        for item in data:
            res = find_key_recursive(item, target_substrings)
            if res != "N/A":
                return res
    return "N/A"


def fetch_airport_fees(code, model_id, date_val):
    api_url = "https://www.atlanticaviation.com/umbraco/api/FacilityLookup/Get"
    
    # Try both standard parameter variants in case of API parameter naming updates
    params = {
        "airportCode": code,
        "aiportCode": code,
        "makeModelId": model_id,
        "makeModelid": model_id,
        "arrivalDate": date_val,
    }

    try:
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                return {
                    "Airport Code": str(code),
                    "Arrival Date": str(date_val),
                    "Facility Fee": "JSON Parsing Error",
                    "Gallons to Waive": "N/A",
                    "Hangar": "N/A",
                    "Security Fee": "N/A",
                    "Regular Parking": "N/A",
                }

            if show_raw_json:
                st.subheader(f"Raw Response Payload for {code}:")
                st.json(data)

            # Direct extraction with fallback key matching
            facility_raw = data.get("facilityFee") or data.get("FacilityFee") or data.get("facility")
            gallons_raw = data.get("gallonsNeededToWaiveFacilityFee") or data.get("gallonsToWaive") or data.get("WaiveGallons")
            hangar_raw = data.get("hangarFee") or data.get("hangarFees") or data.get("hangar") or data.get("Hangar")
            security_raw = data.get("securityFee") or data.get("SecurityFee") or data.get("security")
            parking_raw = data.get("regularParking") or data.get("RegularParking") or data.get("parkingFee") or data.get("parking")

            # Parse extracted values
            facility_res = parse_fee_payload(facility_raw)
            gallons_res = extract_gallons_string(gallons_raw)
            hangar_res = parse_fee_payload(hangar_raw)
            security_res = parse_fee_payload(security_raw)
            parking_res = parse_fee_payload(parking_raw)

            # Recursive search fallback if direct key access returned N/A
            if hangar_res == "N/A":
                hangar_res = find_key_recursive(data, ["hangar"])
            if facility_res == "N/A":
                facility_res = find_key_recursive(data, ["facility"])
            if security_res == "N/A":
                security_res = find_key_recursive(data, ["security"])
            if parking_res == "N/A":
                parking_res = find_key_recursive(data, ["parking", "overnight"])

            return {
                "Airport Code": str(code),
                "Arrival Date": str(date_val),
                "Facility Fee": str(facility_res),
                "Gallons to Waive": str(gallons_res),
                "Hangar": str(hangar_res),
                "Security Fee": str(security_res),
                "Regular Parking": str(parking_res),
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


# Streamlit UI Execution
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

    # Cast to string explicitly to prevent Streamlit schema/formatting mismatch
    df = pd.DataFrame(results).astype(str)

    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Rates CSV",
        data=csv_bytes,
        file_name=f"atlantic_lear75_rates_{target_date}.csv",
        mime="text/csv",
    )