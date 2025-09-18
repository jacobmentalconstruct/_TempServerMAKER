document.addEventListener("DOMContentLoaded", () => {
    // --- DATA & DOM ---
    const META = JSON.parse(document.getElementById("meta-json").textContent);
    const FILES = JSON.parse(document.getElementById("files-json").textContent);
    const contentEl = document.querySelector(".content");
    const treeEl = document.querySelector(".tree");

    // --- HELPERS ---
    const humanBytes = (num) => {
        const units = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        while (num >= 1024 && i < units.length - 1) {
            num /= 1024;
            i++;
        }
        return `${num.toFixed(i ? 1 : 0)} ${units[i]}`;
    };

    const escapeHtml = (str) => str.replace(/[&<>]/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;'
    })[char]);

    const path_to_id = (path) => `card_${path.replace(/[^a-zA-Z0-9_-]/g, '_')}`;

    // --- LOGIC ---

    function makeTree(files) {
        const root = {};
        for (const file of files) {
            let currentNode = root;
            const parts = file.path.split('/');
            for (let i = 0; i < parts.length; i++) {
                const part = parts[i];
                currentNode.children = currentNode.children || {};
                currentNode.children[part] = currentNode.children[part] || {};
                currentNode = currentNode.children[part];
                if (i === parts.length - 1) {
                    currentNode.file = file;
                }
            }
        }
        return root;
    }

    function renderTree(node) {
        const ul = document.createElement('ul');
        const entries = Object.keys(node.children || {}).sort();
        for (const key of entries) {
            const childNode = node.children[key];
            const li = document.createElement('li');

            if (childNode.file) {
                const a = document.createElement('a');
                const cardId = path_to_id(childNode.file.path);
                a.href = `#${cardId}`;
                a.textContent = key;
                a.className = 'file';
                a.onclick = (e) => {
                    e.preventDefault();
                    const targetEl = document.getElementById(cardId);
                    if (targetEl) {
                        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        targetEl.style.outline = '1px solid var(--accent)';
                        setTimeout(() => { targetEl.style.outline = 'none'; }, 1200);
                    }
                };
                li.appendChild(a);
            } else {
                const div = document.createElement('div');
                div.textContent = key;
                div.className = 'folder';
                const nestedUl = renderTree(childNode);
                nestedUl.hidden = true;
                div.onclick = () => {
                    div.classList.toggle('open');
                    nestedUl.hidden = !nestedUl.hidden;
                };
                li.appendChild(div);
                li.appendChild(nestedUl);
            }
            ul.appendChild(li);
        }
        return ul;
    }

    function renderAllCards() {
        contentEl.innerHTML = '';
        const overviewCard = `<div class="card"><h3>Overview</h3><div class="body"><div class="meta"><div><b>Root:</b> <code>${META.root}</code></div><div><b>Generated:</b> ${new Date(META.generated_at).toLocaleString()}</div><div><b>Files:</b> ${META.file_count}</div><div><b>Total:</b> ${humanBytes(META.total_bytes)}</div></div></div></div>`;
        contentEl.insertAdjacentHTML('beforeend', overviewCard);

        FILES.forEach(file => {
            const cardId = path_to_id(file.path);
            const content = typeof file.text === 'string'
                ? `<details><summary>Contents (${humanBytes(file.text.length)})</summary><pre>${escapeHtml(file.text)}</pre></details>`
                : `<div class="small">(binary or too large to preview)</div>`;
            const fileCard = `<div class="card" id="${cardId}"><h3>${file.path}</h3><div class="body"><div class="meta"><div><b>Size:</b> ${humanBytes(file.size)}</div><div><b>MIME:</b> ${file.mime}</div></div>${content}</div></div>`;
            contentEl.insertAdjacentHTML('beforeend', fileCard);
        });
    }
    
    // --- NEW EXPORT FUNCTIONS ---

    /**
     * Creates a downloadable self-contained HTML file of the current page.
     */
    function exportHtml() {
        const cleanHtml = `<!DOCTYPE html>\n${document.documentElement.outerHTML}`;
        const blob = new Blob([cleanHtml], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'file_dump_export.html';
        document.body.appendChild(a); // Required for Firefox
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 100);
    }

    /**
     * Creates a downloadable AI-friendly text report of all file contents.
     */
    function exportAiReport() {
        const lines = [JSON.stringify(META, null, 2)];
        for (const file of FILES) {
            lines.push('\n' + '='.repeat(80));
            lines.push(`FILE: ${file.path}`);
            lines.push('-'.repeat(80));
            lines.push(typeof file.text === 'string' ? file.text : '[binary or omitted]');
        }
        const reportText = lines.join('\n');
        const blob = new Blob([reportText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ai_report.txt';
        document.body.appendChild(a); // Required for Firefox
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 100);
    }

    // --- EVENT LISTENERS ---
    document.getElementById('expand').onclick = () => document.querySelectorAll('details').forEach(d => d.open = true);
    document.getElementById('collapse').onclick = () => document.querySelectorAll('details').forEach(d => d.open = false);
    document.getElementById('export-html').onclick = exportHtml;
    document.getElementById('export-report').onclick = exportAiReport;
    document.getElementById('search').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.card').forEach(card => {
            const h3 = card.querySelector('h3');
            if (!h3 || h3.textContent === 'Overview') return;
            card.style.display = h3.textContent.toLowerCase().includes(query) ? '' : 'none';
        });
    });

    // --- INITIALIZE ---
    document.title = `Index of ${META.root}`;
    document.querySelector('.title').textContent = `Index of ${META.root}`;
    renderAllCards();
    treeEl.innerHTML = '';
    const fileTree = makeTree(FILES);
    treeEl.appendChild(renderTree(fileTree));
});
