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
        price = item.get("unitPrice") or item.get("amount") or item.get("price")
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
        )
        if gallons is not None:
            return f"{int(gallons)}" if gallons == int(gallons) else f"{gallons}"
        return item.get("comment", "N/A")
    elif isinstance(item, (int, float)):
        return f"{int(item)}" if item == int(item) else f"{item}"
    elif isinstance(item, str) and item.strip():
        return item.strip()
    return "N/A"


def extract_hangar_value(item):
    """Explicitly combines the base unitPrice ($377) and comment ('plus $31/hr') for Hangar fees."""
    if isinstance(item, dict):
        base_price = (
            item.get("unitPrice")
            or item.get("basePrice")
            or item.get("amount")
            or item.get("price")
        )
        comment = (
            item.get("rateComment")
            or item.get("comment")
            or item.get("description")
            or item.get("formattedRate")
            or item.get("value")
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
            # Avoid repeating the base price if the comment string already starts with or contains it
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


def extract_text_value(item):
    """Extracts base price and combines it with comments for parking or general text fields."""
    if isinstance(item, dict):
        price = item.get("unitPrice") or item.get("amount") or item.get("price")
        comment = (
            item.get("comment")
            or item.get("rateComment")
            or item.get("description")
            or item.get("formattedRate")
            or item.get("value")
            or item.get("label")
            or ""
        )

        base_str = ""
        if price is not None and price != 0:
            base_str = (
                f"${price:,.0f}" if price == int(price) else f"${price:,.2f}"
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


def find_in_data(data, keywords):
    """Recursively traverses the JSON data tree to locate fields matching key terms."""
    if isinstance(data, dict):
        # 1. Direct key match
        for key, val in data.items():
            if any(kw.lower() in key.lower() for kw in keywords):
                if val is not None:
                    return val

        # 2. Check label/name/comment/type fields inside a dictionary object
        comment = (
            data.get("comment")
            or data.get("rateComment")
            or data.get("name")
            or data.get("label")
            or data.get("title")
            or data.get("type")
            or ""
        )
        if any(kw.lower() in str(comment).lower() for kw in keywords):
            return data

        # 3. Recurse nested values
        for val in data.values():
            res = find_in_data(val, keywords)
            if res is not None:
                return res

    elif isinstance(data, list):
        for item in data:
            res = find_in_data(item, keywords)
            if res is not None:
                return res

    return None


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

            # 1. Facility Fee
            raw_facility = find_in_data(
                data, ["facilityFee", "facility fee", "facility"]
            )
            facility_fee = extract_price_value(raw_facility)

            # 2. Gallons Needed to Waive
            raw_gallons = find_in_data(
                data,
                [
                    "gallonsNeededToWaiveFacilityFee",
                    "gallonsNeeded",
                    "gallonsToWaive",
                    "gallons",
                    "waive",
                ],
            )
            gallons_str = extract_gallons_value(raw_gallons)

            # 3. Hangar Fee
            raw_hangar = find_in_data(
                data, ["hangarFee", "hangarRate", "hangar"]
            )
            hangar_fee = extract_hangar_value(raw_hangar)

            # 4. Security Fee
            raw_security = find_in_data(
                data, ["securityFee", "security fee", "security"]
            )
            security_fee = extract_price_value(raw_security)

            # 5. Regular Parking
            raw_parking = find_in_data(
                data,
                [
                    "regularParking",
                    "parkingFee",
                    "parking",
                    "overnightParking",
                    "overnight",
                ],
            )
            parking_fee = extract_text_value(raw_parking)

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