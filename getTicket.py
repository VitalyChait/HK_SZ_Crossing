from selenium.common import exceptions
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from base64 import b64decode
from config import App
from capcha_detector import runCaptchaDecoder
from json import loads
from time import sleep


def userInformation():
    # INIT
    passport = App.get("passport")
    password = App.get("password")
    img_out_PATH = App.get("captcha_img_output_PATH")
    img_out_format = App.get("captcha_img_output_format")
    return passport, password, img_out_PATH, img_out_format


def driverSettings():
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--incognito")
    caps = DesiredCapabilities.CHROME
    caps["goog:loggingPrefs"] = {"performance": "ALL"}
    caps['pageLoadStrategy'] = 'none'
    driver = Chrome(desired_capabilities=caps, options=chrome_options, service=Service(App.get("chromedriverPATH")))
    return driver


def process_browser_logs_for_network_events_frameStoppedLoading(logs, counter):
    # Function to make sure the captcha jpeg images were loaded from ChromeDriver logs
    key_stepB = "method"
    key_stepC_partA = "params"
    key_stepC_partB = "headers"
    key_stepC_partC = "Content-Type"
    filter_a = "Network.responseReceivedExtraInfo"
    filter_b = "image/jpeg"
    # Loop logs
    for entry in logs:
        stepA = loads(entry["message"])["message"]
        stepB = stepA[key_stepB]
        if not (filter_a == stepB):
            continue
        stepC = stepA[key_stepC_partA][key_stepC_partB][key_stepC_partC]
        if not(filter_b == stepC):
            continue
        # jpeg element was loaded
        counter += 1
    return counter


