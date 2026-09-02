"""Adapter for news aggregation from various sources"""

import logging
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

import feedparser
import requests

from hub.utils.http import acquire_rate_limit


class NewsAggregatorAdapter:
    """Adapter for aggregating news from multiple RSS sources"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "FamilyHub News Aggregator 1.0"})

    def fetch_from_rss(self, url: str, category: str = "general", priority: str = "normal") -> List[Dict]:
        """Fetch news items from an RSS feed."""
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                self.logger.error(f"Invalid URL: {url}")
                return []

            # Fetch the RSS feed
            if not acquire_rate_limit("news"):
                self.logger.error("News feed rate limited for %s", url)
                return []
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            # Parse the feed
            feed = feedparser.parse(response.content)

            news_items = []
            for entry in feed.entries[:15]:  # Limit to 15 most recent items
                try:
                    # Parse publication date
                    published_at = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        published_at = datetime(*entry.updated_parsed[:6])

                    # Extract description
                    description = entry.get("summary", "") or entry.get("description", "")
                    if not description and hasattr(entry, "content"):
                        description = entry.content[0].get("value", "") if entry.content else ""

                    # Extract the main content if summary is too long
                    if len(description) > 500:
                        description = description[:500] + "..."

                    # Create news item
                    news_item = {
                        "title": entry.get("title", "")[:200],  # Limit title length
                        "description": description,
                        "url": entry.get("link", ""),
                        "source": parsed_url.netloc,
                        "category": category,
                        "published_at": published_at.isoformat() if published_at else None,
                        "priority": priority,
                        "author": entry.get("author", ""),
                        "tags": [tag.term for tag in entry.get("tags", [])],
                    }

                    news_items.append(news_item)
                except Exception as e:
                    self.logger.warning(f"Error parsing news entry from {url}: {e}")
                    continue

            return news_items
        except requests.RequestException as e:
            self.logger.error(f"Error fetching news from {url}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing news feed from {url}: {e}")
            return []

    def fetch_multiple_feeds(self, urls: List[Dict[str, str]]) -> List[Dict]:
        """Fetch news from multiple RSS feeds."""
        all_news = []

        for feed_info in urls:
            url = feed_info.get("url", "")
            category = feed_info.get("category", "general")
            priority = feed_info.get("priority", "normal")

            news_items = self.fetch_from_rss(url, category, priority)
            all_news.extend(news_items)

        # Sort by publication date (newest first)
        all_news.sort(key=lambda x: x["published_at"], reverse=True)
        return all_news

    def filter_by_priority(self, news_items: List[Dict], min_priority: str = "normal") -> List[Dict]:
        """Filter news by minimum priority level."""
        priority_order = {"low": 0, "normal": 1, "important": 2, "breaking": 3}

        min_priority_level = priority_order.get(min_priority, 1)

        filtered_news = []
        for item in news_items:
            item_priority_level = priority_order.get(item.get("priority", "normal"), 1)
            if item_priority_level >= min_priority_level:
                filtered_news.append(item)

        return filtered_news

    def filter_by_category(self, news_items: List[Dict], categories: List[str]) -> List[Dict]:
        """Filter news by specific categories."""
        if not categories:
            return news_items

        filtered_news = []
        for item in news_items:
            if item.get("category") in categories:
                filtered_news.append(item)

        return filtered_news

    def search_news(self, news_items: List[Dict], query: str) -> List[Dict]:
        """Search for news items containing the query term."""
        if not query:
            return news_items

        query_lower = query.lower()
        search_results = []

        for item in news_items:
            title_match = query_lower in item.get("title", "").lower()
            desc_match = query_lower in item.get("description", "").lower()

            if title_match or desc_match:
                search_results.append(item)

        return search_results


# Global instance
news_aggregator_adapter = NewsAggregatorAdapter()
