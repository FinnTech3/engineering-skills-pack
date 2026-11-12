// Render part of a Markdown file as a card screenshot (headings, paragraphs, lists, tables, code blocks).
// Usage: node md_shot.mjs file.md out.png "Window title" ["Section A,Section B"] [colourA] [colourB]
// With a section list, only the "**Request:**" line and the named "## " sections are drawn (a trim, and
// the caption next to the image should say so). Without it, the whole file is drawn.
// Resolves `playwright` from node_modules next to this file or from NODE_PATH.
import { createRequire } from 'node:module';
import fs from 'node:fs';
const { chromium } = createRequire(import.meta.url)('playwright');

const [, , mdFile, out, title = '', sections = '', colA = '#4338ca', colB = '#1e1b4b'] = process.argv;
if (!mdFile || !out) {
  console.error('usage: node md_shot.mjs file.md out.png "title" ["Section A,Section B"] [colourA] [colourB]');
  process.exit(2);
}
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`(.+?)`/g, '<code>$1</code>');

let lines = fs.readFileSync(mdFile, 'utf8').split('\n');
if (sections) {
  const wanted = new Set(sections.split(',').map((x) => x.trim()));
  const kept = [];
  let current = null;
  let fence = false;
  for (const ln of lines) {
    if (/^```/.test(ln)) fence = !fence;
    if (!fence && /^## /.test(ln)) current = ln.slice(3).trim();
    if (current === null ? /^\*\*Request:\*\*/.test(ln) : wanted.has(current)) kept.push(ln);
  }
  lines = kept;
}

const html = [];
for (let i = 0; i < lines.length;) {
  const ln = lines[i];
  if (/^```/.test(ln)) {
    const code = [];
    for (i++; i < lines.length && !/^```/.test(lines[i]); i++) code.push(lines[i]);
    i++;
    html.push('<pre>' + esc(code.join('\n')) + '</pre>');
  } else if (/^\|/.test(ln) && /^\|[-: |]+\|$/.test(lines[i + 1] || '')) {
    const cells = (r) => r.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
    let t = '<table><tr>' + cells(ln).map((c) => `<th>${inline(c)}</th>`).join('') + '</tr>';
    for (i += 2; i < lines.length && /^\|/.test(lines[i]); i++) {
      t += '<tr>' + cells(lines[i]).map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>';
    }
    html.push(t + '</table>');
  } else if (/^#{1,3} /.test(ln)) {
    const n = ln.match(/^#+/)[0].length;
    html.push(`<h${n}>${inline(ln.replace(/^#+ /, ''))}</h${n}>`);
    i++;
  } else if (/^- /.test(ln)) {
    let ul = '<ul>';
    for (; i < lines.length && /^- /.test(lines[i]); i++) {
      const item = lines[i].slice(2);
      ul += /^\[[ x]\] /.test(item) ? `<li class="cb">&#9744; ${inline(item.slice(4))}</li>` : `<li>${inline(item)}</li>`;
    }
    html.push(ul + '</ul>');
  } else {
    if (ln.trim()) html.push(`<p>${inline(ln)}</p>`);
    i++;
  }
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1188, height: 200 }, deviceScaleFactor: 2 });
await page.setContent(`<style>
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(135deg,${colA},${colB});padding:44px;font-family:Inter,system-ui,sans-serif;color:#1f2937}
.card{width:1100px;margin:0;background:#fff;border-radius:18px;padding:30px 42px 34px;box-shadow:0 24px 60px rgba(0,0,0,.35)}
.bar{font-size:15px;color:#6b7280;margin-bottom:14px}
h2{font-size:22px;margin:22px 0 8px}h3{font-size:18px;margin:16px 0 6px}
p,li{font-size:17px;line-height:1.55;margin:6px 0}ul{margin:6px 0;padding-left:26px}li.cb{list-style:none;margin-left:-22px}
table{border-collapse:collapse;margin:10px 0;font-size:16px}th,td{border:1px solid #e5e7eb;padding:7px 14px;text-align:left}
th{background:#f3f4f6}
pre{background:#0d1117;color:#e6edf3;border-radius:10px;padding:14px 18px;font:14.5px/1.5 'DejaVu Sans Mono',monospace;
white-space:pre-wrap;margin:10px 0}
code{background:#f3f4f6;border-radius:4px;padding:1px 5px;font:14.5px/1.1 'DejaVu Sans Mono',monospace}
</style><div class="card"><div class="bar">${esc(title)}</div>${html.join('')}</div>`);
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log('wrote', out);
