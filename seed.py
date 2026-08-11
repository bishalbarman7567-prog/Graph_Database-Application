"""
Loads realistic (hand-modeled, not scraped) seed data representing a slice
of the JS/Python open-source ecosystem: packages, their dependency edges,
the maintainers who publish them, and the organizations those maintainers
are affiliated with.

Safe to re-run: every write uses MERGE, so re-running this script updates
rather than duplicates data.

Usage:
    python seed.py
"""
from db import get_session

PACKAGES = [
    {"name": "left-pad-plus", "ecosystem": "npm", "version": "3.2.0", "description": "String padding utility"},
    {"name": "http-fetcher", "ecosystem": "npm", "version": "1.8.4", "description": "Thin fetch wrapper with retries"},
    {"name": "json-schema-lite", "ecosystem": "npm", "version": "2.1.0", "description": "Lightweight JSON schema validator"},
    {"name": "date-utils", "ecosystem": "npm", "version": "4.0.1", "description": "Date parsing and formatting"},
    {"name": "web-router", "ecosystem": "npm", "version": "6.3.2", "description": "Client-side routing"},
    {"name": "state-store", "ecosystem": "npm", "version": "5.0.0", "description": "Predictable state container"},
    {"name": "ui-components", "ecosystem": "npm", "version": "9.4.1", "description": "Shared component library"},
    {"name": "admin-dashboard", "ecosystem": "npm", "version": "1.2.0", "description": "Internal admin dashboard app"},
    {"name": "customer-portal", "ecosystem": "npm", "version": "2.5.3", "description": "Customer-facing web portal"},
    {"name": "build-tool-cli", "ecosystem": "npm", "version": "7.1.0", "description": "Project build/bundling CLI"},
    {"name": "logger-core", "ecosystem": "npm", "version": "3.3.3", "description": "Structured logging"},
    {"name": "crypto-helpers", "ecosystem": "npm", "version": "1.0.9", "description": "Common crypto/hashing helpers"},
    {"name": "auth-middleware", "ecosystem": "npm", "version": "4.2.0", "description": "Session/auth middleware"},
    {"name": "config-loader", "ecosystem": "npm", "version": "2.0.4", "description": "Env/config file loader"},
    {"name": "test-runner-fast", "ecosystem": "npm", "version": "8.0.0", "description": "Fast unit test runner"},
    {"name": "reqsafe", "ecosystem": "pypi", "version": "2.31.0", "description": "HTTP client wrapper"},
    {"name": "dataframe-lite", "ecosystem": "pypi", "version": "1.5.2", "description": "Small tabular data library"},
    {"name": "ml-preprocess", "ecosystem": "pypi", "version": "0.9.1", "description": "ML feature preprocessing"},
    {"name": "yamlparse", "ecosystem": "pypi", "version": "6.0.1", "description": "YAML parsing"},
    {"name": "task-queue", "ecosystem": "pypi", "version": "3.1.0", "description": "Background task queue"},
    {"name": "api-service", "ecosystem": "pypi", "version": "1.0.0", "description": "Internal API service"},
    {"name": "etl-pipeline", "ecosystem": "pypi", "version": "2.2.0", "description": "Internal ETL pipeline"},
]

# (from, to, version_range) — "from DEPENDS_ON to"
DEPENDENCIES = [
    ("http-fetcher", "left-pad-plus", "^3.0.0"),
    ("json-schema-lite", "left-pad-plus", "^3.0.0"),
    ("web-router", "http-fetcher", "^1.5.0"),
    ("state-store", "logger-core", "^3.0.0"),
    ("ui-components", "web-router", "^6.0.0"),
    ("ui-components", "state-store", "^5.0.0"),
    ("ui-components", "date-utils", "^4.0.0"),
    ("admin-dashboard", "ui-components", "^9.0.0"),
    ("admin-dashboard", "auth-middleware", "^4.0.0"),
    ("admin-dashboard", "build-tool-cli", "^7.0.0"),
    ("customer-portal", "ui-components", "^9.0.0"),
    ("customer-portal", "auth-middleware", "^4.0.0"),
    ("customer-portal", "json-schema-lite", "^2.0.0"),
    ("auth-middleware", "crypto-helpers", "^1.0.0"),
    ("auth-middleware", "config-loader", "^2.0.0"),
    ("auth-middleware", "logger-core", "^3.0.0"),
    ("build-tool-cli", "config-loader", "^2.0.0"),
    ("build-tool-cli", "test-runner-fast", "^8.0.0"),
    ("crypto-helpers", "logger-core", "^3.0.0"),
    ("config-loader", "yamlparse", "^6.0.0"),
    ("etl-pipeline", "dataframe-lite", "^1.5.0"),
    ("etl-pipeline", "task-queue", "^3.0.0"),
    ("etl-pipeline", "yamlparse", "^6.0.0"),
    ("ml-preprocess", "dataframe-lite", "^1.5.0"),
    ("api-service", "reqsafe", "^2.31.0"),
    ("api-service", "task-queue", "^3.0.0"),
    ("api-service", "ml-preprocess", "^0.9.0"),
    ("task-queue", "reqsafe", "^2.31.0"),
]

