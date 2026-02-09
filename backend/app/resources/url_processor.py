import requests
from bs4 import BeautifulSoup
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class URLProcessor:
    """Extract text content from web URLs"""
    
    def fetch_url_content(self, url: str) -> Tuple[str, str]:
        """
        Fetch and extract text from URL
        
        Returns:
            Tuple of (title, content)
        """
        try:
            # Fetch URL
            response = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=30
            )
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "Untitled"
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text(separator='\\n')
            
            # Clean up text
            lines = [line.strip() for line in text.splitlines()]
            lines = [line for line in lines if line]
            content = '\\n\\n'.join(lines)
            
            if len(content) < 100:
                raise ValueError("Extracted content too short (< 100 characters)")
            
            return title_text, content
            
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            raise ValueError(f"Failed to fetch URL content: {str(e)}")

# Singleton
url_processor = URLProcessor()