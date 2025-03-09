import os
from typing import Dict, Any, List, Tuple, Optional
import json
from textblob import TextBlob
import nltk
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import time

from utils.logger import LoggerMixin
from utils.yaml_handler import get_agent_config


class ContentAnalyzer(LoggerMixin):
    """Agent for analyzing article content using LLMs and NLP"""
    
    def __init__(self):
        """Initialize the Content Analyzer Agent"""
        # Load configuration
        self.agent_config = get_agent_config()
        
        # Configure TextBlob
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            self.logger.info("Downloading NLTK data...")
            nltk.download('punkt')
            nltk.download('stopwords')
        
        # Set up LLM
        self._setup_llm()
        
        # Sentiment thresholds
        self.positive_threshold = self.agent_config['analysis_config']['sentiment_threshold_positive']
        self.negative_threshold = self.agent_config['analysis_config']['sentiment_threshold_negative']
        
        # Summary length
        self.summary_min_words = self.agent_config['analysis_config']['summary_min_words']
        self.summary_max_words = self.agent_config['analysis_config'].get('summary_max_words', 250)
    
    def _setup_llm(self):
        """Set up LLM instance"""
        # Get LLM config
        llm_config = self.agent_config['llm']
        model_name = llm_config['model_name']
        
        # Create LLM instance
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.0,  # Use deterministic output for analysis
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        # Define prompt templates
        self.topic_prompt = PromptTemplate.from_template("""
        Extract the main topics from the following news article. Return between 2-5 topics.
        Format the response as a JSON array of strings.
        
        Article: {article_content}
        
        Topics:
        """)
        
        self.summary_prompt = PromptTemplate.from_template("""
        Summarize the following news article in at least {min_words} words but no more than {max_words} words.
        The summary should cover the key points and maintain the tone of the original article.
        
        Article: {article_content}
        
        Summary:
        """)
        
        self.analysis_prompt = PromptTemplate.from_template("""
        Analyze the following news article and provide:
        1. A summary (at least {min_words} words)
        2. 2-5 main topics covered in the article
        3. The overall sentiment (Positive, Negative, or Neutral)
        4. A sentiment polarity score between -1.0 (Very Negative) and 1.0 (Very Positive)
        
        Format your response as a JSON object with the keys: "summary", "topics", "sentiment", "polarity".
        
        Article: {article_content}
        
        Analysis:
        """)
    
    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the content of an article
        
        Args:
            article: Article dictionary with content
            
        Returns:
            Article with added analysis fields
        """
        content = article.get('content', '')
        
        if not content or not article.get('scrape_success', False):
            self.logger.warning(f"No content to analyze for article: {article.get('title', 'Unknown')}")
            # Add empty analysis fields
            article['summary'] = ""
            article['topics'] = []
            article['sentiment'] = "Neutral"
            article['polarity_score'] = 0.0
            return article
        
        title = article.get('title', '')
        self.logger.info(f"Analyzing article: {title}")
        
        try:
            # Option 1: Use the combined analysis chain for everything
            result = self._run_combined_analysis(content)
            
            # Option 2: If the combined analysis fails, fall back to individual analyses
            if not result:
                topics = self._extract_topics(content)
                summary = self._generate_summary(content)
                sentiment, polarity = self._analyze_sentiment(content)
                
                article['summary'] = summary
                article['topics'] = topics
                article['sentiment'] = sentiment
                article['polarity_score'] = polarity
            else:
                # Use the combined analysis results
                article['summary'] = result.get('summary', '')
                article['topics'] = result.get('topics', [])
                article['sentiment'] = result.get('sentiment', 'Neutral')
                article['polarity_score'] = result.get('polarity', 0.0)
            
            # Add analysis timestamp
            article['analysis_timestamp'] = time.time()
            
        except Exception as e:
            self.logger.error(f"Error analyzing article: {str(e)}")
            # Fall back to basic analysis
            self.logger.info("Falling back to basic sentiment analysis")
            sentiment, polarity = self._analyze_sentiment_textblob(content)
            
            article['summary'] = ""
            article['topics'] = []
            article['sentiment'] = sentiment
            article['polarity_score'] = polarity
        
        return article
    
    def _run_combined_analysis(self, content: str) -> Dict[str, Any]:
        """
        Run the combined analysis using the LLM
        
        Args:
            content: Article content
            
        Returns:
            Dictionary with analysis results or None if failed
        """
        try:
            # Truncate content if too long
            max_length = 8000  # Adjust based on model token limits
            if len(content) > max_length:
                self.logger.info(f"Truncating content from {len(content)} to {max_length} chars")
                content = content[:max_length]
            
            # Format the prompt
            formatted_prompt = self.analysis_prompt.format(
                article_content=content,
                min_words=self.summary_min_words
            )
            
            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)
            
            # Extract content from the message
            if hasattr(result, 'content'):
                result_text = result.content
            else:
                result_text = str(result)
            
            # Parse the JSON response
            try:
                analysis = json.loads(result_text)
                return analysis
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse JSON from LLM response: {result_text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in combined analysis: {str(e)}")
            return None
    
    def _extract_topics(self, content: str) -> List[str]:
        """
        Extract main topics from article content
        
        Args:
            content: Article content
            
        Returns:
            List of topic strings
        """
        # Truncate content if too long
        max_length = 6000
        if len(content) > max_length:
            content = content[:max_length]
        
        try:
            # Format the prompt
            formatted_prompt = self.topic_prompt.format(article_content=content)
            
            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)
            
            # Extract content from the message
            if hasattr(result, 'content'):
                result_text = result.content
            else:
                result_text = str(result)
            
            # Parse JSON array from the result
            try:
                topics = json.loads(result_text)
                if isinstance(topics, list):
                    return topics
                return []
            except json.JSONDecodeError:
                # If not valid JSON, try to extract topics with regex
                import re
                topics = re.findall(r'"([^"]+)"', result_text)
                return topics[:5]  # Limit to 5 topics
                
        except Exception as e:
            self.logger.error(f"Error extracting topics: {str(e)}")
            return []
    
    def _generate_summary(self, content: str) -> str:
        """
        Generate a summary of the article content
        
        Args:
            content: Article content
            
        Returns:
            Summary text
        """
        # Truncate content if too long
        max_length = 6000
        if len(content) > max_length:
            content = content[:max_length]
        
        try:
            # Format the prompt
            formatted_prompt = self.summary_prompt.format(
                article_content=content,
                min_words=self.summary_min_words,
                max_words=self.summary_max_words
            )
            
            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)
            
            # Extract content from the message
            if hasattr(result, 'content'):
                return result.content.strip()
            else:
                return str(result).strip()
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            
            # Fallback: simple extractive summary
            sentences = nltk.sent_tokenize(content)
            if len(sentences) > 3:
                return " ".join(sentences[:3])
            return content[:300] + "..."
    
    def _analyze_sentiment(self, content: str) -> Tuple[str, float]:
        """
        Analyze sentiment using LLM and TextBlob as backup
        
        Args:
            content: Article content
            
        Returns:
            Tuple of (sentiment category, polarity score)
        """
        # Try TextBlob first
        sentiment, polarity = self._analyze_sentiment_textblob(content)
        
        # Return TextBlob results
        return sentiment, polarity
    
    def _analyze_sentiment_textblob(self, content: str) -> Tuple[str, float]:
        """
        Analyze sentiment using TextBlob
        
        Args:
            content: Article content
            
        Returns:
            Tuple of (sentiment category, polarity score)
        """
        analysis = TextBlob(content)
        polarity = analysis.sentiment.polarity
        
        # Determine sentiment category based on polarity
        if polarity >= self.positive_threshold:
            sentiment = "Positive"
        elif polarity <= self.negative_threshold:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        return sentiment, polarity
    
    def analyze_multiple_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze multiple articles
        
        Args:
            articles: List of article dictionaries with content
            
        Returns:
            List of articles with added analysis fields
        """
        self.logger.info(f"Analyzing {len(articles)} articles")
        print(f"Analyzing {len(articles)} articles")
        
        results = []
        
        for i, article in enumerate(articles):
            try:
                analyzed_article = self.analyze_article(article)
                results.append(analyzed_article)
                
                # Log progress
                if (i + 1) % 5 == 0 or i == len(articles) - 1:
                    self.logger.info(f"Analyzed {i + 1}/{len(articles)} articles")
                    print(f"Analyzed {i + 1}/{len(articles)} articles")
            except Exception as e:
                self.logger.error(f"Error analyzing article {i+1}/{len(articles)}: {str(e)}")
                print(f"Error analyzing article {i+1}/{len(articles)}: {str(e)}")
                # Add the original article to ensure we don't lose data
                article['summary'] = ""
                article['topics'] = []
                article['sentiment'] = "Neutral"
                article['polarity_score'] = 0.0
                article['analysis_error'] = str(e)
                results.append(article)
        
        return results