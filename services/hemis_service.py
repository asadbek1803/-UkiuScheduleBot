import logging
import requests
import re
import time
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Optional

LOGIN_URL     = "https://student.ukiu.uz/dashboard/login"
CAPTCHA_URL   = "https://student.ukiu.uz/dashboard/captcha"
TIMETABLE_URL = "https://student.ukiu.uz/education/time-table"
PROFILE_URL   = "https://student.ukiu.uz/student/profile"
DASHBOARD_URL = "https://student.ukiu.uz/dashboard"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_hemis_lock        = asyncio.Lock()
_last_request_time = 0.0
_MIN_INTERVAL      = 2.0


def _wait():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.time()


def _get(session: requests.Session, url: str, **kwargs) -> requests.Response:
    _wait()
    return session.get(url, **kwargs)


def _post(session: requests.Session, url: str, **kwargs) -> requests.Response:
    _wait()
    return session.post(url, **kwargs)


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent":                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language":           "uz,ru;q=0.9,en;q=0.8",
        "Accept-Encoding":           "gzip, deflate, br",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":            "document",
        "Sec-Fetch-Mode":            "navigate",
        "Sec-Fetch-Site":            "none",
        "Sec-Fetch-User":            "?1",
        "Cache-Control":             "max-age=0",
    })
    return session


def get_hemis_captcha(
    session: requests.Session,
) -> Tuple[Optional[str], Optional[bytes], Optional[Dict]]:
    try:
        logger.info("Login sahifasi yuklanmoqda...")
        response = _get(session, LOGIN_URL, timeout=15)
        response.raise_for_status()

        csrf = None
        for pattern in [
            r'name="_csrf-frontend" value="(.+?)"',
            r'name="csrf-token" content="(.+?)"',
            r'csrf-token" content="(.+?)"',
        ]:
            match = re.search(pattern, response.text)
            if match:
                csrf = match.group(1)
                break

        if not csrf:
            logger.error("CSRF token topilmadi")
            return None, None, None

        logger.info(f"CSRF token olindi: {csrf[:20]}...")
        time.sleep(1.5)

        logger.info("Captcha yuklanmoqda...")
        captcha_response = _get(session, CAPTCHA_URL, timeout=15)
        captcha_response.raise_for_status()
        logger.info(f"Captcha olindi: {len(captcha_response.content)} bytes")

        return csrf, captcha_response.content, session.cookies.get_dict()

    except requests.exceptions.Timeout:
        logger.error("HEMIS so'rovi timeout")
        return None, None, None
    except requests.exceptions.RequestException as e:
        logger.error(f"Tarmoq xatoligi (captcha): {e}")
        return None, None, None
    except Exception as e:
        logger.error(f"Kutilmagan xatolik (captcha): {e}")
        return None, None, None


