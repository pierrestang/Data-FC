"use strict";

const TOP = 10;
/* Colonnes triables : total brut ou ratio par match, pour chaque stat. */
const SORTS = [
  { key: "goals", metric: "goals", ratio: false, label: "Buts" },
  { key: "assists", metric: "assists", ratio: false, label: "Passes", title: "Passes décisives" },
  { key: "ga", metric: "ga", ratio: false, label: "B+P", title: "Buts + passes" },
  { key: "r-goals", metric: "goals", ratio: true, label: "Buts / match", title: "Buts par match joué" },
  { key: "r-assists", metric: "assists", ratio: true, label: "Passes / match", title: "Passes décisives par match joué" },
  { key: "r-ga", metric: "ga", ratio: true, label: "B+P / match", title: "Buts + passes par match joué" },
];

/* Périmètres du filtre. `row` : lignes du détail qui comptent ; `player` : joueurs classés.
   « Toutes compétitions » = championnat + coupe d'Europe, joueurs des clubs du Big 5 seulement
   (sinon un joueur de Benfica n'aurait que ses buts européens). Les vues coupes incluent tout le monde. */
const isType = (t) => (r, C) => C[r.comp]?.type === t;
const isComp = (k) => (r) => r.comp === k;
const SCOPES = [
  { key: "all", label: "Toutes compétitions", row: (r, C) => C[r.comp]?.type !== "national", player: (p) => p.big5 },
  { key: "leagues", label: "Championnats", row: isType("league") },
  { key: "eng", label: "Premier League", indent: true, row: isComp("eng") },
  { key: "esp", label: "La Liga", indent: true, row: isComp("esp") },
  { key: "ita", label: "Serie A", indent: true, row: isComp("ita") },
  { key: "ger", label: "Bundesliga", indent: true, row: isComp("ger") },
  { key: "fra", label: "Ligue 1", indent: true, row: isComp("fra") },
  { key: "cups", label: "Coupes d’Europe", row: isType("cup") },
  { key: "ucl", label: "Champions League", indent: true, row: isComp("ucl") },
  { key: "uel", label: "Europa League", indent: true, row: isComp("uel") },
  { key: "uecl", label: "Conference League", indent: true, row: isComp("uecl") },
  { key: "usc", label: "Supercoupe de l’UEFA", row: isComp("usc") },
  { key: "fic", label: "Coupe intercontinentale de la FIFA", row: isComp("fic") },
  { key: "domcups", label: "Coupes nationales", row: isType("domcup") },
  { key: "efa", label: "FA Cup", indent: true, row: isComp("efa") },
  { key: "elc", label: "Carabao Cup", indent: true, row: isComp("elc") },
  { key: "cdr", label: "Copa del Rey", indent: true, row: isComp("cdr") },
  { key: "coi", label: "Coppa Italia", indent: true, row: isComp("coi") },
  { key: "dfb", label: "DFB-Pokal", indent: true, row: isComp("dfb") },
  { key: "cdf", label: "Coupe de France", indent: true, row: isComp("cdf") },
  { key: "domsuper", label: "Supercoupes nationales", row: isType("domsuper") },
  { key: "ecs", label: "Community Shield", indent: true, row: isComp("ecs") },
  { key: "esc", label: "Supercopa de España", indent: true, row: isComp("esc") },
  { key: "isc", label: "Supercoppa Italiana", indent: true, row: isComp("isc") },
  { key: "gsc", label: "Supercoupe d’Allemagne", indent: true, row: isComp("gsc") },
  { key: "tdc", label: "Trophée des champions", indent: true, row: isComp("tdc") },
  { key: "national", label: "Sélections", row: isType("national") },
  { key: "unl", label: "Ligue des nations UEFA", indent: true, row: isComp("unl") },
  { key: "euq", label: "Qualifications à l’Euro 2028", indent: true, row: isComp("euq") },
  { key: "wcq", label: "Éliminatoires CdM 2030 – Amérique du Sud", indent: true, row: isComp("wcq") },
  { key: "can", label: "Coupe d’Afrique des nations 2027", indent: true, row: isComp("can") },
  { key: "asc", label: "Coupe d’Asie 2027", indent: true, row: isComp("asc") },
  { key: "cnl", label: "Ligue des nations de la CONCACAF 2026-2027", indent: true, row: isComp("cnl") },
  { key: "gold", label: "Gold Cup 2027", indent: true, row: isComp("gold") },
];
const scopeOf = (k) => SCOPES.find((s) => s.key === k) || SCOPES[0];
const ESPN_SLUGS = { eng: "eng.1", esp: "esp.1", ita: "ita.1", ger: "ger.1", fra: "fra.1",
  ucl: "uefa.champions", uel: "uefa.europa", uecl: "uefa.europa.conf", usc: "uefa.super_cup",
  fic: "fifa.intercontinental_cup", unl: "uefa.nations", euq: "uefa.euroq", wcq: "fifa.worldq.conmebol",
  efa: "eng.fa", elc: "eng.league_cup", cdr: "esp.copa_del_rey", coi: "ita.coppa_italia", dfb: "ger.dfb_pokal",
  cdf: "fra.coupe_de_france", ecs: "eng.charity", esc: "esp.super_cup", isc: "ita.super_cup", gsc: "ger.super_cup",
  tdc: "fra.super_cup", can: "caf.nations", asc: "afc.asian.cup", cnl: "concacaf.nations.league", gold: "concacaf.gold" };

