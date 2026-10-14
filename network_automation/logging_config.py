"""Logging setup for the automation run."""

import logging
from datetime import datetime


LOG_FILENAME = f'network_automation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    filename=LOG_FILENAME, level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console)