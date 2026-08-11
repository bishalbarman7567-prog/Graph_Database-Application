"""
Every query the application runs, in one place, so they're easy to review.
All queries are parameterised (no string concatenation) and are run through
db.run_query(), which uses the official Neo4j driver's parameter binding.
"""
from db import run_query


def search_packages(term: str, limit: int = 10) -> list[dict]:
    """Autocomplete-style search by package name (case-insensitive, prefix or substring)."""
    cypher = """
    MATCH (p:Package)
    WHERE toLower(p.name) CONTAINS toLower($term)
    RETURN p.name AS name, p.ecosystem AS ecosystem, p.version AS version
    ORDER BY p.name
    LIMIT $limit
    """
    return run_query(cypher, {"term": term, "limit": limit})


def get_package_overview(name: str) -> list[dict]:
    """
    One-hop view of a package: its own properties, direct dependencies
    (what it needs), direct dependents (what needs it), and its maintainers.
    """
    cypher = """
    MATCH (p:Package {name: $name})
    OPTIONAL MATCH (p)-[dep:DEPENDS_ON]->(direct_dep:Package)
    OPTIONAL MATCH (dependent:Package)-[:DEPENDS_ON]->(p)
    OPTIONAL MATCH (m:Maintainer)-[:MAINTAINS]->(p)
    OPTIONAL MATCH (m)-[:AFFILIATED_WITH]->(org:Organization)
    RETURN p { .name, .ecosystem, .version, .description } AS package,
           collect(DISTINCT direct_dep.name) AS direct_dependencies,
           collect(DISTINCT dependent.name) AS direct_dependents,
           collect(DISTINCT {name: m.name, org: org.name}) AS maintainers
    """
    return run_query(cypher, {"name": name})


def transitive_dependencies(name: str, max_hops: int = 5) -> list[dict]:
    """
    Multi-hop traversal (2+ hops): everything a package pulls in transitively,
    with the shortest hop-count to each. This is the query a relational schema
    would need a recursive CTE (and a fixed max depth) to approximate.
    """
    cypher = """
    MATCH (root:Package {name: $name})
    MATCH path = (root)-[:DEPENDS_ON*1..%d]->(dep:Package)
    WITH dep, min(length(path)) AS hops
    RETURN dep.name AS name, dep.ecosystem AS ecosystem, hops
    ORDER BY hops, name
    """ % max_hops
    return run_query(cypher, {"name": name})


def blast_radius(maintainer_name: str, max_hops: int = 5) -> list[dict]:
    """
    'If this maintainer's account were compromised, what's exposed?'

    Finds every package the maintainer directly maintains, then follows
    DEPENDS_ON edges *backwards* (variable-length) to every package that
    transitively depends on those — i.e. every package whose build could be
    poisoned via a supply-chain attack on this one maintainer.

    This is the kind of query a relational database handles awkwardly:
    it's an open-ended variable-length reverse traversal across a
    self-referential many-to-many table, which needs a recursive CTE with a
    hand-picked depth cap and quickly becomes hard to reason about and slow
    to run as the depth grows. In Cypher it's a single pattern.
    """
    cypher = """
    MATCH (m:Maintainer {name: $maintainer_name})-[:MAINTAINS]->(owned:Package)
    OPTIONAL MATCH path = (exposed:Package)-[:DEPENDS_ON*1..%d]->(owned)
    WITH owned, exposed, path
    WHERE exposed IS NOT NULL
    RETURN owned.name AS directly_maintained,
           exposed.name AS exposed_package,
           length(path) AS hops
    ORDER BY directly_maintained, hops, exposed_package
    """ % max_hops
    return run_query(cypher, {"maintainer_name": maintainer_name})


def shortest_dependency_path(from_name: str, to_name: str) -> list[dict]:
    """Shortest DEPENDS_ON chain connecting two packages, in either direction."""
    cypher = """
    MATCH (a:Package {name: $from_name}), (b:Package {name: $to_name})
    MATCH path = shortestPath((a)-[:DEPENDS_ON*..8]-(b))
    RETURN [n IN nodes(path) | n.name] AS chain, length(path) AS hops
    """
    return run_query(cypher, {"from_name": from_name, "to_name": to_name})


def list_maintainers(limit: int = 50) -> list[dict]:
    cypher = """
    MATCH (m:Maintainer)
    OPTIONAL MATCH (m)-[:MAINTAINS]->(p:Package)
    OPTIONAL MATCH (m)-[:AFFILIATED_WITH]->(org:Organization)
    RETURN m.name AS name, org.name AS organization, count(DISTINCT p) AS packages_maintained
    ORDER BY packages_maintained DESC
    LIMIT $limit
    """
    return run_query(cypher, {"limit": limit})


def dependency_subgraph_nodes(name: str, max_hops: int = 2) -> list[dict]:
    """All nodes within max_hops of the package in either direction, for the D3 view."""
    cypher = """
    MATCH (root:Package {name: $name})
    OPTIONAL MATCH (root)-[:DEPENDS_ON*0..%d]->(down:Package)
    OPTIONAL MATCH (up:Package)-[:DEPENDS_ON*0..%d]->(root)
    WITH collect(DISTINCT down) + collect(DISTINCT up) AS nodeList
    UNWIND nodeList AS n
    WITH DISTINCT n
    RETURN n.name AS id, n.ecosystem AS ecosystem
    """ % (max_hops, max_hops)
    return run_query(cypher, {"name": name})


def dependency_subgraph_edges(name: str, max_hops: int = 2) -> list[dict]:
    """All DEPENDS_ON edges among nodes within max_hops of the package, for the D3 view."""
    cypher = """
    MATCH (root:Package {name: $name})
    OPTIONAL MATCH (root)-[:DEPENDS_ON*0..%d]->(down:Package)
    OPTIONAL MATCH (up:Package)-[:DEPENDS_ON*0..%d]->(root)
    WITH collect(DISTINCT down) + collect(DISTINCT up) + [root] AS nodeList
    UNWIND nodeList AS a
    MATCH (a)-[:DEPENDS_ON]->(b)
    WHERE b IN nodeList
    RETURN DISTINCT a.name AS source, b.name AS target
    """ % (max_hops, max_hops)
    return run_query(cypher, {"name": name})
