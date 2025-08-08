import pandas as pd
from math import ceil
from datetime import datetime,date
from selenium import webdriver
import os
import time
import socket
import shutil
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sheet_handler import get_credentials


# --- Config ---
SPREADSHEET_ID = '1Plw03aIqzMHWzDO48KG-AjOmnOkebjeX4Wdau7nFOeE'
SHEET_NAME = 'Worksheet 1'
TARGET_URL = 'https://www.dubaipulse.gov.ae/data/dld-transactions/dld_transactions-open'

# --- Selenium: extract update date ---
options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

driver.get(TARGET_URL)
time.sleep(2)  # let the page render JS

date_text = driver.find_element(By.XPATH, '(//div[@class="update-date"])[2]').text
driver.quit()
print(date_text)
web_date=None
# Parse 'Updated: DD Mon YYYY'
for line in date_text.split('\n'):
    if "Updated:" in line:
        date_part = line.split("Updated:")[1].strip().split(" File Size")[0].strip()
        web_date = datetime.strptime(date_part, "%d %b %Y").date()
        break


# --- Sheets API: compare and update ---
creds = get_credentials()
sheet = build('sheets', 'v4', credentials=creds)
drive = build('drive', 'v3', credentials=creds)

# Read A2:C2
row = sheet.spreadsheets().values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=f"{SHEET_NAME}!A2:C2"
).execute().get('values', [])[0]

sheet_date = datetime.strptime(row[0], "%d %b. %Y").date()

if sheet_date >= web_date:
    print(" Sheet is up-to-date.")
else:
    print(" Outdated. Deleting sheet IDs and updating date...")

    # Delete the sheets (IDs in B2 and C2)
    for sid in row[1:3]:
        if sid:
            try:
                drive.files().delete(fileId=sid).execute()
                print(f" Deleted file: {sid}")
            except Exception as e:
                print(f" Could not delete {sid}: {e}")

    # Update A2 with new date, clear B2 and C2
    new_row = [[web_date.strftime("%d %b. %Y")]]

