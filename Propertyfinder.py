# ---------------- PROPERTY FINDER SCRAPER ----------------
import re
import time
import requests
from datetime import date, datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from googleapiclient.discovery import build
from sheet_handler import get_credentials, append_property_to_sheet, init_daily_sheet, SPREADSHEET_ID

# ---------------- GOOGLE SHEETS ----------------
creds = get_credentials()
service = build('sheets', 'v4', credentials=creds)
site = 'PF'
init_daily_sheet()

# ---------------- FUNCTIONS ----------------
def extract_number(value):
    """Extract numeric value from strings like '1,234 AED'."""
    if not isinstance(value, str):
        return None
    value = value.replace(',', '').replace('AED', '').replace('$', '').strip()
    match = re.search(r'[\d.]+', value)
    return float(match.group()) if match else None

def get_aed_to_eur_rate():
    """Fetch current AED to EUR conversion rate."""
    try:
        response = requests.get("https://open.er-api.com/v6/latest/AED", timeout=10)
        data = response.json()
        return data.get("rates", {}).get("EUR", None)
    except:
        return None

def get_existing_unit_ids(sheet_tab):
    """Fetch all Unit IDs from the current sheet to avoid duplicates."""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_tab}!A2:A"
        ).execute()
        return {row[0] for row in result.get('values', []) if row}
    except:
        return set()
