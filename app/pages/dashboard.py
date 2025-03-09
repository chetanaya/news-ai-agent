import streamlit as st
import os
import sys
import pandas as pd
import plotly.express as px
import ast
from collections import Counter

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.yaml_handler import get_app_config
from utils.database import DataManager

# Set page config
st.set_page_config(
    page_title="Brand News Analyzer - Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load app configuration
@st.cache_data(ttl=300)
def load_app_config():
    return get_app_config()

app_config = load_app_config()

# Initialize Data Manager
data_manager = DataManager()

# Title
st.title("Brand News Dashboard")
st.markdown("Visualize and explore news articles and analysis")

# Initialize session state for dashboard
if 'dashboard_view' not in st.session_state:
    st.session_state.dashboard_view = "latest"
    st.session_state.selected_timestamp = None
    st.session_state.selected_dashboard_brands = []

# Sidebar controls
st.sidebar.title("Dashboard Controls")

# View selection
view_options = ["Latest Refresh", "Historical Data"]
selected_view = st.sidebar.radio("Data View", view_options)
st.session_state.dashboard_view = "latest" if selected_view == "Latest Refresh" else "historical"

# Load data based on view
def load_dashboard_data():
    if st.session_state.dashboard_view == "historical":
        # Get available timestamps
        timestamps = data_manager.get_all_refresh_timestamps()
        if timestamps:
            selected_timestamp = st.sidebar.selectbox(
                "Select refresh timestamp:",
                timestamps,
                index=0
            )
            st.session_state.selected_timestamp = selected_timestamp
            return data_manager.get_data_by_timestamp(selected_timestamp)
        else:
            st.sidebar.warning("No historical data available")
            return pd.DataFrame()
    else:
        return data_manager.get_latest_data()

# Load the data
df = load_dashboard_data()

# Check if data is available
if df.empty:
    st.info("No data available for analysis. Please select brands and refresh data on the home page.")
    st.sidebar.warning("No data found for the selected view.")
    st.stop()

# Brand filter in sidebar
if 'brand' in df.columns:
    all_brands = sorted(df['brand'].unique())
    
    if not st.session_state.selected_dashboard_brands:
        st.session_state.selected_dashboard_brands = all_brands
    
    selected_brands = st.sidebar.multiselect(
        "Filter by Brands:",
        all_brands,
        default=st.session_state.selected_dashboard_brands
    )
    st.session_state.selected_dashboard_brands = selected_brands
    
    # Apply brand filter
    if selected_brands:
        df = df[df['brand'].isin(selected_brands)]

# Date range filter if available
if 'published_date' in df.columns:
    try:
        # Convert to datetime if string
        if df['published_date'].dtype == 'object':
            df['published_date'] = pd.to_datetime(df['published_date'], errors='coerce')
        
        # Get min and max dates
        min_date = df['published_date'].min().date()
        max_date = df['published_date'].max().date()
        
        # Date range slider
        date_range = st.sidebar.date_input(
            "Date range",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df['published_date'].dt.date >= start_date) & 
                    (df['published_date'].dt.date <= end_date)]
    except:
        pass

# Create dashboard tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview", 
    "😊 Sentiment Analysis", 
    "🔍 Topic Analysis",
    "📰 Articles"
])

