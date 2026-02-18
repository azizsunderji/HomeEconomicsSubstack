"""
Capture screenshot of PyDeck HTML map using Selenium.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os

OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/outputs"
html_path = f"{OUTPUT_DIR}/domestic_migration_3d_interactive.html"
output_path = f"{OUTPUT_DIR}/domestic_migration_3d_screenshot.png"

print("Setting up headless Chrome...")

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=2700,2250")
chrome_options.add_argument("--hide-scrollbars")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

try:
    # Try to create driver
    driver = webdriver.Chrome(options=chrome_options)

    print(f"Loading HTML file...")
    driver.get(f"file://{html_path}")

    # Wait for map to render
    print("Waiting for map to render...")
    time.sleep(8)  # Give deck.gl time to load and render

    # Take screenshot
    print(f"Capturing screenshot...")
    driver.save_screenshot(output_path)

    driver.quit()
    print(f"\nSaved: {output_path}")

except Exception as e:
    print(f"Error: {e}")
    print("\nFallback: Open the HTML file manually in Chrome and screenshot.")
    print(f"HTML file: {html_path}")
