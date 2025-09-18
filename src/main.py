from scrapers import VanguardETFScraper
from selenium.webdriver.common.by import By

if __name__ == "__main__":
    # Create scraper instance
    with VanguardETFScraper(
        headless=False
    ) as scraper:  # Set headless=False to see browser

        # Scrape VT (Vanguard Total World Stock ETF) portfolio composition
        df = scraper.scrape_portfolio_composition("VT")

        if not df.empty:
            print("\nPortfolio Composition (Top 20 holdings):")
            print(df.head(20))

            print(f"\nSummary:")
            print(f"Total holdings: {len(df)}")
            print(f"Total percentage covered: {df['Percentage'].sum():.2f}%")

            # Save to CSV
            scraper.save_to_csv(df, "vt_holdings.csv")
        else:
            print("No data found. The website structure might have changed.")

            # Print page source snippet for debugging
            print("\nDebugging info:")
            print("Page title:", scraper.driver.title)
            print("Current URL:", scraper.driver.current_url)

            # Look for any text mentioning holdings or equity
            page_text = scraper.driver.find_element(By.TAG_NAME, "body").text.lower()
            if "holding" in page_text:
                print("Found 'holding' text on page")
            if "equity" in page_text:
                print("Found 'equity' text on page")
