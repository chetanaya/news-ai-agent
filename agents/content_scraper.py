import requests
from bs4 import BeautifulSoup
import time
import random
from typing import Dict, Any, Optional, List
import re

from utils.logger import LoggerMixin
from utils.yaml_handler import get_agent_config


class ContentScraper(LoggerMixin):
    """Agent for scraping content from news article URLs"""
    
    def __init__(self):
        """Initialize the Content Scraper Agent"""
        self.agent_config = get_agent_config()
        
        # Extract configuration
        self.timeout = self.agent_config['fetch_config']['request_timeout']
        self.user_agent = self.agent_config['fetch_config']['user_agent']
        
        # Set up headers for requests
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Common article content selectors for different websites
        self.content_selectors = [
            'article', '.article-content', '.entry-content', 
            '.post-content', '.story-body', '.article-body',
            '[itemprop="articleBody"]', '.news-article', '.story',
            '.content', '.post', '.article', '.story-content',
            '#content', '#article-body', '.main-content'
        ]
        
        # Elements to remove (ads, related content, etc.)
        self.remove_selectors = [
            '.ad', '.advertisement', '.social-share', '.related',
            '.sidebar', '.comment', '.footer', '.nav', '.menu',
            '.subscription', '.newsletter', '.popup', '.overlay',
            '.cookie-notice'
        ]
    
    def scrape_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape content from a news article URL
        
        Args:
            article: Article metadata dictionary
            
        Returns:
            Article with added content field
        """
        url = article.get('url', '')
        if not url:
            self.logger.error("No URL provided for article")
            article['content'] = ""
            article['scrape_success'] = False
            return article
        
        self.logger.info(f"Scraping content from: {url}")
        
        try:
            # Get the page content
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch {url}: Status {response.status_code}")
                article['content'] = ""
                article['scrape_success'] = False
                return article
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article content
            content = self._extract_article_content(soup)
            
            if not content:
                self.logger.warning(f"Could not extract content from {url}")
                # Try to get at least something
                content = self._extract_fallback_content(soup)
            
            # Clean content
            clean_content = self._clean_content(content)
            
            article['content'] = clean_content
            article['scrape_success'] = True
            
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            article['content'] = ""
            article['scrape_success'] = False
        
        return article
    
    def _extract_article_content(self, soup: BeautifulSoup) -> str:
        """
        Extract the main article content using common selectors
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Extracted content as text
        """
        # Try each selector in order
        for selector in self.content_selectors:
            elements = soup.select(selector)
            if elements:
                # Take the largest content block if multiple matches
                largest_element = max(elements, key=lambda x: len(x.get_text()))
                
                # Remove unwanted elements before extracting text
                for remove_selector in self.remove_selectors:
                    for el in largest_element.select(remove_selector):
                        el.decompose()
                
                return largest_element.get_text()
        
        return ""
    
    def _extract_fallback_content(self, soup: BeautifulSoup) -> str:
        """
        Fallback method to extract content when main selectors fail
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Extracted content as text
        """
        # Remove header, footer, nav
        for tag in ['header', 'footer', 'nav', 'aside']:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove script and style tags
        for tag in ['script', 'style', 'noscript', 'iframe', 'svg']:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove unwanted classes
        for selector in self.remove_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Look for paragraphs in the body
        paragraphs = soup.find_all('p')
        
        if paragraphs:
            # Filter out very short paragraphs (likely navigation/metadata)
            valid_paragraphs = [p.get_text() for p in paragraphs if len(p.get_text()) > 50]
            
            if valid_paragraphs:
                return "\n\n".join(valid_paragraphs)
        
        # Last resort: just get the body text
        body = soup.find('body')
        if body:
            return body.get_text()
            
        return soup.get_text()
    
    def _clean_content(self, content: str) -> str:
        """
        Clean extracted content
        
        Args:
            content: Raw extracted content
            
        Returns:
            Cleaned content
        """
        # Replace multiple newlines with a single newline
        clean = re.sub(r'\n+', '\n', content)
        
        # Replace multiple spaces with a single space
        clean = re.sub(r'\s+', ' ', clean)
        
        # Remove leading/trailing whitespace
        clean = clean.strip()
        
        # Split into paragraphs and rejoin (better formatting)
        paragraphs = re.split(r'\n\s*\n', clean)
        clean_paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return "\n\n".join(clean_paragraphs)
    
    def scrape_multiple_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scrape content from multiple articles with rate limiting
        
        Args:
            articles: List of article metadata dictionaries
            
        Returns:
            List of articles with added content
        """
        self.logger.info(f"Scraping {len(articles)} articles")
        results = []
        
        for i, article in enumerate(articles):
            # Add some rate limiting to be respectful
            if i > 0:
                delay = random.uniform(1.0, 3.0)
                time.sleep(delay)
            
            # Scrape the article
            scraped_article = self.scrape_article(article)
            results.append(scraped_article)
            
            # Log progress
            if (i + 1) % 5 == 0 or i == len(articles) - 1:
                self.logger.info(f"Scraped {i + 1}/{len(articles)} articles")
        
        return results