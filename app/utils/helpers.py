from typing import Dict, Any, List, Tuple
import re

def normalize_text(text: str) -> str:
    """
    Normalize text by lowercasing and removing special characters
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters
    text = re.sub(r'[^\w\s]', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_year_from_title(title: str) -> Tuple[str, int]:
    """
    Extract year from movie title if present (e.g., "Movie Title (2020)")
    Returns tuple of (clean_title, year or None)
    """
    year_pattern = r'\((\d{4})\)$'
    match = re.search(year_pattern, title)
    
    if match:
        year = int(match.group(1))
        clean_title = title[:match.start()].strip()
        return clean_title, year
    
    return title, None

def calculate_pagination(
    total_items: int, 
    page: int = 1, 
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Calculate pagination details
    
    Args:
        total_items: Total number of items
        page: Current page (1-indexed)
        page_size: Number of items per page
    
    Returns:
        Dictionary with pagination details
    """
    # Ensure values are valid
    page = max(1, page)
    page_size = max(1, min(100, page_size))
    
    # Calculate values
    total_pages = (total_items + page_size - 1) // page_size
    has_previous = page > 1
    has_next = page < total_pages
    
    # Return dict with pagination info
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_previous": has_previous,
        "has_next": has_next,
        "previous_page": page - 1 if has_previous else None,
        "next_page": page + 1 if has_next else None
    }

def create_text_for_embedding(movie: Dict[str, Any]) -> str:
    """
    Create text representation for movie embedding generation
    
    Args:
        movie: Movie data dict with title and genres
        
    Returns:
        Text string to use for embedding generation
    """
    title = movie.get("title", "")
    
    # Extract clean title without year
    clean_title, year = extract_year_from_title(title)
    
    # Get genres as string
    genres = movie.get("genres", "")
    if isinstance(genres, list):
        genres = " ".join(genres)
    
    # Combine for embedding input
    text = f"{clean_title}. {genres}"
    
    return text 