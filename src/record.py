"""
Run this using PC in basement

1. Iterate through each event
2. Screen record each round
3. Pull out data for that specific round
4. Store data
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Set up Chrome options
chrome_options = Options()

# Replace <YourUsername> with your actual Windows username
chrome_options.add_argument(r"--user-data-dir=C:\\Users\\kulac\AppData\\Local\\Google\\Chrome\\User Data")
chrome_options.add_argument("--profile-directory=Default")  # Change 'Default' if you use a different Chrome profile

# Optionally, set the path to chromedriver.exe if it's not in the PATH environment variable
# driver = webdriver.Chrome(executable_path=r'C:\path\to\chromedriver.exe', options=chrome_options)

# Initialize the WebDriver with the specified options
driver = webdriver.Chrome(options=chrome_options)

# Open the webpage
driver.get('https://ufcfightpass.com/season/24054')

input()

# Close the browser once done enter is pressed
driver.quit()