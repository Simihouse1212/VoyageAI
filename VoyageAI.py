import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re
from dateutil.parser import parse  # Add to requirements.txt: python-dateutil

# Helper for transport with indirect route suggestion
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
            for result in soup.select('.tF2Cxc')[:3]:
                title = result.select_one('h3').text if result.select_one('h3') else "Option"
                snippet = result.select_one('.VwiC3b').text if result.select_one('.VwiC3b') else ""
                price_match = re.search(r'\$?\d+[\d,.]*', snippet)
                price = price_match.group(0) if price_match else "~$20-40 (estimated)"
                link = result.select_one('a')['href'] if result.select_one('a') else google_url
                options.append({"mode": title, "price": price, "link": link})
            
            # Add indirect suggestion if no direct
            if "Pattaya" in start.lower() and "Phayao" in dest.lower():
                options.append({"mode": "Indirect: Bus/Train Pattaya to Bangkok (2-3h, ~$4-14), then Bus Bangkok to Phayao (10-11h, ~$18-36)", "price": "~$22-50 total", "link": "https://www.bookaway.com/routes/thailand/bangkok-to-phayao"})
        
        options.sort(key=lambda x: float(re.sub(r'[^\d.]', '', x['price'])) if re.sub(r'[^\d.]', '', x['price']) else float('inf'))
        return options[:3] or [{"mode": "No specific options found", "price": "", "link": google_url}]
    except Exception as e:
        return [{"mode": "Error: " + str(e), "price": "", "link": ""}]

# Helper for hotels (ensure price/rating display)
def search_hotels(dest, date_start, date_end):
    try:
        url = f"https://www.booking.com/searchresults.html?ss={dest}&checkin={date_start}&checkout={date_end}&group_adults=2&no_rooms=1&order=price"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        hotels = []
        for item in soup.find_all('div', {'data-testid': 'property-card'}):
            name = item.find('div', {'data-testid': 'title'}).text.strip() if item.find('div', {'data-testid': 'title'}) else "Unknown Hotel"
            price = item.find('span', {'data-testid': 'price-and-discounted-price'}).text.strip() if item.find('span', {'data-testid': 'price-and-discounted-price'}) else "Price N/A"
            rating = item.find('div', {'data-testid': 'review-score'}).text.strip().split()[0] if item.find('div', {'data-testid': 'review-score'}) else "Rating N/A"
            link = item.find('a', {'data-testid': 'title-link'})['href'] if item.find('a', {'data-testid': 'title-link'}) else "https://www.booking.com"
            hotels.append({"name": name, "price": price, "rating": rating, "link": link})
        
        if len(hotels) < 2:  # Fallback
            google_query = f"best hotels in {dest} {date_start} to {date_end} prices ratings"
            google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
            response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.select('.tF2Cxc')[:3]:
                title = result.select_one('h3').text if result.select_one('h3') else "Hotel Option"
                snippet = result.select_one('.VwiC3b').text if result.select_one('.VwiC3b') else ""
                price = re.search(r'\$?\d+[\d,.]*', snippet).group(0) if re.search(r'\$?\d+[\d,.]*', snippet) else "Price N/A"
                rating = re.search(r'\d\.\d', snippet).group(0) if re.search(r'\d\.\d', snippet) else "Rating N/A"
                link = result.select_one('a')['href'] if result.select_one('a') else google_url
                hotels.append({"name": title, "price": price, "rating": rating, "link": link})
        
        hotels.sort(key=lambda h: float(re.sub(r'[^\d.]', '', h['price'])) if re.sub(r'[^\d.]', '', h['price']) else float('inf'))
        return hotels[:3] or [{"name": "No specific hotels found", "price": "N/A", "rating": "N/A", "link": google_url}]
    except Exception as e:
        return [{"name": "Error: " + str(e), "price": "N/A", "rating": "N/A", "link": ""}]

# Helper for attractions with better parsing
def get_attractions(dest, date_start, date_end):
    try:
        google_query = f"top attractions in {dest} Thailand things to do"
        google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
        response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        attractions = []
        for result in soup.select('.tF2Cxc')[:5]:
            title = result.select_one('h3').text if result.select_one('h3') else ""
            snippet = result.select_one('.VwiC3b').text if result.select_one('.VwiC3b') else ""
            if title and any(word in snippet.lower() for word in ['attraction', 'visit', 'site']):
                attractions.append(title)
        
        if not attractions:
            # Hardcoded fallback for Phayao based on real data
            if "phayao" in dest.lower():
                attractions = ["Kwan Phayao Lake", "Wat Si Khom Kham Temple", "Phu Langka Forest Park", "Phayao Cultural Exhibition Hall", "Wat Analayo"]
            else:
                attractions = ["Local highlights—search for more!"]
        
        # Generate varied itinerary
        start_dt = datetime.datetime.strptime(date_start, '%Y-%m-%d')
        end_dt = datetime.datetime.strptime(date_end, '%Y-%m-%d')
        days = (end_dt - start_dt).days + 1
        itinerary = []
        for i in range(days):
            attr = attractions[i % len(attractions)] if attractions else "Free exploration day"
            itinerary.append(f"Day {i+1}: Morning at {attr}, afternoon for local sights or relaxation. Try street food!")
        
        return attractions, "\n".join(itinerary)
    except Exception as e:
        return [str(e)], "Error generating itinerary. Try manually!"

# Streamlit app
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
        if transports[0]['mode'] != "No specific options found" and "Error" not in transports[0]['mode']:
            for t in transports:
                st.markdown(f"- **{t['mode']}** for {t['price']}: [Book here]({t['link']})")
        else:
            google_link = f"https://www.google.com/search?q=transport+from+{requests.utils.quote(start)}+to+{requests.utils.quote(dest)}+{date_start_str}"
            st.warning(f"No direct options found. Try [searching on Google]({google_link}) or different dates!")
        
        # Hotels
        st.subheader("Best Hotel Options (Quality/Price) 🏨")
        hotels = search_hotels(dest, date_start_str, date_end_str)
        if hotels[0]['name'] != "No specific hotels found" and "Error" not in hotels[0]['name']:
            for h in hotels:
                st.markdown(f"- **{h['name']}** - Rating: {h['rating']}, Price: {h['price']}: [Book here]({h['link']})")
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
