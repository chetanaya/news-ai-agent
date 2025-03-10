import streamlit as st
import os
import sys
import datetime

# Add parent directory to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from utils.yaml_handler import (
    get_app_config,
    get_brands_config,
    get_sources_config,
    save_yaml_config,
    get_agent_config,
)
from utils.database import DataManager
from agents.agent_orchestrator import AgentOrchestrator

# Set page config
st.set_page_config(
    page_title="Brand News Analyzer - Home",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
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
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.refresh_running = False
    st.session_state.last_refresh_time = None
    st.session_state.last_results_path = None
    st.session_state.selected_brands = []


# Function to get all available brands
@st.cache_data(ttl=300)
def get_available_brands():
    brands = brands_config.get("brands", [])
    return [brand["name"] for brand in brands]


available_brands = get_available_brands()

# Title and description
st.title("Brand News Analyzer")
st.markdown(app_config["app"]["description"])

# Main content
st.header("Start Tracking Brands")

# Brand selection
st.subheader("Brand Selection")
col1, col2 = st.columns([3, 1])

with col1:
    selected_brands = st.multiselect(
        "Select brands to track:",
        available_brands,
        default=st.session_state.selected_brands,
        help="Select one or more brands to analyze news articles for",
    )
    st.session_state.selected_brands = selected_brands

# Add region selector for DuckDuckGo
sources_config = get_sources_config()
agent_config = get_agent_config()

# Get the DuckDuckGo source
duck_source = None
for source in sources_config.get("news_sources", []):
    if source.get("name") == "DuckDuckGo" and source.get("enabled", True):
        duck_source = source
        break

if duck_source:
    st.subheader("DuckDuckGo Settings")

    # Get available regions from config
    regions = agent_config.get("duckduckgo_regions", [])
    region_names = [r["name"] for r in regions]
    region_ids = [r["id"] for r in regions]

    # Get current region
    current_region = duck_source.get("params", {}).get("region", "us-en")
    current_index = (
        region_ids.index(current_region) if current_region in region_ids else 0
    )

    # Region selector
    new_region_name = st.selectbox(
        "Select region for DuckDuckGo search:",
        region_names,
        index=current_index,
        help="Select the region for DuckDuckGo search results",
    )

    # Map back to region ID
    new_region = region_ids[region_names.index(new_region_name)]

    # Update if changed
    if new_region != current_region:
        if "params" not in duck_source:
            duck_source["params"] = {}
        duck_source["params"]["region"] = new_region
        save_yaml_config(sources_config, os.path.join("config", "sources.yaml"))
        st.success(f"DuckDuckGo region updated to {new_region_name}")
        st.rerun()

with col2:
    refresh_button = st.button(
        "🔄 Refresh Data", disabled=st.session_state.refresh_running
    )


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
        st.session_state.last_refresh_time = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
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
    brands_count = (
        latest_data["brand"].nunique() if "brand" in latest_data.columns else 0
    )

    # Sentiment stats if available
    sentiment_stats = {}
    if "sentiment" in latest_data.columns:
        sentiment_counts = latest_data["sentiment"].value_counts()
        for sentiment in ["positive", "neutral", "negative"]:
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
            st.metric("Positive Articles", sentiment_stats.get("positive", 0))

        with col4:
            st.metric("Negative Articles", sentiment_stats.get("negative", 0))

    # Show last refresh time
    if st.session_state.last_refresh_time:
        st.info(f"Last refresh: {st.session_state.last_refresh_time}")

    # Link to dashboard
    st.markdown("### [View Full Dashboard](/Dashboard)")

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
