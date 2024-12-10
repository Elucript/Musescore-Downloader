import img2pdf
import os
from playwright.sync_api import sync_playwright
import requests
import sys
import time
import nocairosvg
import json


if getattr(sys, 'frozen', False):
    script_dir = os.path.dirname(sys.executable)
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))

root_dir = os.path.join(script_dir, "core")
svg_folder = os.path.join(root_dir, "svg")
png_folder = os.path.join(root_dir, "png")
pdf_folder = os.path.join(script_dir, "exported sheet music")
midi_folder = os.path.join(script_dir, "midi exports")

os.makedirs(svg_folder, exist_ok=True)
os.makedirs(png_folder, exist_ok=True)
os.makedirs(pdf_folder, exist_ok=True)
os.makedirs(midi_folder, exist_ok=True)

url = 'https://musescore.com/user/34008453/scores/15304666'
score_name = ""


def scrape(p):
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    def handle_response(response):
        if "/api/jmuse" in response.url and "midi" in response.url:
            print(f"Intercepted Response URL: {response.url}")
            try:

                response_body = response.json()
                print("Captured Response Data:")
                print(json.dumps(response_body, indent=4))

                midi_url = response_body.get("info", {}).get("url")
                if midi_url:
                    print(f"Extracted MIDI URL: {midi_url}")
                    download_midi(midi_url)
                else:
                    print("No MIDI URL found in the response.")
            except Exception as e:
                print(f"Error parsing response: {e}")

    def download_midi(midi_url):
        response = requests.get(midi_url)
        if response.status_code == 200:
            midi_filename = os.path.join(midi_folder, f"{score_name}.midi")
            with open(midi_filename, 'wb') as f:
                f.write(response.content)
                print(f"MIDI downloaded to {midi_filename}")
        else:
            print(f"Failed to download MIDI. HTTP status code: {response.status_code}")

    page.on("response", handle_response)
    page.goto(url, timeout=0)

    svg_elements = page.wait_for_selector('.EEnGW.F16e6', timeout=30000)
    img_elements = page.locator('.EEnGW.F16e6').element_handles()

    for index, element in enumerate(img_elements):
        element.scroll_into_view_if_needed()
        time.sleep(3)  
        svg = element.query_selector('.KfFlO')
        if svg is not None:
            grabSvg(svg, index)
        else:
            print(f"No SVG found for img element at index {index}")

    page.goto(f"{url}/piano-tutorial", timeout=0)
    browser.close()

    
def grabSvg(svg, index):
    img_src = svg.get_attribute('src')
    svg_filename = os.path.join(svg_folder, f"{index}.svg")
    response = requests.get(img_src)
    with open(svg_filename, 'wb') as f:
        f.write(response.content)
        print(f"Downloaded {svg_filename}")

def convertToPng():
    i = 0
    for filename in sorted(os.listdir(svg_folder), key=lambda x: int(x.split('.')[0])):  # Ensure files are sorted numerically
        if not filename.endswith(".svg"): continue
        svg_path = os.path.join(svg_folder, filename)
        png_path = os.path.join(png_folder, f"{i}.png")
        nocairosvg.svg2png(url=svg_path, write_to=png_path)
        print(f"Converted {filename} to {png_folder}")
        i += 1
        
    print("All SVGs have been converted!")
    
    for filename in sorted(os.listdir(svg_folder), key=lambda x: int(x.split('.')[0])):  # Sort before deleting
        if not filename.endswith(".svg"): continue
        os.remove(os.path.join(svg_folder, filename))
        print(f"Deleted {filename} from {svg_folder}")
        
    print("Removed all SVGs!")
    

def createPdf():
    files = [f for f in os.listdir(png_folder) if f.endswith('.png')]

    # Sort the files numerically
    files_sorted = sorted(files, key=lambda x: int(x.split('.')[0]))

    # Print the sorted list of files
    print(files_sorted)

    pdf_data = img2pdf.convert([os.path.join(png_folder, filename) for filename in files_sorted])  
    
    with open(os.path.join(pdf_folder, f"{score_name}.pdf"), "wb") as pdf:
        pdf.write(pdf_data)

    for filename in sorted(os.listdir(png_folder), key=lambda x: int(x.split('.')[0])):  # Sort before deleting
        if filename.endswith(".png"):
            os.remove(os.path.join(png_folder, filename))
            print(f"Deleted {filename} from {png_folder}")
        
    print("Removed all PNGs!")
    print("\n\n\nPdf has been made!")
    print("midi is downloaded!")

if __name__ == "__main__":
    url = input("Provide musecore.com link: ")
    score_name = input("Inset PDF File Name: ")
    with sync_playwright() as playwright:
        scrape(playwright)
    time.sleep(2)
    convertToPng()
    createPdf()
