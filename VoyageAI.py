import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re

# Helper function to search web for transport (flights/trains)
def search_transport(start, dest, date_start, date_end):
    # Using a free search like Rome2Rio for transport options
    query = f"best transport from {start} to {dest} {date_start} to {date_end} quality price"
    url = f"https://www.rome2rio.com/search/{start}/{dest}?departureDate={date_start}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Scrape for options (this is simplified; parse based on site structure)
    options = []
    for item in soup.find_all('div', class_='route-summary'):  # Adjust class based on site
        mode = item.find('span', class_='mode').text if item.find('span', class_='mode') else "Unknown"
        price = item.find('span', class_='price').text if item.find('span', class_='price') else "N/A"
        link = item.find('a')['href'] if item.find('a') else "https://www.rome2rio.com"
        options.append({"mode": mode, "price": price, "link": f"https://www.rome2rio.com{link}"})
    
    # Sort by price (simple heuristic for best quality/price)
    options.sort(key=lambda x: float(re.sub(r'[^\d.]', '', x['price'])) if x['price'] != "N/A" else float('inf'))
    return options[:3]  # Top 3 best

# Helper for hotels
def search_hotels(dest, date_start, date_end):
    query = f"best hotels in {dest} {date_start} to {date_end} quality price"
    url = f"https://www.booking.com/searchresults.html?dest_type=city&dest_id=-{dest}&checkin={date_start}&checkout={date_end}"  # Note: Booking.com URLs need proper params
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(response.text, 'html.parser')
    
    hotels = []
    for item in soup.find_all('div', {'data-testid': 'property-card'}):
        name = item.find('div', {'data-testid': 'title'}).text.strip()
        price = item.find('span', {'data-testid': 'price-and-discounted-price'}).text.strip()
        rating = item.find('div', {'data-testid': 'review-score'}).text.strip()
        link = item.find('a', {'data-testid': 'title-link'})['href']
        hotels.append({"name": name, "price": price, "rating": rating, "link": f"https://www.booking.com{link}"})
    
    # Sort by rating/price ratio
    def score(h): 
        p = float(re.sub(r'[^\d.]', '', h['price'])) if h['price'] else float('inf')
        r = float(h['rating'].split()[0]) if h['rating'] else 0
        return -r / p if p > 0 else float('-inf')  # Higher rating, lower price
    hotels.sort(key=score, reverse=True)
    return hotels[:3]

# Helper for attractions and itinerary
def get_attractions(dest):
    url = f"https://en.wikipedia.org/wiki/{dest}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    attractions = []
    for li in soup.find_all('li', class_='mw-parser-output'):  # Rough scrape; adjust
        text = li.text.strip()
        if "attraction" in text.lower() or "site" in text.lower():
            attractions.append(text)
    
    # Generate simple itinerary
    days = (datetime.datetime.strptime(date_end, '%Y-%m-%d') - datetime.datetime.strptime(date_start, '%Y-%m-%d')).days
    itinerary = [f"Day {i+1}: Visit {attractions[i % len(attractions)] if attractions else 'major sites'}" for i in range(days)]
    return attractions[:5], "\n".join(itinerary)

# Streamlit app
st.title("Travel Planner App")

start = st.text_input("Starting Location (e.g., New York)")
dest = st.text_input("Destination (e.g., Paris)")
date_range = st.text_input("Date Range (e.g., 2025-08-01 to 2025-08-07)")

if st.button("Plan My Trip"):
    if start and dest and date_range:
        try:
            date_start, date_end = date_range.split(" to ")
            st.write(f"Planning trip from {start} to {dest} for {date_start} to {date_end}...")
            
            # Transport
            st.subheader("Best Transportation Options (Quality/Price)")
            transports = search_transport(start, dest, date_start, date_end)
            for t in transports:
                st.write(f"- {t['mode']} for {t['price']}: [Book here]({t['link']})")
            
            # Hotels
            st.subheader("Best Hotel Options (Quality/Price)")
            hotels = search_hotels(dest, date_start, date_end)
            for h in hotels:
                st.write(f"- {h['name']} ({h['rating']} rating) for {h['price']}: [Book here]({h['link']})")
            
            # Attractions
            st.subheader("Major Attractions & Itinerary")
            attractions, itinerary = get_attractions(dest)
            st.write("Top Attractions:", ", ".join(attractions))
            st.write("Detailed Plan:\n" + itinerary)
        
        except Exception as e:
            st.error(f"Oops, something went wrong: {e}. Try refining your inputs!")
    else:
        st.warning("Please fill in all fields.")
