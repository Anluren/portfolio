from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from portfolio import debug_print

class Quotemedia:
    price_history_url = 'https://www.quotemedia.com/portal/history?qm_symbol='
    dividend_url = 'https://www.quotemedia.com/portal/dividends?qm_symbol='
    quote_url = 'https://www.quotemedia.com/portal/quote/?qm_symbol='
    NEXT_BUTTON_ID = 'DataTables_Table_0_next'
    WEB_DATA_ID = "DataTables_Table_0"
    def __init__(self):
        self.driver = webdriver.Chrome()

    def __del__(self):
        self.driver.quit()

    def get_realtime_price(self, ticker):
        full_url = Quotemedia.quote_url + ticker
        self.driver.get(full_url)

        wait = WebDriverWait(self.driver, 10, poll_frequency=1)
        try:
            wait.until(
                lambda driver: driver.find_element_by_class_name('qmod-quotegrid')
            )
        except TimeoutError:
            self.driver.close()
            return ""
        web_data = self.driver.find_element_by_class_name('qmod-quotegrid').text
        debug_print(web_data)
        return web_data

    def get_price_history(self, ticker):
        full_url = Quotemedia.price_history_url + ticker
        self.driver.get(full_url)
        web_data = []

        input("Press any key to continue...")
        wait = WebDriverWait(self.driver, 10, poll_frequency=1)
        try:
            wait.until(
                lambda driver: driver.find_element_by_id(Quotemedia.WEB_DATA_ID)
            )
        except TimeoutError:
            self.driver.close()

        elem = self.driver.find_element_by_id(Quotemedia.WEB_DATA_ID)
        debug_print(elem.text)
        # skip the title line for the data table
        web_data += (elem.text.splitlines())[1:]

        # read more lines from the table
        while True:
            try:
                button = self.driver.find_element_by_id(Quotemedia.NEXT_BUTTON_ID)
            except:
                break

            # press the button
            if button.is_displayed():
                button.click()
            else:
                break

            # now wait for the data to be reloaded
            wait = WebDriverWait(self.driver, 10, poll_frequency=1)
            try:
                wait.until(
                    lambda driver: driver.find_element_by_id(Quotemedia.WEB_DATA_ID)
                )
                elem = self.driver.find_element_by_id(Quotemedia.WEB_DATA_ID)
                # skip the title line for the data table
                web_data += (elem.text.splitlines())[1:]
                debug_print(elem.text)
            except:
                break
        self.driver.close()

        # write the result into a file
        with open(ticker + ".csv", 'w') as csv_file:
            csv_file.write(" Date,Open,High,Low,Close,Adj Close,Volume\n")
            for line in web_data:
                line = line.replace("--", "00") 
                fields = line.split()
                csv_file.write(" " + ','.join(fields[0:6]) + "\n")


if __name__ == '__main__':
    browser = Quotemedia()
    browser.get_realtime_price("VTI")
#   browser.get_price_history("TDB902:CA")
#   browser.get_price_history("TDB900:CA")
#   browser.get_price_history("TDB911:CA")
