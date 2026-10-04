import datetime
import streamlit as st

# 1. Capture the date input from Streamlit
target_date = st.sidebar.date_input("Arrival Date", datetime.date.today())

# 2. Format as MM/DD/YY (e.g., 10/04/26) using lowercase %y for 2-digit year
date_str = target_date.strftime("%m/%d/%y")

# 3. Pass in the params dictionary for requests
params = {
    "airportCode": "ABQ",
    "makeModelId": "996",
    "arrivalDate": date_str,  # e.g., '10/04/26'
}