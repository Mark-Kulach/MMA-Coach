import cv2
import numpy as np
import pyautogui
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import psycopg2
import os


def connect_to_db():
    if os.name == "nt":
        DB_HOST = input("HOST:") + ".tcp.ngrok.io"
        DB_PORT = input("PORT:")

    else:
        DB_HOST = 'localhost'
        DB_PORT = 5432
        
    DB_NAME = 'mma_coach'
    DB_USER = 'postgres'

    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, port=DB_PORT)
    cursor = conn.cursor()
    
    return conn, cursor


def end_of_video(driver):
    try:
        driver.find_element(By.XPATH, "//div[@class='btn btn-play']")
        return True  
    except NoSuchElementException:
        return False


def main():
    input("PRESS ENTER TO START: ")

    driver = webdriver.Chrome()
    conn, cursor = connect_to_db()
    current_event = 1

    cursor.execute("SELECT video_link FROM events WHERE id = %s", (current_event))
    link = cursor.fetchone()
    driver.get(link[0])
    time.sleep(5)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter('screen_record.mp4', fourcc, 30.0, pyautogui.size())

    while True:
        if end_of_video(driver):
            current_event += 1
            cursor.execute("SELECT video_link FROM events WHERE id = %s", (current_event))
            link = cursor.fetchone()

            if link is None:
                break

            driver.get(link[0])
            time.sleep(5)

        img = pyautogui.screenshot()
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        out.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    out.release()
    driver.quit()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()