def propertyfind():
# ---------------- SELENIUM SETUP ----------------
    CHROME_DRIVER_PATH = r"chromedriver-win64/chromedriver.exe"  # <-- Adjust path

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")           # Headless mode
    chrome_options.add_argument("--window-size=1920,1080")  # Needed for rendering
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    service_chrome = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service_chrome, options=chrome_options)
    wait = WebDriverWait(driver, 15)

    # ---------------- SCRAPING START ----------------
    base_url = "https://www.propertyfinder.ae/en/search?c=1&fu=0&ob=nd&page="
    page = 1
    valid_links = []

    while True:
        print(f"\nChecking page {page}")
        driver.get(base_url + str(page))
        time.sleep(3)  # Let JS render

        # Smooth scroll to trigger lazy-loading
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        property_cards = driver.find_elements(By.XPATH, '//article[@data-testid="property-card"]')
        print(f"Found {len(property_cards)} property cards on page {page}")

        page_links = []
        for card in property_cards:
            try:
                date_elements = card.find_elements(By.XPATH, './/p[contains(@class, "publish-info")]')
                if not date_elements:
                    continue
                date_text = date_elements[0].get_attribute("innerText").strip().lower()
                # Only keep listings posted in last 24h
                if "hours ago" in date_text or "minutes ago" in date_text:
                    link_element = card.find_element(By.XPATH, './/a[contains(@class, "property-card__link")]')
                    href = link_element.get_attribute("href")
                    if href:
                        page_links.append(href)
            except:
                continue

        if len(page_links) < 5 or page > 1:  # Stop if almost no new listings
            print(f"No valid listings on page {page}, stopping.")
            break

        valid_links.extend(page_links)
        page += 1
    def num_suffix(n: int) -> str:
        """Return ordinal suffix like 1st, 2nd, 3rd, 4th..."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    # ---------------- FINAL LINK SCRAPING ----------------
    print(f"Total valid links found: {len(valid_links)}")

    for link in valid_links:
        try:
            driver.get(link)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Initialize all fields
            Bedroom_Count = Bathroom_Count = Sqft = Contract_Status = Price_AED = Average_price_per_sqft = Listed_Date = Location = Building_Name = Address = MAP_URL = '-'
            Sqm = Price_EUR = EUR_Sqm = AED_SqFt = Unit_ID = AVER = '-'
            price1 = price2 = price3 = price4 = price5 = price6 = price7 = price8 = price9 = price10 = \
                area_sqft1 = area_sqft2 = area_sqft3 = area_sqft4 = area_sqft5 = area_sqft6 = area_sqft7 = area_sqft8 = area_sqft9 = area_sqft10 = \
                price_per_sqft1 = price_per_sqft2 = price_per_sqft3 = price_per_sqft4 = price_per_sqft5 = price_per_sqft6 = price_per_sqft7 = price_per_sqft8 = price_per_sqft9 = price_per_sqft10 = '-'

            # Extract Unit ID
            match = re.search(r'\d+(?=\.html$)', link)
            if match:
                Unit_ID = match.group()

            # Bedroom count
            try:
                Bedroom_Count_raw = driver.find_element(By.XPATH, '//span[@data-testid="property-attributes-bedrooms"]').text
                Bedroom_Count = extract_number(Bedroom_Count_raw)
            except:
                pass

            # Bathroom count
            try:
                Bathroom_Count_raw = driver.find_element(By.XPATH, '//span[@data-testid="property-attributes-bathrooms"]').text
                Bathroom_Count = extract_number(Bathroom_Count_raw)
            except:
                pass

            # Size (sqft/sqm)
            try:
                size_text = driver.find_element(By.XPATH, '//div[@data-testid="property-attributes-size"]').text
                size_parts = size_text.split('/')
                Sqft = float(size_parts[0].strip().split()[0].replace(',', ''))
                Sqm = float(size_parts[1].strip().split()[0])
            except:
                pass

            # Price in AED and EUR
            try:
                Price_AED_clean = driver.find_element(By.XPATH, '//span[@data-testid="property-price-value"]').text
                Price_AED = float(Price_AED_clean.replace(',', '').strip())
                rate = get_aed_to_eur_rate()
                if rate:
                    Price_EUR = round(Price_AED * rate, 2)
            except:
                pass

            # AED/SqFt & EUR/Sqm
            try:
                if isinstance(Price_AED, float) and isinstance(Sqft, float):
                    AED_SqFt = round(Price_AED / Sqft, 2)
                if isinstance(Price_EUR, float) and isinstance(Sqm, float):
                    EUR_Sqm = round(Price_EUR / Sqm, 2)
            except:
                pass

            # Average price per sqft (optional)
            try:
                Avg_price = driver.find_element(By.XPATH, '(//span[@class="styles_text--bold__jrPK_"])[1]').text
                Avg_Sqft = driver.find_element(By.XPATH, '(//span[@class="styles_text--bold__jrPK_"])[2]').text
                avg_price_num = extract_number(Avg_price)
                avg_sqft_num = extract_number(Avg_Sqft)
                if avg_price_num and avg_sqft_num:
                    Average_price_per_sqft = round(avg_price_num / avg_sqft_num, 2)
            except:
                pass

            # Calculate AVER
            if Average_price_per_sqft and Average_price_per_sqft != 0:
                # AVER = round(AED_SqFt / Average_price_per_sqft, 5)
                AVER = round(AED_SqFt / Average_price_per_sqft, 5)
                AVER = f"{AVER:.5f}"  # Convert to string with dot
                # keeps 5 decimals
            else:
                AVER = "-"

            Listed_Date = date.today().strftime('%Y-%m-%d')
            Crawl_Date = date.today().strftime('%Y-%m-%d')

            # Full location & MAP URL
            fullapartmentname = ''
            try:
                fullapartmentname = driver.find_element(By.XPATH, "//p[@class='styles-module_map__title__M2mBC']").text
                Full_Location = [part.strip() for part in fullapartmentname.split(',')]
                Location = Full_Location[-2] if len(Full_Location) >= 2 else '-'
                Address = ', '.join(Full_Location)
                Building_Name = Full_Location[0]
                formatted_address = fullapartmentname.replace(",", "+").replace(" ", "+")
                MAP_URL = f"https://www.google.com/maps?q={formatted_address}"
            except:
                pass

            TypeH = driver.find_element(By.XPATH, '//p[@data-testid="property-details-type"]').text

            # Contract status
            try:
                driver.find_element(By.XPATH, '//span[contains(text(),"Available from")]')
                Contract_Status = 'Ready'
            except:
                Contract_Status = 'Off-Plan'
            tx_data = {}

            try:
                # Click "See all transactions in this location"
                button = wait.until(EC.presence_of_element_located((
                    By.XPATH, "//a[contains(text(), 'See all transactions in this location')]"
                )))
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                # time.sleep(1)
                driver.execute_script("""
                    let f = document.querySelector('footer');
                    if (f) f.style.display = 'none';
                    let s = document.querySelector('.sticky, .fixed, .floating, .banner');
                    if (s) s.style.display = 'none';
                """)
                driver.execute_script("arguments[0].click();", button)
                # print("Clicked successfully.")

                try:
                    dropdown_button = wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[data-testid='transaction-history-sort']")
                    ))
                    dropdown_button.click()
                    time.sleep(1)
                    Oldest_option = wait.until(EC.visibility_of_element_located(
                        (By.XPATH, "//button[contains(@class, 'styles-module_dropdown-content__item') and contains(text(), 'Oldest')]")
                    ))
                    Oldest_option.click()

                    # Wait until table rows appear
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tbody tr"))
                    )

                    # Select all rows
                    rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")

                    # Lists to store results
                    sold_for_aed = []
                    sold_per_sqft = []

                    for row in rows:
                        columns = row.find_elements(By.TAG_NAME, "td")
                        if len(columns) >= 3:
                            sold_for_aed.append(columns[1].text.strip().replace(",", "").replace("AED", "").strip())
                            sold_per_sqft.append(columns[2].text.strip().replace(",", "").strip())

                    # print("Sold for (AED):", sold_for_aed)
                    # print("Sold for (AED per sqft):", sold_per_sqft)

                    # If both lists have less than 10 items, assign variables
                    for i in range(1, 11):
                        if i <= len(sold_for_aed):
                            sold_price = float(sold_for_aed[i - 1])
                            price_sqft = float(sold_per_sqft[i - 1])
                            total_area = round(sold_price / price_sqft, 2)
                        else:
                            sold_price = price_sqft = total_area = "-"

                        tx_data[f'price{i}'] = sold_price
                        tx_data[f'price_per_sqft{i}'] = price_sqft
                        tx_data[f'area_sqft{i}'] = total_area


                except Exception as e:
                    print("Error:", e)


            except Exception as e:
                for i in range(1, 11):
                    sold_price = price_sqft = total_area = "-"
                    tx_data[f'price{i}'] = sold_price
                    tx_data[f'price_per_sqft{i}'] = price_sqft
                    tx_data[f'area_sqft{i}'] = total_area

            # Prepare data row
            data_to_insert = {
                "Unit ID": f"PF+{Unit_ID}",
                "URL": link,
                "MAP URL": MAP_URL,
                "Crawl Date": Crawl_Date,
                "Listed Date": Listed_Date,
                "Location": Location,
                "Building Name": Building_Name,
                "Address": Address,
                "Price AED": Price_AED,
                "Price EUR": Price_EUR,
                "BD": Bedroom_Count,
                "Bathr.": Bathroom_Count,
                "Sqft": Sqft,
                "Sqm": Sqm,
                "AED/SqFt": AED_SqFt,
                "EUR/Sqm": EUR_Sqm,
                "Contract Status": Contract_Status,
                "Avrg. price/sqft Last 10-30": Average_price_per_sqft,
                "AVER./": AVER,
                "1st sold AED": price1,
                "1st sold Sqft": area_sqft1,
                "1st sold AED_Sqft": price_per_sqft1,
                "2nd sold AED": price2,
                "2nd sold Sqft": area_sqft2,
                "2nd sold AED_Sqft": price_per_sqft2,
                "3rd sold AED": price3,
                "3rd sold Sqft": area_sqft3,
                "3rd sold AED_Sqft": price_per_sqft3,
                "4th sold AED": price4,
                "4th sold Sqft": area_sqft4,
                "4th sold AED_Sqft": price_per_sqft4,
                "5th sold AED": price5,
                "5th sold Sqft": area_sqft5,
                "5th sold AED_Sqft": price_per_sqft5,
                "6th sold AED": price6,
                "6th sold Sqft": area_sqft6,
                "6th sold AED_Sqft": price_per_sqft6,
                "7th sold AED": price7,
                "7th sold Sqft": area_sqft7,
                "7th sold AED_Sqft": price_per_sqft7,
                "8th sold AED": price8,
                "8th sold Sqft": area_sqft8,
                "8th sold AED_Sqft": price_per_sqft8,
                "9th sold AED": price9,
                "9th sold Sqft": area_sqft9,
                "9th sold AED_Sqft": price_per_sqft9,
                "10th sold AED": price10,
                "10th sold Sqft": area_sqft10,
                "10th sold AED_Sqft": price_per_sqft10
            }
            try:
                append_property_to_sheet(service, data_to_insert, fullapartmentname, TypeH, site)
                print(f"Inserted: PF+{Unit_ID}")
                # break
            except Exception as e:
                print(e)
                break

        except Exception as e:
            print(f"Error processing {link}: {e}")
            continue

    driver.quit()
    print("PA Scraping completed successfully!")
