import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re
from dateutil.parser import parse  # Add to requirements.txt: python-dateutil

# Add background image and text color fix via CSS
st.markdown("""
    <style>
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1920&q=80");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        font-size: 16px;  /* Increase global font size for better readability */
    }
    .stApp > header {  /* Semi-transparent header */
        background-color: rgba(255, 255, 255, 0.7);
    }
    /* Make text dark for readability */
    .stMarkdown, .stText, .stWarning, .stSubheader, .stTitle, p, div {
        color: #333333 !important;  /* Dark gray */
    }
    a { color: #0066cc !important; }  /* Links blue for visibility */
    /* Specific button styling: Bold black text for readability */
    .stButton > button {
        color: #000000 !important;  /* Black text */
        font-weight: bold !important;  /* Bolder for emphasis */
        font-size: 18px !important;  /* Slightly larger button text */
    }
    </style>
""", unsafe_allow_html=True)

# Helper for transport with enhanced fallback and clearer formatting
def search_transport(start, dest, date_start, date_end):
    try:
        # Primary: Rome2Rio
        url = f"https://www.rome2rio.com/search/{start}/{dest}?departureDate={date_start}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        options = []
        for item in soup.select('.route__details, .itinerary-item'):
            mode = item.select_one('.route__title, .mode').text.strip() if item.select_one('.route__title, .mode') else "Unknown"
            price = item.select_one('.route__price, .price').text.strip() if item.select_one('.route__price, .price') else "N/A"
            link = item.select_one('a')['href'] if item.select_one('a') else "/"
            options.append({"mode": mode, "price": price, "link": f"https://www.rome2rio.com{link}"})
        
        if len(options) < 2:  # Fallback with indirect via Bangkok and parsed details
            google_query = f"best transport from {start} to {dest} Thailand {date_start} prices"
            google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
            response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.select('.tF2Cxc')
