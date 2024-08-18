import random
import cloudscraper
from bs4 import BeautifulSoup
import json
import asyncio
from telegram import Bot
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Movie details
movie_url = os.getenv("movie_url")
tracked_theaters_file = "tracked_theaters.json"

# Set up Telegram Bot
bot = Bot(token=TELEGRAM_API_TOKEN)

async def send_message(message):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"Sent Telegram message: {message}")
    except Exception as e:
        print(f"Failed to send message: {e}")

def get_theaters_and_show_timings(url):
    # Use cloudscraper to handle Cloudflare
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url)

    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')
    
    venue_list = soup.find('ul', id='venuelist')
    
    if venue_list is None:
        print("Error: 'venuelist' element not found in the HTML.")
        return {}

    theaters_and_timings = {}
    
    for li in venue_list.find_all('li', class_='list'):
        theater_name = li.get('data-name')
        
        show_times = []
        for showtime in li.find_all('a', class_='showtime-pill'):
            showtime_text = showtime.get('data-display-showtime', '').strip()
            if showtime_text:
                show_times.append(showtime_text)
        
        theaters_and_timings[theater_name] = show_times
    
    return theaters_and_timings

def load_tracked_theaters_and_timings():
    try:
        with open(tracked_theaters_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_tracked_theaters_and_show_timings(data):
    with open(tracked_theaters_file, "w") as file:
        json.dump(data, file, indent=4)

async def check_for_new_theaters_and_show_timings():
    print("Checking for new theaters and show timings...")
    current_data = get_theaters_and_show_timings(movie_url)
    tracked_data = load_tracked_theaters_and_timings()

    message = []
    new_theaters = []
    new_show_timings = []

    # Initialize tracked_data if it's empty
    if not tracked_data:
        tracked_data = {}

    for theater, timings in current_data.items():
        if theater not in tracked_data:
            # New theater
            new_theaters.append(f"{theater} - {', '.join(timings)}")
            tracked_data[theater] = timings  # Track this theater
        else:
            # Check for new show timings in existing theaters
            existing_timings = set(tracked_data[theater])
            current_timings = set(timings)
            new_timings = current_timings - existing_timings
            if new_timings:
                new_show_timings.append(f"{theater}\n{', '.join(new_timings)}")
                tracked_data[theater].extend(new_timings)  # Track new timings

    # Format message for new theaters
    if new_theaters:
        message.append("New Theatre added:\n" + "\n".join(new_theaters))

    # Format message for new show timings
    if new_show_timings:
        message.append("New Shows added:\n" + "\n".join(new_show_timings))

    # Send the message if there are any updates
    if message:
        await send_message("\n\n".join(message))

    # Save the updated tracked data
    save_tracked_theaters_and_show_timings(tracked_data)

async def main():
    print("Bot is up and running!")
    while True:
        await check_for_new_theaters_and_show_timings()
        delay = random.uniform(2, 10)  # Generate a random delay between 2 and 10 seconds
        await asyncio.sleep(delay)

if __name__ == "__main__":
    asyncio.run(main())
