from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from portfolio import *

class Quotemedia:
    price_history_url = 'https://www.quotemedia.com/portal/history?qm_symbol='
    dividend_url = 'https://www.quotemedia.com/portal/dividends?qm_symbol='
    NEXT_BUTTON_ID = 'DataTables_Table_0_next'
    WEB_DATA_ID = "DataTables_Table_0"
    def __init__(self):
        self.driver = webdriver.Chrome()

    def __del__(self):
        self.driver.close()


    def get_price_history(self, ticker):
        full_url = Quotemedia.price_history_url + ticker
        self.driver.get(full_url)
        web_data = []


        input("Press any key to continue...")
        wait = WebDriverWait(self.driver, 10, poll_frequency=1)
        try:
            wait.until(
                lambda driver: self.driver.find_element_by_id(Quotemedia.WEB_DATA_ID)
            )
        #    element = WebDriverWait(driver, 10, poll_frequency=5).until(
        #        EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
        #    )
        except TimeoutError:
            self.driver.close()

    #    time.sleep(10)
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
                    lambda driver: self.driver.find_element_by_id(Quotemedia.WEB_DATA_ID)
                )
            #    element = WebDriverWait(driver, 10, poll_frequency=5).until(
            #        EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
            #    )
                elem = self.driver.find_element_by_id(Quotemedia.WEB_DATA_ID)
                # skip the title line for the data table
                web_data += (elem.text.splitlines())[1:]
                debug_print(elem.text)
            except:
                break

if __name__ == '__main__':
    browser = Quotemedia()
    browser.get_price_history("VTI")
