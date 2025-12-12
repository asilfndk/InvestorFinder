"""
Investor Service - Handles investor search and profile scraping.
"""

from typing import List, Tuple, Optional
import logging
import asyncio

from app.core.providers import get_search, get_scraper
from app.core.events import event_bus, Event, EventType
from app.models import InvestorProfile, SearchResult

logger = logging.getLogger(__name__)


class InvestorService:
    """
    Service for finding and managing investor information.
    Coordinates search and scraping providers.
    """

    def __init__(
        self,
        search_provider: str = "google",
        scraper_provider: str = "linkedin"
    ):
        self.search_provider_name = search_provider
        self.scraper_provider_name = scraper_provider
        # Store all found investors
        self._all_investors: List[InvestorProfile] = []
        self._current_page = 0
        self._page_size = 10

    async def find_investors(
        self,
        sectors: List[str],
        location: Optional[str] = None,
        num_results: int = 30,
        enrich_profiles: bool = True
    ) -> Tuple[List[InvestorProfile], List[SearchResult]]:
        """
        Find investors based on sectors and location.
        Default location is United States.

        Returns:
            Tuple of (investors, search_results)
        """
        investors: List[InvestorProfile] = []
        search_results: List[SearchResult] = []

        # Default to United States if no location specified
        if not location:
            location = "United States"

        # Publish search started event
        await event_bus.publish(Event(
            type=EventType.SEARCH_STARTED,
            data={"sectors": sectors, "location": location}
        ))

        try:
            # Get search provider using new registry
            search_provider = await get_search(self.search_provider_name)

            # Search for investors
            search_results = await search_provider.search_investors(
                sectors=sectors,
                location=location,
                num_results=num_results
            )

            # Publish search completed event
            await event_bus.publish(Event(
                type=EventType.SEARCH_COMPLETED,
                data={"results_count": len(search_results)}
            ))

        except Exception as e:
            logger.error(f"Search failed: {e}")
            await event_bus.publish(Event(
                type=EventType.SEARCH_FAILED,
                data={"error": str(e)}
            ))
            return investors, search_results

        # Get scraper provider using new registry
        try:
            scraper = await get_scraper(self.scraper_provider_name)
        except Exception as e:
            logger.error(f"Failed to get scraper: {e}")
            scraper = None

        # Process results - both LinkedIn and web results
        seen_names = set()

        for result in search_results:
            try:
                if "linkedin.com/in/" in result.url:
                    # LinkedIn profile - try to get detailed info
                    profile = None

                    # First try to extract from search result (faster)
                    if scraper and hasattr(scraper, 'scrape_from_search_result'):
                        profile = await scraper.scrape_from_search_result(
                            title=result.title,
                            snippet=result.snippet,
                            url=result.url
                        )

                    # If that didn't work, try scraping the page
                    if not profile and scraper:
                        try:
                            profile = await scraper.scrape_profile(result.url)
                        except Exception as e:
                            logger.warning(
                                f"Profile scrape failed for {result.url}: {e}")

                    if profile and profile.name and profile.name.lower() not in seen_names:
                        seen_names.add(profile.name.lower())
                        investors.append(profile)

                        await event_bus.publish(Event(
                            type=EventType.INVESTOR_FOUND,
                            data={"name": profile.name, "source": "linkedin"}
                        ))

                elif "linkedin.com/company/" in result.url:
                    # Company page - extract company name
                    company_name = result.title.split(
                        " | ")[0] if " | " in result.title else result.title
                    if company_name and company_name.lower() not in seen_names:
                        seen_names.add(company_name.lower())
                        investors.append(InvestorProfile(
                            name=company_name,
                            company=company_name,
                            linkedin_url=result.url,
                            bio=result.snippet[:500] if result.snippet else None,
                            source="linkedin"
                        ))

                elif "crunchbase.com/person" in result.url:
                    # Crunchbase person profile
                    name = result.title.split(
                        " - ")[0] if " - " in result.title else result.title
                    name = name.replace(" | Crunchbase", "").strip()[:100]
                    if name and name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        investors.append(InvestorProfile(
                            name=name,
                            bio=result.snippet[:500] if result.snippet else None,
                            source="crunchbase"
                        ))

                elif "angel.co" in result.url or "wellfound.com" in result.url:
                    # AngelList/Wellfound profile
                    name = result.title.split(
                        " - ")[0] if " - " in result.title else result.title
                    name = name.replace(" | AngelList", "").replace(
                        " | Wellfound", "").strip()[:100]
                    if name and name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        investors.append(InvestorProfile(
                            name=name,
                            bio=result.snippet[:500] if result.snippet else None,
                            source="angellist"
                        ))

                else:
                    # Other web results - try to extract investor info from title/snippet
                    # Look for patterns like "Name, Partner at VC Firm"
                    name = None
                    company = None

                    title_text = result.title
                    if " - " in title_text:
                        parts = title_text.split(" - ")
                        potential_name = parts[0].strip()
                        # Check if it looks like a name (not a company name)
                        if len(potential_name.split()) <= 4 and not any(word in potential_name.lower() for word in ["inc", "ltd", "llc", "capital", "ventures", "fund"]):
                            name = potential_name[:100]
                            if len(parts) > 1:
                                company = parts[1].strip()[:100]

                    if name and name.lower() not in seen_names:
                        seen_names.add(name.lower())

                        # Try to extract email
                        email = None
                        try:
                            emails = await self._extract_emails(result.url)
                            if emails:
                                email = emails[0]
                        except:
                            pass

                        investors.append(InvestorProfile(
                            name=name,
                            company=company,
                            email=email,
                            bio=result.snippet[:500] if result.snippet else None,
                            source="web_search"
                        ))

            except Exception as e:
                logger.warning(f"Failed to process result {result.url}: {e}")
                continue

        logger.info(
            f"Found {len(investors)} investors from {len(search_results)} search results")

        # Enrich profiles with LinkedIn data
        if enrich_profiles and investors:
            investors = await self._enrich_investor_profiles(investors)

        # Store all investors for pagination
        self._all_investors = investors
        self._current_page = 0

        return investors, search_results

    async def _enrich_investor_profiles(
        self,
        investors: List[InvestorProfile],
        max_enrich: int = 15  # Limit enrichment to avoid rate limiting
    ) -> List[InvestorProfile]:
        """
        Enrich investor profiles with additional LinkedIn data.
        """
        try:
            scraper = await get_scraper(self.scraper_provider_name)

            if not hasattr(scraper, 'enrich_profile'):
                logger.info("Scraper doesn't support profile enrichment")
                return investors

            enriched_investors = []
            enrich_count = 0

            for investor in investors:
                if enrich_count < max_enrich and investor.linkedin_url:
                    try:
                        enriched = await scraper.enrich_profile(investor)
                        enriched_investors.append(enriched)
                        enrich_count += 1
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.2)
                    except Exception as e:
                        logger.warning(
                            f"Failed to enrich {investor.name}: {e}")
                        enriched_investors.append(investor)
                else:
                    enriched_investors.append(investor)

            logger.info(f"Enriched {enrich_count} investor profiles")
            return enriched_investors

        except Exception as e:
            logger.error(f"Profile enrichment failed: {e}")
            return investors

    def get_paginated_investors(
        self,
        page: int = 0,
        page_size: int = 10
    ) -> Tuple[List[InvestorProfile], int, bool]:
        """
        Get paginated investors.

        Returns:
            Tuple of (investors_on_page, total_count, has_more)
        """
        total = len(self._all_investors)
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, total)

        if start_idx >= total:
            return [], total, False

        page_investors = self._all_investors[start_idx:end_idx]
        has_more = end_idx < total

        return page_investors, total, has_more

    async def _scrape_profile(self, url: str) -> Optional[InvestorProfile]:
        """Scrape a profile from URL."""
        try:
            scraper = await get_scraper(self.scraper_provider_name)
            return await scraper.scrape_profile(url)
        except Exception as e:
            logger.error(f"Profile scrape failed for {url}: {e}")
            return None

    async def _extract_emails(self, url: str) -> List[str]:
        """Extract emails from a URL."""
        try:
            search_provider = await get_search(self.search_provider_name)

            # Check if provider supports email extraction
            if hasattr(search_provider, 'extract_emails'):
                return await search_provider.extract_emails(url)
        except Exception as e:
            logger.warning(f"Email extraction failed for {url}: {e}")

        return []

    async def get_investor_details(self, linkedin_url: str) -> Optional[InvestorProfile]:
        """Get detailed investor information from LinkedIn URL."""
        return await self._scrape_profile(linkedin_url)
