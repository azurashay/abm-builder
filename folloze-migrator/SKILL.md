---
name: folloze-migrator
description: "Migrate an existing web page or microsite into Folloze as a faithful 1:1 recreation, then deploy it via the Folloze MCP. Use when the user gives a source URL and wants it rebuilt, recreated, replicated, or migrated into Folloze — including pages from TIME Sites, Vev, Sites.design, Webflow, Wix, or any external site builder. Triggers on: 'migrate this page to Folloze', 'recreate this microsite', 'rebuild this page in Folloze', 'make a Folloze version of this site', or a URL plus a Folloze deployment request. This is faithful replication, NOT original design — for an original ABM page from a strategy brief, use abm-page-designer instead."
---

# Folloze Migrator

You recreate an existing page inside Folloze as faithfully as possible — same structure, same content, same look — then deploy it through the Folloze MCP. The goal is a 1:1 migration the original owner would recognize instantly, not a redesign or an "inspired by" version.

## Golden Rule

**Match the source. Do not improve it.** Every decision answers one question: "Does this make the page closer to the original?" You are not a designer here — you are a faithful reproduction artist. Same section order, same copy (verbatim, in the original language), same colors, same fonts, same images, same layout. If you find yourself reordering sections, rewriting headlines, or "cleaning up" the design, stop — that is the opposite of this skill's job.

The one allowed exception: technical constraints Folloze imposes (see Technical Constraints). When the platform cannot reproduce something exactly, get as close as possible and note the delta in your final report.

## Operating Principle: Minimise User Friction

The migration should feel almost automatic from the user's side. If they're asking "what about X?" or "did you check Y?" you've failed the operating principle — you should have surfaced X and Y yourself before deploying. Specifically:

- **Find every image, video, iframe, and overlay yourself** before the user has to point them out.
- **Use real, signed media URLs from the source** — do not invent SVG placeholders for logos that exist in the source.
- **Do the side-by-side comparison yourself** before saying "done" — never ask the user to spot the differences.
- **Pre-empt obvious questions** ("are the images real?", "does the video work?", "is the container wide enough?") by answering them in your own QA.

## Input

1. **A source URL is required.** If the user did not give one, ask for it before doing anything.
2. Optionally the user may provide screenshots, a brand guide, or notes. Use them as additional truth.
3. If the page has multiple views/routes (e.g. hash routes like `/#section`, tabs, or a multi-page site), confirm with the user whether to migrate one page or the whole thing, and which.

## Phase 1 — Capture the Source Completely

This is where most migrations fail. A shallow capture produces a page that "looks kind of like it" but feels wrong. Capture deeply, in this order:

### Step 1.1 — Render the page in Chrome MCP

Modern site builders (TIME Sites, Vev, Sites.design, Webflow, Wix, Framer, Figma Sites) ship pages that **hydrate with JavaScript** — a plain HTML fetch misses content, computed styles, fonts, and lazy-loaded images. Always render in a real browser:

- Open the URL via Chrome MCP (`mcp__Claude_in_Chrome__navigate`).
- Wait 4–6 seconds for hydration.
- **Scroll through the entire page once** to force lazy-loaded images and videos to load. Use a loop in `javascript_tool` that scrolls in 400px steps with 150ms waits.
- Capture per-section screenshots as you go — these become your source of truth in Phase 3.
- If a domain is blocked by Chrome MCP, fall back to `WebFetch` for text + screenshots from the user.

### Step 1.2 — Inventory every media asset (the part most migrations miss)

**Do this systematically before writing any HTML.** The source page typically uses:

