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

def detect_end(driver):
    # Return true if play next button appears
    try:
        driver.find_element(By.XPATH, "//div[@class='btn btn-play']")
        return True  
    except NoSuchElementException:
        return False


def detect_bell():
    global bell_sounded
    
    # Set up device and audio parameters
    device_index = 1  # Replace with your actual device index after checking sd.query_devices()
    sd.default.device = device_index
    sample_rate = 44100  # CD-quality audio
    sample_duration = 0.5  # Duration of each sample in seconds
    
    # Frequency range for the bell (in Hz), assuming it has a distinct sound
    bell_frequency = 1000  # Example frequency, adjust based on your bell sound
    frequency_tolerance = 50  # +/- range around bell frequency
    
    # Convert bell frequency to FFT bin index
    fft_size = int(sample_rate * sample_duration)
    bell_index = int(bell_frequency / (sample_rate / fft_size))
    tolerance_index = int(frequency_tolerance / (sample_rate / fft_size))
    
    # Continuously listen for bell sound
    while True:
        # Record audio data
        audio_data = sd.rec(int(sample_duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()  # Wait until recording is complete
        
        # Process audio data to detect bell
        audio_data = audio_data.flatten()  # Flatten to mono if stereo
        fft_data = np.abs(fft(audio_data))  # Perform FFT and get magnitude spectrum
        
        # Check if bell frequency magnitude is above a threshold
        bell_magnitude = np.max(fft_data[bell_index - tolerance_index:bell_index + tolerance_index])
        detection_threshold = 1000  # Threshold for bell detection, adjust as needed
        
        if bell_magnitude > detection_threshold:
            bell_sounded = True



def find_fight():
    # FIX: db structure
    """
    1. Pull all videos you missed
    2. Order them correctly in events
    3. Pull a list of fight_names given each video link (chronological)
    4. Fix ordering / ids of fights_table given this data (saved in json?)
    """

    pass

def record_round(driver):
    pass


def push_to_db():
    pass


def main():
    # Init frame capture / .mp4 writer
    sct = mss.mss()
    monitor = sct.monitors[1]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    frame_rate = 60.0
    frame_time = 1.0 / frame_rate

    # Connect to google drive API
    global service
    service = drive_api.get_service()

    # Initialize chrome and db
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    conn, cursor = connect_to_db()
    login_fight_pass(driver)

    # Pull event from db
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
            fight_id, num_rounds = find_fight()

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