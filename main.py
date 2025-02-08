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
                # If we tried the URL with the year, now try the base URL without it
                if url == url_with_year:
                    response = requests.get(base_url, headers=HEADERS, timeout=10)
                response.raise_for_status()

            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract Scores
            critic_score = soup.select_one('rt-text[slot="criticsScore"]')
            audience_score = soup.select_one('rt-text[slot="audienceScore"]')

            # Extract Certified Fresh Status
            critic_certified = bool(soup.select_one("score-icon-critics[certified='true']"))
            audience_certified = bool(soup.select_one("score-icon-audience[certified='true']"))

            # Log the correct URL
            print(f"Successfully fetched Rotten Tomatoes data from: {url}")  # Console log

            return {
                "critic_score": critic_score.text.strip() if critic_score else "N/A",
                "audience_score": audience_score.text.strip() if audience_score else "N/A",
                "critic_certified_fresh": critic_certified,
                "audience_certified_fresh": audience_certified,
                "rotten_tomatoes_url": url  # Correct URL based on what was fetched
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
