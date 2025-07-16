import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re
from dateutil.parser import parse  # Add to requirements.txt: python-dateutil

# Helper for transport with improved fallback
def search_transport(start, dest, date_start, date_end):
    try:
        # Primary: Rome2Rio
        url = f"https://www.rome2rio.com/search/{start}/{dest}?departureDate={date_start}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        options = []
        for item in soup.select('.route__details, .itinerary-item'):  # Broader selectors for robustness
            mode = item.select_one('.route__title, .mode').text.strip() if item.select_one('.route__title, .mode') else "Unknown"
            price = item.select_one('.route__price, .price').text.strip() if item.select_one('.route__price, .price') else "N/A"
            link = item.select_one('a')['href'] if item.select_one('a') else "/"
            options.append({"mode": mode, "price": price, "link": f"https://www.rome2rio.com{link}"})
        
        if not options:  # Fallback to Google search
            google_query = f"best cheap transport from {start} to {dest} on {date_start} to {date_end}"
            google_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}"
            response = requests.get(google_url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.select('.tF2Cxc')[:3]:  # Grab top organic results
                title = result.select_one('h3').text if result.select_one('h3') else "Option"
                link = result.select_one('a')['href'] if result.select_one('a') else google_url
                options.append({"mode": title, "price": "Check for prices", "link": link})
        
        # Sort by price (simple heuristic)
        options.sort(key=lambda x: float(re.sub(r'[^\d.]', '', x['price'])) if re.sub(r'[^\d.]', '', x['price']) else float('inf'))
        return options[:3] or [{"mode": "No options found", "price": "", "link": ""}]
    except Exception as e:
        return [{"mode": "Error", "price": str(e), "link": ""}]

# Helper for hotels
def search_hotels(dest, date_start, date_end):
    try:
        url = f"https://www.booking.com/searchresults.html?dest_type=city&label=gen173nr-1FCAEoggI46AdIM1gEaN4BiAEBmAExuAEXyAEM2AEB6AEB-AELiAIBqAIDuAL3gYy1BsACAdICJGYzNGU5N2M5LTc3ZjMtNDk5Yi1iZGYyLTBhN2M3ZGY3N2E5ZdgCBuACAQ&sid=36c40fda79e61b345568991803650971&sb=1&src=searchresults&src_elem=sb&error_url=https%3A%2F%2Fwww.booking.com%2Fsearchresults.html%3Flabel%3Dgen173nr-1FCAEoggI46AdIM1gEaN4BiAEBmAExuAEXyAEM2AEB6AEB-AELiAIBqAIDuAL3gYy1BsACAdICJGYzNGU5N2M5LTc3ZjMtNDk5Yi1iZGYyLTBhN2M3ZGY3N2E5ZdgCBuACAQ%3Bsid%3D36c40fda79e61b345568991803650971%3Btmpl%3Dsearchresults%3Bcity%3D-{dest}%3Bclass_interval%3D1%3Bdest_id%3D-{dest}%3Bdest_type%3Dcity%3Bdtdisc%3D0%3Binac%3D0%3Bindex_postcard%3D0%3Blabel_click%3Dundef%3Boffset%3D0%3Bpostcard%3D0%3Broom1%3DA%252CA%3Bsb_price_type%3Dtotal%3Bshw_aparth%3D1%3Bslp_r_match%3D0%3Bsrpvid%3D3b3a5a5e5e5a00a5%3Bss_all%3D0%3Bssb%3Dempty%3Bsshis%3D0%3Btop_ufis%3D1%26%3B&ss={dest}&checkin={date_start}&checkout={date_end}&group_adults=2&no_rooms=1"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        hotels = []
        for item in soup.find_all('div', {'data-testid': 'property-card'}):
            name = item.find('div', {'data-testid': 'title'}).text.strip() if item.find('div', {'data-testid': 'title'}) else "Unknown"
            price = item.find('span', {'data-testid': 'price-and-discounted-price'}).text.strip() if item.find('span', {'data-testid': 'price-and-discounted-price'}) else "N/A"
            rating = item.find('div', {'data-testid': 'review-score'}).text.strip().split()[0] if item.find('div', {'data-testid': 'review-score'}) else "N/A"
            link = item.find('a', {'data-testid': 'title-link'})['href'] if item.find('a', {'data-testid': 'title-link'}) else "https://www.booking.com"
            hotels.append({"name": name, "price": price, "rating": rating, "link": link})
        
        # Sort by rating/price ratio
        def score(h):
            p = float(re.sub(r'[^\d.]', '', h['price'])) if h['price'] != "N/A" else float('inf')
            r = float(h['rating']) if h['rating'] != "N/A" else 0
            return -r / (p + 1)  # Avoid division by zero
        hotels.sort(key=score)
        return hotels[:3] or [{"name": "No hotels found", "price": "", "rating": "", "link": ""}]
    except Exception as e:
        return [{"name": "Error", "price": str(e), "rating": "", "link": ""}]

# Helper for attractions and itinerary
def get_attractions(dest, date_start, date_end):
    try:
        url = f"https://en.wikipedia.org/wiki/{dest}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        attractions = []
        content = soup.find('div', id='mw-content-text')
        if content:
            for p in content.find_all('p')[:10]:  # Grab from paragraphs
                if re.search(r'(attraction|site|landmark|museum|park)', p.text.lower()):
                    attractions.append(p.text.strip()[:100] + "...")  # Shorten
        
        if not attractions:
            attractions = ["Explore local sites—check TripAdvisor for more!"]
        
        # Generate simple itinerary
        start_dt = datetime.datetime.strptime(date_start, '%Y-%m-%d')
        end_dt = datetime.datetime.strptime(date_end, '%Y-%m-%d')
        days = (end_dt - start_dt).days + 1
        itinerary = [f"Day {i+1}: {attractions[i % len(attractions)]}" for i in range(days)]
        return attractions[:5], "\n".join(itinerary)
    except Exception as e:
        return [str(e)], "Error generating itinerary"

# Streamlit app
st.set_page_config(page_title="Epic Travel Planner", page_icon="✈️")
st.title("Epic Travel Planner 🌍")
st.markdown("Plan your dream trip with real-time deals and itineraries! Powered by web magic.")

col1, col2 = st.columns(2)
with col1:
    start = st.text_input("Starting Location (e.g., Pattaya)")
with col2:
    dest = st.text_input("Destination (e.g., Phayao)")

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
        if transports[0]['mode'] != "No options found" and transports[0]['mode'] != "Error":
            for t in transports:
                st.markdown(f"- **{t['mode']}** for {t['price']}: [Book here]({t['link']})")
        else:
            st.warning(f"No transport options found—try different dates or [search manually on Google](https://www.google.com/search?q=transport+from+{start}+to+{dest}+{date_start_str})!")
        
        # Hotels
        st.subheader("Best Hotel Options (Quality/Price) 🏨")
        hotels = search_hotels(dest, date_start_str, date_end_str)
        if hotels[0]['name'] != "No hotels found" and hotels[0]['name'] != "Error":
            for h in hotels:
                st.markdown(f"- **{h['name']}** ({h['rating']} rating) for {h['price']}: [Book here]({h['link']})")
        else:
            st.warning("No hotels found—check Booking.com manually!")
        
        # Attractions
        st.subheader("Major Attractions & Itinerary 📍")
        attractions, itinerary = get_attractions(dest, date_start_str, date_end_str)
        st.write("Top Attractions: " + ", ".join(attractions))
        st.markdown("**Detailed Plan:**\n" + itinerary)
    else:
        st.warning("Please fill in starting location and destination!")

# Sidebar with static image
st.sidebar.title("Adventure Awaits!")
st.sidebar.image("https://images.unsplash.com/photo-1501785888041-af3ef285b470?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=200", caption="Get exploring!")
