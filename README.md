# Brand News Analyzer

A Streamlit application that tracks brand news, performs AI-powered content analysis, and visualizes the results.

## Features

- **Customizable Brand Tracking**: Follow news about your favorite brands
- **AI-Powered Analysis**: Uses OpenAI's GPT models to analyze news content
- **Automated Content Extraction**: Scrapes news articles for full content
- **Rich Visualizations**: Interactive dashboard for sentiment and topic analysis
- **Historical Data**: View and compare news across different time periods

## Architecture

The application consists of several key components:

1. **News Fetcher Agent**: Collects news articles from various sources
2. **Content Scraper Agent**: Extracts full article content
3. **Content Analyzer Agent**: Uses AI to summarize, extract topics, and analyze sentiment
4. **Agent Orchestrator**: Coordinates the workflow between agents
5. **Streamlit UI**: Provides the user interface and visualizations

## Installation

### Prerequisites

- Python 3.9 or higher
- OpenAI API key
- NewsAPI key (optional, for additional sources)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/chetanaya/news-ai-agent.git
   cd news-ai-agent
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Create a `.env` file in the root directory:
   ```
   OPENAI_API_KEY=your_openai_api_key
   NEWS_API_KEY=your_newsapi_key
   ```

4. Create necessary directories:
   ```
   mkdir -p data/raw data/processed data/archive logs
   ```

## Usage

### Running the App

Start the Streamlit app:
```
streamlit run app/app.py
```

### Configuration

All configuration is done through YAML files in the `config` directory:

- `brands.yaml`: Define brands to track and their keywords
- `sources.yaml`: Configure news sources
- `agent_config.yaml`: Configure AI models and analysis parameters
- `app_config.yaml`: Configure app appearance and dashboard settings

You can also modify these configurations through the Settings page in the application.

## Workflow

1. **Select Brands**: Choose which brands you want to track
2. **Refresh Data**: Click the refresh button to fetch new articles
3. **Analyze Results**: View the sentiment and topic analysis in the dashboard
4. **Explore Articles**: Read summaries and full content of the articles

## Components Details

### News Fetcher

The News Fetcher agent collects articles from:
- RSS feeds (like Google News)
- News APIs (like NewsAPI)

It searches for articles based on brand keywords and deduplicates results.

### Content Scraper

The Content Scraper visits each article URL and:
- Extracts the main content using BeautifulSoup
- Cleans and normalizes the text
- Handles different website layouts

### Content Analyzer

The Content Analyzer uses OpenAI's GPT models to:
- Generate concise summaries (100+ words)
- Extract main topics from the content
- Analyze sentiment (positive/negative/neutral)
- Calculate polarity scores

### Data Management

The application stores:
- Raw article metadata
- Processed analysis results
- Historical data with timestamps

## Customization

### Adding New Brands

1. Go to Settings > Brand Settings
2. Fill in the brand name, keywords, and websites
3. Click "Add Brand"

### Adding News Sources

1. Modify the `config/sources.yaml` file
2. Add a new source with type (RSS or API) and endpoint

### Modifying Analysis Parameters

1. Go to Settings > Advanced Settings
2. Adjust sentiment thresholds, summary length, etc.

## Troubleshooting

### API Key Issues

If you encounter errors related to API keys:
1. Check that your `.env` file contains the correct keys
2. Verify the keys are valid and have sufficient quota
3. You can update keys in Settings > API Configuration

### Scraping Issues

If content scraping fails:
1. Check your internet connection
2. Some sites may block scraping - consider adding a delay between requests
3. You may need to update the content selectors in `content_scraper.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Uses [LangChain](https://github.com/langchain-ai/langchain) for AI orchestration
- Powered by [OpenAI](https://openai.com/) GPT models
- Web scraping with [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)