"""
Google Search Provider implementation.
Uses Google Custom Search API.
Modern Protocol-based approach.
"""

import re
import asyncio
from typing import List, Optional
import logging

import httpx
from bs4 import BeautifulSoup

from app.core.providers import register
from app.core.exceptions import SearchProviderError
from app.models import SearchResult
from app.config import get_settings

logger = logging.getLogger(__name__)


@register("search", "google")
class GoogleSearchProvider:
    """
    Google search provider implementation using Custom Search API.
    Implements SearchProvider protocol without inheritance.
    """

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.google_search_api_key
        self._search_engine_id = settings.google_search_engine_id
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    @property
    def name(self) -> str:
        """Provider name for Protocol compliance."""
        return "google"

    @property
    def provider_name(self) -> str:
        """Backward compatible property."""
        return self.name

    async def search(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """Perform a Google Custom Search."""
        if not self._api_key or not self._search_engine_id:
            logger.warning("Google Search API key or Engine ID not configured")
            return []

        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self._api_key,
                "cx": self._search_engine_id,
                "q": query,
                "num": min(num_results, 10)  # Max 10 per request
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("items", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", "")
                ))

            logger.info(
                f"Google search found {len(results)} results for: {query[:50]}...")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Google API error: {e.response.status_code} - {e.response.text}")
            raise SearchProviderError(
                message=f"Search API error: {e.response.status_code}",
                provider="google",
                query=query,
                original_error=e
            )
        except Exception as e:
            logger.error(f"Google search error: {e}")
            raise SearchProviderError(
                message=f"Search failed: {str(e)}",
                provider="google",
                query=query,
                original_error=e
            )

    async def search_investors(
        self,
        sectors: List[str],
        location: Optional[str] = None,
        num_results: int = 30
    ) -> List[SearchResult]:
        """Search for US-based investors in specific sectors with comprehensive queries."""
        results = []
        seen_urls = set()

        # Build sector-specific queries
        sector_query = " OR ".join(sectors)

        # Default to United States for location
        location = location or "United States"
        location_suffix = f" \"{location}\"" if location else ""

        # Multiple search queries for comprehensive results - US focused
        search_queries = [
            # LinkedIn profile searches - US VCs
            f"site:linkedin.com/in/ investor {sector_query} partner Silicon Valley OR \"San Francisco\" OR \"New York\"",
            f"site:linkedin.com/in/ \"venture capital\" {sector_query} {location_suffix}",
            f"site:linkedin.com/in/ \"managing partner\" OR \"general partner\" VC {sector_query} {location_suffix}",
            f"site:linkedin.com/in/ \"angel investor\" {sector_query} {location_suffix}",
            f"site:linkedin.com/in/ \"investment director\" OR \"principal\" venture {sector_query} {location_suffix}",
            # Top US VC hubs
            f"site:linkedin.com/in/ VC partner {sector_query} \"Menlo Park\" OR \"Palo Alto\" OR \"Boston\"",
            f"site:linkedin.com/in/ seed investor {sector_query} \"Los Angeles\" OR \"Austin\" OR \"Seattle\"",
            # VC firm websites with investor names
            f"\"partner\" \"venture capital\" {sector_query} investor portfolio {location_suffix}",
            f"VC fund {sector_query} \"managing director\" OR \"partner\" {location_suffix}",
            # Crunchbase and AngelList for investor profiles
            f"site:crunchbase.com/person investor {sector_query} {location_suffix}",
            f"site:angel.co investor {sector_query} {location_suffix}",
        ]

        # Run searches
        for query in search_queries:
            try:
                query_results = await self.search(query, 10)
                for result in query_results:
                    # Filter out LinkedIn posts, only keep profiles and companies
                    if "/posts/" in result.url or "/pulse/" in result.url:
                        continue
                    if result.url not in seen_urls:
                        seen_urls.add(result.url)
                        results.append(result)

                # Limit total results
                if len(results) >= num_results:
                    break

            except Exception as e:
                logger.warning(f"Search query failed: {query[:50]}... - {e}")
                continue

        logger.info(
            f"Total unique US investor results found: {len(results)} for sectors: {sectors}")
        return results[:num_results]

    async def extract_emails(self, url: str) -> List[str]:
        """Extract emails from a URL."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._headers,
                    timeout=10,
                    follow_redirects=True
                )

                if response.status_code == 200:
                    return await self.extract_emails_from_text(response.text)

        except Exception as e:
            logger.warning(f"Email extraction failed for {url}: {e}")

        return []

    async def extract_emails_from_text(self, text: str) -> List[str]:
        """Extract emails from text content."""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)

        # Filter false positives
        filtered = [
            email for email in set(emails)
            if not email.endswith(('.png', '.jpg', '.gif', '.css', '.js'))
            and 'example' not in email.lower()
            and 'test' not in email.lower()
        ]

        return filtered

    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and parse webpage content."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self._headers,
                    timeout=10,
                    follow_redirects=True
                )

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')

                    for element in soup(['script', 'style', 'nav', 'footer']):
                        element.decompose()

                    text = soup.get_text(separator=' ', strip=True)
                    return text[:5000]

        except Exception as e:
            logger.warning(f"Page fetch failed for {url}: {e}")

        return None
