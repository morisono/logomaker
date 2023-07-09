import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

from modules.utils import get_md5_hash


def google_image_search(query, image_format, limits, temp_dir, image_size, aspect_ratio, color, image_type, region, safe_search, license):
    options = Options()
    options.add_argument("--headless")
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-browser-side-navigation')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-gpu')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    options.add_argument('--no-sandbox')
    # options.add_argument('--start-maximized')
    options.add_argument('--window-size=1920,1080')
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    options.add_experimental_option("excludeSwitches", ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    service = Service(executable_path='./chromedriver_linux64')

    driver = webdriver.Chrome(options=options, service=service)
    search_url = f'https://www.google.com/search?tbm=isch&q={query}&tbs=ift:{image_format}'

    if image_size:
        search_url += f'&tbs=isz:{image_size}'
    if aspect_ratio:
        search_url += f'&tbs=iar:{aspect_ratio}'
    if color:
        search_url += f'&tbs=ic:{color}'
    if image_type:
        search_url += f'&tbs=itp:{image_type}'
    if region:
        search_url += f'&gl={region}'
    if safe_search:
        search_url += f'&safe={safe_search}'
    if license:
        search_url += f'&tbs=sur:{license}'

    try:
        driver.get(search_url)
        image_links = []
        for _ in range(3):
            for element in driver.find_elements(By.TAG_NAME, "body"):
                element.send_keys(Keys.END)
        image_elements = driver.find_elements(By.CSS_SELECTOR, "img.rg_i")


        for i, element in enumerate(image_elements[:limits]):
            image_url = element.get_attribute('src')
            image_filename = f"{i+1:05d}_{get_md5_hash(image_url)}.{image_format}"
            temp_file_path = os.path.join(temp_dir, image_filename)
            element.screenshot(temp_file_path)
            image_links.append((image_url, image_filename, temp_file_path))

        return image_links

    finally:
        driver.quit()