MAINTAINERS = [
    {"name": "Priya Nandan", "email": "priya@oss-collective.dev"},
    {"name": "Marcus Webb", "email": "marcus@indiehub.dev"},
    {"name": "Sofia Reyes", "email": "sofia@corelabs.io"},
    {"name": "Tom Achebe", "email": "tom@indiehub.dev"},
    {"name": "Lena Fischer", "email": "lena@corelabs.io"},
    {"name": "Dev Patel", "email": "dev@oss-collective.dev"},
]

ORGANIZATIONS = [{"name": "OSS Collective"}, {"name": "IndieHub"}, {"name": "CoreLabs"}]

# (maintainer, org)
AFFILIATIONS = [
    ("Priya Nandan", "OSS Collective"),
    ("Dev Patel", "OSS Collective"),
    ("Marcus Webb", "IndieHub"),
    ("Tom Achebe", "IndieHub"),
    ("Sofia Reyes", "CoreLabs"),
    ("Lena Fischer", "CoreLabs"),
]

# (maintainer, package) — deliberately concentrates risk: Marcus alone maintains
# two widely-depended-on low-level packages, which is what makes the
# "blast radius" query interesting to demo.
MAINTAINS = [
    ("Marcus Webb", "logger-core"),
    ("Marcus Webb", "left-pad-plus"),
    ("Priya Nandan", "http-fetcher"),
    ("Priya Nandan", "json-schema-lite"),
    ("Sofia Reyes", "ui-components"),
    ("Sofia Reyes", "web-router"),
    ("Sofia Reyes", "state-store"),
    ("Tom Achebe", "auth-middleware"),
    ("Tom Achebe", "crypto-helpers"),
    ("Lena Fischer", "config-loader"),
    ("Lena Fischer", "yamlparse"),
    ("Dev Patel", "build-tool-cli"),
    ("Dev Patel", "test-runner-fast"),
    ("Dev Patel", "reqsafe"),
    ("Dev Patel", "task-queue"),
    ("Dev Patel", "dataframe-lite"),
    ("Dev Patel", "ml-preprocess"),
    ("Dev Patel", "date-utils"),
]


def seed():
    with get_session() as session:
        session.run(
            "UNWIND $rows AS row "
            "MERGE (p:Package {name: row.name}) "
            "SET p.ecosystem = row.ecosystem, p.version = row.version, p.description = row.description",
            rows=PACKAGES,
        )
        session.run(
            "UNWIND $rows AS row "
            "MATCH (a:Package {name: row[0]}), (b:Package {name: row[1]}) "
            "MERGE (a)-[r:DEPENDS_ON]->(b) "
            "SET r.version_range = row[2]",
            rows=DEPENDENCIES,
        )
        session.run(
            "UNWIND $rows AS row MERGE (m:Maintainer {name: row.name}) SET m.email = row.email",
            rows=MAINTAINERS,
        )
        session.run(
            "UNWIND $rows AS row MERGE (:Organization {name: row.name})",
            rows=ORGANIZATIONS,
        )
        session.run(
            "UNWIND $rows AS row "
            "MATCH (m:Maintainer {name: row[0]}), (o:Organization {name: row[1]}) "
            "MERGE (m)-[:AFFILIATED_WITH]->(o)",
            rows=AFFILIATIONS,
        )
        session.run(
            "UNWIND $rows AS row "
            "MATCH (m:Maintainer {name: row[0]}), (p:Package {name: row[1]}) "
            "MERGE (m)-[:MAINTAINS]->(p)",
            rows=MAINTAINS,
        )
    print(
        f"Seeded {len(PACKAGES)} packages, {len(DEPENDENCIES)} DEPENDS_ON edges, "
        f"{len(MAINTAINERS)} maintainers, {len(ORGANIZATIONS)} organizations, "
        f"{len(MAINTAINS)} MAINTAINS edges."
    )


if __name__ == "__main__":
    seed()