/* Lien « Source » : page de stats de la compétition choisie quand la source est ESPN. */
function sourceUrl() {
  const src = state.data.source || {};
  const slug = ESPN_SLUGS[state.scope];
  return src.name === "ESPN" && slug ? `https://www.espn.com/soccer/stats/_/league/${slug}` : src.url;
}

function renderSourceLinks() {
  const url = sourceUrl();
  if (url) $("#source-link").href = url;
}

const fmtInt = new Intl.NumberFormat("fr-FR");
const fmtRatio = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtDate = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" });
const fmtTime = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" });
const fmtDay = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });

const state = { data: null, scope: "all", stats: new Set(["goals", "assists", "ga"]), ratios: false, sort: "goals", limit: TOP, open: new Set() };
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ratio = (n, mp) => (mp ? n / mp : 0);
const val = (o, m) => (m === "ga" ? o.goals + o.assists : o[m]);

function initials(name) {
  const words = name.replace(/[^\p{L}\d ]/gu, "").split(/\s+/).filter((w) => w.length > 2 || /\d/.test(w));
  return (words.length > 1 ? words[0][0] + words[1][0] : (words[0] || name).slice(0, 3)).toUpperCase();
}

function crest(clubId) {
  const c = state.data.clubs[clubId];
  if (!c) return "";
  return c.logo
    ? `<img class="crest" src="${esc(c.logo)}" alt="" title="${esc(c.name)}" loading="lazy" decoding="async">`
    : `<span class="crest-fallback" aria-hidden="true">${esc(initials(c.name))}</span>`;
}

const flag = (path, title) =>
  path ? `<img class="flag" src="${esc(path)}" alt="${esc(title)}" title="${esc(title)}" loading="lazy">` : `<span class="flag" title="${esc(title)}"></span>`;

function compIcon(key) {
  const c = state.data.competitions[key];
  if (!c?.icon) return `<span class="flag"></span>`;
  return c.type === "cup" ? `<img class="comp-logo" src="${esc(c.icon)}" alt="" loading="lazy">` : flag(c.icon, "");
}

/* Totaux d'un joueur dans le périmètre choisi (null s'il n'y a pas joué). */
function inScope(p, S) {
  if (S.player && !S.player(p)) return null;
  const C = state.data.competitions;
  const rows = p.breakdown.filter((r) => S.row(r, C));
  if (!rows.length) return null;
  const sum = (k) => rows.reduce((n, r) => n + (r[k] || 0), 0);
  const byWeight = [...rows].sort((a, b) => (b.minutes ?? b.matches) - (a.minutes ?? a.matches));
  return {
    ...p, matches: sum("matches"), goals: sum("goals"), assists: sum("assists"),
    minutes: rows.every((r) => r.minutes != null) ? sum("minutes") : null,
    clubs: [...new Set(byWeight.map((r) => r.club).filter(Boolean))],
  };
}

