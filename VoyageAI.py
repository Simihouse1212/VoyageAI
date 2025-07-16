import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re
from dateutil.parser import parse  # Add to requirements.txt: python-dateutil

# Helper for transport with improved Google fallback parsing
def search_transport(start, dest, date_start, date_end):
    try:
        # Primary: Rome2Rio
        url = f"https://www.rome2rio.com/search/{start}/{dest}?departureDate={date_start}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        options = []
        for item in soup.select('.route__details, .itinerary-item'):  # Broader selectors
            mode = item.select_one('.route__title, .mode').text.strip() if item.select_one('.route__title, .mode') else "Unknown"
            price = item.select_one('.route__price, .price').text.strip() if item.select_one('.route__price, .price') else "N/A"
            link = item.select_one('a')['href'] if item.select_one('a') else "/"
            options.append({"mode": mode, "price": price, "link": f"https://www.rome2rio.com{link}"})
        
        if len(options) < 2:  # Improved fallback to Google with better parsing
            google_query = f"best cheap transport from {start} to {dest} {date_start} to {date_end} prices"
            google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
            response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.select('.tF2Cxc')[:3]:  # Parse top results for details
                title = result.select_one('h3').text if result.select_one('h3') else "Option"
                snippet = result.select_one('.VwiC3b').text if result.select_one('.VwiC3b') else ""
                price_match = re.search(r'\$?\d+[\d,.]*', snippet)  # Extract possible price
                price = price_match.group(0) if price_match else "Check site"
                link = result.select_one('a')['href'] if result.select_one('a') else google_url
                options.append({"mode": title, "price": price, "link": link})
        
        # Sort by price
        options.sort(key=lambda x: float(re.sub(r'[^\d.]', '', x['price'])) if re.sub(r'[^\d.]', '', x['price']) else float('inf'))
        return options[:3] or [{"mode": "No specific options found", "price": "", "link": google_url}]
    except Exception as e:
        return [{"mode": "Error: " + str(e), "price": "", "link": ""}]

# Helper for hotels with improved fallback
def search_hotels(dest, date_start, date_end):
    try:
        # Primary: Booking.com (simplified URL)
        url = f"https://www.booking.com/searchresults.html?ss={dest}&checkin={date_start}&checkout={date_end}&group_adults=2&no_rooms=1&order=price"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        hotels = []
        for item in soup.find_all('div', {'data-testid': 'property-card'}):
            name = item.find('div', {'data-testid': 'title'}).text.strip() if item.find('div', {'data-testid': 'title'}) else "Unknown"
            price = item.find('span', {'data-testid': 'price-and-discounted-price'}).text.strip() if item.find('span', {'data-testid': 'price-and-discounted-price'}) else "N/A"
            rating = item.find('div', {'data-testid': 'review-score'}).text.strip().split()[0] if item.find('div', {'data-testid': 'review-score'}) else "N/A"
            link = item.find('a', {'data-testid': 'title-link'})['href'] if item.find('a', {'data-testid': 'title-link'}) else "https://www.booking.com"
            hotels.append({"name": name, "price": price, "rating": rating, "link": link})
        
        if len(hotels) < 2:  # Fallback to Google
            google_query = f"best cheap hotels in {dest} {date_start} to {date_end} prices ratings"
            google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
            response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.select('.tF2Cxc')[:3]:
                title = result.select_one('h3').text if result.select_one('h3') else "Hotel"
                snippet = result.select_one('.VwiC3b').text if result.select_one('.VwiC3b') else ""
                price_match = re.search(r'\$?\d+[\d,.]*', snippet)
                price = price_match.group(0) if price_match else "Check site"
                rating_match = re.search(r'\d\.\d', snippet)
                rating = rating_match.group(0) if rating_match else "N/A"
                link = result.select_one('a')['href'] if result.select_one('a') else google_url
                hotels.append({"name": title, "price": price, "rating": rating, "link": link})
        
        # Sort by rating/price
        def score(h):
            p = float(re.sub(r'[^\d.]', '', h['price'])) if re.sub(r'[^\d.]', '', h['price']) else float('inf')
            r = float(h['rating']) if re.sub(r'[^\d.]', '', h['rating']) else 0
            return -r / (p + 1)
        hotels.sort(key=score)
        return hotels[:3] or [{"name": "No specific hotels found", "price": "", "rating": "", "link": google_url}]
    except Exception as e:
        return [{"name": "Error: " + str(e), "price": "", "rating": "", "link": ""}]

