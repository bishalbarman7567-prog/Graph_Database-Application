from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import db
import queries as q

app = FastAPI(title="Dependency Risk Explorer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe(fn, *args, **kwargs):
    """Runs a query function and turns any DB problem into a clean 503, never a raw 500."""
    try:
        return fn(*args, **kwargs)
    except db.DatabaseUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/health")
def health():
    ok, error = db.verify_connectivity()
    return {"connected": ok, "error": error}


@app.get("/api/packages/search")
def search(term: str = Query(..., min_length=1), limit: int = 10):
    return safe(q.search_packages, term, limit)


@app.get("/api/packages/{name}")
def package_overview(name: str):
    result = safe(q.get_package_overview, name)
    if not result or result[0]["package"] is None:
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")
    return result[0]


@app.get("/api/packages/{name}/transitive-dependencies")
def transitive_deps(name: str, max_hops: int = 5):
    return safe(q.transitive_dependencies, name, max_hops)


@app.get("/api/packages/{name}/subgraph")
def subgraph(name: str, max_hops: int = 2):
    nodes = safe(q.dependency_subgraph_nodes, name, max_hops)
    if not nodes or all(n["id"] is None for n in nodes):
        raise HTTPException(status_code=404, detail=f"Package '{name}' not found")
    edges = safe(q.dependency_subgraph_edges, name, max_hops)
    nodes = [n for n in nodes if n["id"] is not None]
    return {"nodes": nodes, "edges": edges}


@app.get("/api/maintainers")
def maintainers(limit: int = 50):
    return safe(q.list_maintainers, limit)


@app.get("/api/maintainers/{name}/blast-radius")
def blast_radius(name: str, max_hops: int = 5):
    rows = safe(q.blast_radius, name, max_hops)
    return rows


@app.get("/api/path")
def shortest_path(from_name: str, to_name: str):
    rows = safe(q.shortest_dependency_path, from_name, to_name)
    if not rows:
        raise HTTPException(status_code=404, detail="No dependency path found between those packages")
    return rows[0]


# --- Serve the static frontend (no build step needed) ---
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
