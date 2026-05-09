"use strict";

const sidebarContent = document.getElementById("sidebar-content");
const backWrap = document.getElementById("back-button-wrap");
const breadcrumbs = document.getElementById("breadcrumbs");
const pageContent = document.getElementById("page-content");
const filesSection = document.getElementById("files-section");
const filesList = document.getElementById("files-list");

const state = {
    course: null,
    selectedPath: null,
};

// ---------- API ----------

async function api(url) {
    const res = await fetch(url);
    if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`${res.status} ${res.statusText}: ${text}`);
    }
    return res.json();
}

// ---------- Sidebar: courses list ----------

async function loadCourses() {
    backWrap.innerHTML = "";
    sidebarContent.innerHTML = `<div class="loading">Načítám kurzy…</div>`;
    try {
        const courses = await api("/api/courses");
        if (!courses.length) {
            sidebarContent.innerHTML = `<div class="placeholder">V adresáři kurzů nejsou žádné podsložky.</div>`;
            return;
        }
        const ul = document.createElement("ul");
        ul.className = "courses-list";
        for (const c of courses) {
            const li = document.createElement("li");
            const btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = c.name;
            btn.addEventListener("click", () => openCourse(c.name));
            li.appendChild(btn);
            ul.appendChild(li);
        }
        sidebarContent.replaceChildren(ul);
    } catch (err) {
        showSidebarError(err);
    }
}

// ---------- Sidebar: course tree ----------

async function openCourse(name) {
    state.course = name;
    state.selectedPath = null;
    sidebarContent.innerHTML = `<div class="loading">Načítám strom…</div>`;
    backWrap.innerHTML = "";
    const back = document.createElement("button");
    back.type = "button";
    back.className = "back-btn";
    back.textContent = "← Zpět na kurzy";
    back.addEventListener("click", () => {
        state.course = null;
        loadCourses();
        breadcrumbs.replaceChildren();
        clearMain();
    });
    backWrap.appendChild(back);

    try {
        const tree = await api(`/api/tree?course=${encodeURIComponent(name)}`);
        renderTree(tree);
        // Implicitně otevřít kořen kurzu (zobrazit jeho index.html, pokud je).
        loadContent("");
    } catch (err) {
        showSidebarError(err);
    }
}

function renderTree(rootNode) {
    const wrapper = document.createElement("div");
    wrapper.className = "tree";
    wrapper.appendChild(renderNode(rootNode, true));
    sidebarContent.replaceChildren(wrapper);
}

function renderNode(node, isRoot) {
    const li = document.createElement("li");

    const row = document.createElement("button");
    row.type = "button";
    row.className = "tree-node";
    row.dataset.path = node.path;

    const toggle = document.createElement("span");
    toggle.className = "toggle";
    const hasChildren = node.children && node.children.length > 0;
    toggle.textContent = hasChildren ? "▶" : "";
    if (!hasChildren) toggle.classList.add("empty");

    const name = document.createElement("span");
    name.className = "tree-name";
    name.textContent = node.name;

    row.appendChild(toggle);
    row.appendChild(name);
    if (node.has_index) {
        const dot = document.createElement("span");
        dot.className = "has-index-dot";
        dot.title = "Stránka má textový obsah";
        row.appendChild(dot);
    }
    li.appendChild(row);

    let childrenUl = null;
    if (hasChildren) {
        childrenUl = document.createElement("ul");
        childrenUl.className = "tree-children";
        childrenUl.hidden = !isRoot; // root rozbalený, ostatní zavřené
        for (const child of node.children) {
            childrenUl.appendChild(renderNode(child, false));
        }
        li.appendChild(childrenUl);
        if (isRoot) toggle.textContent = "▼";
    }

    row.addEventListener("click", (e) => {
        e.stopPropagation();
        // toggle expand pokud má potomky
        if (hasChildren && childrenUl) {
            childrenUl.hidden = !childrenUl.hidden;
            toggle.textContent = childrenUl.hidden ? "▶" : "▼";
        }
        // vybrat uzel a načíst obsah
        document.querySelectorAll(".tree-node.active").forEach(el => el.classList.remove("active"));
        row.classList.add("active");
        loadContent(node.path);
    });

    return li;
}

// ---------- Main: content ----------

async function loadContent(relPath) {
    if (!state.course) return;
    state.selectedPath = relPath;
    renderBreadcrumbs(relPath);
    pageContent.innerHTML = `<div class="loading">Načítám obsah…</div>`;
    filesSection.hidden = true;
    filesList.replaceChildren();

    try {
        const data = await api(
            `/api/content?course=${encodeURIComponent(state.course)}&path=${encodeURIComponent(relPath)}`
        );
        if (data.html != null) {
            pageContent.innerHTML = data.html;
        } else if ((data.files || []).length === 0) {
            pageContent.innerHTML = `<div class="empty-page">Tato stránka je prázdná.</div>`;
        } else {
            pageContent.innerHTML = "";
        }
        if (data.files && data.files.length) {
            filesSection.hidden = false;
            for (const f of data.files) {
                const li = document.createElement("li");
                const a = document.createElement("a");
                a.href = f.url;
                a.target = "_blank";
                a.rel = "noopener";
                a.textContent = f.name;
                li.appendChild(a);
                if (typeof f.size === "number") {
                    const size = document.createElement("span");
                    size.className = "size";
                    size.textContent = formatSize(f.size);
                    li.appendChild(size);
                }
                filesList.appendChild(li);
            }
        }
    } catch (err) {
        pageContent.innerHTML = `<div class="error">Chyba načítání: ${escapeHtml(err.message)}</div>`;
    }
}

function renderBreadcrumbs(relPath) {
    breadcrumbs.replaceChildren();
    const parts = [state.course, ...(relPath ? relPath.split("/") : [])];
    parts.forEach((p, i) => {
        if (i > 0) {
            const sep = document.createElement("span");
            sep.className = "sep";
            sep.textContent = "/";
            breadcrumbs.appendChild(sep);
        }
        const span = document.createElement("span");
        span.className = "crumb";
        span.textContent = p;
        breadcrumbs.appendChild(span);
    });
}

function clearMain() {
    pageContent.innerHTML = `<div class="placeholder">Vyber kurz vlevo a v něm stránku ke zobrazení.</div>`;
    filesSection.hidden = true;
    filesList.replaceChildren();
    breadcrumbs.replaceChildren();
}

// ---------- Helpers ----------

function showSidebarError(err) {
    sidebarContent.innerHTML = "";
    const div = document.createElement("div");
    div.className = "error";
    div.textContent = err.message || String(err);
    sidebarContent.appendChild(div);
}

function escapeHtml(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

// ---------- boot ----------

loadCourses();
