import psycopg2
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Database connection settings
DB_HOST = 'localhost'
DB_NAME = 'mma_coach'
DB_USER = 'postgres'  # replace with your PostgreSQL username
DB_PASS = 'R@M$frappes1'  # replace with your PostgreSQL password

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

    # Connect to PostgreSQL database
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    cursor = conn.cursor()

    for section in SECTIONS:
        driver.get(section)

        input("Page Loaded -- input enter once all events are loaded in:")

        for event in driver.find_element(By.CLASS_NAME, "card-list").find_elements(By.TAG_NAME, "a"):
            title = event.find_element(By.CLASS_NAME, "card-side__title").text
            link = event.get_attribute("href")

            # Insert event into the database
            cursor.execute("INSERT INTO events (title, link) VALUES (%s, %s)", (title, link))

    # Commit the changes and close the database connection
    conn.commit()
    cursor.close()
    conn.close()

get_events()

driver.quit()