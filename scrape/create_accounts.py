import hashlib
import re
import time
import os
import uuid
from selenium import webdriver
from python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask
from selenium.common.exceptions import NoSuchElementException, WebDriverException, TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

from config import ANTI_CAPTCHA_API_KEY, HEADLESS, GECKO_DRIVER_PATH
from proxy.socks_proxy import ProxyRequest
from scrape.temp_mail import temp_mail
from sqlite.make_csv import make_csv
from sqlite.sqlite_stuff import SqliteCursor

site_key_reg = re.compile(r"(?<=window.___grecaptchaSiteKey = ')(.+?)(?=')")
EXPECTED_RESULT = '"success": true,'
client = AnticaptchaClient(ANTI_CAPTCHA_API_KEY)

DIR = os.path.dirname(os.path.abspath(__file__))


def get_token(url, site_key):
    task = NoCaptchaTaskProxylessTask(
        website_url=url,
        website_key=site_key
    )
    job = client.createTask(task)
    job.join(maximum_time=60 * 15)
    return job


def make_reddit_account(driver):
    password = r_id = hashlib.md5(str(uuid.uuid4()).encode('utf-8')).hexdigest()
    email_address, get_verification_link = temp_mail(r_id)
    WebDriverWait(driver, 20).until(ec.presence_of_element_located((  # Insert Email
        By.CSS_SELECTOR,
        r"#regEmail"
    ))).send_keys(email_address)
    WebDriverWait(driver, 20).until(ec.element_to_be_clickable((  # Click Submit
        By.CSS_SELECTOR,
        r"body > div > main > div:nth-child(1) > div > div.Step__content > form > fieldset.AnimatedForm__field.m-small-margin > button"
    ))).click()
    WebDriverWait(driver, 20).until(ec.element_to_be_clickable((  # Click first suggested username
        By.CSS_SELECTOR,
        r"body > div.App.m-desktop > main > div:nth-child(2) > div > div > div.AnimatedForm__content > div.Onboarding__usernameGenerator > div > div > a:nth-child(1)"
    ))).click()
    username = WebDriverWait(driver, 20).until(ec.presence_of_element_located((  # Get username value
        By.CSS_SELECTOR,
        r"body > div > main > div:nth-child(2) > div > div > div.AnimatedForm__content > div.Onboarding__usernameGenerator > div > div > a:nth-child(1)"
    ))).text
    while not username:
        username = WebDriverWait(driver, 20).until(ec.presence_of_element_located((  # Ensure we have username value
            By.CSS_SELECTOR,
            r"body > div > main > div:nth-child(2) > div > div > div.AnimatedForm__content > div.Onboarding__usernameGenerator > div > div > a:nth-child(1)"
        ))).text
        time.sleep(0.1)
    WebDriverWait(driver, 20).until(ec.presence_of_element_located((  # Insert password
        By.CSS_SELECTOR,
        r"#regPassword"
    ))).send_keys(password)
    WebDriverWait(driver, 20).until(ec.element_to_be_clickable((  #
        By.CSS_SELECTOR,
        r"body > div > main > div:nth-child(2) > div > div > div.AnimatedForm__bottomNav > button"
    ))).click()
    try:
        WebDriverWait(driver, 20).until(ec.element_to_be_clickable((  # Clicking submit before solving captcha sometimes makes it appear when it otherwise doesn't
            By.CSS_SELECTOR,
            r"button.AnimatedForm__submitButton:nth-child(3)"
        ))).click()
        WebDriverWait(driver, 30).until(ec.presence_of_element_located((  # Ensure reCaptcha is loaded
            By.CSS_SELECTOR,
            r"#g-recaptcha > div:nth-child(1) > div:nth-child(1) > iframe:nth-child(1)"
        )))
    except WebDriverException:
        return None

    def finish_making_reddit_account():
        WebDriverWait(driver, 20).until(ec.element_to_be_clickable((  # Click finish on screen asking you to follow stuff
            By.CSS_SELECTOR,
            r"button.AnimatedForm__submitButton:nth-child(2)"
        ))).click()
        time.sleep(5)  # Give reddit time to deliver email
        if get_verification_link is None:
            return username, password, email_address
        elif verify_url := get_verification_link():
            driver.get(verify_url)
            return username, password, email_address
        raise Exception("No email was received from reddit!")

    return finish_making_reddit_account


