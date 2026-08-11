"""
Thin wrapper around the official Neo4j Python driver, pointed at a CognoDB
Cloud instance. CognoDB speaks openCypher over Bolt, so the standard driver
works unmodified — only the connection details change.
"""
import os
import logging
from contextlib import contextmanager

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError

load_dotenv()

logger = logging.getLogger("db")

URI = os.environ.get("COGNODB_URI")
USER = os.environ.get("COGNODB_USER", "cognodb")
PASSWORD = os.environ.get("COGNODB_PASSWORD")

_driver = None


class DatabaseUnavailableError(RuntimeError):
    """Raised when CognoDB cannot be reached or credentials are invalid."""


def get_driver():
    """Lazily create a single shared driver instance for the app's lifetime."""
    global _driver
    if _driver is None:
        if not URI or not PASSWORD:
            raise DatabaseUnavailableError(
                "COGNODB_URI / COGNODB_PASSWORD are not set. Copy .env.example "
                "to .env and fill in your CognoDB Cloud connection details."
            )
        _driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    return _driver


def verify_connectivity():
    """Used at startup and by /api/health — never lets a bad connection crash the app."""
    try:
        get_driver().verify_connectivity()
        return True, None
    except DatabaseUnavailableError as e:
        return False, str(e)
    except AuthError:
        return False, "Authentication with CognoDB failed — check COGNODB_PASSWORD."
    except ServiceUnavailable:
        return False, "CognoDB instance is unreachable — check the URI and that the instance is running."
    except Exception as e:  # noqa: BLE001 — surface anything unexpected as a clean message
        return False, f"Unexpected database error: {e}"


@contextmanager
def get_session():
    """
    Context manager yielding a driver session. Any failure is normalized into
    DatabaseUnavailableError so API routes can return a clean 503 instead of
    a raw stack trace.
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            yield session
    except DatabaseUnavailableError:
        raise
    except AuthError as e:
        raise DatabaseUnavailableError("Authentication with CognoDB failed.") from e
    except ServiceUnavailable as e:
        raise DatabaseUnavailableError("CognoDB is unreachable right now.") from e
    except Neo4jError as e:
        logger.exception("Neo4j query error")
        raise DatabaseUnavailableError(f"Database query failed: {e.message}") from e


def run_query(cypher: str, params: dict | None = None) -> list[dict]:
    """Run a parameterised Cypher query and return a list of plain dicts."""
    with get_session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]
