import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re
from dateutil.parser import parse  # Add this to requirements.txt: dateutil

# Helper function to search web for transport (flights/trains) with fallback
def search_transport(start, dest, date_start, date_end):
    try:
        # Primary: Rome2Rio
        url = f"https://www.rome2rio.com/search/{start}/{dest}?departureDate={date_start}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        options = []
        for item in soup.select('.route__details'):  # Updated selector for robustness
            mode = item.select_one('.route__title').text if item.select_one('.route__title') else "Unknown"
            price = item.select_one('.route__price').text if item.select_one('.route__price') else "N/A"
            link = item.select_one('a')['href'] if item.select_one('a') else "/"
            options.append({"mode": mode, "price": price, "link": f"https://www.rome2rio.com{link}"})
        
        if not options:  # Fallback to simple Google search if nothing found
            google_url = f"https://www.google.com/search?q=best+transport+from+{start}+to+{dest}+{date_start}+price"
            response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.select('.g'):  # Grab top results
                title = result.select_one('h3').text if result.select_one('h3') else "N/A"
                link = result.select_one('a')['href'] if result.select_one('a') else "https://www.google.com"
                options.append({"mode": title, "price": "Check site", "link": link})
        
        # Sort by price (heuristic)
        options.sort(key=lambda x: float(re.sub(r'[^\d.]', '', x['price'])) if x['price'] != "N/A" and x['price'] != "Check site" else float('inf'))
        return options[:3]  # Top 3
    except Exception as e:
        return [{"mode": "Error", "price": str(e), "link": ""}]

# Similar updates for hotels and attractions (I kept them similar but added try-except)

# ... (Rest of the helpers for hotels and attractions, update similarly with try-except and better selectors)

# Streamlit app with UI improvements
st.set_page_config(page_title="Epic Travel Planner", page_icon="✈️")  # Make it more captivating
st.title("Epic Travel Planner 🌍")
st.markdown("Plan your dream trip with real-time deals and itineraries! Powered by web magic.")

col1, col2 = st.columns(2)
with col1:
    start = st.text_input("Starting Location (e.g., Pattaya)", "Pattaya")
with col2:
    dest = st.text_input("Destination (e.g., Phayao)", "Phayao")

st.subheader("Pick Your Dates 📅")
date_start = st.date_input("Start Date", value=datetime.date.today() + datetime.timedelta(days=7))
date_end = st.date_input("End Date", value=date_start + datetime.timedelta(days=7))
date_range = f"{date_start} to {date_end}"  # For display

if st.button("Plan My Trip! 🚀", help="Let's go!"):
    if start and dest:
        st.write(f"Planning your adventure from {start} to {dest} for {date_range}...")
        
        # Transport
        st.subheader("Best Transport Options (Quality/Price) 🚌✈️")
        transports = search_transport(start, dest, str(date_start), str(date_end))
        if transports and transports[0]['mode'] != "Error":
            for t in transports:
                st.markdown(f"- **{t['mode']}** for {t['price']}: [Book here]({t['link']})")
        else:
            st.warning("No transport options found—try different dates or check manually!")
        
        # ... (Similar for hotels and attractions, with nicer markdown)
    else:
        st.warning("Fill in your locations!")

st.sidebar.image("https://source.unsplash.com/random/200x200/?travel", caption="Ready for adventure?")  # Add a random travel image
