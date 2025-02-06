import requests
from bs4 import BeautifulSoup
import sys

def scrape_metacritic(url):
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/98.0.4758.102 Safari/537.36'),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.google.com'
    }
    session = requests.Session()
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error retrieving URL {url}: {e}")
        return None
    return BeautifulSoup(response.text, 'html.parser')

def get_score(soup, score_type):
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

def parse_page(soup):
    data = {}
    try:
        title_tag = soup.find('h1')
        data['title'] = title_tag.text.strip() if title_tag else 'N/A'
    except Exception:
        data['title'] = 'N/A'

    data['metascore'] = get_score(soup, 'meta')
    data['userscore'] = get_score(soup, 'user')
    
    return data

def main():
    if len(sys.argv) < 3:
        print("Usage: python scraper.py [movie|tv] [slug]")
        sys.exit(1)

    category = sys.argv[1].lower()
    slug = sys.argv[2]

    if category == 'movie':
        base_url = 'https://www.metacritic.com/movie/'
    elif category == 'tv':
        base_url = 'https://www.metacritic.com/tv/'
    else:
        print("Category must be 'movie' or 'tv'.")
        sys.exit(1)

    url = base_url + slug
    print(f"Scraping URL: {url}")

    soup = scrape_metacritic(url)
    if soup is None:
        print("Failed to retrieve the page.")
        sys.exit(1)

    data = parse_page(soup)
    print("\nScraped Data:")
    for key, value in data.items():
        print(f"{key}: {value}")

if __name__ == '__main__':
    main()