# Helper for attractions and itinerary with Google search for better results
def get_attractions(dest, date_start, date_end):
    try:
        # Use Google for top attractions
        google_query = f"top attractions in {dest} things to do"
        google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
        response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        attractions = []
        for result in soup.select('.tF2Cxc')[:5]:
            title = result.select_one('h3').text if result.select_one('h3') else ""
            if title:
                attractions.append(title)
        
        if not attractions:
            attractions = ["Local highlights—search for more details!"]
        
        # Generate itinerary based on attractions
        start_dt = datetime.datetime.strptime(date_start, '%Y-%m-%d')
        end_dt = datetime.datetime.strptime(date_end, '%Y-%m-%d')
        days = (end_dt - start_dt).days + 1
        itinerary = []
        for i in range(days):
            attr = attractions[i % len(attractions)] if attractions else "Free day to explore"
            itinerary.append(f"Day {i+1}: Visit {attr}. Enjoy local cuisine and relax!")
        
        return attractions, "\n".join(itinerary)
    except Exception as e:
        return [str(e)], "Error generating itinerary. Try manually!"

# Streamlit app (no sidebar)
st.set_page_config(page_title="Epic Travel Planner", page_icon="✈️")
st.title("Epic Travel Planner 🌍")
st.markdown("Plan your dream trip with real-time deals and itineraries! Powered by web magic.")

col1, col2 = st.columns(2)
with col1:
    start = st.text_input("Starting Location")
with col2:
    dest = st.text_input("Destination")

st.subheader("Pick Your Dates 📅")
date_start = st.date_input("Start Date", value=datetime.date.today() + datetime.timedelta(days=7))
date_end = st.date_input("End Date", value=date_start + datetime.timedelta(days=7))
date_start_str = str(date_start)
date_end_str = str(date_end)

if st.button("Plan My Trip! 🚀"):
    if start and dest:
        st.write(f"Planning your adventure from {start} to {dest} for {date_start_str} to {date_end_str}...")
        
        # Transport
        st.subheader("Best Transport Options (Quality/Price) 🚌✈️")
        transports = search_transport(start, dest, date_start_str, date_end_str)
        if transports[0]['mode'] != "No specific options found" and transports[0]['mode'] != "Error":
            for t in transports:
                st.markdown(f"- **{t['mode']}** for {t['price']}: [Book here]({t['link']})")
        else:
            google_link = f"https://www.google.com/search?q=transport+from+{requests.utils.quote(start)}+to+{requests.utils.quote(dest)}+{date_start_str}"
            st.warning(f"No specific transport options found. [Search manually on Google]({google_link}) or try different dates!")
        
        # Hotels
        st.subheader("Best Hotel Options (Quality/Price) 🏨")
        hotels = search_hotels(dest, date_start_str, date_end_str)
        if hotels[0]['name'] != "No specific hotels found" and hotels[0]['name'] != "Error":
            for h in hotels:
                st.markdown(f"- **{h['name']}** ({h['rating']} rating) for {h['price']}: [Book here]({h['link']})")
        else:
            google_link = f"https://www.google.com/search?q=hotels+in+{requests.utils.quote(dest)}+{date_start_str}+to+{date_end_str}"
            st.warning(f"No specific hotels found. [Search manually on Google]({google_link})!")
        
        # Attractions
        st.subheader("Major Attractions & Itinerary 📍")
        attractions, itinerary = get_attractions(dest, date_start_str, date_end_str)
        st.write("Top Attractions: " + ", ".join(attractions))
        st.markdown("**Detailed Plan:**\n" + itinerary)
    else:
        st.warning("Please fill in starting location and destination!")
