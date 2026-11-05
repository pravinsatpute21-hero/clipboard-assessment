import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

BASE_URL = "https://analyst-assessment-production.up.railway.app"


def scrape_community_detail(url):
    """Scrape individual community page for full details"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    data = {
        'name': '',
        'street': '',
        'city': '',
        'state': '',
        'zip': '',
        'care_offerings': '',
        'administrator': '',
        'phone': '',
        'url': url
    }

    # Name
    h1 = soup.find('h1')
    if h1:
        data['name'] = h1.text.strip()

    # Get all text lines cleanly
    wrap = soup.find('div', class_='wrap')
    if not wrap:
        wrap = soup

    # Find all dt/dd pairs (label/value)
    dts = wrap.find_all('dt')
    dds = wrap.find_all('dd')

    if dts and dds:
        for dt, dd in zip(dts, dds):
            label = dt.text.strip().upper()
            value = dd.text.strip()

            if 'ADDRESS' in label:
                # Parse address lines
                lines = [l.strip() for l in dd.get_text('\n').split('\n') if l.strip()]
                if len(lines) >= 1:
                    data['street'] = lines[0]
                if len(lines) >= 2:
                    # Parse "City, ST 12345"
                    city_line = lines[1]
                    parts = city_line.split(',')
                    if len(parts) >= 2:
                        data['city'] = parts[0].strip()
                        state_zip = parts[1].strip().split(' ')
                        if len(state_zip) >= 1:
                            data['state'] = state_zip[0].strip()
                        if len(state_zip) >= 2:
                            data['zip'] = state_zip[1].strip()

            elif 'CARE' in label:
                badges = dd.find_all(class_='badge')
                if badges:
                    data['care_offerings'] = ', '.join([b.text.strip() for b in badges])
                else:
                    data['care_offerings'] = value

            elif 'ADMIN' in label:
                data['administrator'] = value

            elif 'PHONE' in label:
                data['phone'] = value

    else:
        # Fallback - parse by text sections
        text = wrap.get_text(separator='\n')
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        for i, line in enumerate(lines):
            upper = line.upper()
            if upper == 'ADDRESS' and i + 2 < len(lines):
                data['street'] = lines[i + 1]
                city_line = lines[i + 2]
                parts = city_line.split(',')
                if len(parts) >= 2:
                    data['city'] = parts[0].strip()
                    state_zip = parts[1].strip().split(' ')
                    if len(state_zip) >= 1:
                        data['state'] = state_zip[0].strip()
                    if len(state_zip) >= 2:
                        data['zip'] = state_zip[1].strip()

            elif upper == 'CARE OFFERINGS' and i + 1 < len(lines):
                care = []
                j = i + 1
                while j < len(lines) and lines[j].upper() not in ['ADMINISTRATOR', 'PHONE', 'ADDRESS']:
                    care.append(lines[j])
                    j += 1
                data['care_offerings'] = ', '.join(care)

            elif upper == 'ADMINISTRATOR' and i + 1 < len(lines):
                data['administrator'] = lines[i + 1]

            elif upper == 'PHONE' and i + 1 < len(lines):
                data['phone'] = lines[i + 1]

    return data


def scrape_all_communities():
    """Scrape all pages and get every community"""
    all_communities = []

    page = 1
    while True:
        print(f"Scraping page {page}...")
        url = f"{BASE_URL}/communities?page={page}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all community links
        links = soup.find_all('a', href=lambda h: h and '/communities/' in h)

        if not links:
            print(f"No more communities on page {page}")
            break

        for link in links:
            community_url = BASE_URL + link['href']
            print(f"  Scraping: {link.text.strip()}")
            detail = scrape_community_detail(community_url)
            all_communities.append(detail)
            time.sleep(0.3)

        # Check next page
        next_button = soup.find('a', string=lambda t: t and 'Next' in str(t))
        if not next_button:
            break
        page += 1

    return all_communities


if __name__ == "__main__":
    print("Starting scraper...")
    communities = scrape_all_communities()

    df = pd.DataFrame(communities)
    df.to_csv('website_communities.csv', index=False)

    print(f"\nDone! Scraped {len(communities)} communities")
    print(df[['name', 'city', 'state', 'zip', 'care_offerings']].to_string())