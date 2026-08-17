import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

const API = "/api";
const colors = {
  Character: "#ff8a3d",
  Place: "#36a3ff",
  Object: "#9fd356",
  Event: "#ff5ea8",
  Concept: "#a78bfa",
};
const labels = {
  fr: {
    choose: "Choisir un corpus",
    search: "Rechercher un nœud…",
    select: "Sélectionnez un nœud pour voir ses sources et générer un balado.",
    initial: "Sélectionnez un corpus, puis cliquez sur un nœud.",
    sources: "Sources",
    podcast: "Générer le balado",
    generating: "Génération…",
    script: "Texte du balado",
    empty: "Aucun graphe chargé",
    legend: "Légende",
    corpusLabel: "Corpus",
    languageLabel: "Langue",
    graphLabel: "Graphe de connaissances",
    nodeType: "Type",
    summary: "Résumé",
    relation: "Relation",
    noSummary: "Aucun résumé disponible.",
    audioUnsupported: "Votre navigateur ne peut pas lire cet audio.",
    errorPrefix: "Erreur",
    nodeTypes: {
      Character: "Personnage",
      Place: "Lieu",
      Object: "Objet",
      Event: "Événement",
      Concept: "Concept",
    },
  },
  en: {
    choose: "Choose a corpus",
    search: "Search a node…",
    select: "Select a node to see sources and generate a podcast.",
    initial: "Select a corpus, then click a node.",
    sources: "Sources",
    podcast: "Generate podcast",
    generating: "Generating…",
    script: "Podcast text",
    empty: "No graph loaded",
    legend: "Legend",
    corpusLabel: "Corpus",
    languageLabel: "Language",
    graphLabel: "Knowledge graph",
    nodeType: "Type",
    summary: "Summary",
    relation: "Relation",
    noSummary: "No summary available.",
    audioUnsupported: "Your browser cannot play this audio.",
    errorPrefix: "Error",
    nodeTypes: {
      Character: "Character",
      Place: "Place",
      Object: "Object",
      Event: "Event",
      Concept: "Concept",
    },
  },
};
let locale = "fr", corpora = [], graph = { nodes: [], edges: [] }, selected = null, corpusId = "";
let simulation = null;
const $ = (id) => document.getElementById(id);
const esc = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
async function json(path, opts){ const res = await fetch(`${API}${path}`, opts); if(!res.ok) throw new Error(await res.text()); return res.json(); }
function setMessage(text){ const el=$("message"); el.textContent=text||""; el.hidden=!text; }
function typeLabel(type){ return labels[locale].nodeTypes[type] || type; }
function renderChrome(){
  const t=labels[locale];
  document.documentElement.lang = locale;
  $("corpus-label").textContent = t.corpusLabel;
  $("language-label").textContent = t.languageLabel;
  $("corpus-select").setAttribute("aria-label", t.corpusLabel);
  $("language-select").setAttribute("aria-label", t.languageLabel);
  $("corpus-select").querySelector("option").textContent=t.choose;
  $("search-input").placeholder=t.search;
  $("graph").setAttribute("aria-label", t.graphLabel);
}
function renderLegend(){
  const t=labels[locale];
  $("legend").innerHTML = `<strong>${esc(t.legend)}</strong>` + Object.entries(colors).map(([k,v])=>`<span><i style="background:${v}"></i>${esc(typeLabel(k))}</span>`).join("");
}
function renderSidebar(){
  const t=labels[locale], el=$("sidebar");
  if(!selected){ el.innerHTML=`<p>${corpusId ? esc(t.select) : esc(t.initial)}</p>`; return; }
  const refs=(selected.source_refs||[]).map(r=>`<li>${esc(r.text)}${r.location?` <span>(${esc(r.location)})</span>`:""}</li>`).join("");
  el.innerHTML=`<h2>${esc(selected.label)}</h2><p class="node-type">${esc(typeLabel(selected.type))}</p><dl class="node-meta"><dt>${esc(t.nodeType)}</dt><dd>${esc(typeLabel(selected.type))}</dd></dl><h3>${esc(t.summary)}</h3><p>${esc(selected.summary||t.noSummary)}</p>${refs?`<h3>${esc(t.sources)}</h3><ul class="sources">${refs}</ul>`:""}<button id="podcast" class="button">${esc(t.podcast)}</button><section id="podcast-result" class="podcast"></section>`;
  $("podcast").onclick=generatePodcast;
}
function currentNodes(){ const q=$("search-input").value.trim().toLowerCase(); return q ? graph.nodes.filter(n=>`${n.label} ${n.type} ${n.summary}`.toLowerCase().includes(q)) : graph.nodes; }
function renderGraph(nodes=currentNodes()){
  const container = $("graph");
  container.innerHTML="";
  if(simulation) simulation.stop();
  if(!nodes.length){ container.innerHTML=`<div class="empty">${esc(labels[locale].empty)}</div>`; return; }
  const ids = new Set(nodes.map(n=>n.id));
  const links = graph.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)).map(e=>({ ...e }));
  const simNodes = nodes.map(n=>({ ...n }));
  const width = container.clientWidth || 900;
  const height = container.clientHeight || 620;
  const svg = d3.select(container).append("svg").attr("viewBox", [0,0,width,height]).attr("role","img").attr("aria-label", labels[locale].graphLabel);
  const defs = svg.append("defs");
  defs.append("filter").attr("id","glow").html('<feGaussianBlur stdDeviation="3.5" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>');
  const zoomLayer = svg.append("g");
  svg.call(d3.zoom().scaleExtent([0.35, 3.5]).on("zoom", (event)=>zoomLayer.attr("transform", event.transform)));
  const link = zoomLayer.append("g").attr("class","links").selectAll("path").data(links).join("path").attr("class","edge");
  const linkLabel = zoomLayer.append("g").attr("class","edge-labels").selectAll("text").data(links).join("text").text(d=>d.label||d.relation).attr("class","edge-label");
  const node = zoomLayer.append("g").attr("class","nodes").selectAll("g").data(simNodes).join("g").attr("class", d=>`node${selected?.id===d.id ? " selected" : ""}`).attr("tabindex",0).attr("role","button").attr("aria-label", d=>`${d.label}, ${typeLabel(d.type)}`).on("click keydown", (event,d)=>{ if(event.type === "click" || event.key === "Enter" || event.key === " "){ selected=graph.nodes.find(n=>n.id===d.id); renderSidebar(); renderGraph(currentNodes()); }}).call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));
  node.append("circle").attr("r", d=>selected?.id===d.id ? 19 : 14).attr("fill", d=>colors[d.type]||"#9ca3af");
  node.append("text").attr("y", 28).text(d=>d.label);
  node.append("title").text(d=>`${d.label}\n${typeLabel(d.type)}\n${d.summary || ""}`);
  simulation = d3.forceSimulation(simNodes).force("link", d3.forceLink(links).id(d=>d.id).distance(130).strength(0.55)).force("charge", d3.forceManyBody().strength(-430)).force("collide", d3.forceCollide().radius(52)).force("center", d3.forceCenter(width/2, height/2)).force("x", d3.forceX(width/2).strength(0.04)).force("y", d3.forceY(height/2).strength(0.04)).on("tick", ticked);
  function ticked(){
    link.attr("d", d=>`M${d.source.x},${d.source.y} Q${(d.source.x+d.target.x)/2},${(d.source.y+d.target.y)/2-18} ${d.target.x},${d.target.y}`);
    linkLabel.attr("x", d=>(d.source.x+d.target.x)/2).attr("y", d=>(d.source.y+d.target.y)/2-12);
    node.attr("transform", d=>`translate(${d.x},${d.y})`);
  }
  function dragstarted(event,d){ if(!event.active) simulation.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }
  function dragged(event,d){ d.fx=event.x; d.fy=event.y; }
  function dragended(event,d){ if(!event.active) simulation.alphaTarget(0); d.fx=null; d.fy=null; }
}
async function loadCorpora(){ corpora = await json("/corpora"); const select=$("corpus-select"); select.innerHTML = `<option value="">${esc(labels[locale].choose)}</option>` + corpora.map(c=>`<option value="${esc(c.id)}">${esc(c.name)} (${c.node_count})</option>`).join(""); }
async function loadGraph(id){ corpusId=id; selected=null; $("search-input").disabled=!id; if(!id){ graph={nodes:[],edges:[]}; renderGraph(); renderSidebar(); return; } graph = await json(`/graph?corpus_id=${encodeURIComponent(id)}`); renderGraph(); renderSidebar(); }
async function generatePodcast(){ const btn=$("podcast"), out=$("podcast-result"), t=labels[locale]; btn.disabled=true; btn.textContent=t.generating; try{ const res=await json("/podcast", { method:"POST", headers:{"Content-Type":"application/json", "Accept-Language": locale}, body:JSON.stringify({ corpus_id: corpusId, entity_id: selected.id }) }); out.innerHTML=`<h3>${esc(t.script)}</h3><pre>${esc(res.script||"")}</pre>${res.audio_url?`<audio controls src="${esc(res.audio_url)}">${esc(t.audioUnsupported)}</audio>`:""}`; }catch(e){ out.textContent=`${t.errorPrefix}: ${String(e)}`; }finally{ btn.disabled=false; btn.textContent=t.podcast; } }
$("language-select").onchange=(e)=>{ locale=e.target.value; renderChrome(); renderLegend(); loadCorpora().then(()=>{$("corpus-select").value=corpusId}); renderGraph(currentNodes()); renderSidebar(); };
$("corpus-select").onchange=(e)=>loadGraph(e.target.value).catch(err=>setMessage(String(err)));
$("search-input").oninput=()=>renderGraph(currentNodes());
renderChrome(); renderLegend(); renderGraph(); renderSidebar(); loadCorpora().catch(err=>setMessage(String(err)));
