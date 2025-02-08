from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import os
import uvicorn

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to ["https://spark.tdvorak.dev"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMDB_API_KEY = "054582e9ee66adcbe911e0008aa482a8"
TMDB_BASE_URL = "https://api.themoviedb.org/3/"

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/98.0.4758.102 Safari/537.36'),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': 'https://www.google.com'
}

# Serve the documentation HTML page
@app.get("/")
def read_root():
    print("Serving the root page.")  # Console log
    return FileResponse("index.html")

def scrape_metacritic(url):
    """Scrapes Metacritic scores from the given URL."""
    print(f"Scraping Metacritic for URL: {url}")  # Console log
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        print(f"Error fetching Metacritic data from {url}")  # Console log
        return {"metascore": "N/A", "userscore": "N/A", "metacritic_certified": False, "metacritic_url": url}

    soup = BeautifulSoup(response.text, 'html.parser')

    def get_score(score_type):
        if score_type == 'meta':
            score_div = soup.find('div', class_=lambda c: c and ('c-siteReviewScore' in c) and ('c-siteReviewScore_user' not in c))
        elif score_type == 'user':
            score_div = soup.find('div', class_=lambda c: c and ('c-siteReviewScore_user' in c))
        else:
            return 'N/A'
        
        if score_div:
            span = score_div.find('span')
            return span.text.strip() if span else 'N/A'
        return 'N/A'

    # Check for the "Must See" badge
    must_see_badge = soup.find('img', class_="c-productScoreInfo_must")
    metacritic_certified = bool(must_see_badge)

    return {
        "metascore": get_score('meta'),
        "userscore": get_score('user'),
        "metacritic_certified": metacritic_certified,
        "metacritic_url": url
    }


def scrape_rotten_tomatoes(category, title, release_year=None):
    """Scrapes Rotten Tomatoes critic and audience scores, along with certification status."""
    title_slug = title.lower().replace(" ", "_")

    # Adjust URL construction based on category
    if category == "movie":
        base_url = f"https://www.rottentomatoes.com/m/{title_slug}"
    elif category == "tv":
        base_url = f"https://www.rottentomatoes.com/tv/{title_slug}"
    else:
        print(f"Invalid category {category}")  # Console log
        return {
            "critic_score": "N/A",
            "audience_score": "N/A",
            "critic_certified_fresh": False,
            "audience_certified_fresh": False,
            "rotten_tomatoes_url": "N/A"
        }

    # Try with year if provided, otherwise just the base URL
    url_with_year = f"{base_url}_{release_year}" if release_year else None
    urls_to_try = [url_with_year] if url_with_year else [base_url]

    for url in urls_to_try:
        print(f"Trying Rotten Tomatoes URL: {url}")  # Console log
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 404:
                print(f"404 error for {url}, trying base URL...")  # Console log
                # If we tried the URL with the year and got 404, now try the base URL without it
                if url == url_with_year:
                    response = requests.get(base_url, headers=HEADERS, timeout=10)
                    url = base_url  # Update the URL to base URL since the year-based URL failed
                response.raise_for_status()

            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract Scores
            critic_score = soup.select_one('rt-text[slot="criticsScore"]')
            audience_score = soup.select_one('rt-text[slot="audienceScore"]')

            # Adjust extraction for certification status
            critic_certified = False
            audience_certified = False

            critic_certified_tag = soup.find('score-icon-critics')
            if critic_certified_tag and critic_certified_tag.get('certified') == 'true':
                critic_certified = True

            audience_certified_tag = soup.find('score-icon-audience')
            if audience_certified_tag and audience_certified_tag.get('certified') == 'true':
                audience_certified = True

            # Log the correct URL
            print(f"Successfully fetched Rotten Tomatoes data from: {url}")  # Console log

            return {
                "critic_score": critic_score.text.strip() if critic_score else "N/A",
                "audience_score": audience_score.text.strip() if audience_score else "N/A",
                "critic_certified_fresh": critic_certified,
                "audience_certified_fresh": audience_certified,
                "rotten_tomatoes_url": url  # Correct URL without the year if needed
            }
        except requests.RequestException as e:
            print(f"Error fetching data for {url}: {e}")  # Console log
            continue  # Try the next URL if there's an error

    # If all attempts fail, return default values
    return {
        "critic_score": "N/A",
        "audience_score": "N/A",
        "critic_certified_fresh": False,
        "audience_certified_fresh": False,
        "rotten_tomatoes_url": "N/A"
    }



    
def get_tmdb_data(category, tmdb_id):
    """Fetches movie/TV show data from TMDB."""
    print(f"Fetching TMDB data for {category} with ID: {tmdb_id}")  # Console log
    url = f"{TMDB_BASE_URL}{category}/{tmdb_id}?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"TMDB data found for {category} ID: {tmdb_id}")  # Console log
        return response.json()
    else:
        print(f"Error fetching TMDB data for {category} ID: {tmdb_id}")  # Console log
        return None

@app.get("/{category}/{tmdb_id}")
def get_movie_data(category: str, tmdb_id: int):
    print(f"Received request for {category} with TMDB ID: {tmdb_id}")  # Console log
    if category not in ["movie", "tv"]:
        print(f"Invalid category: {category}")  # Console log
        return {"error": "Invalid category"}

    # Get TMDB data
    tmdb_data = get_tmdb_data(category, tmdb_id)
    if not tmdb_data:
        print(f"No TMDB data found for ID: {tmdb_id}")  # Console log
        return {"error": "TMDB data not found"}

    title = tmdb_data.get("title", tmdb_data.get("name", ""))
    release_year = tmdb_data.get("release_date", tmdb_data.get("first_air_date", ""))[:4]

    # Get Metacritic scores
    title_slug = title.lower().replace(" ", "-")
    metacritic_url = f"https://www.metacritic.com/{category}/{title_slug}"
    metacritic_data = scrape_metacritic(metacritic_url)

    # Get Rotten Tomatoes scores
    rotten_tomatoes_data = scrape_rotten_tomatoes(category, title, release_year)

    return {
        "tmdb": tmdb_data,
        "metacritic": metacritic_data,
        "rotten_tomatoes": rotten_tomatoes_data
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))  # Use Railway's PORT or default to 8000
    print(f"Starting FastAPI server on port {port}")  # Console log
    uvicorn.run(app, host="0.0.0.0", port=port)
