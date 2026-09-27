import os
import sys
import time
import requests
from datetime import datetime
from strategies_database import get_strategy_by_day
from renderer import render_strategy_card

BUFFER_TOKEN = (os.environ.get("BUFFER_TOKEN") or "").strip().strip('"').strip("'")
FREEIMAGE_API_KEY = "6d207e02198a847aa98d0a2a901485a5"

def upload_image_to_cdn(image_path):
    ua_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    image_url = None

    # Provider 1: Catbox.moe (Direct static image CDN with explicit filename)
    try:
        with open(image_path, "rb") as f:
            r_cat = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (os.path.basename(image_path), f, "image/jpeg")},
                headers=ua_headers,
                timeout=(10.0, 30.0)
            )
            if r_cat.status_code == 200 and r_cat.text.startswith("http"):
                image_url = r_cat.text.strip()
                print(f"CDN Provider 1 (Catbox) success: {image_url}")
    except Exception as e:
        print(f"CDN Provider 1 (Catbox) note: {e}")

    # Provider 2: Direct GitHub Raw / jsDelivr CDN
    if not image_url:
        try:
            gh_raw = f"https://raw.githubusercontent.com/prateek-upmanyu/LINKEDIN-STRATEGIES-BLC/master/{os.path.basename(image_path)}"
            r_gh = requests.head(gh_raw, timeout=(5.0, 10.0))
            if r_gh.status_code == 200 and "image" in r_gh.headers.get("Content-Type", ""):
                image_url = gh_raw
                print(f"CDN Provider 2 (GitHub Raw) success: {image_url}")
        except Exception as e:
            print(f"CDN Provider 2 (GitHub Raw) note: {e}")

    # Provider 3: FreeImage.host
    if not image_url:
        try:
            with open(image_path, "rb") as f:
                r_free = requests.post(
                    "https://freeimage.host/api/1/upload",
                    data={"key": FREEIMAGE_API_KEY, "action": "upload"},
                    files={"source": (os.path.basename(image_path), f, "image/jpeg")},
                    headers=ua_headers,
                    timeout=(5.0, 15.0)
                )
                if r_free.status_code == 200:
                    image_url = r_free.json().get("image", {}).get("url")
                    if image_url:
                        print(f"CDN Provider 3 (FreeImage) success: {image_url}")
        except Exception as e:
            print(f"CDN Provider 3 (FreeImage) note: {e}")

    if not image_url:
        raise RuntimeError("Failed to upload image to any public CDN for Buffer.")

    time.sleep(1.5)
    return image_url

def post_to_buffer(token, caption, image_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    url = "https://api.buffer.com"

    # 1. Fetch organization ID
    q_org = {"query": "query { account { organizations { id name } } }"}
    r_org = requests.post(url, headers=headers, json=q_org, timeout=(4.0, 10.0))
    if r_org.status_code != 200 or "data" not in r_org.json():
        raise RuntimeError(f"Buffer organization query failed: {r_org.text}")
    
    orgs = r_org.json()["data"]["account"]["organizations"]
    if not orgs:
        raise RuntimeError("No organizations found in Buffer account.")
    org_id = orgs[0]["id"]

    # 2. Fetch channels (LinkedIn Business Page)
    q_chan = {
        "query": "query GetChannels($input: ChannelsInput!) { channels(input: $input) { id name service type } }",
        "variables": {"input": {"organizationId": org_id}}
    }
    r_chan = requests.post(url, headers=headers, json=q_chan, timeout=(4.0, 10.0))
    if r_chan.status_code != 200 or "data" not in r_chan.json():
        raise RuntimeError(f"Buffer channels query failed: {r_chan.text}")
    
    channels = r_chan.json()["data"]["channels"]
    target_channel = None
    for c in channels:
        if c.get("service") == "linkedin":
            target_channel = c
            break
    
    if not target_channel:
        raise RuntimeError("No connected LinkedIn channel found in Buffer.")
    
    channel_id = target_channel["id"]
    channel_name = target_channel["name"]
    print(f"Targeting Buffer channel: '{channel_name}' (ID: {channel_id})")

    # 3. Create post via Buffer GraphQL API
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            status
          }
        }
        ... on InvalidInputError {
          message
        }
        ... on UnexpectedError {
          message
        }
        ... on RestProxyError {
          message
        }
      }
    }
    """

    variables = {
      "input": {
        "channelId": channel_id,
        "text": caption,
        "mode": "shareNow",
        "schedulingType": "automatic",
        "assets": [
          {
            "image": {
              "url": image_url
            }
          }
        ]
      }
    }

    res = requests.post(url, headers=headers, json={"query": mutation, "variables": variables}, timeout=(5.0, 15.0))
    if res.status_code != 200:
        raise RuntimeError(f"Buffer API request failed: {res.status_code} - {res.text}")
    
    res_data = res.json()
    create_res = res_data.get("data", {}).get("createPost", {})
    if "post" in create_res:
        post_id = create_res["post"]["id"]
        status = create_res["post"]["status"]
        print(f"Buffer post created successfully! Post ID: {post_id} (Status: {status})")
        return post_id
    elif "message" in create_res:
        raise RuntimeError(f"Buffer post creation failed: {create_res['message']}")
    else:
        raise RuntimeError(f"Buffer post creation failed: {res.text}")

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

    if not BUFFER_TOKEN:
        raise RuntimeError("BUFFER_TOKEN secret is missing or empty. Please set it in GitHub repository secrets.")

    cdn_url = upload_image_to_cdn(out_image)
    post_to_buffer(BUFFER_TOKEN, strategy["caption"], cdn_url)

    # Record history
    history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategy_history.txt")
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - Playbook #{strategy['id']} - {strategy['title']}\n")
    print("Strategy history updated successfully.")

if __name__ == "__main__":
    main()