def hemis_login(
    session: requests.Session,
    csrf: str,
    login: str,
    password: str,
    captcha_code: str,
) -> Tuple[bool, Optional[str]]:
    try:
        response = _post(
            session,
            LOGIN_URL,
            data={
                "_csrf-frontend":              csrf,
                "FormStudentLogin[login]":     login,
                "FormStudentLogin[password]":  password,
                "FormStudentLogin[reCaptcha]": captcha_code,
            },
            headers={
                "Referer":      LOGIN_URL,
                "Origin":       "https://student.ukiu.uz",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            allow_redirects=True,
            timeout=15,
        )
    except requests.exceptions.Timeout:
        logger.error("Login so'rovi timeout")
        return False, "Server javob bermadi. Qaytadan urinib ko'ring."
    except requests.exceptions.RequestException as e:
        logger.error(f"Login tarmoq xatoligi: {e}")
        return False, "Tarmoq xatoligi. Qaytadan urinib ko'ring."

    if "login" not in response.url.lower():
        return True, None

    text = response.text.lower()
    if "captcha" in text:
        return False, "Captcha noto'g'ri"
    if "kiritgan ma'lumotlaringizni tekshirib bo'lmadi" in text:
        return False, "Login yoki parol noto'g'ri"

    return False, "Login amalga oshmadi"


def fetch_schedule(session: requests.Session, week_id: str = None) -> List[Dict]:
    url = f"{TIMETABLE_URL}?week={week_id}" if week_id else TIMETABLE_URL
    logger.info(f"Jadval yuklanmoqda: {url}")

    try:
        response = _get(session, url, allow_redirects=True, timeout=15)
    except requests.exceptions.Timeout:
        logger.error("Jadval so'rovi timeout")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Jadval tarmoq xatoligi: {e}")
        return []

    if "login" in response.url.lower():
        logger.error("Session tugagan — login sahifasiga yo'naltirildi")
        return []

    if response.status_code != 200:
        logger.error(f"Jadval sahifasi xatoligi: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    days = soup.select("div.box.box-success.sh")
    logger.info(f"{len(days)} ta kun topildi")

    parsed_lessons = []
    for day in days:
        day_title_elem = day.select_one(".box-title")
        raw_title = day_title_elem.text.strip() if day_title_elem else "Unknown"
        day_title = raw_title.split("\n")[0].strip()

        for lesson in day.select("li.list-group-item"):
            time_node   = lesson.select_one(".pull-right")
            lesson_time = time_node.text.strip() if time_node else ""

            lines = [
                line.strip()
                for line in lesson.text.replace(lesson_time, "").split("\n")
                if line.strip()
            ]

            subject     = lines[0] if len(lines) > 0 else ""
            room        = lines[1] if len(lines) > 1 else ""
            lesson_type = lines[2] if len(lines) > 2 else ""
            teacher     = lines[3] if len(lines) > 3 else ""

            pair_match  = re.search(r'(\d+)-juftlik', subject)
            pair_number = int(pair_match.group(1)) if pair_match else 0

            parsed_lessons.append({
                "day":         day_title,
                "pair_number": pair_number,
                "subject":     subject,
                "teacher":     teacher,
                "room":        room,
                "lesson_type": lesson_type,
                "lesson_time": lesson_time,
            })

    return parsed_lessons


def get_student_group(session: requests.Session) -> Optional[str]:
    try:
        response = _get(session, DASHBOARD_URL, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        span = soup.find("span", class_="user-role")
        if span and span.text:
            return span.text.strip()

        for pattern in [r'Guruh:\s*([A-Z0-9\-]+)', r'Group:\s*([A-Z0-9\-]+)']:
            match = re.search(pattern, response.text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None
    except Exception as e:
        logger.error(f"Guruh olishda xatolik: {e}")
        return None


def check_login_status(session: requests.Session) -> bool:
    try:
        response = _get(session, DASHBOARD_URL, timeout=15, allow_redirects=False)

        if response.status_code in [301, 302, 303, 307, 308]:
            if "login" in response.headers.get("Location", "").lower():
                return False

        return response.status_code == 200 and "dashboard" in response.url.lower()
    except Exception as e:
        logger.error(f"Login status tekshirishda xatolik: {e}")
        return False


def get_current_week_id(session: requests.Session) -> Optional[str]:
    try:
        response = _get(session, TIMETABLE_URL, timeout=15)
    except Exception as e:
        logger.error(f"get_current_week_id xatoligi: {e}")
        return None

    soup    = BeautifulSoup(response.text, "html.parser")
    options = soup.select("select option")
    now     = datetime.now()

    months = {
        "yanvar": 1,  "fevral": 2,  "mart": 3,   "aprel": 4,
        "may": 5,     "iyun": 6,    "iyul": 7,    "avgust": 8,
        "sentabr": 9, "oktabr": 10, "noyabr": 11, "dekabr": 12,
    }

    for opt in options:
        matches = re.findall(r'(\d{1,2})\s*(\w+)', opt.text.lower().strip())
        if len(matches) < 2:
            continue

        try:
            start = datetime(now.year, months.get(matches[0][1], now.month), int(matches[0][0]))
            end   = datetime(now.year, months.get(matches[1][1], now.month), int(matches[1][0]))
        except ValueError:
            continue

        if start <= now <= end:
            return opt.get("value")

    return None