function cutoffFor(scope, metric) {
  const c = state.data.cutoffs || {};
  return (c[scope] || (scope === "all" ? c.leagues : null) || {})[metric] || 0;
}

/* Classement selon la colonne choisie.
   - Total : stat décroissante, puis ratio par match ; même stat + même ratio = même rang.
   - Ratio : ratio décroissant, puis stat ; réservé aux joueurs ayant joué au moins 40 % des matchs
     du plus assidu du périmètre (sinon 1 but en 1 match = 1,00 passerait devant tout le monde).
   Dans les deux cas, seuls les joueurs au-dessus du seuil de complétude de la source sont classés. */
function ranking(scoped, sort) {
  const m = sort.metric;
  const cutoff = cutoffFor(state.scope, m);
  const maxMatches = Math.max(0, ...scoped.map((p) => p.matches));
  const minMatches = sort.ratio ? Math.max(1, Math.ceil(maxMatches * 0.4)) : 1;
  const key = (p) => (sort.ratio ? [ratio(val(p, m), p.matches), val(p, m)] : [val(p, m), ratio(val(p, m), p.matches)]);
  const list = scoped
    .filter((p) => p.matches >= minMatches && val(p, m) > cutoff)
    .map((p) => ({ p, k: key(p) }))
    .sort((a, b) => b.k[0] - a.k[0] || b.k[1] - a.k[1] || a.p.name.localeCompare(b.p.name, "fr"));
  let rank = 0;
  list.forEach((e, i) => {
    const prev = list[i - 1];
    if (!prev || Math.abs(prev.k[0] - e.k[0]) > 1e-9 || Math.abs(prev.k[1] - e.k[1]) > 1e-9) rank = i + 1;
    e.rank = rank;
  });
  return { list, minMatches };
}

function matchesTitle(o) {
  return `${fmtInt.format(o.matches)} match${o.matches > 1 ? "s" : ""}${o.minutes != null ? ` · ${fmtInt.format(o.minutes)} min` : ""}`;
}

/* Trois colonnes de stats. Mode « Totaux » : les totaux seuls. Mode « Ratios » : les trois ratios
   par match. La ligne dépliée donne totaux et ratios par compétition. */
const STATS = [
  { metric: "goals", label: "Buts", short: "Buts", title: "buts" },
  { metric: "assists", label: "Passes", short: "Pass.", title: "passes décisives" },
  { metric: "ga", label: "Total", short: "Tot.", title: "buts + passes" },
];
/* Largeurs (px). En « Totaux + ratios », chaque stat a deux sous-colonnes (total | ratio),
   pour que la surbrillance du tri ne couvre que la partie choisie. */
const W_DESK = { rank: 44, player: 220, club: 210, mj: 110, stat: 110, total: 92, ratio: 92, toggle: 36 };
/* Mobile : colonne Club fusionnée sous le nom du joueur, colonnes chiffrées resserrées. */
const W_MOB = { rank: 22, mj: 26, stat: 34, total: 26, ratio: 30, toggle: 14 };
const mq = matchMedia("(max-width: 720px)");
const mobile = () => mq.matches;
const Wd = () => (mobile() ? W_MOB : W_DESK);
/* Colonnes affichées : cases à cocher de la barre de filtre (au moins une stat), ratios en option. */
const view = () => ({ stats: STATS.map((x) => x.metric).filter((m) => state.stats.has(m)), ratios: state.ratios });
const shown = () => STATS.filter((x) => state.stats.has(x.metric));
Object.defineProperty(state, "showRatios", { get: () => state.ratios });
const statCols = () => { const W = Wd(); return state.showRatios ? [W.total, W.ratio] : [W.stat]; };
const colsHtml = (W = Wd()) => `<colgroup><col style="width:${W.rank}px"><col class="c-flex">${mobile() ? "" : `<col class="c-flex">`}<col style="width:${state.showRatios ? W.total : W.mj}px">${
  shown().map(() => statCols().map((w) => `<col style="width:${w}px">`).join("")).join("")}${mobile() ? "" : `<col style="width:${W.toggle}px">`}</colgroup>`;
