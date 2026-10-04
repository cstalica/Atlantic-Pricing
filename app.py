import datetime
import pandas as pd
import streamlit as st
from playwright.sync_api import sync_playwright

st.set_page_config(
    page_title="Atlantic Aviation Fee Scraper", page_icon="✈️", layout="wide"
)
st.title("✈️ Atlantic Aviation Lear 75 Fee Scraper")

AIRPORT_CODES = ["CRP"]

aircraft_model = st.sidebar.text_input("Aircraft Make & Model", "Lear 75")
target_date = st.sidebar.date_input("Arrival Date", datetime.date.today())
date_str = target_date.strftime("%m/%d/%Y")

def fetch_with_browser(code, aircraft, date_val):
    url = f"https://www.atlanticaviation.com/locations/{code}#tripplanning"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        
        # Interact with the dropdown inputs if necessary
        try:
            page.fill("input[placeholder*='aircraft']", aircraft)
            page.keyboard.press("Enter")
            page.fill("input[type='date']", date_val)
            page.wait_for_timeout(2000) # Wait for JS rendering
        except Exception:
            pass

        # Extract values after JS renders
        facility_fee = page.inner_text("h3:has-text('Facility Fee') + p") if page.query_selector("h3:has-text('Facility Fee')") else "N/A"
        waive_gallons = page.inner_text("h3:has-text('Gallons Needed') + p") if page.query_selector("h3:has-text('Gallons Needed')") else "N/A"
        hangar = page.inner_text("h3:has-text('Hangar') + p") if page.query_selector("h3:has-text('Hangar')") else "N/A"
        security_fee = page.inner_text("h3:has-text('Security Fee') + p") if page.query_selector("h3:has-text('Security Fee')") else "N/A"
        parking = page.inner_text("h3:has-text('Regular Parking') + p") if page.query_selector("h3:has-text('Regular Parking')") else "N/A"

        browser.close()
        
        return {
            "Airport Code": code,
            "Aircraft": aircraft,
            "Arrival Date": date_val,
            "Facility Fee": facility_fee,
            "Gallons to Waive": waive_gallons,
            "Hangar": hangar,
            "Security Fee": security_fee,
            "Regular Parking": parking,
            "URL": url
        }

if st.button("🚀 Fetch Fee Data"):
    results = []
    progress_bar = st.progress(0)
    for idx, code in enumerate(AIRPORT_CODES):
        data = fetch_with_browser(code, aircraft_model, date_str)
        results.append(data)
        progress_bar.progress((idx + 1) / len(AIRPORT_CODES))
        
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)