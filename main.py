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
    return FileResponse("index.html")

def scrape_metacritic(url):
    """Scrapes Metacritic scores from the given URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return {"metascore": "N/A", "userscore": "N/A"}

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

    return {
        "metascore": get_score('meta'),
        "userscore": get_score('user')
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
        return {
            "critic_score": "N/A",
            "audience_score": "N/A",
            "critic_certified_fresh": False,
            "audience_certified_fresh": False,
            "rotten_tomatoes_url": "N/A"
        }

    url_with_year = f"{base_url}_{release_year}" if release_year else None
    urls_to_try = [url_with_year] if url_with_year else [base_url]

    for url in urls_to_try:
        try:
            print(f"Trying URL: {url}")  # Debugging line
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 404:
                print(f"404 error for {url}, trying next URL...")
                continue  # Try the next URL if 404

            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract Scores
            critic_score = soup.select_one('rt-text[slot="criticsScore"]')
            audience_score = soup.select_one('rt-text[slot="audienceScore"]')

            # Extract Certified Fresh Status
            critic_certified = bool(soup.select_one("score-icon-critics[certified='true']"))
            audience_certified = bool(soup.select_one("score-icon-audience[certified='true']"))

            return {
                "critic_score": critic_score.text.strip() if critic_score else "N/A",
                "audience_score": audience_score.text.strip() if audience_score else "N/A",
                "critic_certified_fresh": critic_certified,
                "audience_certified_fresh": audience_certified,
                "rotten_tomatoes_url": url
            }
        except requests.RequestException as e:
            print(f"Error fetching data for {url}: {e}")  # Debugging line
            continue  # Try the next URL if there's an error

    return {
        "critic_score": "N/A",
        "audience_score": "N/A",
        "critic_certified_fresh": False,
        "audience_certified_fresh": False,
        "rotten_tomatoes_url": "N/A"
    }

def get_tmdb_data(category, tmdb_id):
    """Fetches movie/TV show data from TMDB."""
    url = f"{TMDB_BASE_URL}{category}/{tmdb_id}?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

@app.get("/{category}/{tmdb_id}")
def get_movie_data(category: str, tmdb_id: int):
    if category not in ["movie", "tv"]:
        return {"error": "Invalid category"}

    # Get TMDB data
    tmdb_data = get_tmdb_data(category, tmdb_id)
    if not tmdb_data:
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
    uvicorn.run(app, host="0.0.0.0", port=port)