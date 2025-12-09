import requests
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- Configuration ---
BASE_URL = "https://acl.gov/aging-and-disability-in-america/data-and-research/profile-older-americans"
OUTPUT_DIR = "Profile_Older_Americans_Data"

# Adding headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


# --- Helper Function to Create Folders ---
def create_year_folder(year):
    """Creates a folder for the given year and returns the path."""
    folder_path = os.path.join(OUTPUT_DIR, str(year))
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


# --- Helper Function for Downloading Files ---
def download_file(url, folder_path, filename=None):
    """Downloads a file from a URL and saves it to a specified folder."""

    if filename is None:
        filename = url.split('/')[-1]

    if '?' in filename:
        filename = filename.split('?')[0]

    file_path = os.path.join(folder_path, filename)

    try:
        print(f"   -> Downloading: {filename}")

        response = requests.get(url, stream=True, timeout=15, headers=HEADERS)
        response.raise_for_status()

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"   -> Saved successfully to: {folder_path}")

    except requests.exceptions.RequestException as e:
        print(f"   -> **ERROR downloading {filename} from {url}: {e}**")
    except Exception as e:
        print(f"   -> **An unexpected error occurred for {filename}: {e}**")


# --- Main Scraping Function ---
def scrape_acl_data():
    """Fetches the page, finds all yearly files, and downloads them."""

    print(f"Starting data scrape from: {BASE_URL}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        # NOTE: Using HEADERS here for the initial request
        response = requests.get(BASE_URL, timeout=20, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

    except requests.exceptions.RequestException as e:
        # If this still fails, it means the website has more advanced blocking
        print(f"**ERROR accessing the website: {e}. The headers might not have worked.**")
        return

    # --- 1. Scrape the Latest Profile (2023) ---
    # The rest of the logic to find links is the same, but should now work
    print("\n--- Scraping Latest Profile (2023) ---")
    latest_year = 2023
    year_folder = create_year_folder(latest_year)

    latest_links = soup.find_all('a', string=re.compile(r'2023 Profile|Data Tables'))

    for link in latest_links:
        if link.has_attr('href'):
            absolute_url = urljoin(BASE_URL, link['href'])

            link_text = link.get_text(strip=True)
            extension = ""
            if 'pdf' in link_text.lower():
                extension = ".pdf"
            elif 'graphics' in link_text.lower() or '.zip' in absolute_url.lower():
                extension = ".zip"
            elif 'data tables' in link_text.lower() or 'excel' in link_text.lower():
                extension = ".xlsx"

            # Using the actual file type extension
            filename = f"Profile_Older_Americans_{latest_year}{extension}"
            download_file(absolute_url, year_folder, filename=filename)

    # --- 2. Scrape Previous Profiles (The Table) ---
    print("\n--- Scraping Previous Profiles (Table Data) ---")

    table_heading = soup.find('h2', string='Previous Profiles')

    if table_heading:
        profile_table = table_heading.find_next_sibling('table')

        if profile_table:
            for row in profile_table.find_all('tr')[1:]:
                cells = row.find_all(['td', 'th'])
                if not cells: continue

                year_text = cells[0].get_text(strip=True)
                year_match = re.search(r'\b\d{4}\b', year_text)

                if year_match:
                    year = int(year_match.group(0))
                    current_year_folder = create_year_folder(year)
                    print(f"\nProcessing Year: {year}")

                    for cell in cells:
                        link = cell.find('a', href=True)
                        if link:
                            absolute_url = urljoin(BASE_URL, link['href'])
                            link_text = link.get_text(strip=True)

                            if 'data tables' in link_text.lower():
                                filename = f"Data_Tables_{year}.xlsx"
                            elif 'graphics' in link_text.lower() or '.zip' in absolute_url.lower():
                                filename = f"Graphics_{year}.zip"
                            elif 'profile' in link_text.lower():
                                filename = f"Profile_Report_{year}.pdf"
                            else:
                                filename = absolute_url.split('/')[-1]

                            download_file(absolute_url, current_year_folder, filename=filename)
                else:
                    # This happens for the older years (2005-2019) where there are only Data Tables
                    # The link finding is based on the whole table, so we should still find the links.
                    pass  # Let the next loop handle any remaining links
        else:
            print("Could not find the 'Previous Profiles' data table structure.")
    else:
        print("Could not find the 'Previous Profiles' section on the page.")

    print("\n--- Scraping Complete ---")


if __name__ == "__main__":
    scrape_acl_data()