def verify_captcha_inner_html(driver):
    has_text = False
    while not has_text:
        elem: WebElement = WebDriverWait(driver, 2).until(ec.presence_of_element_located((  # Ensure reCaptcha is loaded
            By.CSS_SELECTOR,
            r"#g-recaptcha"
        )))
        inner_html = elem.get_attribute("innerHTML")
        has_text = isinstance(inner_html, str) and inner_html.strip() != ""


def form_submit(driver, get_job_fn):
    job = get_job_fn()
    token = job.get_solution_response()
    driver.execute_script(  # Add captcha solution to the div expecting it
        "document.getElementById('g-recaptcha-response').innerHTML='{}';".format(token)
    )
    verify_captcha_inner_html(driver)
    WebDriverWait(driver, 20).until(ec.element_to_be_clickable((  # Click submit
        By.CSS_SELECTOR,
        r"body > div.App.m-desktop > main > div:nth-child(2) > div > div > div.AnimatedForm__bottomNav > button"
    ))).click()
    try:
        WebDriverWait(driver, 2).until(ec.text_to_be_present_in_element_value((  # Check if captcha was invalid
            By.CSS_SELECTOR,
            r"body > div.App.m-desktop > main > div:nth-child(2) > div > div > div.AnimatedForm__bottomNav > span > span.AnimatedForm__submitStatusMessage"
        ), "Captcha not valid."))
        job.report_incorrect_recaptcha()
        return form_submit(driver, get_job_fn)
    except WebDriverException:
        return


def get_site_key(driver):
    if match := re.search(site_key_reg, driver.page_source):
        return match.group(1)
    raise Exception("Got no site key!")


def create_reddit_accounts(url, driver, proxy_address):
    finish_making_reddit_account = make_reddit_account(driver)
    if finish_making_reddit_account is None:
        driver.refresh()
        return create_reddit_accounts(url, driver, proxy_address)
    site_key = get_site_key(driver)
    form_submit(driver, lambda: get_token(url, site_key))
    username, password, email = finish_making_reddit_account()

    with SqliteCursor() as cursor:
        cursor.execute(
            "insert into account(username, password, email, proxy) values(?, ?, ?, ?)",
            (username, password, email, proxy_address)
        )


def get_new_webdriver(proxy_address: str, _headless=None):
    profile = webdriver.FirefoxProfile()
    ip, port = proxy_address.split(':')
    profile.set_preference('network.proxy.type', 1)
    profile.set_preference('network.proxy.socks', ip)
    profile.set_preference('network.proxy.socks_port', int(port))
    options = Options()
    options.headless = HEADLESS if _headless is None else _headless
    driver = webdriver.Firefox(
        firefox_profile=profile,
        options=options,
        executable_path=GECKO_DRIVER_PATH
    )
    driver.set_page_load_timeout(90)
    return driver


def get_webdriver_at_reddit(url):
    socks_addr_handler = ProxyRequest()
    driver = None
    while True:
        try:
            socks_address = socks_addr_handler.get_socks_address()
            driver = get_new_webdriver(socks_address)
            driver.get(url)
            WebDriverWait(driver, 1).until(ec.presence_of_element_located((  # Ensure the reddit login/register page is loaded
                By.CSS_SELECTOR,
                r"body > div > main > div:nth-child(1) > div > div.Step__content > form > h1"
            )))
            return driver, socks_address
        except (NoSuchElementException, WebDriverException, TimeoutException):
            pass
        if driver is not None:
            driver.close()
        time.sleep(0.1)


if __name__ == "__main__":
    _url = r"https://www.reddit.com/account/register/"
    _driver, _socks_address = get_webdriver_at_reddit(_url)
    try:
        create_reddit_accounts(_url, _driver, _socks_address)
        make_csv()
    finally:
        _driver.close()



