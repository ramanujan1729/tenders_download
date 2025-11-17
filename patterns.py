"""Filter patterns for document matching."""
import re

# Pattern for matching Polish word 'kosztorys' and its variations
KOSZTORYS_PATTERN = re.compile(r"kosztorys[a-ząćęłńóśźż]*", re.IGNORECASE)


def get_pattern(pattern_name: str) -> re.Pattern:
    """
    Get a pattern by name.
    
    Args:
        pattern_name: Name of the pattern to retrieve
        
    Returns:
        Compiled regex pattern
        
    Raises:
        ValueError: If pattern name is not found
    """
    patterns = {
        "kosztorys": KOSZTORYS_PATTERN,
    }
    
    if pattern_name not in patterns:
        raise ValueError(f"Pattern '{pattern_name}' not found. Available patterns: {list(patterns.keys())}")
    
    return patterns[pattern_name]

