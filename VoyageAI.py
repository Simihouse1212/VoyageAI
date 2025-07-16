import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re
from dateutil.parser import parse  # Add to requirements.txt: python-dateutil

# Add background image and enhanced text/button fixes via CSS
st.markdown("""
    <style>
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1920&q=80");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    body, .stApp * {
        font-size: 18px !important;  /* Larger global font size for better readability */
        color: #333333 !important;  /* Dark gray text everywhere */
    }
    .stApp > header {  /* Semi-transparent header */
        background-color: rgba(255, 255, 255, 0.7);
    }
    /* Titles and subheaders bigger */
    .stTitle { font-size: 32px !important; }
    .stSubheader { font-size: 24px !important; }
    a { color: #0066cc !important; }  /* Links blue for visibility */
    /* Specific button styling: Bold black text, white background for high contrast */
    .stButton > button {
        color: #000000 !important;  /* Black text */
        background-color: #FFFFFF !important;  /* White background for visibility */
        font-weight: bold !important;  /* Bolder for emphasis */
        font-size: 20px !important;  /* Even larger button text */
        border: 2px solid #000000 !important;  /* Black border to stand out */
    }
    /* Fix input fields: White background, black text for readability */
    .stTextInput input {
        background-color: #FFFFFF !important;  /* White background */
        color: #000000 !important;  /* Black text */
        border: 1px solid #CCCCCC !important;  /* Light border */
    }
    .stDateInput input, .stNumberInput input {
        background-color: #FFFFFF !important;  /* White for date/number pickers too */
        color: #000000 !important;
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
        
        if len(options) < 2:  # Enhanced fallback: More Google results and estimates
            google_query = f"best transport from {start} to {dest} Thailand {date_start} prices durations"
            google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
            response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.select('.tF2Cxc')[:5]:  # Up to 5 for better coverage
                title = result.select_one('h3').text if result.select_one('h3') else "Option"
                snippet = result.select_one('.VwiC3b').text if result.select_one('.VwiC3b') else ""
                price_match = re.search(r'\$?\d+[\d,.]*', snippet)
                price = price_match.group(0) if price_match else "~$20-40 (estimated)"
                duration_match = re.search(r'\d+ ?(h|hour|min)', snippet)
                duration = duration_match.group(0) if duration_match else "~5-10h"
                link = result.select_one('a')['href'] if result.select_one('a') else google_url
                options.append({"mode": f"{title} ({duration})", "price": price, "link": link})
            
            # Specific fallback for common Thai routes (e.g., to Chiang Mai)
            if "chiang mai" in dest.lower():
                options.extend([
                    {"mode": "Bus (direct or via Bangkok, ~10-12h)", "price": "~$20-40", "link": "https://www.bookaway.com/routes/thailand/bangkok-to-chiang-mai"},
                    {"mode": "Train + Bus (~12h total)", "price": "~$15-30", "link": "https://www.rome2rio.com/s/Bangkok/Chiang-Mai"}
                ])
        
        options = [opt for opt in options if opt['price'] != "N/A"]  # Filter junk
        options.sort(key=lambda x: float(re.sub(r'[^\d.]', '', x['price'])) if re.sub(r'[^\d.]', '', x['price']) else float('inf'))
        return options[:3] or [{"mode": "No specific options found", "price": "", "link": google_url}]
    except Exception as e:
        return [{"mode": "Error: " + str(e), "price": "", "link": ""}]

# Helper for hotels with improved fallback and encoding fix
def search_hotels(dest, date_start, date_end):
    hotels = []
    try:
        # Primary: Booking.com
        url = f"https://www.booking.com/searchresults.html?ss={dest}&checkin={date_start}&checkout={date_end}&group_adults=2&no_rooms=1&order=price"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.encoding = 'utf-8'  # Force UTF-8 to handle Thai characters
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for item in soup.find_all('div', {'data-testid': 'property-card'}):
            name = item.find('div', {'data-testid': 'title'}).text.strip() if item.find('div', {'data-testid': 'title'}) else "Unknown Hotel"
            price = item.find('span', {'data-testid': 'price-and-discounted-price'}).text.strip() if item.find('span', {'data-testid': 'price-and-discounted-price'}) else "Price N/A"
            rating = item.find('div', {'data-testid': 'review-score'}).text.strip().split()[0] if item.find('div', {'data-testid': 'review-score'}) else "Rating N/A"
            link = item.find('a', {'data-testid': 'title-link'})['href'] if item.find('a', {'data-testid': 'title-link'}) else "https://www.booking.com"
            hotels.append({"name": name, "price": price, "rating": rating, "link": link})
    except Exception as e:
        st.warning(f"Booking.com scrape failed: {str(e)}. Falling back to Google search.")

    if len(hotels) < 2:  # Fallback to Google with encoding fix (now up to 5 results)
        try:
            google_query = f"best hotels in {dest} {date_start} to {date_end} prices ratings"
            google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
            response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.select('.tF2Cxc')[:5]:  # More results for reliability
                title = result.select_one('h3').text if result.select_one('h3') else "Hotel"
                snippet = result.select_one('.VwiC3b').text if result.select_one('.VwiC3b') else ""
                price_match = re.search(r'\$?\d+[\d,.]*|฿\d+[\d,.]*', snippet)  # Handle USD or THB
                price = price_match.group(0) if price_match else "Check site"
                rating_match = re.search(r'\d\.\d', snippet)
                rating = rating_match.group(0) if rating_match else "N/A"
                link = result.select_one('a')['href'] if result.select_one('a') else google_url
                hotels.append({"name": title, "price": price, "rating": rating, "link": link})
        except Exception as e:
            st.warning(f"Google fallback failed: {str(e)}. Using hardcoded options.")

        # Specific hardcoded fallback for Chiang Mai if still empty
        if len(hotels) < 2 and "chiang mai" in dest.lower():
            hotels = [
                {"name": "Akyra Manor Chiang Mai", "price": "~฿3,000/night", "rating": "8.9", "link": "https://www.booking.com/hotel/th/akyra-manor-chiang-mai.en-gb.html"},
                {"name": "Pingviman Hotel", "price": "~฿2,500/night", "rating": "8.7", "link": "https://www.booking.com/hotel/th/pingviman.en-gb.html"},
                {"name": "99 The Gallery Hotel", "price": "~฿1,800/night", "rating": "8.5", "link": "https://www.booking.com/hotel/th/99-the-gallery.en-gb.html"}
            ]

    if not hotels:
        return [{"name": "No specific hotels found", "price": "N/A", "rating": "N/A", "link": "https://www.google.com/search?q=hotels+in+" + requests.utils.quote(dest)}]

    # Sort by price
    def score(h):
        p = float(re.sub(r'[^\d.]', '', h['price'])) if re.sub(r'[^\d.]', '', h['price']) else float('inf')
        return p
    hotels.sort(key=score)
    return hotels[:3]

# Helper for attractions and itinerary with dynamic web search fallback
def get_attractions(dest, date_start, date_end):
    try:
        google_query = f"top attractions in {dest} things to do"
        google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
        response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        attractions = []
        for result in soup.select('.tF2Cxc')[:5]:
            title = result.select_one('h3').text if result.select_one('h3') else ""
            if title:
                attractions.append(title)
        
        if len(attractions) < 3:  # Dynamic fallback: Use web search for any destination
            # Simulate web search for top attractions (in real code, this could call a tool)
            # For now, adding examples for Chiang Mai as a test
            if "chiang mai" in dest.lower():
                attractions = [
                    "Doi Inthanon National Park (highest peak in Thailand)",
                    "Wat Phra That Doi Suthep (iconic temple with views)",
                    "Elephant Nature Park (ethical sanctuary)",
                    "Night Bazaar (shopping and street food)",
                    "Old City Temples (historic sites like Wat Chedi Luang)"
                ]
            else:
                attractions = ["Local highlights—search for more details! Try [TripAdvisor](https://www.tripadvisor.com/Attractions) for more."]  # General with link
        
        # Generate itinerary based on attractions
        start_dt = datetime.datetime.strptime(date_start, '%Y-%m-%d')
        end_dt = datetime.datetime.strptime(date_end, '%Y-%m-%d')
        days = (end_dt - start_dt).days + 1
        itinerary = []
        for i in range(days):
            attr = attractions[i % len(attractions)] if attractions else "Free day to explore"
            itinerary.append(f"Day {i+1}: Visit {attr}. Enjoy local cuisine and relax!")
        
        return attractions, "\n".join(itinerary), days
    except Exception as e:
        return [str(e)], "Error generating itinerary. Try manually!", 1

# Function to estimate total cost (rough calculation)
def estimate_total_cost(transports, hotels, days, travelers):
    # Transport: Cheapest per person, one-way (assume round-trip x2)
    trans_price = 0
    if transports and transports[0]['price'] and transports[0]['price'] != "N/A":
        trans_str = re.sub(r'[^\d.]', '', transports[0]['price'].split('-')[0])  # Take low end
        trans_price = float(trans_str) * 2 * travelers if trans_str else 50 * travelers  # Default $50/pp round-trip
    
    # Hotels: Cheapest per night, assume per room (divide by 2 if >1 traveler, rough)
    hotel_price = 0
    if hotels and hotels[0]['price'] and hotels[0]['price'] != "N/A":
        hotel_str = re.sub(r'[^\d.]', '', hotels[0]['price'].split('-')[0])  # Take low end
        per_night = float(hotel_str) if hotel_str else 50
        room_factor = max(1, travelers / 2)  # Rough: 1 room for 1-2, more for larger groups
        hotel_price = per_night * days * room_factor
    
    # Other: $50/day/person for attractions, food, etc.
    other_price = 50 * days * travelers
    
    total = trans_price + hotel_price + other_price
    return trans_price, hotel_price, other_price, total

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

travelers = st.number_input("Number of Travelers", min_value=1, max_value=10, value=2, step=1)

if st.button("Plan My Trip! 🚀"):
    if start and dest:
        st.write(f"Planning your adventure from {start} to {dest} for {date_start_str} to {date_end_str} with {travelers} travelers...")
        
        # Transport
        st.subheader("Best Transport Options (Quality/Price) 🚌✈️")
        transports = search_transport(start, dest, date_start_str, date_end_str)
        if transports[0]['mode'] != "No specific options found" and "Error" not in transports[0]['mode']:
            for t in transports:
                st.markdown(f"- **{t['mode']}** for {t['price']}: [Book here]({t['link']})")
        else:
            google_link = f"https://www.google.com/search?q=transport+from+{requests.utils.quote(start)}+to+{requests.utils.quote(dest)}+{date_start_str}"
            st.warning(f"No specific transport options found. [Search manually on Google]({google_link}) or try different dates!")
        
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
        attractions, itinerary, days = get_attractions(dest, date_start_str, date_end_str)
        st.markdown("**Top Attractions:**")
        for attr in attractions:
            st.markdown(f"- {attr}")
        st.markdown("**Detailed Plan:**\n" + itinerary.replace("\n", "\n\n"))  # Add spacing for clarity
        
        # Total Cost Estimate
        st.subheader("Estimated Total Cost 💰")
        trans_est, hotel_est, other_est, total_est = estimate_total_cost(transports, hotels, days, travelers)
        st.markdown(f"*Rough estimate based on cheapest options (per person where applicable). Actual costs may vary!*")
        st.markdown(f"- Transport (round-trip): ~${trans_est:.2f}")
        st.markdown(f"- Hotels ({days} nights): ~${hotel_est:.2f}")
        st.markdown(f"- Attractions/Food/Misc ($50/day/person): ~${other_est:.2f}")
        st.markdown(f"**Grand Total for {travelers} travelers: ~${total_est:.2f}**")
    else:
        st.warning("Please fill in starting location and destination!")
