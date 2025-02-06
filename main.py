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

    title_slug = tmdb_data.get("title", tmdb_data.get("name", "")).lower().replace(" ", "-")
    metacritic_url = f"https://www.metacritic.com/{category}/{title_slug}"
    
    # Get Metacritic scores
    metacritic_data = scrape_metacritic(metacritic_url)

    return {
        "tmdb": tmdb_data,
        "metacritic": metacritic_data
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))  # Use Railway's PORT or default to 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
