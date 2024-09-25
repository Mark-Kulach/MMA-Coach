from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

USER_DATA_PATH = r"C:\\Users\\kulac\AppData\\Local\\Google\\Chrome\\User Data"

# Set chrome profile to default
chrome_options = Options()
chrome_options.add_argument(f"--user-data-dir={USER_DATA_PATH}")
chrome_options.add_argument("--profile-directory=Default")

# Open chrome
driver = webdriver.Chrome(options=chrome_options)


def get_events():
    SECTIONS = [
    "https://ufcfightpass.com/season/24048",  
    "https://ufcfightpass.com/season/24049",
    "https://ufcfightpass.com/season/24050",
    "https://ufcfightpass.com/season/24051",
    "https://ufcfightpass.com/season/24053",
    "https://ufcfightpass.com/season/24054"
    ]

    for section in SECTIONS:
        driver.get(section)

        input("Page Loaded -- input enter once all events are loaded in:")

        with open("events.txt", "a") as file:
            for event in driver.find_element(By.CLASS_NAME, "card-list").find_elements(By.TAG_NAME, "a"):
                title = event.find_element(By.CLASS_NAME, "card-side__title").text
                link = event.get_attribute("href")
                
                file.write(f"{title}: {link},\n")