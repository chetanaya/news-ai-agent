import os
from typing import Dict, Any, List, Tuple, Optional
import json
from textblob import TextBlob
import nltk
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import time
import traceback

# Import at the top level to avoid circular imports
from utils.logger import LoggerMixin
from utils.yaml_handler import get_agent_config, get_brands_config


class ContentAnalyzer(LoggerMixin):
    """Agent for analyzing article content using LLMs and NLP"""

    def __init__(self):
        """Initialize the Content Analyzer Agent"""
        # Load configuration
        self.agent_config = get_agent_config()
        self.brands_config = get_brands_config()

        # Get sentiment values from config
        self.sentiment_values = self.agent_config["analysis_config"].get(
            "sentiment_values",
            {"positive": "Positive", "neutral": "Neutral", "negative": "Negative"},
        )

        # Configure TextBlob
        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:
            self.logger.info("Downloading NLTK data...")
            nltk.download("punkt")
            nltk.download("stopwords")

        # Set up LLM
        self._setup_llm()

        # Sentiment thresholds
        self.positive_threshold = self.agent_config["analysis_config"][
            "sentiment_threshold_positive"
        ]
        self.negative_threshold = self.agent_config["analysis_config"][
            "sentiment_threshold_negative"
        ]

        # Summary length
        self.summary_min_words = self.agent_config["analysis_config"][
            "summary_min_words"
        ]
        self.summary_max_words = self.agent_config["analysis_config"].get(
            "summary_max_words", 250
        )

    def _setup_llm(self):
        """Set up LLM instance"""
        # Get LLM config
        llm_config = self.agent_config["llm"]
        model_name = llm_config["model_name"]

        # Create LLM instance
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.0,  # Use deterministic output for analysis
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

        # Define prompt templates
        self.summary_prompt = PromptTemplate.from_template("""
        Summarize the following news article in at least {min_words} words but no more than {max_words} words.
        The summary should cover the key points and maintain the tone of the original article.
        
        Article: {article_content}
        
        Summary:
        """)

        self.topic_prompt = PromptTemplate.from_template("""
        Classify the following news article into ONE of these topics:
        {categories}
        
        If the article doesn't fit any of these topics, classify it as "Others".
        
        Return ONLY the topic name as a string, with no additional text or explanation.
        
        Article: {article_content}
        
        Topic:
        """)

        self.subcategory_prompt = PromptTemplate.from_template("""
        Classify the following news article into ONE of these subcategories:
        {subcategories}
        
        If the article doesn't fit any of these subcategories, classify it as "Others".
        
        Return ONLY the subcategory name as a string, with no additional text or explanation.
        
        Article: {article_content}
        
        Subcategory:
        """)

        self.product_line_prompt = PromptTemplate.from_template("""
        Identify which (if any) of the following product lines are mentioned in the news article:
        {product_lines}
        
        If none are mentioned, return "None".
        If multiple are mentioned, return the MOST prominently featured one.
        
        Return ONLY the product line name as a string, with no additional text or explanation.
        
        Article: {article_content}
        
        Product Line:
        """)

        self.relevancy_prompt = PromptTemplate.from_template("""
        Determine if the following news article is relevant business news about {brand_name}.
        
        Answer with ONLY "Yes" or "No".
        - Answer "Yes" if the article contains substantive business information about {brand_name}.
        - Answer "No" if the article only mentions {brand_name} in passing or is not business-focused.
        
        Article: {article_content}
        
        Is this relevant business news about {brand_name}?
        """)

        self.sentiment_prompt = PromptTemplate.from_template("""
        Analyze the sentiment of this news article about {brand_name}.
        
        Respond with ONLY one of these three values: "Positive", "Neutral", or "Negative".
        
        Article: {article_content}
        
        Sentiment:
        """)

    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the content of an article

        Args:
            article: Article dictionary with content

        Returns:
            Article with added analysis fields
        """
        content = article.get("content", "")

        if not content or not article.get("scrape_success", False):
            self.logger.warning(
                f"No content to analyze for article: {article.get('title', 'Unknown')}"
            )
            # Add empty analysis fields
            article["summary"] = ""
            article["topic"] = "Others"
            article["subcategory"] = "Others"
            article["product_line"] = "None"
            article["is_relevant"] = False
            article["sentiment"] = self.sentiment_values["neutral"]
            article["polarity_score"] = 0.0
            return article

        title = article.get("title", "")
        brand_name = article.get("brand", "")
        self.logger.info(f"Analyzing article: {title} for brand: {brand_name}")
        print(f"Analyzing article: {title} for brand: {brand_name}")

        # Find the brand in the config
        brand_info = None
        for brand in self.brands_config.get("brands", []):
            if brand.get("name") == brand_name:
                brand_info = brand
                break

        # Get categories, subcategories, and product lines for the brand
        categories = brand_info.get("categories", []) if brand_info else []
        subcategories = brand_info.get("subcategories", []) if brand_info else []
        product_lines = brand_info.get("product_lines", []) if brand_info else []

        try:
            # Perform each analysis task separately

            # Generate summary
            self.logger.info(f"Generating summary for article: {title}")
            article["summary"] = self._generate_summary(content)

            # Classify topic
            if brand_info:
                self.logger.info(
                    f"Classifying article into topic for brand: {brand_name}"
                )
                article["topic"] = self._classify_topic(content, categories)
                self.logger.info(f"Classified as topic: {article['topic']}")

                # Classify subcategory
                self.logger.info(
                    f"Classifying article into subcategory for brand: {brand_name}"
                )
                article["subcategory"] = self._classify_subcategory(
                    content, subcategories
                )
                self.logger.info(f"Classified as subcategory: {article['subcategory']}")

                # Identify product line
                self.logger.info(f"Identifying product line for brand: {brand_name}")
                article["product_line"] = self._identify_product_line(
                    content, product_lines
                )
                self.logger.info(f"Identified product line: {article['product_line']}")

                # Check relevancy
                self.logger.info(f"Checking relevancy for brand: {brand_name}")
                article["is_relevant"] = self._check_relevancy(content, brand_name)
                self.logger.info(f"Relevancy check: {article['is_relevant']}")

                # Analyze sentiment
                self.logger.info(f"Analyzing sentiment for brand: {brand_name}")
                sentiment, polarity = self._analyze_sentiment(content, brand_name)
                article["sentiment"] = sentiment
                article["polarity_score"] = polarity
                self.logger.info(f"Sentiment: {sentiment}, Polarity: {polarity}")
            else:
                # Default values if brand info not found
                self.logger.warning(
                    f"No brand info found for {brand_name}, using default classifications"
                )
                article["topic"] = "Others"
                article["subcategory"] = "Others"
                article["product_line"] = "None"
                article["is_relevant"] = False
                sentiment, polarity = self._analyze_sentiment_textblob(content)
                article["sentiment"] = sentiment
                article["polarity_score"] = polarity

            # Add analysis timestamp
            article["analysis_timestamp"] = time.time()

        except Exception as e:
            self.logger.error(f"Error analyzing article: {str(e)}")
            self.logger.error(traceback.format_exc())
            print(f"Error analyzing article: {str(e)}")

            # Fall back to basic analysis
            self.logger.info("Falling back to basic sentiment analysis")
            sentiment, polarity = self._analyze_sentiment_textblob(content)

            article["summary"] = ""
            article["topic"] = "Others"
            article["subcategory"] = "Others"
            article["product_line"] = "None"
            article["is_relevant"] = False
            article["sentiment"] = sentiment
            article["polarity_score"] = polarity

        return article

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
                max_words=self.summary_max_words,
            )

            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)

            # Extract content from the message
            if hasattr(result, "content"):
                return result.content.strip()
            else:
                return str(result).strip()

        except Exception as e:
            self.logger.error(f"Error generating summary: {str(e)}")
            self.logger.error(traceback.format_exc())

            # Fallback: simple extractive summary
            sentences = nltk.sent_tokenize(content)
            if len(sentences) > 3:
                return " ".join(sentences[:3])
            return content[:300] + "..."

    def _analyze_sentiment(self, content: str, brand_name: str) -> Tuple[str, float]:
        """
        Analyze sentiment using LLM with TextBlob as backup

        Args:
            content: Article content
            brand_name: Name of the brand

        Returns:
            Tuple of (sentiment category, polarity score)
        """
        try:
            # Try LLM-based sentiment analysis first
            # Truncate content if too long
            max_length = 6000
            if len(content) > max_length:
                content = content[:max_length]

            # Format the prompt
            formatted_prompt = self.sentiment_prompt.format(
                article_content=content, brand_name=brand_name
            )

            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)

            # Extract content from the message
            if hasattr(result, "content"):
                sentiment_text = result.content.strip()
            else:
                sentiment_text = str(result).strip()

            # Map to configured sentiment values
            if sentiment_text.lower() == "positive":
                sentiment = self.sentiment_values["positive"]
                polarity = 0.5  # Default positive polarity
            elif sentiment_text.lower() == "negative":
                sentiment = self.sentiment_values["negative"]
                polarity = -0.5  # Default negative polarity
            else:
                sentiment = self.sentiment_values["neutral"]
                polarity = 0.0  # Default neutral polarity

            # Get TextBlob polarity for a more precise score
            _, textblob_polarity = self._analyze_sentiment_textblob(content)

            # Return LLM sentiment with TextBlob polarity
            return sentiment, textblob_polarity

        except Exception as e:
            self.logger.error(f"Error in LLM sentiment analysis: {str(e)}")
            # Fall back to TextBlob
            return self._analyze_sentiment_textblob(content)

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
            sentiment = self.sentiment_values["positive"]
        elif polarity <= self.negative_threshold:
            sentiment = self.sentiment_values["negative"]
        else:
            sentiment = self.sentiment_values["neutral"]

        return sentiment, polarity

    def _classify_topic(self, content: str, categories: List[str]) -> str:
        """
        Classify the article into one of the predefined topics

        Args:
            content: Article content
            categories: List of possible topics

        Returns:
            Topic string
        """
        if not content or not categories:
            return "Others"

        # Truncate content if too long
        max_length = 6000
        if len(content) > max_length:
            content = content[:max_length]

        try:
            # Format the prompt
            categories_str = "\n".join(categories)
            formatted_prompt = self.topic_prompt.format(
                article_content=content, categories=categories_str
            )

            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)

            # Extract content from the message
            if hasattr(result, "content"):
                topic = result.content.strip()
            else:
                topic = str(result).strip()

            # Verify that the returned topic is in the list
            if topic in categories:
                return topic

            return "Others"

        except Exception as e:
            self.logger.error(f"Error classifying topic: {str(e)}")
            self.logger.error(traceback.format_exc())
            return "Others"

    def _classify_subcategory(self, content: str, subcategories: List[str]) -> str:
        """
        Classify the article into one of the predefined subcategories

        Args:
            content: Article content
            subcategories: List of possible subcategories

        Returns:
            Subcategory string
        """
        if not content or not subcategories:
            return "Others"

        # Truncate content if too long
        max_length = 6000
        if len(content) > max_length:
            content = content[:max_length]

        try:
            # Format the prompt
            subcategories_str = "\n".join(subcategories)
            formatted_prompt = self.subcategory_prompt.format(
                article_content=content, subcategories=subcategories_str
            )

            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)

            # Extract content from the message
            if hasattr(result, "content"):
                subcategory = result.content.strip()
            else:
                subcategory = str(result).strip()

            # Verify that the returned subcategory is in the list
            if subcategory in subcategories:
                return subcategory

            return "Others"

        except Exception as e:
            self.logger.error(f"Error classifying subcategory: {str(e)}")
            self.logger.error(traceback.format_exc())
            return "Others"

    def _identify_product_line(self, content: str, product_lines: List[str]) -> str:
        """
        Identify the product line mentioned in the article

        Args:
            content: Article content
            product_lines: List of possible product lines

        Returns:
            Product line string or "None"
        """
        if not content or not product_lines:
            return "None"

        # Truncate content if too long
        max_length = 6000
        if len(content) > max_length:
            content = content[:max_length]

        try:
            # Format the prompt
            product_lines_str = "\n".join(product_lines)
            formatted_prompt = self.product_line_prompt.format(
                article_content=content, product_lines=product_lines_str
            )

            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)

            # Extract content from the message
            if hasattr(result, "content"):
                product_line = result.content.strip()
            else:
                product_line = str(result).strip()

            # Verify that the returned product line is in the list
            if product_line in product_lines:
                return product_line

            # If "None" or not in list, return "None"
            if product_line.lower() == "none":
                return "None"

            return "None"

        except Exception as e:
            self.logger.error(f"Error identifying product line: {str(e)}")
            self.logger.error(traceback.format_exc())
            return "None"

    def _check_relevancy(self, content: str, brand_name: str) -> bool:
        """
        Check if the article is relevant business news about the brand

        Args:
            content: Article content
            brand_name: Name of the brand

        Returns:
            Boolean indicating relevancy
        """
        if not content or not brand_name:
            return False

        # Truncate content if too long
        max_length = 6000
        if len(content) > max_length:
            content = content[:max_length]

        try:
            # Format the prompt
            formatted_prompt = self.relevancy_prompt.format(
                article_content=content, brand_name=brand_name
            )

            # Invoke the LLM directly
            result = self.llm.invoke(formatted_prompt)

            # Extract content from the message
            if hasattr(result, "content"):
                answer = result.content.strip().lower()
            else:
                answer = str(result).strip().lower()

            # Check for "yes" in the answer
            return "yes" in answer

        except Exception as e:
            self.logger.error(f"Error checking relevancy: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def analyze_multiple_articles(
        self, articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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
                self.logger.error(
                    f"Error analyzing article {i + 1}/{len(articles)}: {str(e)}"
                )
                self.logger.error(traceback.format_exc())
                print(f"Error analyzing article {i + 1}/{len(articles)}: {str(e)}")

                # Add the original article to ensure we don't lose data
                article["summary"] = ""
                article["topic"] = "Others"
                article["subcategory"] = "Others"
                article["product_line"] = "None"
                article["is_relevant"] = False
                article["sentiment"] = self.sentiment_values["neutral"]
                article["polarity_score"] = 0.0
                article["analysis_error"] = str(e)
                results.append(article)

        return results
