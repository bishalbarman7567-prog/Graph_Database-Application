const API = ""; // same-origin, backend serves the frontend

// ---------- generic fetch helper with graceful error handling ----------
async function apiGet(path) {
  let res;
  try {
    res = await fetch(API + path);
  } catch (networkErr) {
    throw new Error("Can't reach the server. Is the backend running?");
  }
  if (res.status === 503) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "The database is unreachable right now.");
  }
  if (res.status === 404) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Not found.");
  }
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}

function showError(container, message) {
  container.innerHTML = `<div class="error-msg">${escapeHtml(message)}</div>`;
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// ---------- connectivity banner ----------
async function checkHealth() {
  const banner = document.getElementById("conn-banner");
  try {
    const health = await apiGet("/api/health");
    if (!health.connected) {
      banner.hidden = false;
      banner.textContent = `⚠ Database unreachable: ${health.error}`;
    } else {
      banner.hidden = true;
    }
  } catch (e) {
    banner.hidden = false;
    banner.textContent = `⚠ ${e.message}`;
  }
}
checkHealth();
setInterval(checkHealth, 30000);

// ---------- tabs ----------
document.querySelectorAll(".tab").forEach((tabBtn) => {
  tabBtn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => {
      t.classList.remove("active");
      t.setAttribute("aria-selected", "false");
    });
    tabBtn.classList.add("active");
    tabBtn.setAttribute("aria-selected", "true");

    const target = tabBtn.dataset.tab;
    document.querySelectorAll("[data-panel]").forEach((p) => (p.hidden = true));
    document.getElementById(`panel-${target}`).hidden = false;

    if (target === "blast") loadMaintainers();
  });
});

/* =========================================================
   EXPLORE TAB
   ========================================================= */
const searchInput = document.getElementById("search-input");
const resultList = document.getElementById("search-results");
let searchDebounce;

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  const term = searchInput.value.trim();
  if (!term) {
    resultList.innerHTML = "";
    return;
  }
  searchDebounce = setTimeout(() => runSearch(term), 200);
});

async function runSearch(term) {
  try {
    const results = await apiGet(`/api/packages/search?term=${encodeURIComponent(term)}`);
    resultList.innerHTML = "";
    if (results.length === 0) {
      resultList.innerHTML = `<li class="muted">No packages match "${escapeHtml(term)}"</li>`;
      return;
    }
    results.forEach((r) => {
      const li = document.createElement("li");
      li.innerHTML = `<span>${escapeHtml(r.name)}</span><span class="eco">${escapeHtml(r.ecosystem)}</span>`;
      li.addEventListener("click", () => selectPackage(r.name));
      resultList.appendChild(li);
    });
  } catch (e) {
    resultList.innerHTML = `<li class="error-msg">${escapeHtml(e.message)}</li>`;
  }
}

let currentPackage = null;

async function selectPackage(name) {
  currentPackage = name;
  document.getElementById("explore-empty").hidden = true;
  const detail = document.getElementById("package-detail");
  const transitiveList = document.getElementById("transitive-list");
  transitiveList.hidden = true;
  transitiveList.innerHTML = "";

  try {
    const data = await apiGet(`/api/packages/${encodeURIComponent(name)}`);
    detail.hidden = false;
    document.getElementById("pkg-name").textContent = data.package.name;
    document.getElementById("pkg-ecosystem").textContent = data.package.ecosystem;
    document.getElementById("pkg-description").textContent = data.package.description || "No description.";
    document.getElementById("pkg-version").textContent = data.package.version || "—";
    document.getElementById("pkg-deps").textContent =
      data.direct_dependencies.filter(Boolean).join(", ") || "None";
    document.getElementById("pkg-dependents").textContent =
      data.direct_dependents.filter(Boolean).join(", ") || "None";
    document.getElementById("pkg-maintainers").textContent =
      data.maintainers.filter((m) => m.name).map((m) => `${m.name}${m.org ? ` (${m.org})` : ""}`).join(", ") ||
      "Unknown";
  } catch (e) {
    detail.hidden = false;
    detail.innerHTML = "";
    showError(detail, e.message);
    return;
  }

  loadGraph(name);
}

document.getElementById("show-transitive").addEventListener("click", async () => {
  if (!currentPackage) return;
  const box = document.getElementById("transitive-list");
  box.hidden = false;
  box.innerHTML = '<p class="muted small">Loading&hellip;</p>';
  try {
    const rows = await apiGet(`/api/packages/${encodeURIComponent(currentPackage)}/transitive-dependencies`);
    if (rows.length === 0) {
      box.innerHTML = '<p class="muted small">This package has no dependencies.</p>';
      return;
    }
    box.innerHTML = rows
      .map((r) => `<div class="row"><span>${escapeHtml(r.name)}</span><span class="hops">${r.hops} hop${r.hops > 1 ? "s" : ""}</span></div>`)
      .join("");
  } catch (e) {
    showError(box, e.message);
  }
});

// ---------- D3 force graph ----------
async function loadGraph(name) {
  const loading = document.getElementById("graph-loading");
  const empty = document.getElementById("graph-empty");
  const svg = document.getElementById("graph-svg");
  empty.hidden = true;
  loading.hidden = false;
  svg.replaceChildren();

  try {
    const { nodes, edges } = await apiGet(`/api/packages/${encodeURIComponent(name)}/subgraph?max_hops=2`);
    loading.hidden = true;
    drawGraph(nodes, edges, name);
  } catch (e) {
    loading.hidden = true;
    empty.hidden = false;
    empty.textContent = `Couldn't load schematic: ${e.message}`;
  }
}

