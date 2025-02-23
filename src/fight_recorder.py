import cv2
import mss
import numpy as np
import sounddevice as sd
import time
import threading

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from data_scraper import login_fight_pass, connect_to_db

import drive_api

import pytesseract

def detect_end(driver):
    # Return true if play next button appears
    try:
        driver.find_element(By.XPATH, "//div[@class='btn btn-play']")
        return True  
    except NoSuchElementException:
        return False


def detect_bell():
    # Initialize flag
    global bell_sounded
    
    # Set device to virtual audio cable (makes it possible to record output audio)
    sd.default.device = 3
    # How much sound data to pull each second (44.1hz is standard)
    sample_rate = 44100
    # How long to listen (shorter = faster response, lower accuracy)
    sample_duration = 1
    
    # Run permanently in the background
    while True:
        # Record audio sample
        audio_data = sd.rec(
            int(sample_duration * sample_rate), # How much data to pull out (size of ndarray)
            samplerate=sample_rate, 
            channels=2, # Number of audio channels (2 s)
            dtype='int16' # range of sound data points (-32768, 32768)
            )
        sd.wait() # Wait until .rec finishes (.rec is non-blockingm, meaning it )

        # Convert stereo data (2 channels) into 1 channel (simpler to process)
        mono_data = np.mean(audio_data, axis=1)

        # Separate raw sound data into represents the amplitudes of different frequencies in the audio.
        fft_data = np.fft.rfft(mono_data)

        frequencies = np.fft.rfftfreq(len(mono_data), 1 / sample_rate)

        bell_freq_range = (800, 1200)

        bell_energy = np.sum(np.abs(fft_data[(frequencies >= bell_freq_range[0]) & (frequencies <= bell_freq_range[1])]))

        bell_sounded = bell_energy > 900



def record_round(driver):
    pass


def push_to_db():
    pass


def main():
    # Init frame capture / .mp4 writer
    global sct, monitor, frame_time
    sct = mss.mss()
    monitor = sct.monitors[1]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    frame_rate = 60.0
    frame_time = 1.0 / frame_rate

    # Connect to google drive API
    global service
    service = drive_api.get_service()

    # Initialize chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    login_fight_pass(driver)


    # Pull 1st event from db
    conn, cursor = connect_to_db()
    current_event = 1
    cursor.execute("SELECT video_link FROM events WHERE id = %s", (current_event,))
    link = cursor.fetchone()
    
    # go to event / start video from beginning
    driver.get(link[0])
    try:
        restart = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//a[@class='btn-play']")))
        restart.click()
    except TimeoutException:
        pass

    # Turn on bell detection in the background
    threading.Thread(target=detect_bell, daemon=True).start()

    # Pull fighters db
    cursor.execute("SELECT id, first_name, last_name, nickname FROM fighters")
    fighters = cursor.fetchall()

    while True:
        if detect_end(driver):
            # Go to next event
            current_event += 1
            cursor.execute("SELECT video_link FROM events WHERE id = %s", (current_event,))
            fight_id = None
            link = cursor.fetchone()

            # Break out of loop if no next event
            if link is None:
                break
            
            # go to event / start video from beginning
            driver.get(link[0])
            try:
                restart = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(By.XPATH, "//a[@class='btn-play']"))
                restart.click()
            except TimeoutException:
                pass
    
        if bell_sounded:
            bell_sounded = False
            
            current_round = 1
            fight_id, num_rounds = find_fight(fighters)

            folder_metadata = {
                'name': str(fight_id),
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': ['18PXrlm5SE1FUY7VloiHfIGUADD21_sWb']
            }

            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')

            while current_round <= num_rounds:
                out = cv2.VideoWriter(f'{current_round}.mp4', fourcc, frame_rate, (1920, 1080))

                while not bell_sounded:
                    start_time = time.time()

                    # take screenshot, convert into cv2 format, write to video file
                    sct_img = sct.grab(monitor)
                    frame = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
                    out.write(frame)

                    elapsed_time = time.time() - start_time

                    if elapsed_time < frame_time:
                        time.sleep(frame_time - elapsed_time)
                    
                out.release()
                file_metadata = {
                    'name': f"{current_round}.mp4",
                    'parents': [folder_id],
                    'mimeType': 'video/mp4'
                }

                media = drive_api.MediaFileUpload(f"{current_round}.mp4", mimetype='video/mp4')
                service.files().create(body=file_metadata, media_body=media, fields='id').execute()

                current_round += 1


        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Close chromedriver
    driver.quit()


# Make imports possible
if __name__ == "__main__":#
    main()