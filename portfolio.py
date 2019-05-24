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
#DIVIDEND_DATA_XPATH = "//*[@id='DataTables_Table_0']"
DIVIDEND_DATA_ID = "DataTables_Table_0"
DIVIDEND_DATA_URL = "https://www.quotemedia.com/portal/dividends?qm_symbol="
HISTORY_DATA_URL = "https://www.quotemedia.com/portal/history?qm_symbol="
PORTFOLIO_DB_NAME = "portfolio.db"

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

# convert date in following format to timedate.date:
# yyyy-mm-dd
def str_to_date(date_str):
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

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

    def record_from_web_element(self, elem_str_array):
        index = 0
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


class Fund_price_entry:
    def __init__(self):
        pass

    def __str__(self):
        try:
            return f"{self.date} open:{self.open} high:{self.high} low:{self.low} close:{self.close}"
        except:
            return ""

    def __repr__(self):
        try:
            return f"{self.date} open:{self.open} high:{self.high} low:{self.low} close:{self.close}"
        except:
            return ""

    def get_date(self):
        return self.date

    # parse history price scraped from https://www.quotemedia.com/
    #2019-05-09 22.11 22.15 22.00 22.10 22.081 37.29k -0.45% -0.10 823,445.00 163
    def record_web_data(self, line):
        line_fields = line.replace("--", "00").split()
        self.date = str_to_date(line_fields[0])
        self.open = float(line_fields[1])
        self.high = float(line_fields[2])
        self.low = float(line_fields[3])
        self.close = float(line_fields[4])

    def record_data_base_data(self, price_record):
        self.date = str_to_date(price_record[0])
        self.open = float(price_record[1])
        self.high = float(price_record[2])
        self.low = float(price_record[3])
        self.close = float(price_record[4])


    def get_date_entry_update_sql_cmd(self, ticker):
        cmd = f'INSERT INTO "{ticker}.HistoricalPrice" (Date,' \
               f'Open,High,Low,Close) VALUES ' \
                f'("{self.date!s}", {self.open!s}, {self.high}, {self.low}, {self.close});'
        return cmd

class Fund_price_history:
    def __init__(self, fund_ticker):
        self.history = {}
        self.ticker = fund_ticker

    def __repr__(self):
        text = ""
        for record in self.history:
            text += str(record) + "\n"
        return text

    def __str__(self):
        return self.__repr__()

    # parse price data with following layout
    #Date Open High Low Close VWAP Volume % Chg Change Trade Val Total Trades
    #2019-05-10 -- -- -- 22.10 -- -- 0.00% -- -- --
    #2019-05-09 22.11 22.15 22.00 22.10 22.081 37.29k -0.45% -0.10 823,445.00 163
    def record_from_web_element(self, elem_str_array):
        price_entries = []
        for line in elem_str_array:
            fund_price_entry = Fund_price_entry()
            fund_price_entry.record_web_data(line)
            # can not trust the date for today, so ignore it
            if (fund_price_entry.get_date() not in self.history) \
                and (date.today() != fund_price_entry.date):
                price_entries.insert(0, fund_price_entry)
                self.history[fund_price_entry.get_date()] = fund_price_entry
            else:
                del fund_price_entry
        return price_entries

    # retrieve history price from data price
    def data_base_read_price_history(self, data_base_cursor):
        count = 0
        sql_cmd = "SELECT * FROM \"" + self.ticker + ".HistoricalPrice\""
        data = data_base_cursor.execute(sql_cmd)
        for line in data:
            fund_price_entry = Fund_price_entry()
            try:
                fund_price_entry.record_data_base_data(line)
            except:
                # ignore if the data in the database is null, like this:
                # 2001-05-21	null	null	null	null	null	null
                next

            if fund_price_entry.get_date() not in self.history:
                self.history[fund_price_entry.get_date()] = fund_price_entry
            else:
                del fund_price_entry
        return count


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
    return access_portfolio_database('SELECT * FROM Product_info')
    

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

class Fundinfo:
    def __init__(self, ticker, shares):
        self.ticker = ticker
        self.shares = shares
        self.historical_price = Fund_price_history(ticker)
        self.history_dividend = Dividend_history(ticker)

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
    
    def get_quotemedia_symbol(self):
        if not self.is_usd:
            return self.ticker + ":CA"
        else:
            return self.ticker
    
    def update_dividend_data(self):
        web_data = scrape_quotemedia_data(self.get_quotemedia_symbol(), 
                                          DIVIDEND_DATA_URL,
                                          DIVIDEND_DATA_ID)
        self.history_dividend.record_from_web_element(web_data)

    def load_history_price_data(self, data_base_cursor):
        # load price history from history
        self.historical_price.data_base_read_price_history(data_base_cursor)
        
        web_data = scrape_quotemedia_data(self.get_quotemedia_symbol(), 
                                          HISTORY_DATA_URL,
                                          DIVIDEND_DATA_ID)
        new_entries = self.historical_price.record_from_web_element(web_data)

        # insert the new entries into the database
        for fund_price_entry in new_entries:
            data_base_cursor.execute(
                fund_price_entry.get_date_entry_update_sql_cmd(self.ticker))


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
    def load_fund_price_history(self, ticker):
        fund = self.find_fund(ticker)
        fund.load_history_price_data(self.db_c)

    def update_all_funds_price_history(self):
        for fund in self.funds:
            debug_print(str(fund))
            self.load_fund_price_history(fund.get_ticker())

def main():
    portfolio = Portfolio()
    portfolio.get_fundinfo_from_sheet()
    portfolio.update_all_funds_price_history()
   

# function to scrape fund data from https://www.quotemedia.com
def scrape_quotemedia_data(ticker, url, table_id):
    full_url = url + ticker
    driver = webdriver.Chrome()
    driver.get(full_url)
    web_data = []

    wait = WebDriverWait(driver, 10, poll_frequency=1)
    try:
        page_loaded = wait.until(
            lambda driver: driver.find_element_by_id(DIVIDEND_DATA_ID)
        )
    except TimeoutError:
        driver.close()

    elem = driver.find_element_by_id(DIVIDEND_DATA_ID)
    debug_print(elem.text)
    # skip the title line for the data table
    web_data += (elem.text.splitlines())[1:]

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
            elem = driver.find_element_by_id(DIVIDEND_DATA_ID)
            # skip the title line for the data table
            web_data += (elem.text.splitlines())[1:]
            debug_print(elem.text)
        except:
            break
    driver.close()
    return web_data


# scrape dividend history of fund
def scrape_dividend(ticker):
    dividend_history = Dividend_history(ticker)
    web_data = scrape_quotemedia_data(ticker, DIVIDEND_DATA_URL, DIVIDEND_DATA_ID)
    dividend_history.record_from_web_element(web_data)

def scrape_history(ticker):
    price_history = Fund_price_history(ticker)
    web_data = scrape_quotemedia_data(ticker, HISTORY_DATA_URL, DIVIDEND_DATA_ID)
    price_history.record_from_web_element(web_data)
    print(price_history)

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
#    scrape_history("ZCN:CA")

#    IEX_TOKEN = read_iex_token('iex.json')
    #main()
#    scrape_dividend("ZCN:CA")