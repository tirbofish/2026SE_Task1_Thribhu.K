import os

# Token blocklist for logout functionality
BLOCKLIST = set()

# Database path - use absolute path relative to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, "databaseFiles", "mono.db")
