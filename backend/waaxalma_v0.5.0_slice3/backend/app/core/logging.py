import logging
from app.core.settings import get_settings

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper()),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("waaxalma")