- `<img>` tags (often only a few of these)
- CSS `background-image` URLs (often many more of these — sections, decorative collages, brochure images)
- `<video>` elements (anthem videos, background loops)
- `<iframe>` elements (hero dashboards, demo widgets, embedded apps)
- HLS streams (`.m3u8` — won't play without hls.js)

Run a single JavaScript dump that collects ALL of these into `window.__allMedia`, sorted by their on-page Y position. Y position is how you match each URL to the right section.

Example extraction script (Y-position-mapped):
```javascript
(async () => {
  // Scroll page to force lazy load
  const h = document.body.scrollHeight;
  for(let y=0; y<h+1000; y+=400) { window.scrollTo(0,y); await new Promise(r=>setTimeout(r,150)); }
  window.scrollTo(0,0);
  // Collect everything with Y position
  const items = [];
  document.querySelectorAll('img').forEach(el => {
    if(el.src && !el.src.startsWith('data:')) items.push({type:'img', src:el.src, y:Math.round(el.getBoundingClientRect().top+window.scrollY), w:el.naturalWidth, h:el.naturalHeight});
  });
  document.querySelectorAll('*').forEach(el => {
    const bg = getComputedStyle(el).backgroundImage;
    if(bg && bg.includes('url(')) {
      const m = bg.match(/url\("([^"]+)"\)/);
      if(m && !m[1].startsWith('data:')) {
        const r = el.getBoundingClientRect();
        items.push({type:'bg', src:m[1], y:Math.round(r.top+window.scrollY), w:Math.round(r.width), h:Math.round(r.height)});
      }
    }
  });
  document.querySelectorAll('video').forEach(el => {
    const src = el.currentSrc || el.src;
    if(src) items.push({type:'video', src, y:Math.round(el.getBoundingClientRect().top+window.scrollY)});
  });
  document.querySelectorAll('iframe').forEach(el => {
    if(el.src) items.push({type:'iframe', src:el.src, y:Math.round(el.getBoundingClientRect().top+window.scrollY)});
  });
  items.sort((a,b)=>a.y-b.y);
  window.__allMedia = items;
  return items.length + ' media items';
})()
```

Then print just the **file names + Y position + size** first to identify each asset by location:
```javascript
window.__allMedia.map((i,n) => n+': Y'+i.y+' ['+i.type+'] '+(i.w||'')+'x'+(i.h||'')+' '+(i.src.match(/\/([^\/?]+)\?/)?.[1]||i.src.slice(-40))).join('\n')
```

Now you can map each section (by Y range) to the URLs it contains.

### Step 1.3 — Extract the long signed URLs

Many CDNs (CloudFront with signed URLs, especially `d.cloudfront.net` paths with `Expires=` and `Signature=` query strings) **require the signature** to load from any non-source domain. The unsigned versions return 403.

The Chrome MCP harness blocks long URLs with cookie/query-string content in normal tool returns. Workarounds:

1. **Best: `document.title` trick** — set `document.title = url` (or a few URLs joined with a delimiter), and the tab title appears in the next tool call's `Tab Context`. ~2000 chars per round, ~3 long signed URLs per batch.
   ```javascript
   document.title = '###' + window.__allMedia.slice(0,3).map(i=>i.src).join(' ### '); 'ok'
   ```
2. **Alt: stash in localStorage** indexed by integer, then retrieve in small batches.

Iterate over batches until you have every signed URL you need.

### Step 1.4 — Match URLs to sections

Print all URLs with their Y position one more time. Then walk the page top to bottom, assigning each URL to its section by Y range. Typical layout:

| Y range | Section | What's there |
|---|---|---|
| 0–200 | Nav | header logo |
| 200–800 | Hero | hero image/video/Figma iframe |
| 800–1600 | Welcome/Intro | anthem video or hero image, brand mark + tagline |
| 1600–2500 | Overview/Features | feature icons (often 6 of them) |
| 2500–3500 | KPIs/Stats | stat cards (usually pattern repetition, no images) |
| 3500–4500 | Demos | embedded demo widget (iframe) |
| 4500–5000 | Modules intro | architecture diagram image (single wide image) |
| 5000–7000 | Modules cards | per-module screenshots (one per card) |
| 7000–8000 | Business AI / value props | HLS video stream or MP4 |
| 8000–8500 | References cards | small generic logos (often placeholders) |
| 8500–9000 | Catalog/Resource | **may have multiple stacked images** (brochures + cover) |
| 9000–9500 | Team | team member photos |
| 9500+ | Footer | footer logo + social icons |

**Watch for stacked/overlapping images** — the catalog/resource section in SAP-style pages often layers a "brochures fan" image with a "cover" image rotated on top. If you see two screenshots at the same Y position (different sizes), that's the giveaway: use both with `position: absolute` and `transform: rotate()`.

### Step 1.5 — Extract typography, colors, and container width

```javascript
const h1 = document.querySelector('h1');
const body = document.body;
JSON.stringify({
  bodyFont: getComputedStyle(body).fontFamily,
  h1Color: getComputedStyle(h1).color,
  h1Size: getComputedStyle(h1).fontSize,
  containerEl: document.querySelector('main > div, [class*="container"], [class*="root"]')?.getBoundingClientRect().width
})
```

Also dump dominant background colors:
```javascript
const colorMap = {};
document.querySelectorAll('*').forEach(el => {
  const bg = getComputedStyle(el).backgroundColor;
  if(bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'rgb(255, 255, 255)') colorMap[bg] = (colorMap[bg]||0)+1;
});
JSON.stringify(colorMap)
```

Also detect available Google font equivalents by checking `document.fonts`.

### Step 1.6 — Build a section-by-section spec

For every section, record: order, copy verbatim, colors, typography, layout, images/media role, icons, navigation links, footer links, interactions.

**Do not translate, paraphrase, shorten, or fix typos.** If the source is Portuguese, the recreation is Portuguese.

## Phase 2 — Rebuild Faithfully

Build a single self-contained HTML file that reproduces the spec.

### Container width — match the source

**Default to a wide container (`max-width: 1500px`, padding `0 60px`)**, not a narrow 1200px. Most modern SAP-style / enterprise marketing sites use wide containers (1400–1536px). Folloze guide allows up to 1536px. If the source clearly uses narrower content (rare), match it — but a too-narrow container is one of the most common "feels wrong" mistakes.

### Use real source URLs for ALL media

- **Header logo** → source's signed logo URL (not a custom SVG you draw)
- **Welcome/intro side** → source's anthem video (`<video autoplay muted loop playsinline>`) OR source's image, whichever the source uses
- **Tagline brand marks** (e.g. small "SAP / Bring out your best.") → source's signed logo URL, not your own SVG
- **Module/feature screenshots** → each card's real source screenshot URL
- **Architecture diagram** in modules intro → source's image (often `success.png` or similar), not your own HTML chart
- **Catalog/resource collage** → all overlapping layers from source (may be 2+ images stacked with rotation)
- **Footer logo** → source's signed logo URL
- **Hero AI dashboards built with Figma Sites** → embed the Figma iframe directly (`https://*.figma.site/`)
- **Demo widgets (Consensus / similar)** → embed the iframe with the signed URL
- **Background videos / anthems** → MP4 `<video>` with the signed URL
- **HLS streams** → see HLS Video Setup below

**Do not build SVG placeholder logos** for things the source has as real images. The most common quality complaint is a fake SAP-style SVG next to the source's real brand mark.

### HLS Video Setup

If the source has an HLS stream (`.m3u8` URL), include hls.js to play it in non-Safari browsers:

```html
<video id="ai-video" autoplay muted loop playsinline style="width:100%;border-radius:12px;display:block"></video>

<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<script>
(function() {
  const video = document.getElementById('ai-video');
  const src = 'https://d.dam.sap.com/x/HASH/hls.m3u8?doi=ID';
  const tryPlay = () => video.play().catch(() => {});
  video.addEventListener('canplay', tryPlay, { once: true });
  if (video.canPlayType('application/vnd.apple.mpegurl')) {
    video.src = src;
  } else if (window.Hls && Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(src);
    hls.attachMedia(video);
    hls.on(Hls.Events.MANIFEST_PARSED, tryPlay);
  }
})();
</script>
```

This is an exception to "no external libraries" because there is no native way to play HLS in Chromium and the source uses HLS.

### Sticky nav — use `position: fixed`, not `position: sticky`

Folloze renders the board inside a container with overflow rules that **break `position: sticky`**. A nav that scrolls correctly in your local preview will not stick once deployed. Always use `position: fixed` for the nav:

```css
body { padding-top: 60px; }  /* compensate for the now out-of-flow nav */
.nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  background: #fff;
  height: 60px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
```

`scroll-margin-top` on sections still applies — keep the 70px value (60 nav + 10 breathing room) so JS-driven nav scrolls land below the fixed bar.

### In-page nav anchors — hash links do NOT work in Folloze

Folloze renders the board inside an iframe with custom routing. `<a href="#section-id">` clicks **don't scroll** in production, even though they work in your local preview. Always use a JS click handler instead.

Add a `navScroll` helper and use it for every nav link and any in-page jump (CTAs that target an anchor on the same page):

```html
<a href="#solution" data-scroll="solution" onclick="navScroll(event,'solution','A Nossa Solução')">A Nossa Solução</a>
```

```javascript
function navScroll(e, id, label, isCta) {
  if (e && e.preventDefault) e.preventDefault();
  const el = document.getElementById(id);
  if (el) {
    const navH = document.querySelector('.nav')?.offsetHeight || 60;
    const top = el.getBoundingClientRect().top + window.pageYOffset - navH - 10;
    window.scrollTo({ top, behavior: 'smooth' });
  }
  if (typeof flzAnalytic === 'function') {
    flzAnalytic(isCta ? 'cta_click' : 'anchor-click', { text: label, area: 'main nav header bar' });
  }
  return false;
}
```

Also add `scroll-margin-top` on the target sections so the sticky nav doesn't cover the heading when scrolling lands:

```css
section[id], nav[id] { scroll-margin-top: 70px; }
```

Pair both: the JS scroll handler handles the actual jump; the CSS rule keeps the offset clean if the browser ever does honour the hash.

### Stacked / overlapping image layouts

When a section uses overlapping images (typical "brochures + cover" catalog pattern):

```html
<div class="catalog-stack">
  <img class="catalog-brochures" src="..." alt="brochures fan">
  <img class="catalog-cover" src="..." alt="cover">
</div>
```

```css
.catalog-stack { position: relative; padding: 30px 20px 80px; }
.catalog-brochures {
  width: 100%;
  transform: rotate(-4deg) translateY(-20px) translateX(20px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
  display: block;
}
.catalog-cover {
  position: absolute;
  width: 50%;
  bottom: 10px;
  left: -10px;
  transform: rotate(6deg);
  box-shadow: 0 16px 40px rgba(0,0,0,0.22);
}
```

Match the source's rotation direction and corner placement — look at where the cover sits in the original (bottom-left vs bottom-right).

### Fonts

- Identify the exact font family. If it is available on Google Fonts, load it via `<link>`.
- If it is proprietary (SAP's "72 Brand", custom foundry fonts), substitute the **closest visual match** from Google Fonts (Montserrat is a good SAP "72 Brand" substitute) and note the substitution in your report. Match weight and feel, not just "a sans-serif."

### Technical Constraints (Folloze platform)

These are the only places you deviate from the source, and only because the platform requires it:

- **Single self-contained HTML file** — all CSS in a `<style>` block, all JS in a `<script>` block at the end.
- **Images via URL, never base64.**
- **Icons as inline SVG only** — never emoji, never icon fonts (Material Symbols / Font Awesome via `<link>` break in Folloze and render as raw text). Recreate the source's icons as inline `<svg>` — but UI icons only. Brand marks / logos are images, not SVGs you draw.
- **Fonts via Google Fonts `<link>`** with `font-display: swap`, plus the Folloze theme stylesheet the MCP guide requires.
- **No external animation libraries** — reproduce any motion with native CSS and vanilla JS. (hls.js is the one exception, when the source needs it.)
- **Analytics** — wire `flzAnalytic` tracking onto every CTA, link-out, and meaningful interaction (see Deployment). External links use `target="_blank" rel="noopener"`.

## Phase 3 — Visual Verification Loop (do not skip)

This is the step that makes the recreation actually match — and the step most likely missing from a first attempt. **Do this BEFORE the user sees it**, not after.

### Step 3.1 — Render your recreation

Serve the HTML locally (Claude Preview MCP) and load it in a browser.

### Step 3.2 — Section-by-section side-by-side

Walk through both pages top to bottom in parallel. For each section, capture screenshots from both and compare:

- Section structure present? ✓/✗
- Headline + copy exactly matching? ✓/✗
- Image/video the **right asset** (not a placeholder, not a swap)? ✓/✗
- Image **layout** matches (number of images, stacking, rotation, position)? ✓/✗
- Colors match? ✓/✗
- Container width feels right (text columns, image proportions)? ✓/✗
- Layout direction (text left + image right, or reversed)? ✓/✗

### Step 3.3 — Common things to spot in this pass

- **Missing overlapping images** — section uses 2 images stacked, you only have 1
- **Wrong image in the slot** — e.g. you used the welcome image in the catalog slot
- **Placeholder SVG instead of real brand mark** — anywhere a real logo URL exists
- **Static image where the source has video** — welcome anthem video is a frequent miss
- **Custom HTML diagram instead of source image** — architecture diagrams are usually a single source image
- **Container too narrow** — text columns squish, images crop awkwardly
- **Missing iframes** — Figma site hero, Consensus demo widget, etc.
- **Empty/blank sections** — HLS video not initialized, iframe URL not loaded
- **Wrong layout for stacked images** — cover in wrong corner, rotation wrong direction
- **Hash anchors that don't scroll in Folloze** — nav links use `<a href="#x">` instead of the `navScroll` JS handler. The local preview hides this because hash anchors work there; only Folloze production breaks. Test in the saved board, not just the preview.
- **Sticky nav that isn't sticky in Folloze** — `position: sticky` works locally but Folloze's container overflow rules break it. Use `position: fixed` + `body { padding-top: <nav-height>px }`.

### Step 3.4 — Iterate

List every difference, fix it, reload, repeat. Aim for 3 passes before showing the user. **Stop only when you cannot find another visible delta**, not when you've done enough work.

### Step 3.5 — Verify at mobile width

Check responsive collapse at ~720px and ~480px. Match the source's responsive behavior — no horizontal overflow.

## Phase 4 — Folloze MCP Deployment

### Before first save

1. Call `get_folloze_landing_page_creation_guide` and treat it as current MCP instructions.
2. **STOP and ask the user**: "Do you want to use the Folloze company theme, or keep the source page's own colors and fonts?" For a 1:1 migration the usual answer is the source's own brand — but you MUST ask and wait before calling `get_company_theme`. Pass the choice as `use_folloze_theme`.
3. Get the company theme per the user's choice and include the theme stylesheet exactly as the guide requires.

### Save flow

1. Build the HTML locally and run Phase 3 visual verification BEFORE presenting.
2. Present to the user with a short summary of what you built and the fidelity deltas you know about. Do NOT save until they approve — but the page they're reviewing should already be the result of your own QA, not a first draft.
3. Save with `save_folloze_board_from_file` (preferred) or `save_folloze_board_from_html`.
4. Pass the existing `boardId` when updating — never create duplicates. Iterating saves are normal: save → user feedback → fix → re-save with the same `boardId`.
5. Return the exact MCP-returned URL. Do not invent deployment URLs.

### Analytics acknowledgements

Do not set analytics acknowledgements true until the saved HTML has: read the guide this session, `flzAnalytic` on all CTA clicks, `target="_blank" rel="noopener"` on external links, and meaningful interactions tracked.

## Fidelity QA Gate

Run this **yourself** before presenting and again before MCP save. Each box ticked must be from a check you actually performed, not a guess.

### Content & structure
- [ ] Same number of sections as the source, in the same order
- [ ] All copy is verbatim and in the original language — nothing translated, rewritten, or invented
- [ ] Nav items + footer links match the source exactly

### Visual fidelity
- [ ] Colors match the source (extracted hex, not approximations)
- [ ] Fonts match or use a noted closest-match substitute (e.g. Montserrat ≈ SAP 72 Brand)
- [ ] Container width matches the source (default 1500px, do not ship 1200px if source is wider)
- [ ] Layout, spacing, and alignment match the source section by section
- [ ] Stacked / overlapping image layouts (catalog, hero collages) reproduced with correct rotation + corner placement

### Media — every asset accounted for
- [ ] Every source `<img>` URL is in the recreation
- [ ] Every source CSS `background-image` URL is in the recreation
- [ ] Every source `<video>` URL is in the recreation
- [ ] Every source `<iframe>` URL is in the recreation
- [ ] HLS streams initialized with hls.js if any
- [ ] Real brand-mark logo URLs used wherever the source uses them — no custom SVG stand-ins
- [ ] Welcome / intro anthem video used if the source uses video (not a static image)
- [ ] Architecture diagram is the source's image, not your own HTML chart
- [ ] All images and videos actually load (no broken/blank slots)
- [ ] Zero base64 in the HTML

### Platform requirements
- [ ] Icons are inline SVG (UI icons only — brand logos are images)
- [ ] Every CTA tracked with `flzAnalytic`; external links `target="_blank" rel="noopener"`
- [ ] Single self-contained HTML file
- [ ] Folloze theme stylesheet `<link>` is present per the MCP guide
- [ ] In-page nav anchors use the `navScroll` JS handler (NOT raw `href="#x"`) — hash anchors do not scroll inside the Folloze iframe
- [ ] `scroll-margin-top` set on target sections so the nav doesn't cover headings
- [ ] Sticky nav uses `position: fixed` (NOT `position: sticky`) — sticky breaks inside Folloze's container; body has compensating `padding-top`

### Visual verification (the pass that catches everything else)
- [ ] You scrolled through both source and recreation side by side
- [ ] You can name every section's image/video asset and confirm it's the right one
- [ ] Mobile/tablet responsive behavior matches the source

## What This Skill Does NOT Do

- Design an original page or write new copy → use `abm-page-designer` with a strategy brief.
- Improve, modernize, or "fix" the source design — fidelity is the whole point.
- Research accounts or build messaging strategy → use `abm-strategist`.
- Translate the page into another language unless the user explicitly asks.

## Output

After MCP save, report:
- What was migrated (source URL → board), one line
- Local source file path
- Board ID and the exact MCP-returned URL
- Any fidelity deltas the platform forced (font substitutions, interactions that could not be reproduced exactly, assets you could not extract)
- A short confidence note on how close the recreation is to the original — and what (if anything) the user should eyeball in Folloze itself
