import streamlit as st
import os
import sys
import datetime
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.yaml_handler import get_app_config, get_brands_config, get_sources_config, save_yaml_config
from utils.database import DataManager
from agents.agent_orchestrator import AgentOrchestrator

# Define the search engine functions directly in this file
def search_engine_selector():
    """
    Component for selecting the default search engine
    
    Returns:
        The selected search engine name
    """
    # Load current configuration
    sources_config = get_sources_config()
    
    # Get available search engines (only enabled ones)
    available_engines = [
        src['name'] for src in sources_config.get('news_sources', [])
        if src.get('enabled', True)
    ]
    
    # Get current default
    default_engine = sources_config.get('default_search_engine', 
                                        available_engines[0] if available_engines else None)
    
    # If no engines available, show message
    if not available_engines:
        st.warning("No news sources are enabled. Please check settings.")
        return None
    
    # Create selectbox
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_engine = st.selectbox(
            "Search Engine",
            available_engines,
            index=available_engines.index(default_engine) if default_engine in available_engines else 0,
            help="Select which search engine to use for fetching news"
        )
    
    with col2:
        if st.button("Set Default") and selected_engine != default_engine:
            # Update default in config
            sources_config['default_search_engine'] = selected_engine
            save_yaml_config(sources_config, os.path.join("config", "sources.yaml"))
            
            st.success(f"Default search engine set to {selected_engine}")
            
            # Rerun to update the interface
            st.experimental_rerun()
    
    return selected_engine

def get_search_engine_info(engine_name=None):
    """
    Get information about a specific search engine or the default one
    
    Args:
        engine_name: Name of the search engine (optional, uses default if None)
        
    Returns:
        Dictionary with search engine configuration
    """
    sources_config = get_sources_config()
    
    if engine_name is None:
        engine_name = sources_config.get('default_search_engine')
    
    # Find the engine in the config
    for source in sources_config.get('news_sources', []):
        if source.get('name') == engine_name:
            return source
    
    return None