function drawGraph(nodes, edges, rootName) {
  const svgEl = document.getElementById("graph-svg");
  const width = svgEl.clientWidth || 700;
  const height = svgEl.clientHeight || 500;

  const svg = d3.select("#graph-svg").attr("viewBox", [0, 0, width, height]);

  const simNodes = nodes.map((n) => ({ ...n }));
  const simLinks = edges.map((e) => ({ ...e }));

  const sim = d3
    .forceSimulation(simNodes)
    .force("link", d3.forceLink(simLinks).id((d) => d.id).distance(90).strength(0.6))
    .force("charge", d3.forceManyBody().strength(-260))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide(34));

  const link = svg
    .append("g")
    .selectAll("line")
    .data(simLinks)
    .join("line")
    .attr("class", "link");

  const node = svg
    .append("g")
    .selectAll("g")
    .data(simNodes)
    .join("g")
    .attr("class", (d) => "node" + (d.id === rootName ? " root" : ""))
    .call(drag(sim))
    .on("click", (_, d) => selectPackage(d.id));

  node.append("circle").attr("r", (d) => (d.id === rootName ? 14 : 9));
  node
    .append("text")
    .attr("dy", (d) => (d.id === rootName ? -20 : -14))
    .attr("text-anchor", "middle")
    .text((d) => d.id);

  sim.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);
    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
  });
}

function drag(sim) {
  return d3
    .drag()
    .on("start", (event, d) => {
      if (!event.active) sim.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on("end", (event, d) => {
      if (!event.active) sim.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    });
}

/* =========================================================
   BLAST RADIUS TAB
   ========================================================= */
let maintainersLoaded = false;

async function loadMaintainers() {
  if (maintainersLoaded) return;
  const select = document.getElementById("maintainer-select");
  try {
    const rows = await apiGet("/api/maintainers");
    rows.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m.name;
      opt.textContent = `${m.name} — ${m.packages_maintained} package${m.packages_maintained === 1 ? "" : "s"}`;
      select.appendChild(opt);
    });
    maintainersLoaded = true;
  } catch (e) {
    const resultBox = document.getElementById("blast-result");
    showError(resultBox, e.message);
  }
}

document.getElementById("maintainer-select").addEventListener("change", async (e) => {
  const name = e.target.value;
  const loading = document.getElementById("blast-loading");
  const empty = document.getElementById("blast-empty");
  const viz = document.getElementById("blast-viz");
  const resultBox = document.getElementById("blast-result");
  resultBox.innerHTML = "";

  if (!name) {
    empty.hidden = false;
    viz.hidden = true;
    return;
  }

  empty.hidden = true;
  viz.hidden = true;
  loading.hidden = false;

  try {
    const rows = await apiGet(`/api/maintainers/${encodeURIComponent(name)}/blast-radius`);
    loading.hidden = true;
    viz.hidden = false;

    const byOwned = new Map();
    rows.forEach((r) => {
      if (!byOwned.has(r.directly_maintained)) byOwned.set(r.directly_maintained, []);
      if (r.exposed_package) byOwned.get(r.directly_maintained).push(r);
    });

    if (byOwned.size === 0) {
      viz.innerHTML = '<p class="muted">This maintainer has no packages on record.</p>';
      return;
    }

    viz.innerHTML = "";
    byOwned.forEach((exposedRows, ownedName) => {
      const block = document.createElement("div");
      block.innerHTML = `<div class="blast-owned">🔑 ${escapeHtml(ownedName)} — directly maintained</div>`;
      if (exposedRows.length === 0) {
        block.innerHTML += `<div class="blast-none">No other packages depend on this one.</div>`;
      } else {
        exposedRows
          .sort((a, b) => a.hops - b.hops)
          .forEach((r) => {
            block.innerHTML += `<div class="blast-exposed-row"><span class="hops-tag">${r.hops} hop${r.hops > 1 ? "s" : ""}</span> ${escapeHtml(r.exposed_package)}</div>`;
          });
      }
      viz.appendChild(block);
    });
  } catch (err) {
    loading.hidden = true;
    empty.hidden = false;
    showError(resultBox, err.message);
  }
});

/* =========================================================
   PATH FINDER TAB
   ========================================================= */
document.getElementById("path-find-btn").addEventListener("click", async () => {
  const from = document.getElementById("path-from").value.trim();
  const to = document.getElementById("path-to").value.trim();
  const empty = document.getElementById("path-empty");
  const loading = document.getElementById("path-loading");
  const viz = document.getElementById("path-viz");
  const resultBox = document.getElementById("path-result");
  resultBox.innerHTML = "";

  if (!from || !to) {
    showError(resultBox, "Enter both a starting and ending package name.");
    return;
  }

  empty.hidden = true;
  viz.hidden = true;
  loading.hidden = false;

  try {
    const data = await apiGet(`/api/path?from_name=${encodeURIComponent(from)}&to_name=${encodeURIComponent(to)}`);
    loading.hidden = true;
    viz.hidden = false;
    viz.innerHTML = data.chain
      .map(
        (name, i) =>
          `<div class="path-node">${escapeHtml(name)}</div>` +
          (i < data.chain.length - 1 ? '<span class="path-arrow">&rarr;</span>' : "")
      )
      .join("");
  } catch (e) {
    loading.hidden = true;
    empty.hidden = false;
    showError(resultBox, e.message);
  }
});
