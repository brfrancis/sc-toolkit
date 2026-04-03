"""
Shared utility functions across sc-toolkit tools
"""

def sanitise_client_name(name: str) -> str:
    """Strip special characters for safe use in filenames and HTML."""
    return ''.join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
