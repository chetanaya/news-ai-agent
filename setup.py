from setuptools import setup, find_packages

setup(
    name="brand-news-analyzer",
    version="0.1.0",
    description="AI-powered brand news analysis application",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.29.0",
        "langchain-core>=0.1.16",
        "langchain>=0.1.0",
        "langchain-openai>=0.0.5",
        "langchain-community>=0.0.13", 
        "beautifulsoup4>=4.12.2",
        "requests>=2.31.0",
        "pandas>=2.1.3",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
        "feedparser>=6.0.10",
        "textblob>=0.17.1",
        "plotly>=5.18.0",
        "altair>=5.1.2",
        "nltk>=3.8.1",
        "pytest>=7.4.3",
        "tqdm>=4.66.1",
        "openai>=1.3.5",
        "duckduckgo-search>=4.1.1"
    ],
    python_requires=">=3.8",
)