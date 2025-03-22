import os
import pandas as pd
import datetime
from typing import List, Dict, Any, Optional
import shutil


class DataManager:
    """Manager for storing and retrieving brand news analysis data"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the DataManager
        
        Args:
            data_dir: Directory where data files are stored
        """
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self.raw_dir = os.path.join(self.data_dir, "raw")
        self.processed_dir = os.path.join(self.data_dir, "processed")
        self.archive_dir = os.path.join(self.data_dir, "archive")
        
        # Ensure directories exist
        for directory in [self.raw_dir, self.processed_dir, self.archive_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def save_raw_data(self, brand: str, data: List[Dict[str, Any]]) -> str:
        """
        Save raw data for a brand
        
        Args:
            brand: Brand name
            data: List of data objects
            
        Returns:
            Path to the saved file
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{brand.lower()}_{timestamp}_raw.csv"
        filepath = os.path.join(self.raw_dir, filename)
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        
        return filepath
    
    def save_processed_data(self, data: List[Dict[str, Any]]) -> str:
        """
        Save processed data from all brands
        
        Args:
            data: List of processed data objects
            
        Returns:
            Path to the saved file
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_analysis_{timestamp}.csv"
        filepath = os.path.join(self.processed_dir, filename)
        
        df = pd.DataFrame(data)
        
        # Make sure refresh_timestamp is included
        if 'refresh_timestamp' not in df.columns:
            df['refresh_timestamp'] = datetime.datetime.now().isoformat()
            
        df.to_csv(filepath, index=False)
        
        return filepath
    
    def get_latest_data(self) -> pd.DataFrame:
        """
        Get the most recent processed data
        
        Returns:
            DataFrame with the latest processed data
        """
        files = os.listdir(self.processed_dir)
        if not files:
            return pd.DataFrame()
        
        # Sort files by timestamp (newest first)
        files.sort(reverse=True)
        latest_file = os.path.join(self.processed_dir, files[0])
        
        return pd.read_csv(latest_file)
    
    def get_all_refresh_timestamps(self) -> List[str]:
        """
        Get all available refresh timestamps
        
        Returns:
            List of timestamps as strings
        """
        files = os.listdir(self.processed_dir)
        timestamps = []
        
        for file in files:
            if file.startswith("news_analysis_") and file.endswith(".csv"):
                # Extract timestamp from filename
                timestamp = file.replace("news_analysis_", "").replace(".csv", "")
                # Convert to human-readable format
                try:
                    dt = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                    timestamps.append(dt.strftime("%Y-%m-%d %H:%M:%S"))
                except ValueError:
                    continue
                
        return sorted(timestamps, reverse=True)
    
    def get_data_by_timestamp(self, timestamp: str) -> pd.DataFrame:
        """
        Get data for a specific timestamp
        
        Args:
            timestamp: Timestamp string in format "YYYY-MM-DD HH:MM:SS"
            
        Returns:
            DataFrame with the data for the given timestamp
        """
        try:
            dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            file_timestamp = dt.strftime("%Y%m%d_%H%M%S")
            
            filename = f"news_analysis_{file_timestamp}.csv"
            filepath = os.path.join(self.processed_dir, filename)
            
            if os.path.exists(filepath):
                return pd.read_csv(filepath)
            
            # Check in archive
            archive_path = os.path.join(self.archive_dir, filename)
            if os.path.exists(archive_path):
                return pd.read_csv(archive_path)
                
            return pd.DataFrame()
            
        except ValueError:
            return pd.DataFrame()
    
    def archive_old_data(self, days: int = 30) -> None:
        """
        Move data older than the specified number of days to archive
        
        Args:
            days: Number of days to keep in the processed directory
        """
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        files = os.listdir(self.processed_dir)
        
        for file in files:
            if not file.startswith("news_analysis_") or not file.endswith(".csv"):
                continue
                
            # Extract timestamp
            try:
                timestamp = file.replace("news_analysis_", "").replace(".csv", "")
                file_date = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                
                if file_date < cutoff:
                    # Move to archive
                    src = os.path.join(self.processed_dir, file)
                    dst = os.path.join(self.archive_dir, file)
                    shutil.move(src, dst)
            except ValueError:
                continue