# ===================== CONFIG =====================
    base_dir = r"C:\Users\shubh\Downloads"
    spreadsheet_title = "Transactions_NULL_Rents"
    chunk_size = 140_000                   # rows per API append
    max_rows_per_sheet = 900_000           # safe for Google Sheets
    max_cells_per_spreadsheet = 10_000_000 # Google Sheets hard limit

    keep_cols = [
        'transaction_id',
        'instance_date',
        'area_name_en',
        'building_name_en',
        'project_name_en',
        'master_project_en',
        'nearest_landmark_en',
        'procedure_area',
        'actual_worth',
        'meter_sale_price'
    ]

    # ===================== HELPER: RETRY API =====================
    def retry_api(fn, **kwargs):
        """Call fn(**kwargs), retrying on timeout or 5xx HttpError up to 3 times."""
        backoff = 1
        for attempt in range(3):
            try:
                return fn(**kwargs).execute()
            except (HttpError, socket.timeout) as e:
                code = getattr(e, 'status_code', None)
                if isinstance(e, socket.timeout) or (code and 500 <= code < 600):
                    print(f" API error {e}, retrying in {backoff}s… (attempt {attempt+1}/3)")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise
        return fn(**kwargs).execute()

    # ===================== STEP 1: DOWNLOAD FILE =====================
    run_folder = os.path.join(base_dir, "DubaiPulse_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(run_folder, exist_ok=True)

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": run_folder,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": run_folder
    })

    driver.get("https://www.dubaipulse.gov.ae/data/dld-transactions/dld_transactions-open")
    try:
        btn = driver.find_element(By.XPATH, '//span[@class="dubainow-download action-icon-span"]')
        btn.click()
        print("Download started…")
    except Exception as e:
        print("Click error:", e)
        driver.quit()
        exit(1)

    print(f"Waiting for downloaded file in: {run_folder}")
    start = time.time()
    max_wait = 1500  # seconds
    downloaded = None

    while True:
        all_files = os.listdir(run_folder)
        finished = [
            f for f in all_files
            if not f.endswith((".crdownload", ".part")) and os.path.isfile(os.path.join(run_folder, f))
        ]
        if finished:
            downloaded = finished[0]
            print(f"Download complete: {downloaded}")
            break

        if time.time() - start > max_wait:
            print("Timeout: No file detected.")
            driver.quit()
            exit(1)

        time.sleep(1)

    driver.quit()

    input_csv = os.path.join(run_folder, downloaded)
    print(f"Saved to: {input_csv} ({os.path.getsize(input_csv)/(1024*1024):.2f} MB)")

    # ===================== STEP 2: GOOGLE SHEETS AUTH =====================
    creds = Credentials.from_authorized_user_file(
        'token.json',
        ['https://www.googleapis.com/auth/spreadsheets']
    )
    sheet_service = build('sheets', 'v4', credentials=creds)

    # ===================== STEP 3: PROCESS CSV =====================
    filtered_chunks = []
    last_10_years = pd.Timestamp.today() - pd.DateOffset(years=10)

    for chunk in pd.read_csv(input_csv, chunksize=100_000, dtype=str):
        chunk = chunk.map(lambda x: x.strip() if isinstance(x, str) else x)
        if 'rent_value' not in chunk.columns or 'meter_rent_price' not in chunk.columns:
            raise KeyError("Columns 'rent_value' and/or 'meter_rent_price' not found in CSV.")
        chunk['rent_value'] = chunk['rent_value'].fillna('null').str.lower()
        chunk['meter_rent_price'] = chunk['meter_rent_price'].fillna('null').str.lower()
        chunk = chunk[(chunk['rent_value'] == 'null') & (chunk['meter_rent_price'] == 'null')]
        chunk = chunk[keep_cols]
        chunk['instance_date'] = pd.to_datetime(chunk['instance_date'], errors='coerce', dayfirst=True)
        chunk = chunk.dropna(subset=['instance_date'])
        chunk = chunk[chunk['instance_date'] >= last_10_years]
        filtered_chunks.append(chunk)

    if not filtered_chunks:
        print("Filtered rows: 0")
        exit()

    df = pd.concat(filtered_chunks)
    df = df.sort_values(by='instance_date', ascending=False)
    df['instance_date'] = df['instance_date'].dt.strftime('%Y-%m-%d')
    df = df.fillna("")
    print(f"Filtered rows (last 10 years, rent null): {len(df)}")

    # ===================== STEP 4: SPLIT AND UPLOAD =====================
    num_columns = len(df.columns)
    rows_per_spreadsheet = min(max_cells_per_spreadsheet // num_columns, max_rows_per_sheet)
    num_spreadsheets = ceil(len(df) / rows_per_spreadsheet)
    print(f"Data will be split into {num_spreadsheets} spreadsheets (max {rows_per_spreadsheet} rows each)")

    start_index = 0
    for file_idx in range(1, num_spreadsheets + 1):
        part_df = df.iloc[start_index:start_index + rows_per_spreadsheet]
        start_index += rows_per_spreadsheet

        Date_Raw = date.today().strftime('%Y%m%d')
        spreadsheet_name = f"{spreadsheet_title}_Part{file_idx}{Date_Raw}"
        resp = retry_api(
            sheet_service.spreadsheets().create,
            body={'properties': {'title': spreadsheet_name}},
            fields='spreadsheetId'
        )
        spreadsheet_id = resp.get('spreadsheetId')
        print(f"Created Spreadsheet: {spreadsheet_name} ({spreadsheet_id})")
        new_row[0].append(f"{spreadsheet_id}")
        # DELETE DEFAULT SHEET
        meta = retry_api(sheet_service.spreadsheets().get, spreadsheetId=spreadsheet_id)
        default_sheet_id = meta['sheets'][0]['properties']['sheetId']
        retry_api(
            sheet_service.spreadsheets().batchUpdate,
            spreadsheetId=spreadsheet_id,
            body={"requests":[{"updateSheetProperties":{"properties":{"sheetId":default_sheet_id,"title":"TempSheet"},"fields":"title"}}]}
        )

        # ADD FIRST DATA SHEET
        add_resp = retry_api(
            sheet_service.spreadsheets().batchUpdate,
            spreadsheetId=spreadsheet_id,
            body={"requests":[{"addSheet":{"properties":{"title":"Sheet1"}}}]}
        )
        current_sheet_id = add_resp['replies'][0]['addSheet']['properties']['sheetId']

        # DELETE TempSheet
        retry_api(
            sheet_service.spreadsheets().batchUpdate,
            spreadsheetId=spreadsheet_id,
            body={"requests":[{"deleteSheet":{"sheetId":default_sheet_id}}]}
        )

        # DELETE EXTRA COLUMNS
        retry_api(
            sheet_service.spreadsheets().batchUpdate,
            spreadsheetId=spreadsheet_id,
            body={"requests":[{"deleteDimension":{"range":{"sheetId":current_sheet_id,"dimension":"COLUMNS","startIndex":num_columns,"endIndex":26}}}]}
        )

        # UPLOAD DATA
        row_counter = 0
        header = [part_df.columns.tolist()]
        current_sheet_name = 'Sheet1'

        for idx in range(0, len(part_df), chunk_size):
            chunk = part_df.iloc[idx:idx+chunk_size]
            values = chunk.values.tolist()

            if row_counter + len(values) + 1 > max_rows_per_sheet:
                current_index = int(current_sheet_name.replace('Sheet','')) + 1
                current_sheet_name = f"Sheet{current_index}"
                add_resp = retry_api(
                    sheet_service.spreadsheets().batchUpdate,
                    spreadsheetId=spreadsheet_id,
                    body={"requests":[{"addSheet":{"properties":{"title":current_sheet_name}}}]}
                )
                current_sheet_id = add_resp['replies'][0]['addSheet']['properties']['sheetId']
                row_counter = 0
                header_needed = True
            else:
                header_needed = row_counter == 0

            batch_values = header + values if header_needed else values
            retry_api(
                sheet_service.spreadsheets().values().append,
                spreadsheetId=spreadsheet_id,
                range=current_sheet_name,
                valueInputOption='RAW',
                body={'values': batch_values}
            )
            row_counter += len(values)
            print(f"Uploaded {len(values)} rows to {current_sheet_name} in {spreadsheet_name}")

    print("Upload completed with retry logic!")
    sheet.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="A2:C2",
        valueInputOption="USER_ENTERED",
        body={"values": new_row}
    ).execute()
    print(" Sheet updated.")
    # ===================== STEP 5: CLEANUP =====================
    print("Cleaning up downloaded files…")
    shutil.rmtree(run_folder)
    print("All files deleted. Process complete.")











