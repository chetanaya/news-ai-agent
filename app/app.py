import streamlit as st
import os
import sys
import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.yaml_handler import get_app_config, get_brands_config
from utils.database import DataManager
from utils.logger import setup_logger
from agents.agent_orchestrator import AgentOrchestrator

# Load environment variables
load_dotenv()

# Set up logger
logger = setup_logger("streamlit_app")

# Set page config
st.set_page_config(
    page_title="Brand News Analyzer",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state if not already done
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.refresh_running = False
    st.session_state.last_refresh_time = None
    st.session_state.last_results_path = None
    st.session_state.selected_brands = []
    st.session_state.view_mode = "latest"

# Load configurations
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_configs():
    app_config = get_app_config()
    brands_config = get_brands_config()
    return app_config, brands_config

app_config, brands_config = load_configs()

# Set up app theme
app_theme = app_config.get('app', {}).get('theme', {})
primary_color = app_theme.get('primary_color', '#4CAF50')
secondary_color = app_theme.get('secondary_color', '#2196F3')

# Custom CSS
st.markdown(f"""
<style>
    .main-header {{
        color: {primary_color};
    }}
    .subheader {{
        color: {secondary_color};
    }}
    .stButton button {{
        background-color: {primary_color};
        color: white;
    }}
    .stButton button:hover {{
        background-color: {secondary_color};
    }}
</style>
""", unsafe_allow_html=True)

# Function to get all available brands
@st.cache_data(ttl=300)
def get_available_brands():
    brands = brands_config.get('brands', [])
    return [brand['name'] for brand in brands]

# Initialize Data Manager
data_manager = DataManager()

# Sidebar
st.sidebar.image("https://placehold.co/400x100/2196F3/FFFFFF?text=Brand+News+Analyzer", use_column_width=True)
st.sidebar.title("Settings")

# Brand selection
available_brands = get_available_brands()
selected_brands = st.sidebar.multiselect(
    "Select brands to track:",
    available_brands,
    default=st.session_state.selected_brands
)

st.session_state.selected_brands = selected_brands

# View selection
view_options = ["Latest Refresh", "Historical Data"]
selected_view = st.sidebar.radio("View", view_options)
if selected_view == "Latest Refresh":
    st.session_state.view_mode = "latest"
else:
    st.session_state.view_mode = "historical"

# Historical data selection (if applicable)
if st.session_state.view_mode == "historical":
    timestamps = data_manager.get_all_refresh_timestamps()
    if timestamps:
        selected_timestamp = st.sidebar.selectbox(
            "Select refresh timestamp:",
            timestamps
        )
        st.session_state.selected_timestamp = selected_timestamp
    else:
        st.sidebar.warning("No historical data available")

# Action buttons
refresh_col, status_col = st.sidebar.columns([2, 1])

with refresh_col:
    refresh_button = st.button("🔄 Refresh Data", disabled=st.session_state.refresh_running)

with status_col:
    if st.session_state.refresh_running:
        st.markdown("⏳ Running...")

# Show last refresh time
if st.session_state.last_refresh_time:
    st.sidebar.info(f"Last refresh: {st.session_state.last_refresh_time}")

# Refresh data function
def refresh_data():
    if not selected_brands:
        st.sidebar.error("Please select at least one brand")
        return
    
    st.session_state.refresh_running = True
    
    try:
        # Initialize orchestrator
        orchestrator = AgentOrchestrator()
        
        # Run the pipeline
        with st.sidebar:
            with st.spinner("Fetching and analyzing news..."):
                results_path = orchestrator.run_full_pipeline(selected_brands)
        
        # Update session state
        st.session_state.last_refresh_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.last_results_path = results_path
        
        # Success message
        st.sidebar.success("Data refreshed successfully!")
        
    except Exception as e:
        st.sidebar.error(f"Error refreshing data: {str(e)}")
    
    finally:
        st.session_state.refresh_running = False
        st.rerun()

# Handle refresh button click
if refresh_button:
    refresh_data()

# Main content
st.markdown(f'<h1 class="main-header">{app_config["app"]["title"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="subheader">{app_config["app"]["description"]}</p>', unsafe_allow_html=True)

# Determine which data to display
def load_data():
    if st.session_state.view_mode == "historical" and hasattr(st.session_state, 'selected_timestamp'):
        return data_manager.get_data_by_timestamp(st.session_state.selected_timestamp)
    else:
        return data_manager.get_latest_data()

# Load the data
df = load_data()

# Display content if data is available
if not df.empty:
    # Filter to selected brands if in the DataFrame
    if 'brand' in df.columns and selected_brands:
        df = df[df['brand'].isin(selected_brands)]
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📰 News Articles", "📊 Sentiment Analysis", "🔍 Topic Insights"])
    
    with tab1:
        st.header("Latest News Articles")
        
        # Filter controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'brand' in df.columns:
                brand_filter = st.multiselect(
                    "Filter by Brand:",
                    df['brand'].unique(),
                    default=df['brand'].unique()
                )
            else:
                brand_filter = []
        
        with col2:
            if 'sentiment' in df.columns:
                sentiment_filter = st.multiselect(
                    "Filter by Sentiment:",
                    df['sentiment'].unique(),
                    default=df['sentiment'].unique()
                )
            else:
                sentiment_filter = []
        
        with col3:
            all_topics = []
            if 'topics' in df.columns:
                # Extract all unique topics
                for topics_list in df['topics'].dropna():
                    if isinstance(topics_list, list):
                        all_topics.extend(topics_list)
                    elif isinstance(topics_list, str):
                        # Handle string representation of list
                        try:
                            import ast
                            topics = ast.literal_eval(topics_list)
                            if isinstance(topics, list):
                                all_topics.extend(topics)
                        except:
                            pass
                
                unique_topics = list(set(all_topics))
                topic_filter = st.multiselect(
                    "Filter by Topic:",
                    unique_topics,
                    default=[]
                )
            else:
                topic_filter = []
        
        # Apply filters
        filtered_df = df.copy()
        
        if brand_filter and 'brand' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['brand'].isin(brand_filter)]
        
        if sentiment_filter and 'sentiment' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['sentiment'].isin(sentiment_filter)]
        
        if topic_filter and 'topics' in filtered_df.columns:
            # Filter for articles that contain any of the selected topics
            topic_mask = filtered_df['topics'].apply(
                lambda x: any(topic in x for topic in topic_filter) 
                if isinstance(x, list) 
                else False
            )
            filtered_df = filtered_df[topic_mask]
        
        # Display articles
        if not filtered_df.empty:
            for i, row in filtered_df.iterrows():
                with st.expander(f"{row.get('brand', 'Unknown')} - {row.get('title', 'No Title')}"):
                    st.markdown(f"**Source:** [{row.get('source', 'Unknown')}]({row.get('url', '#')})")
                    st.markdown(f"**Published:** {row.get('published_date', 'Unknown')}")
                    st.markdown(f"**Sentiment:** {row.get('sentiment', 'Unknown')} ({row.get('polarity_score', 0):.2f})")
                    
                    if 'topics' in row and row['topics']:
                        topics_str = ", ".join(row['topics']) if isinstance(row['topics'], list) else row['topics']
                        st.markdown(f"**Topics:** {topics_str}")
                    
                    if 'summary' in row and row['summary']:
                        st.markdown("### Summary")
                        st.markdown(row['summary'])
                    
                    if 'content' in row and row['content']:
                        with st.expander("View Full Content"):
                            st.markdown(row['content'])
        else:
            st.info("No articles match the selected filters.")
    
    with tab2:
        st.header("Sentiment Analysis")
        
        # Sentiment distribution chart
        if 'sentiment' in df.columns:
            import plotly.express as px
            
            # Count by sentiment
            sentiment_counts = df['sentiment'].value_counts().reset_index()
            sentiment_counts.columns = ['Sentiment', 'Count']
            
            # Plot pie chart
            fig1 = px.pie(
                sentiment_counts, 
                values='Count', 
                names='Sentiment',
                title='Sentiment Distribution',
                color='Sentiment',
                color_discrete_map={
                    'positive': '#4CAF50',
                    'neutral': '#FFC107',
                    'negative': '#F44336'
                }
            )
            st.plotly_chart(fig1)
            
            # Sentiment by brand
            if 'brand' in df.columns:
                sentiment_by_brand = df.groupby(['brand', 'sentiment']).size().reset_index(name='count')
                
                fig2 = px.bar(
                    sentiment_by_brand,
                    x='brand',
                    y='count',
                    color='sentiment',
                    title='Sentiment by Brand',
                    color_discrete_map={
                        'positive': '#4CAF50',
                        'neutral': '#FFC107',
                        'negative': '#F44336'
                    }
                )
                st.plotly_chart(fig2)
            
            # Polarity distribution
            if 'polarity_score' in df.columns:
                fig3 = px.histogram(
                    df,
                    x='polarity_score',
                    nbins=20,
                    title='Polarity Score Distribution',
                    color_discrete_sequence=['#2196F3']
                )
                fig3.update_layout(bargap=0.1)
                st.plotly_chart(fig3)
        else:
            st.info("Sentiment data not available in the dataset.")
    
    with tab3:
        st.header("Topic Insights")
        
        # Extract and count topics
        if 'topics' in df.columns:
            import plotly.express as px
            
            # Process topics
            all_topics = []
            for topics_list in df['topics'].dropna():
                if isinstance(topics_list, list):
                    all_topics.extend(topics_list)
                elif isinstance(topics_list, str):
                    # Handle string representation of list
                    try:
                        import ast
                        topics = ast.literal_eval(topics_list)
                        if isinstance(topics, list):
                            all_topics.extend(topics)
                    except:
                        pass
            
            # Count topics
            from collections import Counter
            topic_counts = Counter(all_topics)
            topic_df = pd.DataFrame([
                {'Topic': topic, 'Count': count} 
                for topic, count in topic_counts.most_common(20)
            ])
            
            if not topic_df.empty:
                # Plot topics bar chart
                fig1 = px.bar(
                    topic_df,
                    x='Count',
                    y='Topic',
                    orientation='h',
                    title='Top 20 Topics',
                    color_discrete_sequence=['#2196F3']
                )
                st.plotly_chart(fig1)
                
                # Topic by brand if available
                if 'brand' in df.columns:
                    st.subheader("Topics by Brand")
                    
                    # Create brand-topic pairs
                    brand_topic_pairs = []
                    for _, row in df.iterrows():
                        brand = row.get('brand')
                        topics = row.get('topics')
                        
                        if not brand or not topics:
                            continue
                        
                        # Process topics list
                        if isinstance(topics, str):
                            try:
                                topics = ast.literal_eval(topics)
                            except:
                                continue
                        
                        if isinstance(topics, list):
                            for topic in topics:
                                brand_topic_pairs.append({
                                    'Brand': brand,
                                    'Topic': topic
                                })
                    
                    if brand_topic_pairs:
                        brand_topic_df = pd.DataFrame(brand_topic_pairs)
                        brand_topic_counts = brand_topic_df.groupby(['Brand', 'Topic']).size().reset_index(name='Count')
                        
                        # Get top topics per brand
                        top_brand_topics = []
                        for brand in brand_topic_df['Brand'].unique():
                            brand_data = brand_topic_counts[brand_topic_counts['Brand'] == brand]
                            top_n = min(5, len(brand_data))
                            top_brand_topics.append(brand_data.nlargest(top_n, 'Count'))
                        
                        brand_topics_df = pd.concat(top_brand_topics)
                        
                        # Plot brand-topic heatmap
                        fig2 = px.density_heatmap(
                            brand_topics_df,
                            x='Brand',
                            y='Topic',
                            z='Count',
                            title='Top Topics by Brand',
                            color_continuous_scale='blues'
                        )
                        st.plotly_chart(fig2)
            else:
                st.info("No topic data available for analysis.")
        else:
            st.info("Topic data not available in the dataset.")
else:
    st.info("No data available. Please select brands and click 'Refresh Data' to start analyzing.")
    
    # Display example cards
    if not selected_brands:
        st.warning("Please select at least one brand from the sidebar to start.")
    else:
        with st.spinner("Ready to fetch data for: " + ", ".join(selected_brands)):
            st.balloons()
            st.markdown("Click the 'Refresh Data' button in the sidebar to begin fetching and analyzing news articles.")