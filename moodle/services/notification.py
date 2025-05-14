import json
import re
import requests

def get_notifications(session):
    # 1. Get main page with proper headers
    resp = session.get(
        'https://elearning.univ-bba.dz/',
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    )
    resp.raise_for_status()

    # 2. Extract configuration using precise regex
    config_json = re.search(r'M\.cfg\s*=\s*({.*?});', resp.text, flags=re.DOTALL)
    if not config_json:
        raise RuntimeError("Moodle configuration not found in page")
    
    try:
        cfg = json.loads(config_json.group(1))
        sesskey = cfg['sesskey']
        userid = cfg['userId']  # Keep as string
    except (KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Config parsing failed: {str(e)}")

    # 3. Prepare EXACT browser-like request
    service_url = 'https://elearning.univ-bba.dz/lib/ajax/service.php'
    headers = {
        'Authority': 'elearning.univ-bba.dz',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/json',
        'Origin': 'https://elearning.univ-bba.dz',
        'Referer': 'https://elearning.univ-bba.dz/',
        'X-Requested-With': 'XMLHttpRequest'
    }

    payload = [{
        "index":0,
        "methodname":"message_popup_get_popup_notifications",
        "args":{
            "useridto": userid,
            "limitnum":50,
            "offset":0,
            "newestfirst":1  # Required by this specific Moodle version
        }
    }]

    # 4. Send with session key in BOTH URL and POST data
    try:
        resp = session.post(
            f"{service_url}?sesskey={sesskey}",
            json=payload,
            headers=headers
        )
        resp.raise_for_status()
        
        # Debug output
        print("Raw response:", resp.text)
        
        data = resp.json()
        if data[0].get('error'):
            raise RuntimeError(f"Moodle API error: {data[0]['exception']['message']}")
            
        return data[0]['data']
        
    except Exception as e:
        print(f"Request failed. Final payload:\n{json.dumps(payload, indent=2)}")
        raise

if __name__ == "__main__":
    # Configure session with browser-like cookies
    session = requests.Session()
    session.cookies.update({
        'MoodleSession': 'gf5ts21uv1ou7087hor3rprrgj',
        'MOODLEID1_': 'sodium%3AjkCWaOoLnlfmY106fl1ek%2FdDP3Mi7FJXWtx4a6yHp7SuO3M7ufH%2BDeQU%2FdNM4hDhDak2VclXIw%3D%3D'
    })
    
    try:
        notifications = get_notifications(session)
        print(f"Success! Found {len(notifications)} notifications:")
        for idx, n in enumerate(notifications, 1):
            print(f"{idx}. [{n['timecreated']}] {n['smallmessage']}")
    except Exception as e:
        print(f"Final error: {str(e)}")