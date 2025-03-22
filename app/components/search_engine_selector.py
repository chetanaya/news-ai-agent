import streamlit as st
import os
import sys

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from utils.yaml_handler import get_sources_config, save_yaml_config

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
            st.rerun()
    
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