import os
import sys
import time
import requests
from datetime import datetime
from strategies_database import get_strategy_by_day
from renderer import render_strategy_card

BUFFER_PROFILE_ID = "6ab2ba02ea19ca0bdeb83136"  # BLC LinkedIn Business Page
FREEIMAGE_API_KEY = "6d207e641835d34fc82813587b1c3144"

def upload_image_to_cdn(image_path):
    print("Uploading strategy image to FreeImage CDN...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    with open(image_path, "rb") as f:
        files = {"source": f}
        data = {
            "key": FREEIMAGE_API_KEY,
            "action": "upload",
            "format": "json"
        }
        res = requests.post(
            "https://freeimage.host/api/1/upload",
            files=files,
            data=data,
            headers=headers,
            timeout=(5.0, 15.0)
        )
        res.raise_for_status()
        json_data = res.json()
        image_url = json_data["image"]["url"]
        print(f"CDN Upload successful: {image_url}")
        return image_url

def post_to_buffer(buffer_token, text, image_url):
    print(f"Posting strategy to Buffer channel {BUFFER_PROFILE_ID}...")
    url = "https://api.bufferapp.com/1/updates/create.json"
    payload = {
        "access_token": buffer_token,
        "profile_ids[]": [BUFFER_PROFILE_ID],
        "text": text,
        "media[picture]": image_url,
        "media[photo]": image_url,
        "now": "true"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    res = requests.post(url, data=payload, headers=headers, timeout=(5.0, 15.0))
    res.raise_for_status()
    result = res.json()
    print("Successfully posted strategy to Buffer!")
    return result

def main():
    print(f"Starting BLC LinkedIn Strategy Publisher - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    strategy = get_strategy_by_day()
    print(f"Selected Strategy #{strategy['id']}: {strategy['title']}")

    out_image = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendered_strategy.jpg")
    render_strategy_card(
        tag_text=strategy["badge"],
        title_text=strategy["title"],
        body_text=strategy["body"],
        takeaway_text=strategy["takeaway"],
        output_path=out_image
    )
    print(f"Strategy card rendered cleanly to {out_image}")

    buffer_token = os.environ.get("BUFFER_TOKEN")
    if not buffer_token:
        print("BUFFER_TOKEN not set in environment. Skipping live Buffer post (local render test completed).")
        return

    cdn_url = upload_image_to_cdn(out_image)
    post_to_buffer(buffer_token, strategy["caption"], cdn_url)

    # Record history
    history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategy_history.txt")
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - Playbook #{strategy['id']} - {strategy['title']}\n")
    print("Strategy history updated.")

if __name__ == "__main__":
    main()