const span = () => (mobile() ? 3 : 5) + shown().length * statCols().length;

/* Totaux toujours affichés ; le ratio (sous-colonne « / match ») seulement si coché dans « Statistiques »,
   y compris dans la ligne dépliée. */
function statCells(o, detail) {
  return shown().map((x) => {
    const v = val(o, x.metric), r = fmtRatio.format(ratio(v, o.matches));
    const onTotal = state.sort === x.metric, onRatio = state.sort === "r-" + x.metric;
    if (state.showRatios) {
      return `<td class="num stat${onTotal ? " sorted" : ""}"><span class="v${onTotal ? " on" : ""}">${v}</span></td>` +
        `<td class="num stat ratio-col${onRatio ? " sorted" : ""}"><span class="r${onRatio ? " on" : ""}">${r}</span></td>`;
    }
    return `<td class="num stat${onTotal ? " sorted" : ""}"><span class="v${onTotal ? " on" : ""}">${v}</span></td>`;
  }).join("");
}

/* Nom du pays en français, à partir du code de drapeau (ISO 3166 ; nations britanniques à part). */
const UK_NATIONS = { "gb-eng": "Angleterre", "gb-sct": "Écosse", "gb-wls": "Pays de Galles", "gb-nir": "Irlande du Nord" };
const regionNames = new Intl.DisplayNames(["fr"], { type: "region" });
function countryName(p) {
  const code = (p.flag || "").match(/flags\/([a-z-]+)\.svg$/)?.[1];
  if (!code) return p.nationName || p.nation || "";
  if (UK_NATIONS[code]) return UK_NATIONS[code];
  try { return regionNames.of(code.toUpperCase()) || p.nationName || ""; } catch (e) { return p.nationName || ""; }
}

function clubAndCountry(p) {
  const country = countryName(p);
  return `<div class="club-country">${clubCell(p.clubs)}
    <div class="country">${flag(p.flag, country)}<span>${esc(country || "—")}</span></div></div>`;
}

/* Nom affiché d'un club ; pour une sélection nationale, le pays en français (« Espagne », pas « Spain »). */
function clubName(c) {
  if (!c) return "—";
  return c.national ? countryName({ flag: c.logo, nationName: c.name }) || c.name : c.name;
}

function clubCell(clubs) {
  const main = state.data.clubs[clubs[0]];
  return `<div class="club">${crest(clubs[0])}<span class="club-name">${esc(clubName(main))}</span>${clubs.length > 1 ? `<span class="pill" title="${clubs.length} clubs">+${clubs.length - 1}</span>` : ""}</div>`;
}

function rowHtml(e) {
  const p = e.p;
  const open = state.open.has(p.id);
  const meta = [p.position, p.age && `${p.age} ans`].filter(Boolean).join(" · ");
  let html = `
  <tr class="row" tabindex="0" data-id="${esc(p.id)}" aria-expanded="${open}">
    <td class="rank${e.rank <= 3 ? " podium" : ""}">${e.rank}</td>
    <td><div class="player"><div class="player-text">
      <span class="player-name">${esc(p.name)}</span>${mobile()
        ? `<span class="player-club">${clubCell(p.clubs)}${flag(p.flag, countryName(p))}</span>`
        : `<span class="player-meta">${esc(meta)}</span>`}</div></div></td>
    ${mobile() ? "" : `<td>${clubAndCountry(p)}</td>`}
    <td class="num mj" title="${esc(matchesTitle(p))}"><span class="v">${p.matches}</span></td>
    ${statCells(p)}
    ${mobile() ? "" : `<td><svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></td>`}
  </tr>`;
  if (open) {
    const C = state.data.competitions, S = scopeOf(state.scope);
    html += `<tr class="detail"><td colspan="${span()}"><table>${colsHtml()}<tbody>
      ${p.breakdown.map((b) => `<tr class="${S.row(b, C) ? "" : "out"}">
        <td></td>
        <td><div class="league">${compIcon(b.comp)}<span class="league-name">${esc(C[b.comp]?.name || b.comp)}</span></div></td>
        ${mobile() ? "" : `<td>${b.club ? clubCell([b.club]) : ""}</td>`}
        <td class="num mj" title="${esc(matchesTitle(b))}"><span class="v">${b.matches}</span></td>
        ${statCells(b, true)}
        ${mobile() ? "" : "<td></td>"}</tr>`).join("")}
    </tbody></table></td></tr>`;
  }
  return html;
}

