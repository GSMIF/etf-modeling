# ETF Modeling

A Python-based tool for scraping and analyzing ETF holdings data from Vanguard.

## Features

- **Complete Holdings Scraper**: Automatically scrapes all holdings from paginated Vanguard ETF pages
- **Pagination Handling**: Intelligently navigates through hundreds of pages to collect complete datasets
- **Flexible Options**: Support for testing with limited pages or single-page scraping
- **CSV Export**: Saves all holdings data (ticker symbols and fund percentages) to CSV format

## Setup

### Create a virtual environment
```bash
python3 -m venv .venv
```

### Activate the virtual environment
```bash
source .venv/bin/activate
```

### Install dependencies
```bash
pip3 install -r requirements.txt
```

## Usage

### Scrape Complete ETF Holdings

By default, the scraper will collect **all holdings** from all pages:

```bash
# Scrape all holdings from VT ETF
python src/main.py

# Scrape from a different ETF
python src/main.py --url "https://investor.vanguard.com/investment-products/etfs/profile/vti"

# Specify custom output file
python src/main.py --out my_etf_holdings.csv
```

### Testing and Development Options

```bash
# Test with limited pages
python src/main.py --max-pages 5

# Original single-page behavior
python src/main.py --single-page

# Show browser window while scraping
python src/main.py --headful
```

### Command Line Options

- `--url`: Vanguard ETF profile URL (default: VT ETF)
- `--out`: Output CSV file path (default: `vt_holdings.csv`)
- `--headful`: Show browser window instead of headless mode
- `--single-page`: Only scrape the first page (for testing)
- `--max-pages N`: Limit scraping to first N pages (for testing)

## Output Format

The scraper generates a CSV file with the following columns:
- **Ticker**: Stock ticker symbol
- **% of fund**: Percentage weight in the ETF

Example output:
```csv
Ticker,% of fund
NVDA,4.11 %
MSFT,3.78 %
AAPL,3.45 %
...
```

## Technical Details

- Uses Selenium WebDriver with Chrome for robust web scraping
- Automatically handles cookie banners and navigation
- Implements smart pagination detection using dropdown selectors
- Includes retry logic and error handling for reliable data collection
- Processes approximately 10 holdings per page with 1-second delays between pages
