#!/usr/bin/env python3
from datetime import date, timedelta
import re
from argparse import ArgumentParser
import requests
from bs4 import BeautifulSoup


# https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
COLOR_ERROR = "\033[31m"
COLOR_PRICE = "\033[32m"
COLOR_HEADER = "\033[36m\033[01m"
COLOR_RESET = "\033[0m"

CATEGORIES = (
    ("tellergericht-i", "Tellergericht 1"),
    ("tellergericht-i-3-60", "Tellergericht 1"),
    ("tellergericht-ii", "Tellergericht 2"),
    ("tellergericht-ii-3-90", "Tellergericht 2"),
    ("tellergericht-iii", "Tellergericht 3"),
    ("wok-gericht", "Asia"),
    ("grill", "Grill"),
    ("nudelbuffet", "Nudelbuffet"),
    ("beilage", "Beilage"),
    ("s-ssspeise", "Süßspeise"),
    ("pizza", "Pizza"),
    ("pizza-vegan", "Vegane Pizza"),
    ("nudelb-ffet", "Nudelbüffet"),
    ("gem-seb-ffet", "Gemüsebüffet"),
    ("hinweis", "Hinweis"),
)


def download_markup():
    url = "https://augsburg.my-mensa.de/essen.php?mensa=aug_universitaetsstr_uni"
    # mensa requires a user agent or else the request will result in a 403 reponse
    headers = {
        # "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        "User-Agent": "AUX Mensa CLI"
    }
    response = requests.get(url, headers=headers)
    # print("Redirects:", len(response.history))
    assert response.status_code == 200, f"Unexpected status code {response.status_code}"

    return response.text


def main(date_query=None):
    if date_query is None:
        now = date.today().strftime("%Y-%m-%d")
    else:
        now = date_query
    print("Dishes for:", now)

    markup = download_markup()

    # &shy; is a soft hyphen and is inserted into the dish names
    markup = markup.replace("&shy;", "")
    soup = BeautifulSoup(markup, features="lxml")
    day_elts = soup.select('div.essenliste.page')

    for day_elt in day_elts:
        datestr = day_elt.get("data-date2")
        if datestr != now:
            continue

        items = day_elt.select("li.conditional")

        by_category = {}
        price_width = 0

        for item in items:
            # name
            name = item.find("h3").find(string=True, recursive=False).strip()
            subnames = item.select_one("p.ct.text2share").find_all(
                string=True, recursive=False
            )
            name += " " + " ".join([sn.strip() for sn in subnames])

            # prices
            price = item.select("p.ct.next.text2share")[0].get_text()
            prices = [
                s.replace(",", ".") for s in re.findall("(\\d+,\\d+)\xa0€", price)
            ]
            if len(prices) != 3:
                price = None
            else:
                price = float(prices[0])

                if len(str(price)) > price_width:
                    price_width = len(str(price))

            # category
            classes = [c for c in item.get("class") if c not in ("conditional", "checkempty") and not c.startswith("dbg")]
            assert len(classes) == 1
            category = classes[0]

            if category not in by_category:
                by_category[category] = []
            by_category[category].append((name, price))

        # make sure that everything is displayed
        all_categories = list(CATEGORIES)
        keys = [key for key, _ in CATEGORIES]
        for k in by_category:
            if k not in keys:
                all_categories.append((k, k))
        for codename, display_name in all_categories:
            if codename in by_category:
                print(COLOR_HEADER, display_name, COLOR_RESET, sep="")
                for name, price in by_category[codename]:
                    if price is None:
                        print(COLOR_ERROR, "?" * price_width, COLOR_RESET, name)
                    else:
                        print(
                            COLOR_PRICE,
                            str(price).ljust(price_width, "0"),
                            COLOR_RESET,
                            name,
                        )

def weekday_query(dayname):
    today = date.today()
    wd = today.weekday()
    if dayname in ("montag", "monday", "mo"):
        target_wd = 0
    elif dayname in ("dienstag", "tuesday", "di", "tu"):
        target_wd = 1
    elif dayname in ("mittwoch", "wednesday", "mi", "we"):
        target_wd = 2
    elif dayname in ("donnerstag", "thursday", "do", "th"):
        target_wd = 3
    elif dayname in ("freitag", "friday", "fr"):
        target_wd = 4
    else:
        return None

    if wd == target_wd:
        delta = 7
    else:
        delta = (target_wd - wd + 7) % 7
    return (today + timedelta(delta)).strftime("%Y-%m-%d")

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("query", nargs="?", default=None)
    args = parser.parse_args()
    date_query = None
    if args.query is not None:
        if args.query in ("morgen", "tomorrow"):
            date_query = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        elif args.query == "übermorgen":
            date_query = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        else:
            date_query = weekday_query(args.query)
        if date_query is None:
            print("Unknown query: " + args.query)
            exit(1)
    main(date_query)
