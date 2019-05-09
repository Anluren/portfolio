# pip install selenium
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
# pip install pandas-datareader
# pip install pyEX 
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
import csv
import sqlite3

import datetime
from datetime import date
import re

import json
from forex_python.converter import CurrencyRates

def get_exchange_rate(date_obj):
    c = CurrencyRates()
    return c.get_rate("USD", "CAD", \
        datetime.datetime(date_obj.year, date_obj.month, date_obj.day, 0,0, 0,0))

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

NEXT_BUTTON_ID = "//*[@id='DataTables_Table_0_next']"
DIVIDEND_DATA_XPATH = "//*[@id='DataTables_Table_0']"
DIVIDEND_DATA_ID = "DataTables_Table_0"
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

# IEX Cloud token
IEX_TOKEN = {}

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
        return

    def __str__(self):
        return f"{self.ex_div_date}\t{self.amount}\t{self.payment_date}"

    def __repr__(self):
        return f"{self.ex_div_date}\t{self.amount}\t{self.payment_date}"


class Dividend_history:
    def __init__(self, fund_ticker):
        self.history = []
        self.ticker = fund_ticker

    def record_from_web_element(self, elem_str):
        # add all record from a web element with dividend records
        elem_str_array = elem_str.splitlines()

        # skip first line which is title of the table
        index = 1
        while index < len(elem_str_array):
            record = Dividend_dist_record()
            try:
                record.record_web_data(elem_str_array, index)
                # add a new record to the history
                self.history.append(record)
            except:
                del record
            finally:
                index += 7

    def __str__(self):
        output = f"Fund Ticker: {self.ticker}\n"
        for record in self.history:
            output += str(record) + "\n"
        return output

    def __repr__(self):
        output = f"Fund Ticker: {self.ticker}\n"
        for record in self.history:
            output += str(record) + "\n"
        return output

PORTFOLIO_DB_NAME = "portfolio.db"

#testing code for accessing database
def access_portfolio_database(sql_cmd):
    conn = sqlite3.connect(PORTFOLIO_DB_NAME)
    c = conn.cursor()
    c.execute(sql_cmd)

    data = c.fetchall()

    conn.commit()
    conn.close()

    return data


def data_base_read_fund_info():
    data = access_portfolio_database('SELECT * FROM Product_info')
    print(data)

ticker_names = [
    "VSB",
    "VAB",
    "BND",
    "XIC",
    "TDB900",
    "VCN",
    "ZCN",
    "TDB902",
    "VTI",
    "TDB911",
    "XEF",
    "VEA",
    "VXUS",
    "VWO",
]
qm_ticker_name = {
}
class Fundinfo:
    def __init__(self, ticker, shares):
        self.ticker = ticker
        self.shares = shares

    def __repr__(self):
        return self.ticker + ", " + str(self.shares)

    def __str__(self):
        return self.ticker + ", " + str(self.shares)

    def get_ticker(self):
        return self.ticker
    
    def is_fund(self, ticker):
        return self.ticker == ticker

    def set_info_from_db(self, da_entry):
        # data base row is like this:
        # (ticker, is_usd, fund_company, full_name)
        self.is_usd = da_entry[1]
        self.fund_company = da_entry[2]
        self.asset_type = da_entry[3]
        self.full_name = da_entry[4]

class Portfolio:
    def __init__(self):
        self.funds = []

        # open the data base
        try:
            self.db_conn = sqlite3.connect(PORTFOLIO_DB_NAME)
            self.db_c = self.db_conn.cursor()
            self.db_opened = 1
        except:
            self.db_opened = 0

    def find_fund(self, ticker):
        for fund in self.funds:
            if fund.is_fund(ticker):
                return fund
        return False

    def __del__(self):
        if self.db_opened:
            self.db_conn.commit()
            self.db_conn.close()

    def __str__(self):
        for fund in self.funds:
            print(fund)

    def get_fundinfo_from_sheet(self):
        """Shows basic usage of the Sheets API.
        Prints values from a sample spreadsheet.
        """
        # The ID and range of a sample spreadsheet.
        with open("spreadsheet_id.txt", 'r') as f:
            SAMPLE_SPREADSHEET_ID = f.readline().strip()

        SAMPLE_RANGE_NAME = 'INPUT!A4:V'

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
            for row in values:
                # Print columns A and E, which correspond to indices 0 and 4.
                if len(row) >= 22:
                    if (row[1] in ticker_names):
                        self.funds.append(Fundinfo(row[1],row[21]))

        # read fund facts from database
        self.db_c.execute('SELECT * FROM Product_info')

        db_data = self.db_c.fetchall()

        for data in db_data:
            fund = self.find_fund(data[0])
            if fund:
                fund.set_info_from_db(data)

        return True

def main():
    portfolio = Portfolio()
    portfolio.get_fundinfo_from_sheet()

def scrape_dividend(ticker):
    dividend_history = Dividend_history(ticker)

    full_url = DIVIDEND_DATA_URL + ticker
    driver = webdriver.Chrome()
    driver.get(full_url)

    wait = WebDriverWait(driver, 10, poll_frequency=1)
    try:
        page_loaded = wait.until(
            lambda driver: driver.find_element_by_id(DIVIDEND_DATA_ID)
        )
    #    element = WebDriverWait(driver, 10, poll_frequency=5).until(
    #        EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
    #    )
    except TimeoutError:
        driver.close()

#    time.sleep(10)
    elem = driver.find_element_by_id(DIVIDEND_DATA_ID)
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
                lambda driver: driver.find_element_by_id(DIVIDEND_DATA_ID)
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

def get_stock_history_price(ticker):
    c = pyEX.Client(IEX_TOKEN["SecretToken"])

def read_iex_token(file):
    with open(file) as f:
        return f.load(f)

def read_history_prices_from_csv(tiker):
    file_name = 'csv/' + tiker + 'csv'
    with open(file_name, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            print(row)

if __name__ == '__main__':
#    data_base_read_fund_info()
    main()
#    scrape_dividend("ZCN:CA")

#    IEX_TOKEN = read_iex_token('iex.json')
    #main()
#    scrape_dividend("ZCN:CA")
