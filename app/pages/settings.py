import streamlit as st
import os
import sys
import yaml
import pandas as pd
import io  # Added missing import for Excel export
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from utils.yaml_handler import (
    get_brands_config,
    get_sources_config,
    get_agent_config,
    get_app_config,
    save_yaml_config,
)
from utils.database import DataManager

# Set page config
st.set_page_config(
    page_title="Brand News Analyzer - Settings",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Data Manager
data_manager = DataManager()

# Title
st.title("Settings")
st.markdown("Configure application settings and manage data")

# Create tabs for different settings categories
tab1, tab2, tab3, tab4 = st.tabs(
    ["Brand Settings", "Data Management", "API Configuration", "Advanced Settings"]
)

# Brand Settings Tab
with tab1:
    st.header("Brand Settings")
    st.markdown("Add, remove, or edit brands to track")

    # Load current brands config
    brands_config = get_brands_config()
    brands = brands_config.get("brands", [])

    # Create a DataFrame for easier editing
    brands_df = pd.DataFrame(brands)

    # Display current brands
    st.subheader("Current Brands")

    for i, brand in enumerate(brands):
        with st.expander(f"Brand: {brand['name']}"):
            col1, col2 = st.columns(2)

            with col1:
                # Edit brand name
                new_name = st.text_input(f"Brand Name", brand["name"], key=f"name_{i}")

                # Edit keywords as a comma-separated string
                keywords_str = ", ".join(brand["keywords"])
                new_keywords_str = st.text_area(
                    f"Keywords (comma-separated)", keywords_str, key=f"keywords_{i}"
                )
                new_keywords = [
                    k.strip() for k in new_keywords_str.split(",") if k.strip()
                ]

            with col2:
                # Edit websites as a comma-separated string
                websites_str = ", ".join(brand["websites"])
                new_websites_str = st.text_area(
                    f"Websites (comma-separated)", websites_str, key=f"websites_{i}"
                )
                new_websites = [
                    w.strip() for w in new_websites_str.split(",") if w.strip()
                ]

                # Delete brand button
                delete_brand = st.button("Delete Brand", key=f"delete_{i}")

            # Update brand if changes were made
            if (
                new_name != brand["name"]
                or new_keywords != brand["keywords"]
                or new_websites != brand["websites"]
            ):
                brands[i]["name"] = new_name
                brands[i]["keywords"] = new_keywords
                brands[i]["websites"] = new_websites

                # Save changes
                brands_config["brands"] = brands
                save_yaml_config(brands_config, os.path.join("config", "brands.yaml"))
                st.success(f"Brand '{new_name}' updated successfully!")
                st.rerun()

            # Handle delete
            if delete_brand:
                brands.pop(i)
                brands_config["brands"] = brands
                save_yaml_config(brands_config, os.path.join("config", "brands.yaml"))
                st.success(f"Brand '{brand['name']}' deleted successfully!")
                st.rerun()

    # Add new brand
    st.subheader("Add New Brand")
    with st.form(key="add_brand_form"):
        new_brand_name = st.text_input("Brand Name")
        new_brand_keywords = st.text_area("Keywords (comma-separated)")
        new_brand_websites = st.text_area("Websites (comma-separated)")

        submit_button = st.form_submit_button(label="Add Brand")

        if submit_button:
            if not new_brand_name:
                st.error("Brand name is required.")
            else:
                # Create new brand
                new_brand = {
                    "name": new_brand_name,
                    "keywords": [
                        k.strip() for k in new_brand_keywords.split(",") if k.strip()
                    ],
                    "websites": [
                        w.strip() for w in new_brand_websites.split(",") if w.strip()
                    ],
                }

                # Add to config
                brands.append(new_brand)
                brands_config["brands"] = brands
                save_yaml_config(brands_config, os.path.join("config", "brands.yaml"))
                st.success(f"Brand '{new_brand_name}' added successfully!")
                st.rerun()

# Data Management Tab
with tab2:
    st.header("Data Management")

    # Get all available data
    timestamps = data_manager.get_all_refresh_timestamps()

    # Display data overview
    st.subheader("Available Data")

    if timestamps:
        df = pd.DataFrame(
            {
                "Timestamp": timestamps,
                "Age": [
                    (datetime.now() - datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")).days
                    for ts in timestamps
                ],
            }
        )

        st.dataframe(df)

        # Data cleanup options
        st.subheader("Data Cleanup")

        # Delete specific dataset
        delete_options = ["Select a dataset..."] + timestamps
        dataset_to_delete = st.selectbox("Select dataset to delete:", delete_options)

        if dataset_to_delete != "Select a dataset...":
            if st.button(f"Delete dataset from {dataset_to_delete}"):
                # Convert to file timestamp format
                dt = datetime.strptime(dataset_to_delete, "%Y-%m-%d %H:%M:%S")
                file_timestamp = dt.strftime("%Y%m%d_%H%M%S")
                filename = f"news_analysis_{file_timestamp}.csv"

                # Get file path
                processed_dir = os.path.join(data_manager.data_dir, "processed")
                archive_dir = os.path.join(data_manager.data_dir, "archive")

                processed_path = os.path.join(processed_dir, filename)
                archive_path = os.path.join(archive_dir, filename)

                # Delete file if it exists
                deleted = False
                if os.path.exists(processed_path):
                    os.remove(processed_path)
                    deleted = True

                if os.path.exists(archive_path):
                    os.remove(archive_path)
                    deleted = True

                if deleted:
                    st.success(
                        f"Dataset from {dataset_to_delete} deleted successfully!"
                    )
                    st.rerun()
                else:
                    st.error("Dataset file not found.")

        # Archive old data
        st.subheader("Archive Old Data")
        days_to_keep = st.slider("Keep data in active storage for days:", 1, 90, 30)

        if st.button(f"Archive data older than {days_to_keep} days"):
            data_manager.archive_old_data(days=days_to_keep)
            st.success(f"Data older than {days_to_keep} days moved to archive!")
            st.rerun()
    else:
        st.info("No data available yet.")

# API Configuration Tab
with tab3:
    st.header("API Configuration")

    # Load current API config
    agent_config = get_agent_config()
    sources_config = get_sources_config()

    # API Keys
    st.subheader("API Keys")

    # OpenAI API Key
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    openai_key_masked = "••••••" + openai_key[-4:] if openai_key else ""

    st.markdown("**OpenAI API Key**")
    openai_col1, openai_col2 = st.columns([3, 1])

    with openai_col1:
        new_openai_key = st.text_input(
            "OpenAI API Key",
            value=openai_key_masked,
            type="password" if not openai_key else "default",
        )

    with openai_col2:
        save_openai = st.button("Save OpenAI Key")

    if save_openai and new_openai_key and new_openai_key != openai_key_masked:
        # Save to .env file
        with open(".env", "a+") as f:
            f.write(f"\nOPENAI_API_KEY={new_openai_key}\n")
        st.success("OpenAI API Key saved!")

    # News API Key
    news_api_key = os.environ.get("NEWS_API_KEY", "")
    news_api_key_masked = "••••••" + news_api_key[-4:] if news_api_key else ""

    st.markdown("**News API Key**")
    news_col1, news_col2 = st.columns([3, 1])

    with news_col1:
        new_news_api_key = st.text_input(
            "News API Key",
            value=news_api_key_masked,
            type="password" if not news_api_key else "default",
        )

    with news_col2:
        save_news_api = st.button("Save News API Key")

    if save_news_api and new_news_api_key and new_news_api_key != news_api_key_masked:
        # Save to .env file
        with open(".env", "a+") as f:
            f.write(f"\nNEWS_API_KEY={new_news_api_key}\n")
        st.success("News API Key saved!")

    # News Source Settings
    st.subheader("News Source Settings")

    # Default search engine
    available_engines = [src["name"] for src in sources_config.get("news_sources", [])]
    default_engine = sources_config.get(
        "default_search_engine", available_engines[0] if available_engines else ""
    )

    new_default_engine = st.selectbox(
        "Default Search Engine",
        available_engines,
        index=available_engines.index(default_engine)
        if default_engine in available_engines
        else 0,
    )

    # News source toggle
    st.subheader("Enable/Disable News Sources")

    sources_updated = False
    for i, source in enumerate(sources_config.get("news_sources", [])):
        source_name = source.get("name", f"Source {i + 1}")
        source_enabled = source.get("enabled", True)

        new_enabled = st.checkbox(
            f"Enable {source_name}", value=source_enabled, key=f"src_enabled_{i}"
        )

        if new_enabled != source_enabled:
            sources_config["news_sources"][i]["enabled"] = new_enabled
            sources_updated = True

    # Save source settings
    if st.button("Save News Source Settings") or (
        sources_updated or new_default_engine != default_engine
    ):
        # Update default engine
        sources_config["default_search_engine"] = new_default_engine

        # Save to file
        save_yaml_config(sources_config, os.path.join("config", "sources.yaml"))
        st.success("News source settings saved successfully!")

    # Display current sources
    st.subheader("News Sources Configuration")

    for i, source in enumerate(sources_config.get("news_sources", [])):
        with st.expander(f"Source: {source['name']}"):
            source_col1, source_col2 = st.columns(2)

            with source_col1:
                # Basic settings
                new_source_name = st.text_input(
                    f"Source Name", source["name"], key=f"src_name_{i}"
                )
                new_source_type = st.selectbox(
                    f"Source Type",
                    ["rss", "api", "duckduckgo"],
                    index=0
                    if source["type"] == "rss"
                    else 1
                    if source["type"] == "api"
                    else 2,
                    key=f"src_type_{i}",
                )

            with source_col2:
                # Endpoint or parameters based on type
                if source["type"] in ["rss", "api"]:
                    # Endpoint for RSS or API
                    new_endpoint = st.text_input(
                        f"API Endpoint",
                        source.get("api_endpoint", ""),
                        key=f"src_endpoint_{i}",
                    )
                elif source["type"] == "duckduckgo":
                    # Parameters for DuckDuckGo
                    params = source.get("params", {})

                    # Time limit options
                    timelimit_options = [None, "d", "w", "m"]
                    timelimit_labels = [
                        "No limit",
                        "Past day",
                        "Past week",
                        "Past month",
                    ]
                    timelimit_index = (
                        timelimit_options.index(params.get("timelimit", "w"))
                        if params.get("timelimit", "w") in timelimit_options
                        else 2
                    )

                    new_timelimit = st.selectbox(
                        "Time Limit",
                        timelimit_labels,
                        index=timelimit_index,
                        key=f"ddg_time_{i}",
                    )

                    # Region options
                    region_options = ["us-en", "uk-en", "wt-wt"]
                    region_labels = ["United States", "United Kingdom", "Worldwide"]
                    region_index = (
                        region_options.index(params.get("region", "us-en"))
                        if params.get("region", "us-en") in region_options
                        else 0
                    )

                    new_region = st.selectbox(
                        "Region",
                        region_labels,
                        index=region_index,
                        key=f"ddg_region_{i}",
                    )

                    # SafeSearch options
                    safesearch_options = ["on", "moderate", "off"]
                    safesearch_index = (
                        safesearch_options.index(params.get("safesearch", "moderate"))
                        if params.get("safesearch", "moderate") in safesearch_options
                        else 1
                    )

                    new_safesearch = st.selectbox(
                        "SafeSearch",
                        safesearch_options,
                        index=safesearch_index,
                        key=f"ddg_safe_{i}",
                    )

                    new_max_results = st.slider(
                        "Max Results per Search",
                        5,
                        30,
                        params.get("max_results", 10),
                        key=f"ddg_max_{i}",
                    )

                # API Key field if applicable
                if source["type"] == "api":
                    if "api_key" in source:
                        new_api_key_field = st.text_input(
                            f"API Key Variable",
                            source["api_key"].replace("${", "").replace("}", ""),
                            key=f"src_apikey_{i}",
                        )
                    else:
                        new_api_key_field = st.text_input(
                            f"API Key Variable (leave empty if not needed)",
                            "",
                            key=f"src_apikey_{i}",
                        )

            # Update if changed
            source_updated = False

            if new_source_name != source["name"]:
                source["name"] = new_source_name
                source_updated = True

            if new_source_type != source["type"]:
                source["type"] = new_source_type
                source_updated = True

            # Update type-specific fields
            if source["type"] in ["rss", "api"]:
                if "api_endpoint" in source and new_endpoint != source["api_endpoint"]:
                    source["api_endpoint"] = new_endpoint
                    source_updated = True
                elif "api_endpoint" not in source and new_endpoint:
                    source["api_endpoint"] = new_endpoint
                    source_updated = True

            if source["type"] == "duckduckgo":
                params = source.get("params", {})

                if "params" not in source:
                    source["params"] = {}

                # Map timelimit label to value
                timelimit_map = {
                    "No limit": None,
                    "Past day": "d",
                    "Past week": "w",
                    "Past month": "m",
                }
                timelimit_value = timelimit_map.get(new_timelimit, "w")

                # Map region label to value
                region_map = {
                    "United States": "us-en",
                    "United Kingdom": "uk-en",
                    "Worldwide": "wt-wt",
                }
                region_value = region_map.get(new_region, "us-en")

                # Update parameters
                if timelimit_value != params.get("timelimit", "w"):
                    source["params"]["timelimit"] = timelimit_value
                    source_updated = True

                if region_value != params.get("region", "us-en"):
                    source["params"]["region"] = region_value
                    source_updated = True

                if new_safesearch != params.get("safesearch", "moderate"):
                    source["params"]["safesearch"] = new_safesearch
                    source_updated = True

                if new_max_results != params.get("max_results", 10):
                    source["params"]["max_results"] = new_max_results
                    source_updated = True

            # Handle API key field
            if source["type"] == "api":
                if new_api_key_field:
                    api_key_var = f"${{{new_api_key_field}}}"
                    if "api_key" not in source or source["api_key"] != api_key_var:
                        source["api_key"] = api_key_var
                        source_updated = True
                elif "api_key" in source and not new_api_key_field:
                    del source["api_key"]
                    source_updated = True

            if source_updated:
                save_yaml_config(sources_config, os.path.join("config", "sources.yaml"))
                st.success(f"Source '{new_source_name}' updated!")

    # Add new source button
    st.subheader("Add New Source")
    with st.form("add_source_form"):
        new_source_name = st.text_input("Source Name")
        new_source_type = st.selectbox("Source Type", ["rss", "api", "duckduckgo"])

        # Different fields based on type
        if new_source_type in ["rss", "api"]:
            new_endpoint = st.text_input("API Endpoint URL")

            if new_source_type == "api":
                new_api_key_var = st.text_input("API Key Variable (e.g., NEWS_API_KEY)")

        elif new_source_type == "duckduckgo":
            timelimit = st.selectbox(
                "Time Limit",
                ["No limit", "Past day", "Past week", "Past month"],
                index=2,  # Default to "Past week"
            )

            region = st.selectbox(
                "Region",
                ["United States", "United Kingdom", "Worldwide"],
                index=0,  # Default to United States
            )

            safesearch = st.selectbox(
                "SafeSearch",
                ["on", "moderate", "off"],
                index=1,  # Default to moderate
            )

            max_results = st.slider("Max Results per Search", 5, 30, 10)

        submitted = st.form_submit_button("Add Source")

        if submitted:
            if not new_source_name:
                st.error("Source name is required")
            else:
                # Create source config
                new_source = {
                    "name": new_source_name,
                    "type": new_source_type,
                    "enabled": True,
                }

                # Add type-specific fields
                if new_source_type in ["rss", "api"]:
                    if new_endpoint:
                        new_source["api_endpoint"] = new_endpoint
                    else:
                        st.error("API Endpoint is required for RSS or API sources")
                        st.stop()

                    if new_source_type == "api" and new_api_key_var:
                        new_source["api_key"] = f"${{{new_api_key_var}}}"

                elif new_source_type == "duckduckgo":
                    # Map selected time period to format
                    ddg_time_map = {
                        "Last 24 hours": "d",
                        "Last week": "w",
                        "Last month": "m",
                    }

                    new_source["params"] = {
                        "time_period": ddg_time_map.get(time_period, "w"),
                        "max_results": max_results,
                        "region": "us-en",
                    }

                # Add to sources config
                sources_config["news_sources"].append(new_source)

                # Save updated config
                save_yaml_config(sources_config, os.path.join("config", "sources.yaml"))
                st.success(f"Source '{new_source_name}' added successfully!")
                st.rerun()

# Advanced Settings Tab
with tab4:
    st.header("Advanced Settings")

    # Load agent config
    agent_config = get_agent_config()

    # LLM Settings
    st.subheader("LLM Settings")

    # Get available models from config
    available_models = agent_config.get("llm", {}).get(
        "available_models", ["gpt-4o-mini"]
    )

    llm_model = agent_config.get("llm", {}).get("model_name", "gpt-4")
    new_llm_model = st.selectbox(
        "OpenAI Model",
        available_models,
        index=available_models.index(llm_model) if llm_model in available_models else 0,
    )

    # Fetch Settings
    st.subheader("Fetch Settings")

    max_articles = agent_config.get("fetch_config", {}).get(
        "max_articles_per_brand", 10
    )
    new_max_articles = st.slider("Maximum articles per brand:", 1, 50, max_articles)

    refresh_interval = agent_config.get("fetch_config", {}).get(
        "news_refresh_interval", 3600
    )
    new_refresh_interval = st.number_input(
        "News refresh interval (seconds):",
        min_value=60,
        max_value=86400,
        value=refresh_interval,
        step=300,
    )

    # Analysis Settings
    st.subheader("Analysis Settings")

    summary_min = agent_config.get("analysis_config", {}).get("summary_min_words", 100)
    new_summary_min = st.number_input(
        "Minimum summary length (words):",
        min_value=50,
        max_value=500,
        value=summary_min,
        step=10,
    )

    summary_max = agent_config.get("analysis_config", {}).get("summary_max_words", 250)
    new_summary_max = st.number_input(
        "Maximum summary length (words):",
        min_value=100,
        max_value=1000,
        value=summary_max,
        step=10,
    )

    pos_threshold = agent_config.get("analysis_config", {}).get(
        "sentiment_threshold_positive", 0.1
    )
    new_pos_threshold = st.slider(
        "Positive sentiment threshold:",
        min_value=0.0,
        max_value=0.5,
        value=float(pos_threshold),
        step=0.01,
    )

    neg_threshold = agent_config.get("analysis_config", {}).get(
        "sentiment_threshold_negative", -0.1
    )
    new_neg_threshold = st.slider(
        "Negative sentiment threshold:",
        min_value=-0.5,
        max_value=0.0,
        value=float(neg_threshold),
        step=0.01,
    )

    # Save advanced settings
    if st.button("Save Advanced Settings"):
        # Update values
        agent_config["llm"]["model_name"] = new_llm_model
        agent_config["fetch_config"]["max_articles_per_brand"] = new_max_articles
        agent_config["fetch_config"]["news_refresh_interval"] = new_refresh_interval
        agent_config["analysis_config"]["summary_min_words"] = new_summary_min
        agent_config["analysis_config"]["summary_max_words"] = new_summary_max
        agent_config["analysis_config"]["sentiment_threshold_positive"] = (
            new_pos_threshold
        )
        agent_config["analysis_config"]["sentiment_threshold_negative"] = (
            new_neg_threshold
        )

        # Save to file
        save_yaml_config(agent_config, os.path.join("config", "agent_config.yaml"))
        st.success("Advanced settings saved successfully!")

# Sidebar
st.sidebar.title("Settings Navigation")
st.sidebar.info("""
Use the tabs above to configure:

- **Brand Settings**: Add or modify brands to track
- **Data Management**: Manage historical data
- **API Configuration**: Set up API keys and sources
- **Advanced Settings**: Configure LLM and analysis parameters
""")

# Advanced operations
st.sidebar.title("Advanced Operations")

# Reset configuration
if st.sidebar.button(
    "Reset to Default Configuration",
    help="Reset all configuration files to default values",
):
    if st.sidebar.checkbox("I understand this will reset all configuration"):
        # Would implement reset logic here
        st.sidebar.success("Configuration reset to defaults!")

# Export data
export_format = st.sidebar.selectbox("Export Format", ["CSV", "JSON", "Excel"])
if st.sidebar.button(f"Export Latest Data as {export_format}"):
    latest_data = data_manager.get_latest_data()
    if not latest_data.empty:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_format == "CSV":
            csv = latest_data.to_csv(index=False)
            st.sidebar.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"news_data_{timestamp}.csv",
                mime="text/csv",
            )
        elif export_format == "JSON":
            json = latest_data.to_json(orient="records")
            st.sidebar.download_button(
                label="Download JSON",
                data=json,
                file_name=f"news_data_{timestamp}.json",
                mime="application/json",
            )
        elif export_format == "Excel":
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                latest_data.to_excel(writer, sheet_name="News Data", index=False)

            output.seek(0)
            st.sidebar.download_button(
                label="Download Excel",
                data=output,
                file_name=f"news_data_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    else:
        st.sidebar.warning("No data available to export.")
