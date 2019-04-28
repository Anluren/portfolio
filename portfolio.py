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

import datetime
from datetime import date
import re

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

NEXT_BUTTON_ID = "//*[@id='DataTables_Table_0_next']"
DIVIDEND_DATA_XPATH = "//*[@id='DataTables_Table_0']"
DIVIDEND_DATA_URL = "https://www.quotemedia.com/portal/dividends?qm_symbol="

# class to handle dividend data scraped from webpage, the raw is like this:
#
# 2013-09-25        Ex-Div Date 
# 0.125 CAD         Amount   
# Quarterly         Frequency
# 2013-10-04        Payment
# 2013-09-27        Record
# 2013-09-18        Announced
# Cash Dividend     Type

CAD_DOLLAR = 0
USD_DOLLAR = 1

is_debug = 1

def debug_print(string):
    if is_debug:
        print(string)

class Dividend_dist_record:
    def __init__(self):
        self.ex_div_date = date.today()
        self.amount = 0
        self.denominated  = CAD_DOLLAR
        self.frequency = "Quarterly"
        self.payment_date = date.today()
        self.record_date = date.today()
        self.announced_date = date.today()

    def record_web_data(self, lines, index):
        # 2013-09-25        Ex-Div Date 
        self.ex_div_date = datetime.datetime.strptime(lines[index + 0], "%Y-%m-%d").date()
        # 0.125 CAD         Amount   
        (self.amount, self.denominated) = lines[index + 1].split()
        self.amount = float(self.amount)
        # Quarterly         Frequency
        self.frequency = lines[index + 2]
        # 2013-10-04        Payment
        try:
            self.payment_date = datetime.datetime.strptime(lines[index+3], "%Y-%m-%d").date()
        except:
            self.payment_date = self.ex_div_date

        # 2013-09-27        Record
        self.record_date = datetime.datetime.strptime(lines[index+4], "%Y-%m-%d").date()
        # 2013-09-18        Announced
        self.announced_date = datetime.datetime.strptime(lines[index+5], "%Y-%m-%d").date()
        # return number of line processed
        return 7
    def __str__(self):
        return f"{self.ex_div_date}\t{self.amount}\t{self.payment_date}"

    def __repr__(self):
        return f"{self.ex_div_date}\t{self.amount}\t{self.payment_date}"


class Dividend_history:
    def __init__(self):
        self.history = []
    def record_from_web_element(self, elem_str):
        # add all record from a web element with dividend records
        elem_str_array = elem_str.splitlines()

        # skip first line which is title of the table
        index = 1
        while index < len(elem_str_array):
            record = Dividend_dist_record()
            index += record.record_web_data(elem_str_array, index)

            # add a new record to the history
            self.history.append(record)
    def __str__(self):
        output = ""
        for record in self.history:
            output += str(record) + "\n"
        return output

    def __repr__(self):
        output = ""
        for record in self.history:
            output += str(record) + "\n"
        return output
    
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
    dividend_history = Dividend_history()

    full_url = DIVIDEND_DATA_URL + ticker
    driver = webdriver.Chrome()
    driver.get(full_url)

    wait = WebDriverWait(driver, 10, poll_frequency=1)
    try:
        page_loaded = wait.until(
            lambda driver: driver.find_element_by_xpath(DIVIDEND_DATA_XPATH)
        )
    #    element = WebDriverWait(driver, 10, poll_frequency=5).until(
    #        EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
    #    )
    except TimeoutError:
        driver.close()

#    time.sleep(10)
    elem = driver.find_element_by_xpath(DIVIDEND_DATA_XPATH)
    debug_print(elem.text)
    dividend_history.record_from_web_element(elem.text)

    # read more lines from the table
    while True:
        try:
            button = driver.find_element_by_xpath(NEXT_BUTTON_ID)
        except:
            break

        # press the button
        if button.is_displayed():
            button.click()
        else:
            break

        # now wait for the data to be reloaded
        wait = WebDriverWait(driver, 10, poll_frequency=1)
        try:
            page_loaded = wait.until(
                lambda driver: driver.find_element_by_xpath(DIVIDEND_DATA_XPATH)
            )
        #    element = WebDriverWait(driver, 10, poll_frequency=5).until(
        #        EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
        #    )
            elem = driver.find_element_by_xpath(DIVIDEND_DATA_XPATH)
            debug_print(elem.text)
            dividend_history.record_from_web_element(elem.text)
        except:
            break
        
    # print all history
    print(dividend_history)

    driver.close()

if __name__ == '__main__':
    #main()
    scrape_dividend("ZCN:CA")