function render() {
  const S = scopeOf(state.scope);
  const sort = SORTS.find((x) => x.key === state.sort) || SORTS[0];
  const scoped = state.data.players.map((p) => inScope(p, S)).filter(Boolean);
  const { list } = ranking(scoped, sort);
  // Rangs 1 à N (un ex æquo parfait au dernier rang reste affiché) ; « Afficher plus » ajoute 10 rangs.
  const top = list.filter((e) => e.rank <= state.limit);
  const more = list.length > top.length;
  /* En-têtes : le nom trie par le total ; « / match » (sous-colonne ratio) trie par le ratio. */
  const btn = (key, label, title) => `<button type="button" class="${state.sort === key ? "active" : ""}" data-sort="${key}" title="${esc(title)}">${esc(label)}</button>`;
  const th = (x) => {
    const t = `<th class="num sortable${state.sort === x.metric ? " sorted" : ""}" scope="col">${btn(x.metric, mobile() ? x.short : x.label, `Trier par ${x.title}`)}</th>`;
    if (!state.showRatios) return t;
    return t + `<th class="num sortable ratio-col${state.sort === "r-" + x.metric ? " sorted" : ""}" scope="col">${btn("r-" + x.metric, mobile() ? "/m" : "/ match", `Trier par ${x.title} par match`)}</th>`;
  };
  $("#boards").innerHTML = `
  <section class="card">
    <table class="board${state.showRatios ? " with-ratios" : ""}">${colsHtml()}
      <thead>
        <tr><th class="rank" scope="col">#</th><th scope="col">Joueur</th>${mobile() ? "" : `<th scope="col">Club · Nationalité</th>`}
          <th class="num mj" scope="col" title="Matchs joués">${mobile() ? "MJ" : "Matchs"}</th>${shown().map(th).join("")}${mobile() ? "" : `<th><span class="sr-only">Détail</span></th>`}</tr>
      </thead>
      <tbody>${top.length ? top.map(rowHtml).join("") : `<tr class="empty"><td colspan="${span()}">Aucun joueur pour le moment.</td></tr>`}</tbody>
    </table>
  </section>
  ${more ? `<div class="more-row"><button class="more-link" type="button" data-more>Afficher plus</button></div>` : ""}
  `;
}

function renderScopes() {
  const C = state.data.competitions;
  const comps = new Set(state.data.players.flatMap((p) => p.breakdown.map((r) => r.comp)));
  const groupHas = (type) => [...comps].some((k) => C[k]?.type === type);
  // Une compétition sans données (pas encore commencée) reste visible mais grisée.
  const hasData = (s) => ["all", "leagues"].includes(s.key) || comps.has(s.key)
    || (s.key === "cups" && groupHas("cup")) || (s.key === "national" && groupHas("national"))
    || (s.key === "domcups" && groupHas("domcup")) || (s.key === "domsuper" && groupHas("domsuper"));
  const known = SCOPES.filter((s) => hasData(s) || C[s.key]);
  if (!known.some((s) => s.key === state.scope && hasData(s))) state.scope = "all";
  $("#scope").innerHTML = known.map((s) => {
    const ok = hasData(s);
    return `<label class="${s.indent ? "sub" : ""}${ok ? "" : " off"}"><input type="radio" name="scope" value="${s.key}"${s.key === state.scope ? " checked" : ""}${ok ? "" : " disabled"}> ${esc(s.label)}${ok ? "" : " (à venir)"}</label>`;
  }).join("");
  $("#scope-btn").textContent = scopeOf(state.scope).label;
}

