import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.gov.uk"
INDEX = BASE + "/guidance/the-highway-code"

out = Path("data")
out.mkdir(exist_ok=True)


def get_page(url):
    response = requests.get(
        url,
        headers={"User-Agent": "highway-code-rag student project"},
        timeout=30,
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


# 1. Find the link to every section from the main page
index = get_page(INDEX)
links = []
for a in index.find_all("a", href=True):
    href = a["href"].split("#")[0]
    if href.startswith("/guidance/the-highway-code/") and href not in links:
        links.append(href)

print(len(links), "section pages found")

# 2. Download each section and save its text
for href in links:
    page = get_page(BASE + href)
    main = page.find("main") or page
    pieces = []
    for el in main.find_all(["h1", "h2", "h3", "p", "li", "tr"]):
        if el.name == "tr":
            cells = [c.get_text(" ", strip=True) for c in el.find_all(["th", "td"])]
            row = " | ".join(c for c in cells if c)
            if row:
                pieces.append(row)
        elif not el.find_parent("table"):  # skip text already captured in a table row
            pieces.append(el.get_text(" ", strip=True))
    text = "\n".join(p for p in pieces if p)
    name = href.rsplit("/", 1)[-1]
    (out / f"{name}.txt").write_text(text, encoding="utf-8")
    print("saved", name, "-", len(text), "characters")
    time.sleep(1)  # be polite: wait 1 second between requests