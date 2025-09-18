import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)
import json
import re


class VanguardETFScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome WebDriver"""
        self.setup_driver(headless)

    def setup_driver(self, headless=True):
        """Set up Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Add user agent to avoid detection
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)

    def scrape_portfolio_composition(self, ticker="VT", timeout=30):
        """
        Scrape portfolio composition for a given Vanguard ETF ticker
        Navigate to Holding details/Equity section and handle pagination

        Args:
            ticker (str): ETF ticker symbol (default: "VT")
            timeout (int): Maximum time to wait for page elements

        Returns:
            pandas.DataFrame: DataFrame with ticker symbols and percentage allocations
        """
        url = f"https://investor.vanguard.com/investment-products/etfs/profile/{ticker.lower()}"

        try:
            print(f"Navigating to {url}...")
            self.driver.get(url)

            # Wait for the page to load
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Navigate to Holding details section
            if not self.navigate_to_holding_details():
                print("Could not navigate to Holding details section")
                return pd.DataFrame(columns=["Ticker", "Percentage", "Name"])

            # Navigate to Equity subsection
            if not self.navigate_to_equity_section():
                print("Could not navigate to Equity section")
                return pd.DataFrame(columns=["Ticker", "Percentage", "Name"])

            # Scrape all pages of holdings data
            portfolio_data = self.scrape_paginated_holdings()

            if portfolio_data:
                df = pd.DataFrame(portfolio_data)
                # Sort by percentage descending
                df = df.sort_values("Percentage", ascending=False).reset_index(
                    drop=True
                )
                print(f"Successfully scraped {len(df)} holdings")
                return df
            else:
                print("No portfolio composition data found")
                return pd.DataFrame(columns=["Ticker", "Percentage", "Name"])

        except Exception as e:
            print(f"Error scraping portfolio composition: {str(e)}")
            return pd.DataFrame(columns=["Ticker", "Percentage", "Name"])

    def navigate_to_holding_details(self):
        """Navigate to the Holding details section"""
        try:
            # Look for various possible selectors for "Holding details" or similar
            holding_selectors = [
                "//button[contains(text(), 'Holding details')]",
                "//a[contains(text(), 'Holding details')]",
                "//button[contains(text(), 'Holdings')]",
                "//a[contains(text(), 'Holdings')]",
                "//tab[contains(text(), 'Holding details')]",
                "//div[contains(text(), 'Holding details')]",
                "[data-testid*='holding']",
                "[aria-label*='Holding']",
                ".tab-button:contains('Holding')",
                ".nav-link:contains('Holding')",
            ]

            for selector in holding_selectors:
                try:
                    print(f"Looking for Holding details with selector: {selector}")

                    if selector.startswith("//"):
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )

                    print(f"Found and clicking Holding details button: {element.text}")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", element
                    )
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(3)
                    return True

                except (
                    TimeoutException,
                    NoSuchElementException,
                    ElementClickInterceptedException,
                ):
                    continue

            print("Could not find Holding details button")
            return False

        except Exception as e:
            print(f"Error navigating to holding details: {str(e)}")
            return False

    def navigate_to_equity_section(self):
        """Navigate to the Equity subsection within Holding details"""
        try:
            # Look for Equity tab/button
            equity_selectors = [
                "//button[contains(text(), 'Equity')]",
                "//a[contains(text(), 'Equity')]",
                "//tab[contains(text(), 'Equity')]",
                "//div[contains(text(), 'Equity') and contains(@class, 'tab')]",
                "[data-testid*='equity']",
                ".tab-button:contains('Equity')",
                ".nav-link:contains('Equity')",
                "//span[contains(text(), 'Equity')]/parent::*",
            ]

            for selector in equity_selectors:
                try:
                    print(f"Looking for Equity section with selector: {selector}")

                    if selector.startswith("//"):
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        element = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )

                    print(f"Found and clicking Equity button: {element.text}")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", element
                    )
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(3)
                    return True

                except (
                    TimeoutException,
                    NoSuchElementException,
                    ElementClickInterceptedException,
                ):
                    continue

            # If no Equity tab found, assume we're already in the right section
            print("No Equity tab found, assuming already in correct section")
            return True

        except Exception as e:
            print(f"Error navigating to equity section: {str(e)}")
            return False

    def scrape_paginated_holdings(self):
        """Scrape all holdings from paginated table"""
        all_holdings = []
        page_number = 1
        max_pages = 50  # Safety limit

        while page_number <= max_pages:
            print(f"Scraping page {page_number}...")

            # Wait for table to load properly
            if not self.wait_for_holdings_table():
                print(f"Table failed to load on page {page_number}")
                break

            # Extract holdings from current page
            page_holdings = self.extract_holdings_from_current_page()

            if not page_holdings:
                print(f"No holdings found on page {page_number}")
                # On first page, this might indicate a navigation issue
                if page_number == 1:
                    print("No holdings on first page - checking page structure...")
                    self.debug_page_structure()
                break

            all_holdings.extend(page_holdings)
            print(f"Found {len(page_holdings)} holdings on page {page_number}")

            # Try to navigate to next page
            if not self.go_to_next_page():
                print("No more pages or unable to navigate to next page")
                break

            page_number += 1

        print(f"Total holdings scraped: {len(all_holdings)}")
        return all_holdings

    def debug_page_structure(self):
        """Debug method to understand the page structure when scraping fails"""
        try:
            print("\n--- DEBUG PAGE STRUCTURE ---")

            # Look for all tables on the page
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"Found {len(tables)} table elements")

            for i, table in enumerate(tables):
                table_class = table.get_attribute("class")
                table_text = table.text[:200] if table.text else "No text"
                print(f"Table {i}: class='{table_class}', text='{table_text}...'")

            # Look for Angular components
            angular_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "[class*='_ngcontent']"
            )
            print(f"Found {len(angular_elements)} Angular components")

            # Look for elements containing percentage signs
            percentage_elements = self.driver.find_elements(
                By.XPATH, "//*[contains(text(), '%')]"
            )
            print(f"Found {len(percentage_elements)} elements with '%' text")
            for elem in percentage_elements[:5]:
                print(f"  % element: {elem.text[:50]}...")

            print("--- END DEBUG ---\n")

        except Exception as e:
            print(f"Error in debug: {str(e)}")

    def extract_holdings_from_current_page(self):
        """Extract holdings data from the current page"""
        holdings = []

        try:
            # First, try to find the specific Angular holdings table
            holdings_table = self.find_angular_holdings_table()
            if holdings_table:
                print("Using specifically identified holdings table")
                rows = holdings_table.find_elements(By.CSS_SELECTOR, "tbody tr, tr")
                if rows:
                    print(f"Found {len(rows)} rows in identified holdings table")
                else:
                    print("No rows found in identified table")
            else:
                # Look for the specific Angular table with ticker information
                table_selectors = [
                    "table[class*='_ngcontent-ng-c'] tbody tr",
                    "table[class*='ngcontent'] tbody tr",
                    "[class*='_ngcontent-ng-c872010782'] tbody tr",
                    "[class*='_ngcontent-ng-c872010782'] tr",
                    "table._ngcontent-ng-c872010782 tbody tr",
                    "table._ngcontent-ng-c872010782 tr",
                ]

                rows = []
                for selector in table_selectors:
                    try:
                        rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if rows:
                            print(f"Found {len(rows)} rows with selector: {selector}")
                            break
                    except:
                        continue

                # If specific selector didn't work, try broader Angular component selectors
                if not rows:
                    angular_selectors = [
                        "[class*='_ngcontent-ng-c'] tbody tr",
                        "[class*='_ngcontent-ng-c'] tr",
                        "table[class*='_ngcontent'] tbody tr",
                        "table tbody tr",
                        "[role='row']",
                    ]

                    for selector in angular_selectors:
                        try:
                            rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if rows:
                                print(
                                    f"Found {len(rows)} rows with fallback selector: {selector}"
                                )
                                break
                        except:
                            continue

            # Debug: Print table structure if we found rows
            if rows and len(holdings) == 0:
                print("Debugging table structure...")
                for i, row in enumerate(rows[:3]):  # Check first 3 rows
                    print(f"Row {i} HTML: {row.get_attribute('outerHTML')[:200]}...")
                    print(f"Row {i} text: {row.text}")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    print(f"Row {i} cells: {len(cells)}")
                    for j, cell in enumerate(cells[:5]):  # Check first 5 cells
                        print(
                            f"  Cell {j}: '{cell.text}' (class: {cell.get_attribute('class')})"
                        )
                    print("-" * 50)

            for row in rows:
                try:
                    # Extract data from row
                    ticker, name, percentage = self.extract_holding_data_from_row(row)

                    if ticker and percentage is not None:
                        holdings.append(
                            {
                                "Ticker": ticker.strip(),
                                "Name": name.strip() if name else "",
                                "Percentage": percentage,
                            }
                        )
                    elif (
                        row.text.strip()
                    ):  # If we couldn't parse but there's text, log it
                        print(f"Could not parse row: {row.text[:100]}...")

                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error extracting holdings from current page: {str(e)}")

    def find_angular_holdings_table(self):
        """Specifically look for Angular tables containing holdings data"""
        try:
            # Look for any Angular components that might contain the table
            angular_components = self.driver.find_elements(
                By.CSS_SELECTOR, "[class*='_ngcontent-ng-c']"
            )
            print(f"Found {len(angular_components)} Angular components")

            # Check for tables within these components
            for component in angular_components:
                tables = component.find_elements(By.TAG_NAME, "table")
                if tables:
                    for table in tables:
                        table_text = table.text.lower()
                        # Look for indicators this might be a holdings table
                        if any(
                            keyword in table_text
                            for keyword in [
                                "ticker",
                                "symbol",
                                "%",
                                "percentage",
                                "holding",
                                "equity",
                            ]
                        ):
                            print(
                                f"Found potential holdings table with class: {table.get_attribute('class')}"
                            )
                            return table

            # Alternative: Look for elements containing ticker-like text patterns
            elements = self.driver.find_elements(
                By.XPATH, "//*[contains(text(), '%') or contains(@class, '_ngcontent')]"
            )
            for element in elements:
                if element.tag_name in ["table", "tbody", "tr"]:
                    return element

        except Exception as e:
            print(f"Error finding Angular holdings table: {str(e)}")

        return None

    def extract_holding_data_from_row(self, row):
        """Extract ticker, name, and percentage from a table row"""
        ticker = ""
        name = ""
        percentage = None

        try:
            # Get all cells/text elements in the row
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                cells = row.find_elements(By.CSS_SELECTOR, ".cell, .column, div")

            all_text = []
            for cell in cells:
                cell_text = cell.text.strip()
                if cell_text:
                    all_text.append(cell_text)

            # Also get the complete row text as backup
            row_text = row.text.strip()
            if row_text:
                all_text.append(row_text)

            # Parse the extracted text
            for text in all_text:
                # Look for percentage (number followed by %)
                percentage_match = re.search(r"(\d+\.?\d*)\s*%", text)
                if percentage_match and percentage is None:
                    percentage = float(percentage_match.group(1))

                # Look for ticker (2-6 uppercase letters)
                ticker_match = re.search(r"\b([A-Z]{2,6})\b", text)
                if ticker_match and not ticker:
                    potential_ticker = ticker_match.group(1)
                    # Avoid common non-ticker words
                    if potential_ticker not in [
                        "USD",
                        "CAD",
                        "EUR",
                        "GBP",
                        "CLASS",
                        "CORP",
                        "INC",
                        "LLC",
                        "LTD",
                    ]:
                        ticker = potential_ticker

                # Look for company name (longer text that's not a percentage)
                if len(text) > 10 and "%" not in text and not name:
                    # Clean up the text
                    clean_text = re.sub(r"\b[A-Z]{2,6}\b", "", text).strip()
                    clean_text = re.sub(r"\s+", " ", clean_text).strip()
                    if clean_text and len(clean_text) > 5:
                        name = clean_text

            # If we found multiple potential tickers, keep the first valid one
            # If we found multiple potential names, keep the longest meaningful one

        except Exception as e:
            pass

        return ticker, name, percentage

    def go_to_next_page(self):
        """Navigate to the next page of holdings"""
        try:
            # Look for next page button/link
            next_selectors = [
                "//button[contains(text(), 'Next')]",
                "//a[contains(text(), 'Next')]",
                "//button[@aria-label='Next page']",
                "//button[@aria-label='Go to next page']",
                ".pagination-next",
                ".next-page",
                "[data-testid*='next']",
                "//button[contains(@class, 'next')]",
                ".pager-next",
                "//span[contains(text(), '>')]/parent::button",
            ]

            for selector in next_selectors:
                try:
                    if selector.startswith("//"):
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)

                    # Check if button is enabled
                    if element.is_enabled() and element.is_displayed():
                        print(
                            f"Clicking next page button: {element.get_attribute('outerHTML')[:100]}..."
                        )
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", element
                        )
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", element)
                        time.sleep(3)
                        return True

                except (NoSuchElementException, ElementClickInterceptedException):
                    continue

            print("No next page button found or button is disabled")
            return False

        except Exception as e:
            print(f"Error going to next page: {str(e)}")
            return False

    def save_to_csv(self, df, filename=None):
        """Save DataFrame to CSV file"""
        if filename is None:
            filename = f"vanguard_etf_holdings_{int(time.time())}.csv"

        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
        return filename

    def close(self):
        """Close the WebDriver"""
        if hasattr(self, "driver"):
            self.driver.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example usage
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
