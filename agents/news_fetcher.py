import os
import requests
import feedparser
import datetime
from typing import List, Dict, Any, Optional
import time
import hashlib
from urllib.parse import quote

from utils.logger import LoggerMixin
from utils.yaml_handler import get_sources_config, get_agent_config


class NewsFetcher(LoggerMixin):
    """Agent for fetching news articles from various sources"""
    
    def __init__(self):
        """Initialize the News Fetcher Agent"""
        self.sources_config = get_sources_config()
        self.agent_config = get_agent_config()
        
        # Extract configuration
        self.max_articles = self.agent_config['fetch_config']['max_articles_per_brand']
        self.timeout = self.agent_config['fetch_config']['request_timeout']
        self.user_agent = self.agent_config['fetch_config']['user_agent']
        
        # Set up headers for requests
        self.headers = {
            'User-Agent': self.user_agent
        }
    
    def fetch_news_for_brand(self, brand: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch news for a specific brand from all configured sources
        
        Args:
            brand: Brand configuration dictionary
            
        Returns:
            List of news article metadata
        """
        brand_name = brand['name']
        self.logger.info(f"Fetching news for brand: {brand_name}")
        
        all_articles = []
        
        # Use each keyword to search for news
        for keyword in brand['keywords']:
            self.logger.debug(f"Searching for keyword: {keyword}")
            
            # Try each news source
            for source in self.sources_config['news_sources']:
                try:
                    if source['type'] == 'rss':
                        articles = self._fetch_from_rss(source, keyword)
                    elif source['type'] == 'api':
                        articles = self._fetch_from_api(source, keyword)
                    else:
                        self.logger.warning(f"Unknown source type: {source['type']}")
                        continue
                    
                    all_articles.extend(articles)
                    
                except Exception as e:
                    self.logger.error(f"Error fetching from {source['name']}: {str(e)}")
        
        # Deduplicate articles
        unique_articles = self._deduplicate_articles(all_articles)
        
        # Limit the number of articles
        limited_articles = unique_articles[:self.max_articles]
        
        self.logger.info(f"Found {len(limited_articles)} articles for {brand_name}")
        return limited_articles
    
    def _fetch_from_rss(self, source: Dict[str, Any], keyword: str) -> List[Dict[str, Any]]:
        """
        Fetch news from an RSS feed
        
        Args:
            source: Source configuration
            keyword: Search keyword
            
        Returns:
            List of articles from the RSS feed
        """
        url = source['api_endpoint'].format(keyword=quote(keyword))
        self.logger.debug(f"Fetching RSS from: {url}")
        
        feed = feedparser.parse(url)
        articles = []
        
        for entry in feed.entries:
            article = {
                'title': entry.get('title', ''),
                'url': entry.get('link', ''),
                'source': source['name'],
                'source_type': 'rss',
                'published_date': self._parse_date(entry.get('published', '')),
                'description': entry.get('summary', ''),
                'fetch_date': datetime.datetime.now().isoformat()
            }
            articles.append(article)
            
        return articles
    
    def _fetch_from_api(self, source: Dict[str, Any], keyword: str) -> List[Dict[str, Any]]:
        """
        Fetch news from a REST API
        
        Args:
            source: Source configuration
            keyword: Search keyword
            
        Returns:
            List of articles from the API
        """
        url = source['api_endpoint']
        
        # Set up parameters
        params = {}
        if 'params' in source:
            params = source['params'].copy()
            
            # Format keyword in params
            for key, value in params.items():
                if isinstance(value, str) and '{keyword}' in value:
                    params[key] = value.format(keyword=keyword)
        else:
            params['q'] = keyword
        
        # Add API key if required
        headers = self.headers.copy()
        if 'api_key' in source and source['api_key']:
            headers['Authorization'] = source['api_key']
        
        self.logger.debug(f"Fetching API from: {url}")
        response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
        
        if response.status_code != 200:
            self.logger.error(f"API error: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        articles = []
        
        # Process response based on known API formats
        # NewsAPI format
        if 'articles' in data:
            for item in data['articles']:
                article = {
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'source': item.get('source', {}).get('name', source['name']),
                    'source_type': 'api',
                    'published_date': item.get('publishedAt', ''),
                    'description': item.get('description', ''),
                    'fetch_date': datetime.datetime.now().isoformat()
                }
                articles.append(article)
        
        return articles
    
    def _parse_date(self, date_str: str) -> str:
        """
        Parse date from various formats to ISO format
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            ISO format date string
        """
        if not date_str:
            return datetime.datetime.now().isoformat()
        
        try:
            # Try parsing common RSS date formats
            # RFC 2822
            dt = datetime.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            return dt.isoformat()
        except ValueError:
            try:
                # ISO format
                dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.isoformat()
            except ValueError:
                self.logger.warning(f"Could not parse date: {date_str}")
                return datetime.datetime.now().isoformat()
    
    def _deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate articles based on URL and title
        
        Args:
            articles: List of articles
            
        Returns:
            Deduplicated list of articles
        """
        seen = set()
        unique_articles = []
        
        for article in articles:
            # Create a hash for deduplication
            title = article.get('title', '').strip().lower()
            url = article.get('url', '').strip().lower()
            
            # Skip empty titles or URLs
            if not title or not url:
                continue
            
            # Create a hash of title and URL
            hash_key = hashlib.md5(f"{title}|{url}".encode()).hexdigest()
            
            if hash_key not in seen:
                seen.add(hash_key)
                unique_articles.append(article)
        
        return unique_articles