function renderStatus() {
  const d = state.data;
  const t = new Date(d.updatedAt);
  const hours = (Date.now() - t) / 36e5;
  // « 22:30 » aujourd'hui, « hier 00:00 », sinon « 8 nov. 00:00 ».
  const time = fmtTime.format(t);
  const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((day(new Date()) - day(t)) / 864e5);
  const when = diff === 0 ? time : diff === 1 ? `hier ${time}` : `${fmtDay.format(t)} ${time}`;
  const el = $("#updated");
  el.innerHTML = `Mise à jour : <time datetime="${esc(d.updatedAt)}">${esc(when)}</time>`;
  el.title = `Dernière mise à jour : ${fmtDate.format(t)} · source ${d.source?.name || ""}`;
  el.classList.toggle("stale", hours > 26); // la mise à jour de minuit a sauté
  $("#season").textContent = `Saison ${d.season.replace("-", "–")}`;
  $("#demo-notice").hidden = !d.demo;
  renderSourceLinks();
  $("#source-link").textContent = `Source : ${d.source?.name || "—"}`;
}

function toggle(id, fromKeyboard) {
  state.open.has(id) ? state.open.delete(id) : state.open.add(id);
  render();
  if (fromKeyboard) document.querySelector(`.row[data-id="${CSS.escape(id)}"]`)?.focus();
}

function bind() {
  $("#scope").addEventListener("change", (ev) => {
    state.scope = ev.target.value;
    $("#scope-btn").textContent = scopeOf(state.scope).label;
    $("#scope-menu").open = false;
    state.limit = TOP;
    state.open.clear();
    history.replaceState(null, "", state.scope === "all" ? location.pathname : "#" + state.scope);
    renderSourceLinks();
    render();
  });
  $("#cols-menu").addEventListener("change", (ev) => {
    const box = ev.target;
    if (box.id === "opt-ratios") state.ratios = box.checked;
    else if (box.checked) state.stats.add(box.dataset.stat);
    else if (state.stats.size > 1) state.stats.delete(box.dataset.stat);
    else box.checked = true; // au moins une colonne de stats
    // Le tri doit porter sur une colonne affichée : sinon, total de la première stat visible.
    const metric = state.sort.replace(/^r-/, "");
    const m = view().stats.includes(metric) ? metric : view().stats[0];
    state.sort = (state.sort.startsWith("r-") && view().ratios ? "r-" : "") + m;
    state.limit = TOP;
    render();
  });

  $("#boards").addEventListener("click", (ev) => {
    const sb = ev.target.closest("[data-sort]");
    if (sb) { state.sort = sb.dataset.sort; state.limit = TOP; render(); return; }
    if (ev.target.closest("[data-more]")) { state.limit += TOP; render(); return; }
    const r = ev.target.closest(".row");
    if (r) toggle(r.dataset.id);
  });
  $("#boards").addEventListener("keydown", (ev) => {
    const r = ev.target.closest(".row");
    if (r && (ev.key === "Enter" || ev.key === " ")) { ev.preventDefault(); toggle(r.dataset.id, true); }
  });
  document.addEventListener("click", (ev) => {
    for (const m of document.querySelectorAll(".menu[open]")) if (!m.contains(ev.target)) m.open = false;
  });
  $("#theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("dfc-theme", next); } catch (e) {}
  });
}

async function main() {
  const h = location.hash.slice(1);
  if (SCOPES.some((s) => s.key === h)) state.scope = h;
  bind();
  try {
    const res = await fetch(`data/leaderboard.json?v=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(res.status);
    state.data = await res.json();
    renderScopes();
    renderStatus();
    render();
  } catch (e) {
    $("#updated").textContent = "Mise à jour : indisponible";
    $("#updated").classList.add("stale");
    $("#boards").innerHTML = `<p class="empty-msg">Impossible de charger data/leaderboard.json — lancez scraper/update.py.</p>`;
  }
}

main();

/* Passage ordinateur ↔ mobile (rotation, redimensionnement) : on redessine le tableau. */
mq.addEventListener("change", () => { if (state.data) render(); });
