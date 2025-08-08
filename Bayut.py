from googleapiclient.discovery import build
from sheet_handler import get_credentials, init_daily_sheet, append_property_to_sheet
from selenium.webdriver.common.by import By
from datetime import datetime
import time
from selenium import webdriver
import re
import requests
from datetime import date
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

creds = get_credentials()
service = build('sheets', 'v4', credentials=creds)
site='BA'
init_daily_sheet()
def extract_number(value):
    value = value.replace(',', '') if isinstance(value, str) else ''
    match = re.search(r'\d+', value)
    return int(match.group()) if match else None

def is_recent(date_text):
    try:
        date_obj = datetime.strptime(date_text, "%d %B %Y").date()
        return (datetime.today().date() - date_obj).days <= 0
    except:
        return False


def get_listing_date(driver):
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[@class='_2fdf7fc5' and @aria-label='Reactivated date']"))
        )
        return element.text.strip()
    except:
        return None

def get_aed_to_eur_rate():
    try:
        response = requests.get("https://open.er-api.com/v6/latest/AED")
        data = response.json()
        # print("Exchange API response:", data)
        return data["rates"]["EUR"]
    except:
        pass

# options = uc.ChromeOptions()
# options.headless = True
# options.add_argument("--headless=new")
# driver = uc.Chrome(options=options)



