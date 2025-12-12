"""
LinkedIn Scraper Provider implementation.
Uses httpx for basic profile info extraction.
Modern Protocol-based approach.
"""

import asyncio
import re
from typing import Optional, List
import logging

import httpx
from bs4 import BeautifulSoup

from app.core.providers import register
from app.core.exceptions import ScraperError
from app.models import InvestorProfile
from app.config import get_settings

logger = logging.getLogger(__name__)


@register("scraper", "linkedin")
class LinkedInScraperProvider:
    """
    LinkedIn profile scraper implementation.
    Implements ScraperProvider protocol without inheritance.
    """

    def __init__(self):
        self._settings = get_settings()
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self._scraped_profiles_cache: dict = {}  # Cache for scraped profiles
        self._initialized = False

    @property
    def name(self) -> str:
        """Provider name for Protocol compliance."""
        return "linkedin"

    @property
    def provider_name(self) -> str:
        """Backward compatible property."""
        return self.name

    @property
    def supported_domains(self) -> List[str]:
        return ["linkedin.com/in/", "linkedin.com/company/"]

    def can_handle(self, url: str) -> bool:
        """Check if this scraper can handle the given URL."""
        return any(domain in url for domain in self.supported_domains)

    async def initialize(self) -> None:
        """Initialize scraper."""
        self._initialized = True
        logger.info("LinkedIn scraper initialized (httpx mode)")

    async def scrape_profile(self, url: str) -> Optional[InvestorProfile]:
        """Scrape a LinkedIn profile using httpx (no login required for basic info)."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=self._headers, timeout=15)

                if response.status_code != 200:
                    logger.warning(
                        f"LinkedIn returned {response.status_code} for {url}")
                    # Try to extract info from URL itself
                    return self._extract_from_url(url)

                html = response.text
                soup = BeautifulSoup(html, 'html.parser')

                profile_data = self._parse_public_profile(soup, url)

                if profile_data and profile_data.get("name"):
                    profile_data["linkedin_url"] = url
                    profile_data["source"] = "linkedin"
                    return InvestorProfile(**profile_data)
                else:
                    # Fallback to URL parsing
                    return self._extract_from_url(url)

        except Exception as e:
            logger.error(f"LinkedIn scrape error for {url}: {e}")
            # Return basic info from URL
            return self._extract_from_url(url)

    def _parse_public_profile(self, soup: BeautifulSoup, url: str) -> Optional[dict]:
        """Parse public LinkedIn profile page."""
        data = {}

        try:
            # Try to get name from various meta tags
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title_content = og_title.get('content', '')
                # LinkedIn titles are like "Name - Title | LinkedIn"
                if ' - ' in title_content:
                    parts = title_content.split(' - ')
                    data["name"] = parts[0].strip()
                    if len(parts) > 1:
                        title_part = parts[1].replace(
                            ' | LinkedIn', '').strip()
                        data["title"] = title_part
                elif ' | ' in title_content:
                    data["name"] = title_content.split(' | ')[0].strip()

            # Try og:description for more info
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                desc = og_desc.get('content', '')
                data["bio"] = desc[:500] if desc else None

                # Extract company from description
                if ' at ' in desc:
                    company_match = re.search(r' at ([^\.·]+)', desc)
                    if company_match:
                        data["company"] = company_match.group(1).strip()[:100]

                # Extract location
                location_patterns = [
                    r'(?:based in|located in|from)\s+([^\.·]+)',
                    r'([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?(?:\s+Area)?)\s*·'
                ]
                for pattern in location_patterns:
                    loc_match = re.search(pattern, desc)
                    if loc_match:
                        data["location"] = loc_match.group(1).strip()[:100]
                        break

            # Try to get image
            og_image = soup.find('meta', property='og:image')
            if og_image:
                img_url = og_image.get('content', '')
                if img_url and 'linkedin' in img_url:
                    data["profile_image_url"] = img_url

            # Extract investment focus from bio
            if data.get("bio"):
                data["investment_focus"] = self._extract_investment_focus(
                    data["bio"])

            # If no name found, try other selectors
            if not data.get("name"):
                # Try h1 tag
                h1 = soup.find('h1')
                if h1:
                    data["name"] = h1.get_text(strip=True)[:100]

            return data if data.get("name") else None

        except Exception as e:
            logger.error(f"Profile parsing error: {e}")
            return None

    def _extract_from_url(self, url: str) -> Optional[InvestorProfile]:
        """Extract basic info from LinkedIn URL."""
        try:
            # Extract username from URL
            match = re.search(r'linkedin\.com/in/([^/?]+)', url)
            if match:
                username = match.group(1)
                # Convert URL slug to readable name
                name = username.replace('-', ' ').title()

                return InvestorProfile(
                    name=name,
                    linkedin_url=url,
                    source="linkedin"
                )
        except Exception as e:
            logger.error(f"URL extraction error: {e}")

        return None

    def _extract_investment_focus(self, text: str) -> List[str]:
        """Extract investment focus keywords from text."""
        focus_keywords = {
            "health": ["health", "healthcare", "biotech", "medtech", "medical"],
            "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning"],
            "fintech": ["fintech", "finance", "banking", "payments", "crypto", "blockchain"],
            "e-commerce": ["e-commerce", "ecommerce", "retail", "marketplace", "d2c"],
            "saas": ["saas", "software", "b2b", "enterprise"],
            "edtech": ["edtech", "education", "learning"],
            "cleantech": ["climate", "cleantech", "sustainability", "green", "energy"],
            "gaming": ["gaming", "games", "esports"],
            "mobility": ["mobility", "transportation", "automotive", "ev"],
            "foodtech": ["food", "foodtech", "agtech", "agriculture"]
        }

        text_lower = text.lower()
        found_focus = []

        for category, keywords in focus_keywords.items():
            if any(kw in text_lower for kw in keywords):
                found_focus.append(category)

        return found_focus[:5]  # Limit to 5

    async def scrape_from_search_result(self, title: str, snippet: str, url: str) -> Optional[InvestorProfile]:
        """Create profile from Google search result about LinkedIn profile."""
        try:
            data = {
                "linkedin_url": url,
                "source": "linkedin"
            }

            # Extract name from title (usually "Name - Title | LinkedIn")
            if ' - ' in title:
                parts = title.split(' - ')
                data["name"] = parts[0].strip()
                if len(parts) > 1:
                    title_part = parts[1].replace(' | LinkedIn', '').strip()
                    data["title"] = title_part
            elif ' | ' in title:
                data["name"] = title.split(' | ')[0].strip()
            else:
                data["name"] = title.replace(' | LinkedIn', '').strip()

            # Extract info from snippet
            if snippet:
                data["bio"] = snippet[:500]

                # Look for company
                if ' at ' in snippet:
                    company_match = re.search(r' at ([^\.·\n]+)', snippet)
                    if company_match:
                        data["company"] = company_match.group(1).strip()[:100]

                # Look for location
                location_patterns = [
                    r'([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?(?:\s+Area)?)\s*·',
                    r'Location:\s*([^\.·\n]+)',
                    r'based in\s+([^\.·\n]+)'
                ]
                for pattern in location_patterns:
                    loc_match = re.search(pattern, snippet)
                    if loc_match:
                        data["location"] = loc_match.group(1).strip()[:100]
                        break

                # Extract investment focus
                data["investment_focus"] = self._extract_investment_focus(
                    snippet)

            if data.get("name"):
                return InvestorProfile(**data)

        except Exception as e:
            logger.error(f"Search result parsing error: {e}")

        return None

    async def enrich_profile(self, profile: "InvestorProfile") -> "InvestorProfile":
        """
        Enrich an investor profile with additional LinkedIn data.
        Scrapes the profile page to get more detailed information.
        """
        if not profile.linkedin_url:
            return profile

        # Check cache first
        cache_key = profile.linkedin_url
        if cache_key in self._scraped_profiles_cache:
            cached = self._scraped_profiles_cache[cache_key]
            return self._merge_profiles(profile, cached)

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    profile.linkedin_url,
                    headers=self._headers,
                    timeout=10
                )

                if response.status_code != 200:
                    logger.warning(
                        f"LinkedIn returned {response.status_code} for {profile.linkedin_url}")
                    return profile

                html = response.text
                soup = BeautifulSoup(html, 'html.parser')

                # Get additional data from the page
                enriched_data = self._extract_detailed_info(soup)

                if enriched_data:
                    # Cache the result
                    self._scraped_profiles_cache[cache_key] = enriched_data

                    # Merge with existing profile
                    return self._merge_profiles(profile, enriched_data)

        except Exception as e:
            logger.warning(
                f"Profile enrichment failed for {profile.linkedin_url}: {e}")

        return profile

    def _extract_detailed_info(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract detailed information from LinkedIn profile page."""
        data = {}

        try:
            # Extract from JSON-LD if available
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                import json
                try:
                    ld_data = json.loads(json_ld.string)
                    if isinstance(ld_data, dict):
                        if ld_data.get('name'):
                            data['name'] = ld_data['name']
                        if ld_data.get('jobTitle'):
                            data['title'] = ld_data['jobTitle']
                        if ld_data.get('worksFor'):
                            works_for = ld_data['worksFor']
                            if isinstance(works_for, dict):
                                data['company'] = works_for.get('name')
                            elif isinstance(works_for, list) and works_for:
                                data['company'] = works_for[0].get('name')
                        if ld_data.get('address'):
                            addr = ld_data['address']
                            if isinstance(addr, dict):
                                data['location'] = addr.get(
                                    'addressLocality') or addr.get('addressRegion')
                except json.JSONDecodeError:
                    pass

            # Extract experience section
            experience_section = soup.find(
                'section', {'id': 'experience-section'})
            if experience_section:
                experiences = []
                exp_items = experience_section.find_all(
                    'li', class_='result-card')
                for item in exp_items[:3]:  # Get last 3 positions
                    exp_title = item.find('h3')
                    exp_company = item.find('h4')
                    if exp_title and exp_company:
                        experiences.append({
                            'title': exp_title.get_text(strip=True),
                            'company': exp_company.get_text(strip=True)
                        })
                if experiences:
                    data['experience'] = experiences

            # Try to get description/about section
            about_section = soup.find('section', {'id': 'about-section'})
            if about_section:
                about_text = about_section.get_text(strip=True)
                if about_text:
                    data['bio'] = about_text[:800]
                    # Extract investment focus from bio
                    data['investment_focus'] = self._extract_investment_focus(
                        about_text)

            # Get profile image
            profile_img = soup.find('img', class_='profile-photo')
            if not profile_img:
                profile_img = soup.find('meta', property='og:image')
                if profile_img:
                    data['profile_image_url'] = profile_img.get('content')

            # Extract skills/expertise
            skills_section = soup.find('section', {'id': 'skills-section'})
            if skills_section:
                skills = []
                skill_items = skills_section.find_all(
                    'span', class_='skill-name')
                for skill in skill_items[:10]:
                    skills.append(skill.get_text(strip=True))
                if skills:
                    data['skills'] = skills

        except Exception as e:
            logger.error(f"Detail extraction error: {e}")

        return data if data else None

    def _merge_profiles(self, original: "InvestorProfile", enriched: dict) -> "InvestorProfile":
        """Merge enriched data into the original profile."""
        # Create a dict from the original profile
        profile_dict = original.model_dump()

        # Only update fields that are None or empty in original
        for key, value in enriched.items():
            if key in profile_dict:
                original_value = profile_dict.get(key)
                if not original_value or (isinstance(original_value, list) and len(original_value) == 0):
                    profile_dict[key] = value
                elif key == 'bio' and value and len(str(value)) > len(str(original_value or '')):
                    # Prefer longer bio
                    profile_dict[key] = value
                elif key == 'investment_focus' and value:
                    # Merge investment focus
                    existing = set(profile_dict.get('investment_focus', []))
                    existing.update(value)
                    profile_dict['investment_focus'] = list(existing)[:8]

        # Add scraped indicator
        profile_dict['source'] = f"{profile_dict.get('source', 'linkedin')}_enriched"

        from app.models import InvestorProfile as IP
        return IP(**profile_dict)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._scraped_profiles_cache.clear()
        logger.info("LinkedIn scraper cleaned up")
