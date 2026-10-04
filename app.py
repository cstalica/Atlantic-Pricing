import datetime
import pandas as pd
import requests
import streamlit as st

# Streamlit Page Configuration
st.set_page_config(
    page_title="Atlantic Aviation Fee Scraper",
    page_icon="✈",
    layout="wide",
)

st.title("✈️ Atlantic Aviation Lear 75 Detailed Fee Scraper")
st.write(
    "Direct API scraper targeting Atlantic Aviation's backend endpoint for ABQ and TUL."
)

# Target Airports
AIRPORT_CODES = ["ABQ", "TUL"]

# Sidebar Parameters
st.sidebar.header("Scraper Parameters")
make_model_id = st.sidebar.text_input("Lear 75 Model ID", "971")
target_date = st.sidebar.date_input("Arrival Date", datetime.date.today())
date_str = target_date.strftime("%Y-%m-%d")

show_raw_json = st.sidebar.checkbox("Show Raw JSON Payload", value=False)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.atlanticaviation.com/locations/ABQ",
}


def parse_fee_payload(item):
    """Parses raw primitive values, lists, or dictionary objects into clean string outputs."""
    if item is None:
        return "N/A"

    if isinstance(item, str):
        val = " ".join(item.replace("\n", " ").split()).strip()
        return val if val else "N/A"

    if isinstance(item, (int, float)):
        return f"${item:,.0f}" if item == int(item) else f"${item:,.2f}"

    if isinstance(item, list):
        parsed = [parse_fee_payload(i) for i in item]
        valid = [p for p in parsed if p != "N/A"]
        return " ".join(valid) if valid else "N/A"

    if isinstance(item, dict):
        # 1. Look for direct message string keys
        msg = (
            item.get("hourlyHangarMessage")
            or item.get("hourlyParkingMessage")
            or item.get("dailyParkingMessage")
            or item.get("parkingMessage")
            or item.get("hangarMessage")
            or item.get("rateComment")
            or item.get("formattedRate")
            or item.get("text")
        )
        if msg:
            return parse_fee_payload(msg)

        # 2. Extract unitPrice / amount numerical keys
        unit_price = (
            item.get("unitPrice")
            if "unitPrice" in item
            else item.get("amount")
            if "amount" in item
            else item.get("price")
            if "price" in item
            else item.get("basePrice")
            if "basePrice" in item
            else item.get("rate")
            if "rate" in item
            else item.get("value")
        )

        comment = item.get("comment") or item.get("description") or ""
        comment_str = str(comment).strip()

        if unit_price is not None:
            formatted_price = (
                f"${unit_price:,.0f}"
                if isinstance(unit_price, (int, float))
                and unit_price == int(unit_price)
                else f"${unit_price:,.2f}"
                if isinstance(unit_price, (int, float))
                else str(unit_price).strip()
            )

            # Standardize output for simple unitPrice + standard label objects
            if comment_str and comment_str.lower() not in [
                "security fee",
                "facility fee",
                "hangar fee",
                "parking fee",
            ]:
                if formatted_price not in comment_str:
                    return parse_fee_payload(f"{formatted_price} {comment_str}")
                return parse_fee_payload(comment_str)

            return formatted_price

        if comment_str:
            return parse_fee_payload(comment_str)

        # Fallback dictionary key traversal
        collected = []
        for v in item.values():
            res = parse_fee_payload(v)
            if res != "N/A" and res not in collected:
                collected.append(res)
        return " ".join(collected) if collected else "N/A"

    return "N/A"


def extract_gallons_string(item):
    """Extracts gallons needed to waive facility fee without dollar formatting."""
    if isinstance(item, dict):
        gallons = (
            item.get("unitPrice")
            or item.get("amount")
            or item.get("value")
            or item.get("gallons")
        )
        if gallons is not None:
            return f"{int(gallons)}" if gallons == int(gallons) else f"{gallons}"
        return parse_fee_payload(item.get("comment"))
    elif isinstance(item, (int, float)):
        return f"{int(item)}" if item == int(item) else f"{item}"
    elif isinstance(item, str) and item.strip():
        return item.strip()
    return "N/A"


def fetch_airport_fees(code, model_id, date_val):
    api_url = "https://www.atlanticaviation.com/umbraco/api/FacilityLookup/Get"
    params = {
        "airportCode": code,
        "makeModelId": model_id,
        "arrivalDate": date_val,
    }

    try:
        response = requests.get(
            api_url, params=params, headers=HEADERS, timeout=10
        )
        if response.status_code == 200:
            data = response.json()

            if show_raw_json:
                st.subheader(f"Raw Response Payload for {code}:")
                st.json(data)

            return {
                "Airport Code": str(code),
                "Arrival Date": str(date_val),
                "Facility Fee": parse_fee_payload(
                    data.get("facilityFee") or data.get("facility")
                ),
                "Gallons to Waive": extract_gallons_string(
                    data.get("gallonsNeededToWaiveFacilityFee")
                    or data.get("gallonsToWaive")
                ),
                "Hangar": parse_fee_payload(
                    data.get("hourlyHangarMessage")
                    or data.get("hangarMessage")
                    or data.get("hangarFee")
                ),
                "Security Fee": parse_fee_payload(
                    data.get("securityFee") or data.get("security")
                ),
                "Regular Parking": parse_fee_payload(
                    data.get("hourlyParkingMessage")
                    or data.get("dailyParkingMessage")
                    or data.get("parkingMessage")
                    or data.get("parkingFee")
                ),
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


# Execution Loop
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
    df = pd.DataFrame(results).astype(str)
    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Rates CSV",
        data=csv_bytes,
        file_name=f"atlantic_lear75_rates_{target_date}.csv",
        mime="text/csv",
    )