#!/usr/bin/env python3
"""
Stock Data Fetcher - Fetch stock analysis data from external API

Usage:
    python fetch_stock_data.py "NVDA,AAPL"
    python fetch_stock_data.py NVDA
"""

import json
import sys
import requests
from typing import List, Dict, Any, Optional


class StockDataFetcher:
    """Fetch stock analysis data with retry mechanism."""

    API_URL = "https://stock-analyzer-service-55638944338.us-central1.run.app/stock/analyze"
    MAX_RETRIES = 3
    TIMEOUT = 30

    HEADERS = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cache-control": "no-cache",
    }

    def __init__(self):
        self.retry_count = 0

    def fetch(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Fetch stock data for given symbols.

        Args:
            symbols: List of stock symbols (e.g., ["NVDA", "AAPL"])

        Returns:
            API response as dictionary

        Raises:
            Exception: If all retries fail
        """
        payload = {"symbols": symbols}
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                self.retry_count = attempt + 1
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s
                    print(f"Retry attempt {attempt}/{self.MAX_RETRIES - 1}, waiting {wait_time}s...", file=sys.stderr)
                    import time
                    time.sleep(wait_time)

                response = requests.post(
                    self.API_URL,
                    json=payload,
                    headers=self.HEADERS,
                    timeout=self.TIMEOUT
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                last_error = f"Request timeout after {self.TIMEOUT}s"
                print(f"Timeout on attempt {attempt + 1}", file=sys.stderr)
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {str(e)}"
                print(f"Connection error on attempt {attempt + 1}: {e}", file=sys.stderr)
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP error: {str(e)}"
                print(f"HTTP error on attempt {attempt + 1}: {e}", file=sys.stderr)
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                print(f"Error on attempt {attempt + 1}: {e}", file=sys.stderr)

        raise Exception(f"Failed after {self.MAX_RETRIES} attempts. Last error: {last_error}")


def parse_symbols(input_str: str) -> List[str]:
    """Parse stock symbols from input string."""
    # Support comma-separated, space-separated, or single symbol
    symbols = []
    for part in input_str.replace(",", " ").split():
        part = part.strip().upper()
        if part:
            symbols.append(part)
    return symbols


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_stock_data.py <symbols>", file=sys.stderr)
        print("Example: python fetch_stock_data.py 'NVDA,AAPL'", file=sys.stderr)
        sys.exit(1)

    symbols_input = sys.argv[1]
    symbols = parse_symbols(symbols_input)

    if not symbols:
        print("Error: No valid symbols provided", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching data for: {', '.join(symbols)}", file=sys.stderr)

    fetcher = StockDataFetcher()
    try:
        result = fetcher.fetch(symbols)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
