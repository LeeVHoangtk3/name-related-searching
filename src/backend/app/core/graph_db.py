import logging
from neo4j import GraphDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Connection Pool to Memgraph DB
driver = None

try:
    # Memgraph Bolt protocol (auth is empty by default)
    driver = GraphDatabase.driver(settings.MEMGRAPH_URL, auth=("", ""))
    # Test connection
    with driver.session() as session:
        session.run("RETURN 1")
    logger.info(f"[INFO] Successfully connected to Memgraph at {settings.MEMGRAPH_URL}")
except Exception as e:
    logger.warning(f"[WARN] Could not connect to Memgraph at {settings.MEMGRAPH_URL}. GraphDB functions will run in fallback/mock mode. Error: {e}")
    driver = None

def get_db_session():
    """
    Trả về một session của Graph Database.
    Returns a GraphDatabase session if driver is available, otherwise None.
    """
    if driver is not None:
        try:
            return driver.session()
        except Exception as e:
            logger.warning(f"[WARN] Failed to open GraphDB session: {e}")
    return None
