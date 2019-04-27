from __future__ import print_function
import time
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    # The ID and range of a sample spreadsheet.
    with open("spreadsheet_id.txt", 'r') as f:
        SAMPLE_SPREADSHEET_ID = f.readline().strip()

    SAMPLE_RANGE_NAME = 'ALLOCATIONS!A4:E'

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        print('Name, Major:')
        for row in values:
            # Print columns A and E, which correspond to indices 0 and 4.
            if len(row) >= 5:
                print('%s, %s' % (row[0], row[4]))

def scrape_dividend(ticker):
    url = "https://www.quotemedia.com/portal/dividends?qm_symbol="
    full_url = url + ticker

    driver = webdriver.Chrome("/Users/mzheng/Downloads/chromedriver")
    driver.get(full_url)

    wait = WebDriverWait(driver, 10, poll_frequency=5)
    try:
        page_loaded = wait.until(
            lambda driver: driver.find_element_by_xpath("//*[@id='DataTables_Table_0']")
        )
    #    element = WebDriverWait(driver, 10, poll_frequency=5).until(
    #        EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
    #    )
    except TimeoutError:
        driver.close()

#    time.sleep(10)
    elem = driver.find_element_by_xpath("//*[@id='DataTables_Table_0']")
    print(elem)
    driver.close()

if __name__ == '__main__':
    main()
    #scrape_dividend("VTI")
