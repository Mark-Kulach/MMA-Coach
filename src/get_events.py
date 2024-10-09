import time
import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

def login(bot):
    bot.get('https://ufcfightpass.com/login/')
    
    cookies = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
    cookies.click()

    username_input = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']")))
    password_input = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password']")))

    username_input.clear()
    username_input.send_keys("mark@markkulach.com")
    password_input.clear()
    password_input.send_keys("3TJBiKqvXzJ!H9s")

    login_button = WebDriverWait(bot, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    login_button.click()

    time.sleep(10)


def get_events(bot):
    data = [["events", "title", "link"]]

    seasons = [
        "https://ufcfightpass.com/season/24048",  
        "https://ufcfightpass.com/season/24050",
        "https://ufcfightpass.com/season/24049",
        "https://ufcfightpass.com/season/24051",
        "https://ufcfightpass.com/season/24053",
        "https://ufcfightpass.com/season/24054"
    ]

    for season in seasons:
        bot.get(season)
            
        input("DONE:")

        for event in reversed(bot.find_elements(By.XPATH, "//a[contains(@href, '/video/')]")):
                title = event.find_element(By.CLASS_NAME, "card-side__title").text
                link = event.get_attribute("href")

                data.append([title, link])
            
    return data


def push_to_db(data):
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = 'mma_coach'
    DB_USER = 'postgres'

    formatting = data.pop(0)
    title = formatting[0]
    columns = formatting[1:]

    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, port=DB_PORT)
    cursor = conn.cursor()

    sql_types = {
        int: "INTEGER",
        float: "FLOAT",
        str: "TEXT",
        bool: "BOOLEAN",
        bytes: "BLOB"
    }

    cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables 
                WHERE table_name = %s
                AND table_schema = 'public'
            );
        """, (title,))
        
    if not cursor.fetchone()[0]:
        formatted_columns = [column + " " + sql_types[type(column)] for column in columns]
        cursor.execute(f"CREATE TABLE {title} (\n    " + ",\n    ".join(formatted_columns) + "\n);")

    for values in data:
        query = f"INSERT INTO {title} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))})"
        cursor.execute(query, values)


    conn.commit()
    cursor.close()
    conn.close()


def main():
    driver = webdriver.Chrome()

    login(driver)
    events = get_events(driver)
    push_to_db(events)
    
    driver.quit()


if __name__ == "__main__":
    main()