from pathlib import Path
from os import environ

PROJECT_ROOT = Path(__file__).parent.resolve(strict=True)
CONFIG_ROOT = Path(PROJECT_ROOT, 'customer/config').resolve(strict=True)
UTILS_ROOT = Path(PROJECT_ROOT, 'utils').resolve(strict=True)
LOGGER_ROOT = Path(PROJECT_ROOT, 'logger').resolve(strict=True)
CUSTOMER_ROOT = Path(PROJECT_ROOT, 'customer').resolve(strict=True)

environ['HOME_DIR'] = str(PROJECT_ROOT)