# Set page config
st.set_page_config(
    page_title="Brand News Analyzer - Home",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configurations
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_configs():
    app_config = get_app_config()
    brands_config = get_brands_config()
    return app_config, brands_config

app_config, brands_config = load_configs()

# Initialize Data Manager
data_manager = DataManager()

# Initialize session state if not already done
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.refresh_running = False
    st.session_state.last_refresh_time = None
    st.session_state.last_results_path = None
    st.session_state.selected_brands = []

# Function to get all available brands
@st.cache_data(ttl=300)
def get_available_brands():
    brands = brands_config.get('brands', [])
    return [brand['name'] for brand in brands]

available_brands = get_available_brands()

# Title and description
st.title("Brand News Analyzer")
st.markdown(app_config["app"]["description"])

# Main content
st.header("Start Tracking Brands")

# Add search engine selector
st.subheader("Search Configuration")
selected_engine = search_engine_selector()
engine_info = get_search_engine_info(selected_engine)

if engine_info:
    st.markdown(f"""
    **Using search engine:** {selected_engine} ({engine_info['type']})
    """)
    
    if engine_info['type'] == 'duckduckgo':
        # Show DuckDuckGo specific info
        time_period_map = {
            'd': 'Last 24 hours', 
            'w': 'Last week', 
            'm': 'Last month'
        }
        time_period = engine_info.get('params', {}).get('time_period', 'w')
        max_results = engine_info.get('params', {}).get('max_results', 10)
        
        st.markdown(f"""
        - Time period: {time_period_map.get(time_period, 'Last week')}
        - Results per keyword: {max_results}
        """)
    elif engine_info['type'] == 'rss':
        st.markdown(f"""
        - RSS feed: {engine_info.get('api_endpoint', 'Not specified')}
        """)
    elif engine_info['type'] == 'api':
        api_key_var = engine_info.get('api_key', '').replace('${', '').replace('}', '')
        api_key_set = os.environ.get(api_key_var, '') != ''
        
        st.markdown(f"""
        - API: {engine_info.get('api_endpoint', 'Not specified')}
        - API Key: {'✅ Set' if api_key_set else '❌ Not set'}
        """)
        
        if not api_key_set:
            st.warning(f"API key not set for {selected_engine}. Set it in Settings > API Configuration.")

# Brand selection
st.subheader("Brand Selection")
col1, col2 = st.columns([3, 1])

with col1:
    selected_brands = st.multiselect(
        "Select brands to track:",
        available_brands,
        default=st.session_state.selected_brands,
        help="Select one or more brands to analyze news articles for"
    )
    st.session_state.selected_brands = selected_brands

with col2:
    refresh_button = st.button("🔄 Refresh Data", disabled=st.session_state.refresh_running)

# Refresh data function
def refresh_data():
    if not selected_brands:
        st.error("Please select at least one brand")
        return
    
    st.session_state.refresh_running = True
    
    try:
        # Initialize orchestrator
        orchestrator = AgentOrchestrator()
        
        # Run the pipeline
        with st.spinner("Fetching and analyzing news..."):
            results_path = orchestrator.run_full_pipeline(selected_brands)
        
        # Update session state
        st.session_state.last_refresh_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.last_results_path = results_path
        
        # Success message
        st.success("Data refreshed successfully!")
        
        # Redirect to dashboard
        st.experimental_rerun()
        
    except Exception as e:
        st.error(f"Error refreshing data: {str(e)}")
    
    finally:
        st.session_state.refresh_running = False

# Handle refresh button click
if refresh_button:
    refresh_data()

# Show quick stats if data is available
latest_data = data_manager.get_latest_data()

if not latest_data.empty:
    st.header("Current Statistics")
    
    # Calculate stats
    total_articles = len(latest_data)
    brands_count = latest_data['brand'].nunique() if 'brand' in latest_data.columns else 0
    
    # Sentiment stats if available
    sentiment_stats = {}
    if 'sentiment' in latest_data.columns:
        sentiment_counts = latest_data['sentiment'].value_counts()
        for sentiment in ['positive', 'neutral', 'negative']:
            if sentiment in sentiment_counts:
                sentiment_stats[sentiment] = sentiment_counts[sentiment]
            else:
                sentiment_stats[sentiment] = 0
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Articles", total_articles)
    
    with col2:
        st.metric("Brands Analyzed", brands_count)
    
    if sentiment_stats:
        with col3:
            st.metric("Positive Articles", sentiment_stats.get('positive', 0))
        
        with col4:
            st.metric("Negative Articles", sentiment_stats.get('negative', 0))
    
    # Show last refresh time
    if st.session_state.last_refresh_time:
        st.info(f"Last refresh: {st.session_state.last_refresh_time}")
    
    # Link to dashboard
    st.markdown("### [View Full Dashboard](/dashboard)")

# Help section
with st.expander("How to use this app"):
    st.markdown("""
    ### Getting Started
    1. Select one or more brands from the dropdown menu
    2. Click "Refresh Data" to fetch and analyze the latest news articles
    3. View the results in the Dashboard
    
    ### Features
    - **Automatic content scraping**: We extract the full text of news articles
    - **AI-powered analysis**: Articles are analyzed for sentiment and key topics
    - **Dashboard visualization**: See trends and patterns across brands
    
    ### How it works
    1. **News Collection**: We search various sources for the latest news about your selected brands
    2. **Content Extraction**: Our system visits each article and extracts the relevant content
    3. **AI Analysis**: Advanced AI models analyze the text for sentiment, topics, and create summaries
    4. **Visualization**: All data is organized into an interactive dashboard for easy exploration
    """)

# About section
st.sidebar.title("About")
st.sidebar.info("""
**Brand News Analyzer** helps you track and analyze news about your favorite brands using AI.

Built with:
- Streamlit
- LangChain
- OpenAI
- BeautifulSoup
- Python

© 2023 Brand News Analyzer
""")

# Show available refresh timestamps in sidebar
st.sidebar.title("Available Data")
timestamps = data_manager.get_all_refresh_timestamps()
if timestamps:
    st.sidebar.write("Historical data available:")
    for ts in timestamps[:5]:  # Show only the most recent 5
        st.sidebar.markdown(f"- {ts}")
    
    if len(timestamps) > 5:
        st.sidebar.markdown(f"*Plus {len(timestamps) - 5} more...*")
else:
    st.sidebar.write("No historical data available yet.")