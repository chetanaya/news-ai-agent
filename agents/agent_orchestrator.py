from typing import List, Dict, Any, Optional
import datetime
import time
import concurrent.futures
import traceback

from utils.logger import LoggerMixin
from utils.yaml_handler import get_brands_config, get_agent_config
from utils.database import DataManager
from agents.news_fetcher import NewsFetcher
from agents.content_scraper import ContentScraper
from agents.content_analyzer import ContentAnalyzer


class AgentOrchestrator(LoggerMixin):
    """
    Orchestrator that coordinates all agents in the pipeline
    """
    
    def __init__(self):
        """Initialize the Agent Orchestrator"""
        self.brands_config = get_brands_config()
        self.agent_config = get_agent_config()
        
        # Initialize data manager
        self.data_manager = DataManager()
        
        # Initialize agents
        self.news_fetcher = NewsFetcher()
        self.content_scraper = ContentScraper()
        self.content_analyzer = ContentAnalyzer()
        
        # Extract configuration
        self.max_workers = self.agent_config.get('fetch_config', {}).get('max_workers', 4)
    
    def run_full_pipeline(self, selected_brands: Optional[List[str]] = None) -> str:
        """
        Run the full news collection and analysis pipeline
        
        Args:
            selected_brands: Optional list of brand names to process (if None, process all)
            
        Returns:
            Path to the saved results file
        """
        self.logger.info("Starting full pipeline run")
        start_time = time.time()
        
        # Get brands to process
        brands = self._get_brands_to_process(selected_brands)
        
        if not brands:
            self.logger.warning("No brands to process")
            return ""
        
        # Step 1: Fetch news articles
        articles_by_brand = self._fetch_news_for_brands(brands)
        
        # Flatten articles and add brand field
        all_articles = []
        for brand_name, articles in articles_by_brand.items():
            for article in articles:
                article['brand'] = brand_name
                all_articles.append(article)
        
        if not all_articles:
            self.logger.warning("No articles found for selected brands")
            return ""
        
        # Step 2: Scrape content
        articles_with_content = self._scrape_articles(all_articles)
        
        # Step 3: Analyze content
        analyzed_articles = self._analyze_articles(articles_with_content)
        
        # Step 4: Save results
        results_path = self._save_results(analyzed_articles)
        
        # Log summary
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.logger.info(f"Pipeline completed in {elapsed_time:.2f} seconds")
        self.logger.info(f"Processed {len(all_articles)} articles from {len(brands)} brands")
        self.logger.info(f"Results saved to: {results_path}")
        
        return results_path
    
    def _get_brands_to_process(self, selected_brands: Optional[List[str]]) -> List[Dict[str, Any]]:
        """
        Get the list of brands to process
        
        Args:
            selected_brands: Optional list of brand names to process
            
        Returns:
            List of brand configuration dictionaries
        """
        all_brands = self.brands_config.get('brands', [])
        
        if not selected_brands:
            return all_brands
        
        # Filter to only selected brands
        return [brand for brand in all_brands if brand.get('name') in selected_brands]
    
    def _fetch_news_for_brands(self, brands: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch news for multiple brands
        
        Args:
            brands: List of brand configuration dictionaries
            
        Returns:
            Dictionary mapping brand names to lists of articles
        """
        self.logger.info(f"Fetching news for {len(brands)} brands")
        results = {}
        
        for brand in brands:
            brand_name = brand.get('name')
            try:
                articles = self.news_fetcher.fetch_news_for_brand(brand)
                results[brand_name] = articles
                
                # Save raw data
                if articles:
                    self.data_manager.save_raw_data(brand_name, articles)
                    
            except Exception as e:
                self.logger.error(f"Error fetching news for {brand_name}: {str(e)}")
                self.logger.debug(traceback.format_exc())
                results[brand_name] = []
        
        return results
    
    def _scrape_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scrape content for multiple articles, potentially in parallel
        
        Args:
            articles: List of article metadata dictionaries
            
        Returns:
            List of articles with added content
        """
        self.logger.info(f"Scraping content for {len(articles)} articles")
        
        # For small numbers of articles, don't use parallelism
        if len(articles) <= 5:
            return self.content_scraper.scrape_multiple_articles(articles)
        
        # For larger numbers, use parallel processing
        results = []
        
        # Split articles into chunks for parallel processing
        chunk_size = max(1, len(articles) // self.max_workers)
        article_chunks = [articles[i:i + chunk_size] for i in range(0, len(articles), chunk_size)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            future_to_chunk = {
                executor.submit(self.content_scraper.scrape_multiple_articles, chunk): chunk 
                for chunk in article_chunks
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result()
                    results.extend(chunk_results)
                except Exception as e:
                    self.logger.error(f"Error scraping chunk: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                    # Add original articles without content
                    for article in chunk:
                        article['content'] = ""
                        article['scrape_success'] = False
                        results.append(article)
        
        return results
    
    def _analyze_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze content for multiple articles
        
        Args:
            articles: List of article dictionaries with content
            
        Returns:
            List of articles with added analysis fields
        """
        self.logger.info(f"Analyzing content for {len(articles)} articles")
        
        # For successful scrapes only
        successful_articles = [a for a in articles if a.get('scrape_success', False)]
        failed_articles = [a for a in articles if not a.get('scrape_success', False)]
        
        self.logger.info(f"Successfully scraped: {len(successful_articles)}/{len(articles)} articles")
        
        # Analyze successful articles
        analyzed_articles = self.content_analyzer.analyze_multiple_articles(successful_articles)
        
        # Add dummy analysis for failed articles
        for article in failed_articles:
            article['summary'] = ""
            article['topics'] = []
            article['sentiment'] = "neutral"
            article['polarity_score'] = 0.0
        
        # Combine results
        all_results = analyzed_articles + failed_articles
        
        return all_results
    
    def _save_results(self, articles: List[Dict[str, Any]]) -> str:
        """
        Save analysis results
        
        Args:
            articles: List of analyzed article dictionaries
            
        Returns:
            Path to the saved file
        """
        # Add refresh timestamp
        timestamp = datetime.datetime.now().isoformat()
        for article in articles:
            article['refresh_timestamp'] = timestamp
        
        # Save the data
        results_path = self.data_manager.save_processed_data(articles)
        
        # Archive old data
        archive_days = self.agent_config.get('storage_config', {}).get('archive_days', 30)
        self.data_manager.archive_old_data(days=archive_days)
        
        return results_path