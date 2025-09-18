import time
import re
from typing import List, Tuple, Optional

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


VANGUARD_DEFAULT_URL = (
    "https://investor.vanguard.com/investment-products/etfs/profile/vt"
)

COOKIE_BUTTON_XPATHS = [
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'accept')]",
    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'agree')]",
    "//button[contains(.,'Accept all')]",
    "//button[contains(.,'Accept All')]",
    "//button[contains(.,'I agree')]",
    "//button[contains(.,'Got it')]",
]

TABLE_CANDIDATE_SELECTORS = [
    "table",
    "vgd-table, c11n-table table",
]

HEADER_ALIASES = {
    "ticker": ["ticker", "symbol"],
    "% of fund": ["% of fund", "% of net assets", "weight", "% of etf"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def maybe_click(driver, xpath: str, timeout: float = 2.5) -> bool:
    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        btn.click()
        return True
    except Exception:
        return False


def dismiss_banners(driver):
    for xp in COOKIE_BUTTON_XPATHS:
        if maybe_click(driver, xp, timeout=1.5):
            break


def ensure_on_holdings_section(driver):
    """
    If there is a tab or link that switches to 'Portfolio'/'Holdings' section,
    try to click it. If not present, we just continue.
    """
    XPATHS = [
        "//a[contains(.,'Portfolio')]",
        "//a[contains(.,'Holdings')]",
        "//button[contains(.,'Portfolio')]",
        "//button[contains(.,'Holdings')]",
        "//a[contains(.,'Portfolio & Management')]",
        "//button[contains(.,'Portfolio & Management')]",
        "//a[contains(.,'View all holdings')]",
        "//button[contains(.,'View all holdings')]",
    ]
    for xp in XPATHS:
        if maybe_click(driver, xp, timeout=1.0):
            time.sleep(0.8)


def find_holdings_table(driver) -> Optional[Tuple[List[str], List[List[str]]]]:
    """
    Returns (headers, rows) for the first table that looks like a holdings table:
    Must include a Ticker-like column and a '% of fund'-like column.
    """

    for _ in range(3):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(0.5)

    for selector in TABLE_CANDIDATE_SELECTORS:
        try:
            tables = driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            tables = []

        for tbl in tables:
            if not tbl.is_displayed():
                continue
            headers_elems = tbl.find_elements(By.CSS_SELECTOR, "thead th")
            if not headers_elems:
                headers_elems = tbl.find_elements(
                    By.CSS_SELECTOR, "tr:first-child th, tr:first-child td"
                )

            headers = [_norm(h.text) for h in headers_elems if _norm(h.text)]

            if not headers:
                continue

            header_index = {h: i for i, h in enumerate(headers)}

            def match_index(goal: str) -> Optional[int]:
                goal_aliases = HEADER_ALIASES[goal]
                for cand in headers:
                    for alias in goal_aliases:
                        if alias in cand:
                            return header_index[cand]
                return None

            idx_ticker = match_index("ticker")
            idx_weight = match_index("% of fund")

            if idx_ticker is None or idx_weight is None:
                continue
            row_elems = tbl.find_elements(By.CSS_SELECTOR, "tbody tr")
            if not row_elems:
                row_elems = tbl.find_elements(By.CSS_SELECTOR, "tr")[1:]

            rows: List[List[str]] = []
            for r in row_elems:
                if not r.is_displayed():
                    continue
                cells = r.find_elements(By.CSS_SELECTOR, "th, td")
                if len(cells) < max(idx_ticker, idx_weight) + 1:
                    continue
                texts = [c.text.strip() for c in cells]
                rows.append(texts)

            if rows:
                return ([h for h in headers], rows)

    return None


def parse_ticker_weight(
    headers: List[str], rows: List[List[str]]
) -> List[Tuple[str, str]]:
    h_norm = [_norm(h) for h in headers]

    def find_idx(aliases: List[str]) -> int:
        for i, h in enumerate(h_norm):
            for alias in aliases:
                if alias in h:
                    return i
        raise ValueError("Required column not found")

    idx_ticker = find_idx(HEADER_ALIASES["ticker"])
    idx_weight = find_idx(HEADER_ALIASES["% of fund"])

    extracted = []
    for row in rows:
        if len(row) <= max(idx_ticker, idx_weight):
            continue
        ticker = row[idx_ticker].strip()
        weight = row[idx_weight].strip()
        if weight and not weight.endswith("%"):
            if re.match(r"^\d+(\.\d+)?$", weight):
                weight = f"{weight}%"

        extracted.append((ticker, weight))
    return extracted


def save_csv(pairs: List[Tuple[str, str]], path: str):
    df = pd.DataFrame(pairs, columns=["Ticker", "% of fund"])
    df.to_csv(path, index=False)
    print(f"Saved {len(pairs)} rows to {path}")
