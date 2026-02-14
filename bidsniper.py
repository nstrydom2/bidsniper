import time
import json
from pathlib import Path
from datetime import datetime, timedelta

from faker import Faker
from playwright.sync_api import sync_playwright, Page, Response, Browser

DEBUG = False


def force_delay(delay_secs: int = 2):
    def delay(func):
        def wrapper(*args, **kwargs):
            time.sleep(delay_secs)
            return func(*args, **kwargs)
        return wrapper
    return delay


def rand_user_agent():
    Faker.seed(time.time())
    faker = Faker()
    user_agent = faker.user_agent()

    return user_agent


@force_delay(2)
def test_playwright():
    user_agent = rand_user_agent()

    with (sync_playwright() as p):
        browser = p.firefox.launch()
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()
        response = page.goto('http://nickthedev.site/')
        print(page.title())
        print(response.request.all_headers())
        print(response.all_headers())
        time.sleep(5)
        browser.close()


@force_delay(15)
def get_kbid_cookies(user: str, password: str, user_agent: str = rand_user_agent()):
    kbid_index = "https://www.k-bid.com/"
    kbid_login_url = "https://www.k-bid.com/user/login"
    with sync_playwright() as p, p.firefox.launch() as browser:
        context = browser.new_context(user_agent=user_agent)
        context.headless = False
        page = context.new_page()
        page.goto(kbid_login_url)
        page.fill("#emailAddress", user)
        page.fill("#password", password)
        page.click("button.btn:nth-child(2)")

        return context.cookies(urls=[kbid_index, kbid_login_url])


@force_delay(2)
def load_page(browser: Browser, url: str, user_agent: str = rand_user_agent(), cookiez=None):
    context = browser.new_context(user_agent=user_agent)
    if cookiez is not None:
        context.add_cookies(cookiez)

    page = context.new_page()
    return page.goto(url), page


@force_delay(1)
def snipe_bid(page: Page = None, max_bid: float = 0.0, bid_increment: float = 0.0):
    if page is None:
        raise ValueError("no page provided")

    if bid_increment < 0.0:
        raise ValueError(f"`bid_increment` must be greater than 0.0")

    page.reload()
    current_bid = float(page.locator(".lot-current-bid ").text_content())
    my_bid = current_bid + bid_increment

    if my_bid < max_bid and abs(my_bid - max_bid) < 0.01:
        bid_form = page.locator("form-control bid-lot-detail-input")
        bid_form.fill(f"{my_bid:.2f}")

        lot_bit_submit_btn = page.locator("btn btn-danger")
        lot_bit_submit_btn.click()


def save_cookies(cookiez, cookiez_path) -> None:
    with open(cookiez_path, 'w+') as cookies_file:
        json.dump(obj=cookiez, fp=cookies_file)


def is_ending_today(timeleft_str: str, days_left: int = 1) -> bool:
    hrs, mins, secs = [int(x[:-1]) for x in timeleft_str.split(' ')]
    tomorrow = datetime.now() + timedelta(days=days_left)
    time_left = timedelta(hours=hrs, minutes=mins, seconds=secs)
    return time_left < (tomorrow - datetime.now())


def is_hot_min(timeleft_str: str, sec_left: int = 60) -> bool:
    mins, secs = [int(x[:-1]) for x in timeleft_str.split(' ')]
    future_time = datetime.now() + timedelta(seconds=sec_left)
    time_left = timedelta(minutes=mins, seconds=secs)
    return time_left < (future_time - datetime.now())


if __name__ == '__main__':
    if DEBUG:
        test_playwright()

    cookies, cookies_path = None, Path('cookies.json')
    if not cookies_path.is_file():
        email = "<user_email>"
        password = "<user_password>"
        cookies = get_kbid_cookies(user=email, password=password)
        save_cookies(cookies, cookies_path)
    else:
        cookies = json.loads(cookies_path.read_text())

    lot_url = "https://www.k-bid.com/auction/62828/item/43?offset=44"
    with sync_playwright() as p, p.firefox.launch() as browser:
        response, page = load_page(browser, lot_url, cookiez=cookies)
        time_elmt = page.locator(".lot-timer").text_content()
        current_bid_elmt = page.locator("#lot_current_bid_lot_k-bid_62828_5967548")
        current_bid = float(current_bid_elmt.text_content()[1:])

        idle = True
        while idle or is_ending_today(time_elmt):
            if idle and not is_ending_today(time_elmt):
                time.sleep(300)
                continue

            idle = not is_ending_today(time_elmt)
            if len(time_elmt.split(' ')) < 3 and \
                    is_hot_min(time_elmt):
                snipe_bid(page, cookies, max_bid=40.0, bid_increment=3.35)
                time.sleep(1)
            else:
                time.sleep(5)
