"""
Run this using PC in basement

1. Iterate through each event
2. Screen record each round
3. Pull out data for that specific round
4. Store data
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Set chrome profile to default
chrome_options = Options()
chrome_options.add_argument(r"--user-data-dir=C:\\Users\\kulac\AppData\\Local\\Google\\Chrome\\User Data")
chrome_options.add_argument("--profile-directory=Default")

# Open chrome
driver = webdriver.Chrome(options=chrome_options)

# Go to FightPass
driver.get('https://ufcfightpass.com/season/24054')