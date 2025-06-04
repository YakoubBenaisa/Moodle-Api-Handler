
import requests, json
from bs4 import BeautifulSoup


def login(username, password, university_name):


    login_url = f"https://elearning.univ-{university_name}.dz/login/index.php"

    session = requests.Session()
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, "html.parser")
    login_token = soup.find("input", {"name": "logintoken"})["value"]
    with open("login.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    login_data = {
        "username": username,
        "password": password,
        "logintoken": login_token,
    }

    response = session.post(login_url, data=login_data)
    if response.status_code != 200 or "La connexion a échoué, veuillez réessayer" in response.text:
        return "Login failed"
        #raise Exception("[-] Login failed")
    if "Utilisateurs en ligne" in response.text:
        print("[+] Login successful")
        cookies_dict = session.cookies.get_dict()
        cookies_json = json.dumps(cookies_dict)
        return cookies_json
    return None