# Overview Tab
with tab1:
    st.header("News Overview")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Articles", len(df))
    
    with col2:
        if 'brand' in df.columns:
            st.metric("Brands", df['brand'].nunique())
    
    with col3:
        if 'sentiment' in df.columns:
            positive_count = len(df[df['sentiment'] == 'positive'])
            st.metric("Positive Articles", positive_count, f"{positive_count / len(df):.1%}")
    
    with col4:
        if 'source' in df.columns:
            st.metric("News Sources", df['source'].nunique())
    
    # Articles by brand
    if 'brand' in df.columns:
        st.subheader("Articles by Brand")
        brand_counts = df['brand'].value_counts().reset_index()
        brand_counts.columns = ['Brand', 'Count']
        
        fig = px.bar(
            brand_counts,
            x='Brand',
            y='Count',
            title='Number of Articles by Brand',
            color='Brand',
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Articles by source
    if 'source' in df.columns:
        st.subheader("Top News Sources")
        source_counts = df['source'].value_counts().head(10).reset_index()
        source_counts.columns = ['Source', 'Count']
        
        fig = px.pie(
            source_counts,
            values='Count',
            names='Source',
            title='Top 10 News Sources',
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Publication timeline
    if 'published_date' in df.columns:
        try:
            st.subheader("Publication Timeline")
            # Convert to datetime if not already
            if df['published_date'].dtype == 'object':
                df['published_date'] = pd.to_datetime(df['published_date'], errors='coerce')
            
            # Group by date
            df['pub_date'] = df['published_date'].dt.date
            date_counts = df.groupby('pub_date').size().reset_index(name='count')
            
            fig = px.line(
                date_counts,
                x='pub_date',
                y='count',
                title='Articles Published by Date',
                labels={'pub_date': 'Publication Date', 'count': 'Number of Articles'},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.warning("Could not parse publication dates for timeline.")

# Sentiment Analysis Tab
with tab2:
    st.header("Sentiment Analysis")
    
    if 'sentiment' in df.columns:
        # Sentiment distribution
        st.subheader("Overall Sentiment Distribution")
        sentiment_counts = df['sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['Sentiment', 'Count']
        
        fig = px.pie(
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
        st.plotly_chart(fig, use_container_width=True)
        
        # Sentiment by brand
        if 'brand' in df.columns:
            st.subheader("Sentiment by Brand")
            sentiment_by_brand = df.groupby(['brand', 'sentiment']).size().reset_index(name='count')
            
            # Calculate percentages
            total_by_brand = sentiment_by_brand.groupby('brand')['count'].sum().reset_index()
            sentiment_by_brand = sentiment_by_brand.merge(total_by_brand, on='brand', suffixes=('', '_total'))
            sentiment_by_brand['percentage'] = sentiment_by_brand['count'] / sentiment_by_brand['count_total'] * 100
            
            # Plot
            fig1 = px.bar(
                sentiment_by_brand,
                x='brand',
                y='count',
                color='sentiment',
                title='Sentiment Count by Brand',
                color_discrete_map={
                    'positive': '#4CAF50',
                    'neutral': '#FFC107',
                    'negative': '#F44336'
                },
                barmode='group'
            )
            st.plotly_chart(fig1, use_container_width=True)
            
            fig2 = px.bar(
                sentiment_by_brand,
                x='brand',
                y='percentage',
                color='sentiment',
                title='Sentiment Percentage by Brand',
                color_discrete_map={
                    'positive': '#4CAF50',
                    'neutral': '#FFC107',
                    'negative': '#F44336'
                },
                barmode='stack'
            )
            fig2.update_layout(yaxis_title='Percentage (%)')
            st.plotly_chart(fig2, use_container_width=True)
        
        # Polarity distribution
        if 'polarity_score' in df.columns:
            st.subheader("Polarity Score Distribution")
            
            fig = px.histogram(
                df,
                x='polarity_score',
                nbins=20,
                title='Distribution of Polarity Scores',
                color_discrete_sequence=['#2196F3']
            )
            fig.update_layout(bargap=0.1)
            st.plotly_chart(fig, use_container_width=True)
            
            # Polarity by brand
            if 'brand' in df.columns:
                st.subheader("Polarity by Brand")
                
                fig = px.box(
                    df,
                    x='brand',
                    y='polarity_score',
                    title='Polarity Score Distribution by Brand',
                    color='brand'
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sentiment data not available in the dataset.")

# Topic Analysis Tab
with tab3:
    st.header("Topic Analysis")
    
    if 'topics' in df.columns:
        # Process topics
        all_topics = []
        for topics_list in df['topics'].dropna():
            if isinstance(topics_list, list):
                all_topics.extend(topics_list)
            elif isinstance(topics_list, str):
                # Handle string representation of list
                try:
                    topics = ast.literal_eval(topics_list)
                    if isinstance(topics, list):
                        all_topics.extend(topics)
                except:
                    pass
        
        if all_topics:
            # Count topics
            topic_counts = Counter(all_topics)
            topic_df = pd.DataFrame([
                {'Topic': topic, 'Count': count} 
                for topic, count in topic_counts.most_common(20)
            ])
            
            # Plot top topics
            st.subheader("Top 20 Topics")
            fig = px.bar(
                topic_df,
                x='Count',
                y='Topic',
                orientation='h',
                title='Most Common Topics',
                color='Count',
                color_continuous_scale='blues'
            )
            st.plotly_chart(fig, use_container_width=True)
            
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
                    
                    # Get top topics per brand (for readability)
                    top_topics_per_brand = []
                    for brand in brand_topic_df['Brand'].unique():
                        brand_data = brand_topic_counts[brand_topic_counts['Brand'] == brand]
                        top_n = min(5, len(brand_data))
                        top_brand_topics = brand_data.nlargest(top_n, 'Count')
                        top_topics_per_brand.append(top_brand_topics)
                    
                    if top_topics_per_brand:
                        top_brand_topics_df = pd.concat(top_topics_per_brand)
                        
                        # Plot heatmap
                        fig = px.density_heatmap(
                            top_brand_topics_df,
                            x='Brand',
                            y='Topic',
                            z='Count',
                            title='Top Topics by Brand',
                            color_continuous_scale='blues'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Plot treemap
                        fig = px.treemap(
                            brand_topic_counts,
                            path=['Brand', 'Topic'],
                            values='Count',
                            title='Topics Hierarchy by Brand',
                            color='Count',
                            color_continuous_scale='blues'
                        )
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No topic data found for analysis.")
    else:
        st.info("Topic data not available in the dataset.")

# Articles Tab
with tab4:
    st.header("News Articles")
    
    # Add filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        if 'sentiment' in df.columns:
            sentiment_filter = st.multiselect(
                "Filter by Sentiment:",
                df['sentiment'].unique(),
                default=df['sentiment'].unique()
            )
        else:
            sentiment_filter = []
    
    with filter_col2:
        if 'source' in df.columns:
            source_filter = st.multiselect(
                "Filter by Source:",
                df['source'].unique(),
                default=[]
            )
        else:
            source_filter = []
    
    with filter_col3:
        # Create topic filter from all topics
        all_topics = []
        if 'topics' in df.columns:
            for topics_list in df['topics'].dropna():
                if isinstance(topics_list, list):
                    all_topics.extend(topics_list)
                elif isinstance(topics_list, str):
                    try:
                        topics = ast.literal_eval(topics_list)
                        if isinstance(topics, list):
                            all_topics.extend(topics)
                    except:
                        pass
            
            unique_topics = sorted(list(set(all_topics)))
            topic_filter = st.multiselect(
                "Filter by Topic:",
                unique_topics,
                default=[]
            )
        else:
            topic_filter = []
    
    # Apply filters
    filtered_df = df.copy()
    
    if sentiment_filter and 'sentiment' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['sentiment'].isin(sentiment_filter)]
    
    if source_filter and 'source' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['source'].isin(source_filter)]
    
    if topic_filter and 'topics' in filtered_df.columns:
        # Filter for articles that contain any of the selected topics
        def has_selected_topic(topics_value):
            if isinstance(topics_value, list):
                return any(topic in topics_value for topic in topic_filter)
            elif isinstance(topics_value, str):
                try:
                    topics_list = ast.literal_eval(topics_value)
                    return any(topic in topics_list for topic in topic_filter)
                except:
                    return False
            return False
        
        if topic_filter:
            filtered_df = filtered_df[filtered_df['topics'].apply(has_selected_topic)]
    
    # Sort options
    sort_options = ["Most Recent", "Highest Polarity", "Lowest Polarity"]
    sort_by = st.selectbox("Sort by:", sort_options)
    
    if sort_by == "Most Recent" and 'published_date' in filtered_df.columns:
        try:
            filtered_df = filtered_df.sort_values(by='published_date', ascending=False)
        except:
            pass
    elif sort_by == "Highest Polarity" and 'polarity_score' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by='polarity_score', ascending=False)
    elif sort_by == "Lowest Polarity" and 'polarity_score' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by='polarity_score', ascending=True)
    
    # Display articles
    if not filtered_df.empty:
        for i, row in filtered_df.iterrows():
            with st.expander(f"{row.get('brand', 'Unknown')} - {row.get('title', 'No Title')}"):
                # Article metadata
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**Source:** [{row.get('source', 'Unknown')}]({row.get('url', '#')})")
                    st.markdown(f"**Published:** {row.get('published_date', 'Unknown')}")
                
                with col2:
                    sentiment = row.get('sentiment', 'Unknown')
                    polarity = row.get('polarity_score', 0)
                    
                    # Color-coded sentiment
                    if sentiment == 'positive':
                        st.markdown(f"**Sentiment:** 🟢 {sentiment.capitalize()} ({polarity:.2f})")
                    elif sentiment == 'negative':
                        st.markdown(f"**Sentiment:** 🔴 {sentiment.capitalize()} ({polarity:.2f})")
                    else:
                        st.markdown(f"**Sentiment:** 🟡 {sentiment.capitalize()} ({polarity:.2f})")
                
                with col3:
                    # Display topics
                    if 'topics' in row and row['topics']:
                        topics_str = ""
                        if isinstance(row['topics'], list):
                            topics_str = ", ".join(row['topics'])
                        elif isinstance(row['topics'], str):
                            try:
                                topics_list = ast.literal_eval(row['topics'])
                                if isinstance(topics_list, list):
                                    topics_str = ", ".join(topics_list)
                            except:
                                topics_str = row['topics']
                        
                        st.markdown(f"**Topics:** {topics_str}")
                
                # Summary
                if 'summary' in row and row['summary']:
                    st.markdown("### Summary")
                    st.markdown(row['summary'])
                
                # Full content
                if 'content' in row and row['content']:
                    st.markdown("**Full Content:**")
                    st.markdown(
                        f"<details><summary>Click to expand</summary>{row['content']}</details>", 
                        unsafe_allow_html=True
                    )
    else:
        st.info("No articles match the selected filters.")