#
# import pandas as pd
# from math import ceil
# from datetime import datetime, timedelta
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# import socket
# import time
# from datetime import date
# # ======== CONFIG ========
# input_csv = r'C:\Users\shubh\Downloads\Transactions.csv'
# spreadsheet_title = "Transactions_NULL_Rents"
# chunk_size = 140000                   # rows per API append
# max_rows_per_sheet = 900_000        # safe for Google Sheets
# max_cells_per_spreadsheet = 10_000_000  # Google Sheets hard limit
#
# # Columns to keep
# keep_cols = [
#     'transaction_id',
#     'instance_date',
#     'area_name_en',
#     'building_name_en',
#     'project_name_en',
#     'master_project_en',
#     'nearest_landmark_en',
#     'procedure_area',
#     'actual_worth',
#     'meter_sale_price'
# ]
#
# # ======== HELPER: RETRY LOGIC ========
# def retry_api(fn, **kwargs):
#     """Call fn(**kwargs), retrying on timeout or 5xx HttpError up to 3 times."""
#     backoff = 1
#     for attempt in range(3):
#         try:
#             return fn(**kwargs).execute()
#         except (HttpError, socket.timeout) as e:
#             code = getattr(e, 'status_code', None)
#             if isinstance(e, socket.timeout) or (code and 500 <= code < 600):
#                 print(f"⚠️ API error {e}, retrying in {backoff}s… (attempt {attempt+1}/3)")
#                 time.sleep(backoff)
#                 backoff *= 2
#                 continue
#             raise
#     return fn(**kwargs).execute()
#
# # ======== AUTH ========
# creds = Credentials.from_authorized_user_file(
#     'token.json',
#     ['https://www.googleapis.com/auth/spreadsheets']
# )
# sheet_service = build('sheets', 'v4', credentials=creds)
#
# # ======== FILTER CSV ========
# filtered_chunks = []
# last_10_years = pd.Timestamp.today() - pd.DateOffset(years=10)
#
# for chunk in pd.read_csv(input_csv, chunksize=100_000, dtype=str):
#     chunk = chunk.map(lambda x: x.strip() if isinstance(x, str) else x)
#     if 'rent_value' not in chunk.columns or 'meter_rent_price' not in chunk.columns:
#         raise KeyError("Columns 'rent_value' and/or 'meter_rent_price' not found in CSV.")
#     chunk['rent_value'] = chunk['rent_value'].fillna('null').str.lower()
#     chunk['meter_rent_price'] = chunk['meter_rent_price'].fillna('null').str.lower()
#     chunk = chunk[(chunk['rent_value'] == 'null') & (chunk['meter_rent_price'] == 'null')]
#     chunk = chunk[keep_cols]
#     chunk['instance_date'] = pd.to_datetime(chunk['instance_date'], errors='coerce', dayfirst=True)
#     chunk = chunk.dropna(subset=['instance_date'])
#     chunk = chunk[chunk['instance_date'] >= last_10_years]
#     filtered_chunks.append(chunk)
#
# if not filtered_chunks:
#     print("Filtered rows: 0")
#     exit()
#
# df = pd.concat(filtered_chunks)
# df = df.sort_values(by='instance_date', ascending=False)
# df['instance_date'] = df['instance_date'].dt.strftime('%Y-%m-%d')
# df = df.fillna("")
# print(f"Filtered rows (last 10 years, rent null): {len(df)}")
#
# # ======== CALCULATE SPLITS ========
# num_columns = len(df.columns)
# # limit rows per spreadsheet to stay below both cell and row limits
# rows_per_spreadsheet = min(max_cells_per_spreadsheet // num_columns, max_rows_per_sheet)
# num_spreadsheets = ceil(len(df) / rows_per_spreadsheet)
# print(f"Data will be split into {num_spreadsheets} spreadsheets (max {rows_per_spreadsheet} rows each)")
#
# start_index = 0
# for file_idx in range(1, num_spreadsheets + 1):
#     part_df = df.iloc[start_index:start_index + rows_per_spreadsheet]
#     start_index += rows_per_spreadsheet
#
#     # CREATE SPREADSHEET
#     Date_Raw = date.today().strftime('%Y%m%d')
#     spreadsheet_name = f"{spreadsheet_title}_Part{file_idx}"
#     resp = retry_api(
#         sheet_service.spreadsheets().create,
#         body={'properties': {'title': f'{spreadsheet_name}{Date_Raw}'}},
#         fields='spreadsheetId'
#     )
#     spreadsheet_id = resp.get('spreadsheetId')
#     print(f"✅ Created Spreadsheet: {spreadsheet_name} ({spreadsheet_id})")
#
#     # DELETE DEFAULT SHEET
#     meta = retry_api(sheet_service.spreadsheets().get, spreadsheetId=spreadsheet_id)
#     default_sheet_id = meta['sheets'][0]['properties']['sheetId']
#     retry_api(
#         sheet_service.spreadsheets().batchUpdate,
#         spreadsheetId=spreadsheet_id,
#         body={"requests":[{"updateSheetProperties":{"properties":{"sheetId":default_sheet_id,"title":"TempSheet"},"fields":"title"}}]}
#     )
#
#     # ADD FIRST DATA SHEET
#     add_resp = retry_api(
#         sheet_service.spreadsheets().batchUpdate,
#         spreadsheetId=spreadsheet_id,
#         body={"requests":[{"addSheet":{"properties":{"title":"Sheet1"}}}]}
#     )
#     current_sheet_id = add_resp['replies'][0]['addSheet']['properties']['sheetId']
#
#     # DELETE TempSheet
#     retry_api(
#         sheet_service.spreadsheets().batchUpdate,
#         spreadsheetId=spreadsheet_id,
#         body={"requests":[{"deleteSheet":{"sheetId":default_sheet_id}}]}
#     )
#
#     # DELETE EXTRA COLUMNS (use current_sheet_id, not default)
#     retry_api(
#         sheet_service.spreadsheets().batchUpdate,
#         spreadsheetId=spreadsheet_id,
#         body={"requests":[{"deleteDimension":{"range":{"sheetId":current_sheet_id,"dimension":"COLUMNS","startIndex":num_columns,"endIndex":26}}}]}
#     )
#
#     # UPLOAD DATA
#     row_counter = 0
#     header = [part_df.columns.tolist()]
#     current_sheet_name = 'Sheet1'
#
#     for idx in range(0, len(part_df), chunk_size):
#         chunk = part_df.iloc[idx:idx+chunk_size]
#         values = chunk.values.tolist()
#
#         if row_counter + len(values) + 1 > max_rows_per_sheet:
#             current_index = int(current_sheet_name.replace('Sheet','')) + 1
#             current_sheet_name = f"Sheet{current_index}"
#             add_resp = retry_api(
#                 sheet_service.spreadsheets().batchUpdate,
#                 spreadsheetId=spreadsheet_id,
#                 body={"requests":[{"addSheet":{"properties":{"title":current_sheet_name}}}]}            )
#             current_sheet_id = add_resp['replies'][0]['addSheet']['properties']['sheetId']
#             row_counter = 0
#             header_needed = True
#         else:
#             header_needed = row_counter == 0
#
#         batch_values = header + values if header_needed else values
#         retry_api(
#             sheet_service.spreadsheets().values().append,
#             spreadsheetId=spreadsheet_id,
#             range=current_sheet_name,
#             valueInputOption='RAW',
#             body={'values': batch_values}
#         )
#         row_counter += len(values)
#         print(f"Uploaded {len(values)} rows to {current_sheet_name} in {spreadsheet_name}")
#
# print("🎉 Upload completed with retry logic!")
