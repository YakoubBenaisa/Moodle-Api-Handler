import json
import re
import requests
import logging

logger = logging.getLogger(__name__)

class MoodleTerminator:
    def __init__(self, session_cookies, university_name):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
        })
        self.session.cookies.update(session_cookies)

    def _extract_cfg(self, html):
        # Fix: Adjust regex to match unescaped JS variable
        match = re.search(r'M\.cfg\s*=\s*({.*?});', html, re.DOTALL)
        if not match:
            raise ValueError("M.cfg block not found")
        return json.loads(match.group(1))

    def get_notifications(self):
        # Step 1: Load the main page to retrieve sesskey and userId
        resp = self.session.get(
            f'https://elearning.univ-{university_name}.dz/',
            headers={'Referer': 'https://google.com'}
        )
        resp.raise_for_status()

        # Step 2: Extract M.cfg JSON
        cfg = self._extract_cfg(resp.text)
        sesskey = cfg.get('sesskey')
        userid  = cfg.get('userId')
        if not sesskey or not userid:
            raise RuntimeError(f"Failed to extract sesskey/userId from M.cfg: {cfg}")

        # Step 3: Build the AJAX payload with correct parameters
        payload = [{
            "index":      0,
            "methodname": "message_popup_get_popup_notifications",
            "args": {
                "useridto": userid,
                "limit":    20,
                "offset":   0
            }
        }]

        # Step 4: Call the AJAX service
        api_url = "https://elearning.univ-bba.dz/lib/ajax/service.php"
        params = {
            'sesskey': sesskey,
            'info': 'message_popup_get_popup_notifications'
        }
        r2 = self.session.post(
            api_url,
            params=params,
            json=payload,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type':      'application/json',
                'Origin':            'https://elearning.univ-bba.dz'
            }
        )
        r2.raise_for_status()

        # Step 5: Parse and return the notifications
        data = r2.json()
        if not isinstance(data, list) or not data:
            raise RuntimeError(f"Unexpected response format: {data}")
        first = data[0]
        if first.get('exception') or first.get('error'):
            raise RuntimeError(f"Moodle API Error: {first}")

        # Get the data from the response
        response_data = first.get('data', [])

        # Check if the data is a dictionary with 'notifications' key
        if isinstance(response_data, dict) and 'notifications' in response_data:
            logger.info(f"Found notifications in response: {len(response_data.get('notifications', []))}")
            return response_data.get('notifications', [])

        # Otherwise, return the data as is (assuming it's a list of notifications)
        return response_data


def get_notifications(session_cookies):
    """
    Helper function to get notifications using the MoodleTerminator class.

    Args:
        session_cookies (dict): Dictionary containing session cookies

    Returns:
        list: List of notification objects
    """
    try:
        terminator = MoodleTerminator(session_cookies)
        return terminator.get_notifications()
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise

if __name__ == "__main__":
    # Replace these with your actual session values
    session_cookies = {
        "MoodleSession": "4pt6t3dmk2u2me8vjmud01qjgi",
        "MOODLEID1_": "sodium%3A1vGOgBrc2dmDXVjgN99WHMvOWThOCBycs%2BV9vUpnF6My0XCFj0IcEW4neH4qHAbBftx5JMKRlg%3D%3D"
    }

    try:
        notifs = get_notifications(session_cookies)
        print(f"Captured {len(notifs)} notifications:")
        print(notifs)
    except Exception as e:
        print("Error fetching notifications:", e)