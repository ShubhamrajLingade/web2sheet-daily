from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import date
import os

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_BASE_NAME = 'Property Data Sheet'
SPREADSHEET_ID = None

def get_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('Cred_Client_SHEET.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def init_daily_sheet():
    global SPREADSHEET_ID
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    Date_Raw = date.today().strftime('%Y%m%d')
    spreadsheet_name = f'{SPREADSHEET_BASE_NAME}{Date_Raw}'
    response = drive_service.files().list(
        q=f"name='{spreadsheet_name}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    if response['files']:
        SPREADSHEET_ID = response['files'][0]['id']
        print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        return
    spreadsheet_body = {'properties': {'title': spreadsheet_name}}
    spreadsheet = service.spreadsheets().create(body=spreadsheet_body).execute()
    SPREADSHEET_ID = spreadsheet['spreadsheetId']
    print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    worksheet_names = [
        f'wbrlist_BA_RAk_APP_{Date_Raw}',
        f'wbrlist_BA_RAK_VIL_{Date_Raw}',
        f'wbrlist_BA_DBX_APP_{Date_Raw}',
        f'wbrlist_BA_DBX_VIL_{Date_Raw}',
        f'wbrlist_PF_RAk_APP_{Date_Raw}',
        f'wbrlist_PF_RAK_VIL_{Date_Raw}',
        f'wbrlist_PF_DBX_APP_{Date_Raw}',
        f'wbrlist_PF_DBX_VIL_{Date_Raw}',
    ]
    headers = [[
        "Unit ID","URL","MAP URL","Crawl Date","Listed Date","Location","Building Name","Address",
        "Price AED","Price EUR","BD","Bathr.","Sqft","Sqm","AED/SqFt","EUR/Sqm",
        "Contract Status","Avrg. price/sqft Last 10-30","AVER./",
        "1st sold AED","1st sold Sqft","1st sold AED_Sqft",
        "2nd sold AED","2nd sold Sqft","2nd sold AED_Sqft",
        "3rd sold AED","3rd sold Sqft","3rd sold AED_Sqft",
        "4th sold AED","4th sold Sqft","4th sold AED_Sqft",
        "5th sold AED","5th sold Sqft","5th sold AED_Sqft",
        "6th sold AED","6th sold Sqft","6th sold AED_Sqft",
        "7th sold AED","7th sold Sqft","7th sold AED_Sqft",
        "8th sold AED","8th sold Sqft","8th sold AED_Sqft",
        "9th sold AED","9th sold Sqft","9th sold AED_Sqft",
        "10th sold AED","10th sold Sqft","10th sold AED_Sqft"
    ]]
    requests = [{"addSheet": {"properties": {"title": name}}} for name in worksheet_names]
    service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": requests}).execute()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    default_sheet_id = sheet_metadata['sheets'][0]['properties']['sheetId']
    delete_request = {"requests": [{"deleteSheet": {"sheetId": default_sheet_id}}]}
    service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=delete_request).execute()
    for name in worksheet_names:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{name}!A1",
            valueInputOption='RAW',
            body={'values': headers}
        ).execute()



def append_property_to_sheet(service, data_to_insert, fullapartmentname, TypeH, site, link=None):
    global SPREADSHEET_ID
    Date_Raw = date.today().strftime('%Y%m%d')

    rak_keywords = ["Al Marjan Island", "Mina Al Arab", "Al Hamra", "central", "Nakheel", "Downtown"]

    # 1️⃣ Determine the prefix based on site (BA or PF)
    site_prefix = "BA" if site.upper() == "BA" else "PF"

    # 2️⃣ Determine the sheet tab
    if any(loc in fullapartmentname for loc in rak_keywords):
        # Ras Al Khaimah
        sheet_tab = f"wbrlist_{site_prefix}_RAk_APP_{Date_Raw}" if TypeH == "Apartment" else f"wbrlist_{site_prefix}_RAK_VIL_{Date_Raw}"
    else:
        # Dubai
        sheet_tab = f"wbrlist_{site_prefix}_DBX_APP_{Date_Raw}" if TypeH == "Apartment" else f"wbrlist_{site_prefix}_DBX_VIL_{Date_Raw}"

    # 3️⃣ Fetch headers
    sheet_metadata = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_tab}!1:1"
    ).execute()
    headers = sheet_metadata.get('values', [[]])[0]

    # 4️⃣ Map dict to row order
    row_data = [data_to_insert.get(header, "") for header in headers]

    # 5️⃣ Append row to the correct sheet
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{sheet_tab}!A2",
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': [row_data]}
    ).execute()

    # print(f"{sheet_tab} -> {result.get('updates', {}).get('updatedCells', 0)} cells inserted")
    print('Data Inserted to ',sheet_tab)

if __name__ == '__main__':
    init_daily_sheet()



    """ 
        To create token.json file
    """
#
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.oauth2.credentials import Credentials
# from google.auth.transport.requests import Request
# import os
#
# SCOPES = [
#     "https://www.googleapis.com/auth/spreadsheets",
#     "https://www.googleapis.com/auth/drive"
# ]
#
# def get_credentials():
#     creds = None
#     if os.path.exists("token.json"):
#         creds = Credentials.from_authorized_user_file("token.json", SCOPES)
#
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())  # Auto-refresh
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 "Cred_Client_SHEET.json", SCOPES
#             )
#             creds = flow.run_local_server(port=0)
#
#         with open("token.json", "w") as token_file:
#             token_file.write(creds.to_json())
#
#     return creds
#
# creds = get_credentials()
# print("✅ Token is ready and will auto-refresh now!")


"""
    Other token file but temp
"""
#
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# import os
#
# SCOPES = [
#     "https://www.googleapis.com/auth/spreadsheets",
#     "https://www.googleapis.com/auth/drive"
# ]
#
# def get_credentials():
#     creds = None
#     if os.path.exists("token.json"):
#         creds = Credentials.from_authorized_user_file("token.json", SCOPES)
#
#     # Auto-refresh if expired
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 "credentials.json", SCOPES
#             )
#             creds = flow.run_local_server(port=0)
#
#         # Save the updated token.json
#         with open("token.json", "w") as token_file:
#             token_file.write(creds.to_json())
#
#     return creds
#
#