def bayutfind():
    CHROME_DRIVER_PATH = r"D:\Data Automation\chromedriver-win64\chromedriver.exe"  # <-- Adjust path

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
    wait = WebDriverWait(driver, 10)

    page = 1
    keep_scraping = True


    while keep_scraping:
        if page == 1:
            url = "https://www.bayut.com/for-sale/apartments/uae/?categories=villas&sort=date_desc"
        else:
            url = f"https://www.bayut.com/for-sale/apartments/uae/page-{page}/?categories=villas&sort=date_desc"

        driver.get(url)

        pause_time = 2
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        items = driver.find_elements(By.XPATH, "//li[@role='article']")
        links = []
        for item in items:
            try:
                a = item.find_element(By.XPATH, ".//a[@aria-label='Listing link'][1]")
                href = a.get_attribute("href")
                if href and href not in links:
                    links.append(href)
            except:
                pass

        for link in links[:3]:
            try:
                driver.get(link)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                date_text = get_listing_date(driver)
                Unit_ID = extract_number(link) or '-'
                if date_text:
                    if not is_recent(date_text):
                        keep_scraping = False
                        break
                    else:
                        Bedroom_Count = Bathroom_Count = Sqft = Contract_Status = Price_AED = Average_price_per_sqft = Listed_Date = Location = Building_Name = Address = MAP_URL = '-'
                        Sqm = Price_EUR = EUR_Sqm = AED_SqFt = Unit_ID = '-'
                        price1 = price2 = price3 = price4 = price5 = price6 = price7 = price8 = price9 = price10 = \
                            area_sqft1 = area_sqft2 = area_sqft3 = area_sqft4 = area_sqft5 = area_sqft6 = area_sqft7 = area_sqft8 = area_sqft9 = area_sqft10 = \
                            price_per_sqft1 = price_per_sqft2 = price_per_sqft3 = price_per_sqft4 = price_per_sqft5 = price_per_sqft6 = price_per_sqft7 = price_per_sqft8 = price_per_sqft9 = price_per_sqft10 = '-'

                        try:
                            Bedroom_Count_raw = driver.find_element(By.XPATH, '//span[contains(text(),"Bed")]').text
                            Bedroom_Count = extract_number(Bedroom_Count_raw) or '-'
                        except:
                            Bedroom_Count='1'

                        try:
                            Bathroom_Count_raw = driver.find_element(By.XPATH, '//span[contains(text(),"Bath")]').text
                            Bathroom_Count = extract_number(Bathroom_Count_raw) or '-'
                        except:
                            Bathroom_Count='1'

                        try:
                            Sqft_raw = driver.find_element(By.XPATH, '(//span[contains(text(),"sqft")])[1]').text
                            Sqft = extract_number(Sqft_raw) or '-'
                            Sqm = round(Sqft * 0.092903, 2) if Sqft != '-' else '-'
                        except:
                            pass

                        try:
                            Contract_Status = driver.find_element(By.XPATH, '//span[@aria-label="Completion status"]').text
                        except:
                            pass

                        try:
                            Price_AED_clean = driver.find_element(By.XPATH, '(//span[@aria-label="Price"])[1]').text
                            Price_AED = float(Price_AED_clean.replace(',', '').strip())
                            rate = get_aed_to_eur_rate()
                            Price_EUR = round(Price_AED * rate, 2) if rate else '-'
                        except:
                            pass

                        try:
                            AED_SqFt = round(Price_AED / Sqft, 2) if Price_AED != '-' and Sqft != '-' else '-'
                        except:
                            pass

                        try:
                            EUR_Sqm = round(Price_EUR / Sqm, 2) if Price_EUR != '-' and Sqm != '-' else '-'
                        except:
                            pass

                        try:
                            WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located(
                                    (By.XPATH,
                                     "//*[local-name()='g'][contains(@class, 'ct-series')]/*[local-name()='line' and contains(@class,'ct-bar')]")
                                )
                            )
                            line_elements = driver.find_elements(
                                By.XPATH,
                                "//*[local-name()='g'][contains(@class, 'ct-series')]/*[local-name()='line' and contains(@class,'ct-bar')]"
                            )
                            Average_price_per_sqft = line_elements[-1].get_attribute("ct:value") if line_elements else '-'
                            # print('Average_price_per_sqft',Average_price_per_sqft)
                        except:
                            Average_price_per_sqft = '-'

                        try:
                            Listed_Date = driver.find_element(By.XPATH, '//span[@aria-label="Reactivated date"]').text
                        except:
                            pass

                        Crawl_Date = date.today().strftime('%Y-%m-%d')

                        fullapartmentname=''
                        try:
                            fullapartmentname = driver.find_element(By.XPATH, "//div[@aria-label='Property header']").text
                            Full_Location = [part.strip() for part in fullapartmentname.split(',')]
                            Location = Full_Location[-2] if len(Full_Location) >= 2 else '-'
                            AddressC = Full_Location[1:]
                            Address = ', '.join(AddressC)
                            Building_Name = Full_Location[0]
                            formatted_address = fullapartmentname.replace(",", "+").replace(" ", "+")
                            MAP_URL = f"https://www.google.com/maps?q={formatted_address}"
                        except:
                            pass

                        Unit_ID = extract_number(link) or '-'

                        original_tab = driver.current_window_handle
                        try:
                            element = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH,
                                                            "//a[contains(@href, 'property-market-analysis') and contains(text(),'View sale transactions')]"))
                            )
                            original_tab = driver.current_window_handle
                            element.click()
                            time.sleep(2)
                            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
                            driver.switch_to.window(driver.window_handles[-1])
                            time.sleep(2)
                            time.sleep(5)
                            rows = driver.find_elements(By.XPATH, "//tr[@aria-label='Listing']")
                            last_rows = rows[-10:][::-1]

                            for i in range(10):
                                if i < len(last_rows):
                                    try:
                                        row = last_rows[i]
                                        price_text = row.find_element(By.XPATH,
                                                                      ".//span[@aria-label='Price']").text.strip().replace(",", "")
                                        area_text = row.find_element(By.XPATH,
                                                                     ".//div[@aria-label='Build Up Area']").text.strip().replace(",", "")
                                        price = float(price_text)
                                        area = float(area_text)
                                        price_val = str(int(price))
                                        area_val = str(int(area))
                                        price_per_sqft = str(round(price / area, 2)) if area != 0 else '-'
                                    except:
                                        price_val, area_val, price_per_sqft = '-', '-', '-'
                                else:
                                    price_val, area_val, price_per_sqft = '-', '-', '-'

                                globals()[f"price{i + 1}"] = price_val
                                globals()[f"area_sqft{i + 1}"] = area_val
                                globals()[f"price_per_sqft{i + 1}"] = price_per_sqft

                            driver.close()
                            driver.switch_to.window(original_tab)
                            time.sleep(1)
                        except:
                            for i in range(1, 11):
                                globals()[f"price{i + 1}"] = '-'
                                globals()[f"area_sqft{i + 1}"] = '-'
                                globals()[f"price_per_sqft{i + 1}"] = '-'
                        # Calculate AVER
                        if Average_price_per_sqft and Average_price_per_sqft != "0":
                            try:
                                avg_price = float(Average_price_per_sqft)
                                AVER = round(AED_SqFt / avg_price, 5)
                                AVER = f"{AVER:.5f}"  # Convert to string with dot
                            except (ValueError, TypeError):
                                AVER = "-"
                        else:
                            AVER = "-"

                        # print(AVER,Average_price_per_sqft,AED_SqFt)
                        TypeH = driver.find_element(By.XPATH, '//span[ @ aria-label="Type"]').text
                        data_to_insert = {
                                        "Unit ID": f'BA+{Unit_ID}',
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
                                        "EUR/Sqm":EUR_Sqm,
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
                            print(f"Inserted: BA+{Unit_ID}")
                        except Exception as e:
                            print(e)
                time.sleep(1)
            except Exception as e:
                print(e)
                continue

        if keep_scraping:
            page += 1

    driver.quit()
    print("BA Scraping completed successfully!")