def firstPage(driver, passport, password, img_out_PATH, img_out_format):
    # Load page
    js_LOADED_XPATH = '//html/body/script[4]'
    WebDriverWait(driver, timeout=100).until(lambda d: d.find_element(By.XPATH, js_LOADED_XPATH))
    # Ignore popup message
    pupUpButtonXPATH = '//*[@id="winLoginNotice"]/div[contains(@class, "flexbox btngroup")]/div[contains(@class, "flex1")]/button'
    button = driver.find_element(By.XPATH, pupUpButtonXPATH)
    driver.execute_script("arguments[0].click();", button)
    # Fill login details, for non HK/TWN/Mainland passport
    fillDetailsPassport = driver.find_element(By.ID, 'select_certificate')
    fillDetailsPassport = Select(fillDetailsPassport)
    fillDetailsPassport.select_by_value('3')
    # Fill user's passport number
    passportXPATH = '//*[@id="input_idCardNo"]'
    passportELEMENT = driver.find_element(By.XPATH, passportXPATH)
    driver.execute_script("arguments[0].value = '{}';".format(passport), passportELEMENT)
    # Fill user's password
    passwordXPATH = '//*[@id="input_pwd"]'
    passwordELEMENT = driver.find_element(By.XPATH, passwordXPATH)
    driver.execute_script("arguments[0].value = '{}';".format(password), passwordELEMENT)
    # XPATH(plural) for the elements inside the captcha analyze loop
    captcha_button_xpath = '//*[@id="img_verify"]'
    captchaXPATH = '//*[@id="img_verify"]'
    captcha_TEXTBOX_XPATH = '//*[@id="input_verifyCode"]'
    submitXPATH = '//*[@id="btn_login"]'
    passed_XPATH = '/html/body/div[contains(@class, "person-heade")]'
    # Discard old logs, will be useful later to check that Captcha loaded successfully
    _ = driver.get_log("performance")
    # Mark loaded elements with None
    passFlag = None
    captcha_button = None
    while passFlag is None:
        try:
            # Page 1  condition
            captcha_button = driver.find_element(By.XPATH, captcha_button_xpath)
        except exceptions.NoSuchElementException:
            # Page 2 condition
            passFlag = driver.find_element(By.XPATH, '//*[@id="winOrderNotice"]')
        # Make sure that we are still on Page 1
        if passFlag is None and captcha_button is not None:
            # Reload captcha image
            driver.execute_script("arguments[0].click();", captcha_button)
            counter = 0
            # Loop until image fully loaded, 2 jpeg elements in total are on the webpage
            while counter < 2 and passFlag is None:
                driver.implicitly_wait(0.1)
                counter += process_browser_logs_for_network_events_frameStoppedLoading(driver.get_log("performance"), counter)
                try:
                    # Validate and make sure we are still on Page 1
                    passFlag = driver.find_element(By.XPATH, '//*[@id="winOrderNotice"]')
                except exceptions.NoSuchElementException:
                    pass
        # Validate we did not pass to the 2nd page
        if passFlag is not None:
            break
        elif captcha_button is not None:
            # Loop to validate image is not broken (black image in our case)
            while True:
                # Download Captcha, crop and upscale * 4 (from 140*36 --> 90*25 --> 360*100)
                img_base64 = driver.execute_script("""
                        var ele = arguments[0];
                        var cnv = document.createElement('canvas');
                        <!-- cnv.width = ele.width; cnv.height = ele.height; -->
                        <!-- cnv.getContext('2d').drawImage(ele, 0, 0); -->
                        cnv.width = 360; cnv.height = 100;
                        cnv.getContext('2d').drawImage(ele, 10, 0, 90, 25, 0, 0, 360, 100);
                        return cnv.toDataURL('image/jpeg').substring(22);    
                        """, driver.find_element(By.XPATH, captchaXPATH))
                # "AAA" marks black pixels with base64
                # This is correct to 360*100 image, validate if you change the code
                if not (img_base64[-285:-5] == "".join(["A"]*280)):
                    break
            # Save image
            with open(img_out_PATH+img_out_format, 'wb') as f:
                f.write(b64decode(img_base64))
            # Decode the Captcha
            Captcha_text = runCaptchaDecoder(img_out_PATH, img_out_format)
            if Captcha_text == "":
                continue
            # Fill captcha text box
            captchaELEMENT = driver.find_element(By.XPATH, captcha_TEXTBOX_XPATH)
            driver.execute_script("arguments[0].value = '{}';".format(Captcha_text), captchaELEMENT)
            # Submit button
            submitButton = driver.find_element(By.XPATH, submitXPATH)
            driver.execute_script("arguments[0].click();", submitButton)
            # Validate if our webpage moved
            try:
                passFlag = WebDriverWait(driver, timeout=1).until(lambda d: d.find_element(By.XPATH, passed_XPATH))
            except exceptions.TimeoutException:
                continue
    exit()

def secondPage(driver):
    # Make sure page is fully loaded
    js_LOADED_XPATH = '/html/body/script[3]'
    WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.XPATH, js_LOADED_XPATH))
    # Ignore popup message
    pupUpButtonXPATH = '//*[@id="winOrderNotice"]/div[contains(@class, "flexbox btngroup")]/div[contains(@class, "flex1")]/button'
    button = driver.find_element(By.XPATH, pupUpButtonXPATH)
    driver.execute_script("arguments[0].click();", button)
    # Click on signUp button
    signUP_XPATH = '//*[@id="a_canBookHotel"]'
    signUP_XPATH = driver.find_element(By.XPATH, signUP_XPATH)
    driver.execute_script("arguments[0].click();", signUP_XPATH)


def thirdPage(driver):
    # Only available from 10:00 - 20:00
    sleep(30)


def run():
    passport, password, img_out_PATH, img_out_format = userInformation()
    driver = driverSettings()
    websiteURL = "https://hk.sz.gov.cn:8118/userPage/login"

    # Load website
    driver.get(websiteURL)
    # First Page
    firstPage(driver, passport, password, img_out_PATH, img_out_format)
    secondPage(driver)
    thirdPage(driver)


if __name__ == '__main__':
    run()
