import argparse
from scrapers import (
    VANGUARD_DEFAULT_URL,
    dismiss_banners,
    ensure_on_holdings_section,
    find_holdings_table,
    parse_ticker_weight,
    scrape_all_pages_progressive,
)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Vanguard ETF holdings (Ticker, % of fund) to CSV."
    )
    parser.add_argument(
        "--url", default=VANGUARD_DEFAULT_URL, help="Vanguard ETF profile URL"
    )
    parser.add_argument("--out", default="vt_holdings.csv", help="Output CSV path")
    parser.add_argument(
        "--headful", action="store_true", help="Show browser window (default headless)."
    )
    parser.add_argument(
        "--single-page",
        action="store_true",
        help="Only scrape the first page (for testing).",
    )
    parser.add_argument(
        "--max-pages", type=int, help="Maximum number of pages to scrape (for testing)."
    )
    args = parser.parse_args()

    chrome_opts = webdriver.ChromeOptions()
    if not args.headful:
        chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--window-size=1280,2000")
    chrome_opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()), options=chrome_opts
    )
    try:
        driver.get(args.url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        dismiss_banners(driver)
        ensure_on_holdings_section(driver)
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "table, vgd-table, c11n-table table")
            )
        )

        if args.single_page:
            # Original single-page logic for testing
            found = find_holdings_table(driver)
            if not found:
                ensure_on_holdings_section(driver)
                found = find_holdings_table(driver)

            if not found:
                raise RuntimeError(
                    "Could not find a holdings table with Ticker and % of fund."
                )

            headers, rows = found
            data = parse_ticker_weight(headers, rows)
            if not data:
                raise RuntimeError(
                    "Table found, but no rows with Ticker/% of fund extracted."
                )
        else:
            # multi-page scraping logic with progressive CSV writing
            total_holdings = scrape_all_pages_progressive(
                driver, args.out, max_pages=args.max_pages
            )
            if total_holdings == 0:
                raise RuntimeError("Could not scrape any holdings data from any pages.")
            print(
                f"Scraping completed successfully. {total_holdings} holdings saved to {args.out}"
            )
            return  # Early return since CSV is already written

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
