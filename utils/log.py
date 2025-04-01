import logging
from logging.handlers import RotatingFileHandler

# Create custom logger for your bot
logger = logging.getLogger('Areas')
logger.setLevel(logging.INFO)

# Configure formatter with cleaner output
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set up console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Set up file output with rotation
file_handler = RotatingFileHandler(
    "bot_logs.txt", 
    maxBytes=5_000_000,  # 5MB per file
    backupCount=1,       # Keep 1 backup files
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Filter out low-level library logs
logging.getLogger('telegram').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('keepalive').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)



# Usage example:
# logger.info("Bot started")
# logger.warning("Potential issue detected")
# logger.error("Error occurred: {error_message}")