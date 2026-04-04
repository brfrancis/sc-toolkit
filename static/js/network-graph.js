window.addEventListener('load', function () {

  const COLORS = {
    'Finance':         '#3b82f6',
    'Supply Chain':    '#10b981',
    'IT':              '#f59e0b',
    'Marketing':       '#ec4899',
    'Human Resources': '#8b5cf6',
  };

  const svgEl  = document.getElementById('uci-graph');
  const detail = document.getElementById('node-detail');
  const info   = document.getElementById('graph-info');
  const fnFilterList = document.getElementById('fn-filter-list');

  if (!svgEl || typeof GRAPH_DATA === 'undefined' || typeof d3 === 'undefined') {
    if (info) info.textContent = 'Graph failed to initialise — check console.';
    console.error('Missing: svgEl=' + !!svgEl + ' GRAPH_DATA=' + (typeof GRAPH_DATA) + ' d3=' + (typeof d3));
    return;
  }

  const svg = d3.select(svgEl);
  let width  = svgEl.parentElement.clientWidth  || 800;
  let height = svgEl.parentElement.clientHeight || 600;
  svg.attr('width', width).attr('height', height);

  const defs = svg.append('defs');
  defs.append('marker')
    .attr('id', 'edge-arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 12)
    .attr('refY', 0)
    .attr('markerWidth', 5)
    .attr('markerHeight', 5)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#94a3b8')
    .attr('fill-opacity', 0.75);

  const g = svg.append('g');

  svg.call(
    d3.zoom()
      .scaleExtent([0.05, 4])
      .on('zoom', e => g.attr('transform', e.transform))
  );

  const allNodes = GRAPH_DATA.nodes.map(d => ({ ...d }));
  const allEdges = GRAPH_DATA.edges.map(d => ({ ...d }));
  const nodeById = {};
  allNodes.forEach(n => nodeById[n.id] = n);
  const functionKeys = [...new Set(allNodes.map(n => n.function))];
  const visibleFunctions = new Set(functionKeys);
  const implementedIds = new Set();
  const implementedConnections = new Set();
  let selectedNode = null;

  let searchTerm   = '';

  function nodeColor(d) {
    if (!visibleFunctions.has(d.function)) return '#94a3b8';
    return COLORS[d.function] || '#94a3b8';
  }

  function nodeOpacity(d) {
    if (!visibleFunctions.has(d.function)) return 0;
    if (searchTerm) return d.id.toLowerCase().includes(searchTerm.toLowerCase()) ? 1 : 0.12;
    return 0.85;
  }

  function nodeStroke(d) {
    if (selectedNode === d) return '#1a1a1a';
    if (implementedIds.has(d.id)) return '#16a34a';
    if (implementedConnections.has(d.id)) return '#f59e0b';
    return '#fff';
  }

  function nodeStrokeWidth(d) {
    if (selectedNode === d) return 2.5;
    if (implementedIds.has(d.id)) return 2.2;
    if (implementedConnections.has(d.id)) return 1.8;
    return 1;
  }

  function edgeOpacity(d) {
    const src = nodeById[d.source.id || d.source];
    const tgt = nodeById[d.target.id || d.target];
    if (!src || !tgt) return 0;
    if (!visibleFunctions.has(src.function) || !visibleFunctions.has(tgt.function)) return 0;
    return 0.2;
  }

  function computeFunctionCenters() {
    const radius = Math.min(width, height) * 0.28;
    const cx = width / 2;
    const cy = height / 2;
    const centers = {};
    functionKeys.forEach((fn, i) => {
      const angle = (i / Math.max(functionKeys.length, 1)) * Math.PI * 2;
      centers[fn] = {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
      };
    });
    return centers;
  }
  let functionCenters = computeFunctionCenters();

  const sim = d3.forceSimulation(allNodes)
    .force('link',    d3.forceLink(allEdges).id(d => d.id).distance(d => {
      const src = nodeById[d.source.id || d.source];
      const tgt = nodeById[d.target.id || d.target];
      return src && tgt && src.function === tgt.function ? 35 : 90;
    }).strength(d => {
      const src = nodeById[d.source.id || d.source];
      const tgt = nodeById[d.target.id || d.target];
      return src && tgt && src.function === tgt.function ? 0.75 : 0.25;
    }))
    .force('charge',  d3.forceManyBody().strength(-60))
    .force('center',  d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide(13))
    .force('x', d3.forceX(d => (functionCenters[d.function] || { x: width / 2 }).x).strength(0.09))
    .force('y', d3.forceY(d => (functionCenters[d.function] || { y: height / 2 }).y).strength(0.09))
    .alphaDecay(0.025);

  const link = g.append('g')
    .selectAll('line')
    .data(allEdges)
    .join('line')
    .attr('stroke', '#94a3b8')
    .attr('stroke-width', 0.7)
    .attr('stroke-opacity', 0.2)
    .attr('marker-end', 'url(#edge-arrow)');

  const node = g.append('g')
    .selectAll('circle')
    .data(allNodes)
    .join('circle')
    .attr('r', 5)
    .attr('fill', nodeColor)
    .attr('fill-opacity', nodeOpacity)
    .attr('stroke', nodeStroke)
    .attr('stroke-width', nodeStrokeWidth)
    .style('cursor', 'pointer')
    .on('click', (event, d) => { event.stopPropagation(); selectNode(d); })
    .call(
      d3.drag()
        .on('start', (event, d) => { if (!event.active) sim.alphaTarget(0.1).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag',  (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end',   (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
    );

  const label = g.append('g')
    .selectAll('text')
    .data(allNodes)
    .join('text')
    .text(d => d.id.length > 28 ? d.id.slice(0, 26) + '…' : d.id)
    .attr('font-size', '8px')
    .attr('fill', 'var(--text-muted, #888)')
    .attr('text-anchor', 'start')
    .attr('dx', '0.6em')
    .attr('dy', '0.3em')
    .style('pointer-events', 'none');

  svg.on('click', () => deselectNode());

  sim.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('cx', d => d.x).attr('cy', d => d.y);
    label.attr('x', d => d.x).attr('y', d => d.y);
  });

  function refresh() {
    node.attr('fill', nodeColor).attr('fill-opacity', nodeOpacity);
    node.attr('stroke', nodeStroke).attr('stroke-width', nodeStrokeWidth);
    link.attr('stroke-opacity', edgeOpacity);
    label.attr('opacity', d => {
      if (!visibleFunctions.has(d.function)) return 0;
      if (searchTerm) return d.id.toLowerCase().includes(searchTerm.toLowerCase()) ? 0.95 : 0.08;
      return 0.6;
    });
  }

  function selectNode(d) {
    selectedNode = d;
    refresh();
    label.attr('font-weight', n => n === d ? 600 : 400);
    renderDetail(d);
  }

  function deselectNode() {
    selectedNode = null;
    label.attr('font-weight', 400);
    refresh();
    detail.innerHTML = '<div class="nd-empty">Click a node to inspect it.</div>';
  }

  function normaliseId(value) {
    return (value || '').trim().toLowerCase();
  }

  function updateImplementedHighlights(rawImplemented) {
    implementedIds.clear();
    implementedConnections.clear();

    const byNormalisedId = {};
    allNodes.forEach(n => { byNormalisedId[normaliseId(n.id)] = n.id; });

    rawImplemented.forEach(name => {
      const exact = byNormalisedId[normaliseId(name)];
      if (exact) implementedIds.add(exact);
    });

    allEdges.forEach(e => {
      const src = e.source.id || e.source;
      const tgt = e.target.id || e.target;
      if (implementedIds.has(src) && !implementedIds.has(tgt)) implementedConnections.add(tgt);
      if (implementedIds.has(tgt) && !implementedIds.has(src)) implementedConnections.add(src);
    });

    refresh();
  }

  function renderFunctionFilters() {
    if (!fnFilterList) return;
    fnFilterList.innerHTML = '';
    functionKeys.forEach(fn => {
      const labelEl = document.createElement('label');
      labelEl.className = 'filter-item';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = true;
      checkbox.value = fn;
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) visibleFunctions.add(fn);
        else visibleFunctions.delete(fn);
        refresh();
      });

      const text = document.createElement('span');
      text.textContent = fn;
      labelEl.appendChild(checkbox);
      labelEl.appendChild(text);
      fnFilterList.appendChild(labelEl);
    });
  }

  function renderDetail(d) {
    const out  = allEdges.filter(e => (e.source.id || e.source) === d.id);
    const into = allEdges.filter(e => (e.target.id || e.target) === d.id);

    const outHtml = out.slice(0, 8).map(e => {
      const t = e.target.id || e.target;
      const s = e.scope === 'Within Function' ? '↔ within' : '→ cross';
      return `<div class="nd-rel-item"><span class="nd-arrow">→</span>${t}<span class="nd-scope">${s}</span></div>`;
    }).join('');

    const inHtml = into.slice(0, 8).map(e => {
      const s2 = e.source.id || e.source;
      const sc = e.scope === 'Within Function' ? '↔ within' : '← cross';
      return `<div class="nd-rel-item"><span class="nd-arrow">←</span>${s2}<span class="nd-scope">${sc}</span></div>`;
    }).join('');

    detail.innerHTML = `
      <h3>${d.id}</h3>
      <div class="nd-meta">
        <span>${d.function}</span>
        <span>${d.department}</span>
      </div>
      ${out.length ? `<div class="nd-rels"><h4>Leads to (${out.length})</h4>${outHtml}${out.length > 8 ? `<div class="nd-scope" style="padding-top:4px">+${out.length - 8} more</div>` : ''}</div>` : ''}
      ${into.length ? `<div class="nd-rels"><h4>Comes from (${into.length})</h4>${inHtml}${into.length > 8 ? `<div class="nd-scope" style="padding-top:4px">+${into.length - 8} more</div>` : ''}</div>` : ''}
      ${!out.length && !into.length ? '<div class="nd-scope" style="padding-top:8px">No relationships defined</div>' : ''}
    `;
  }

  document.getElementById('uc-search').addEventListener('input', e => {
    searchTerm = e.target.value.trim();
    refresh();
    if (searchTerm) {
      const match = allNodes.find(n => n.id.toLowerCase().includes(searchTerm.toLowerCase()));
      if (match && match.x) {
        svg.transition().duration(400).call(
          d3.zoom().transform,
          d3.zoomIdentity.translate(width / 2 - match.x, height / 2 - match.y).scale(1.8)
        );
      }
    }
  });

  window.addEventListener('resize', () => {
    width  = svgEl.parentElement.clientWidth  || 800;
    height = svgEl.parentElement.clientHeight || 600;
    svg.attr('width', width).attr('height', height);
    functionCenters = computeFunctionCenters();
    sim.force('center', d3.forceCenter(width / 2, height / 2)).alpha(0.1).restart();
  });

  document.addEventListener('tag-input-change', e => {
    if (e.detail && e.detail.listId === 'implemented-list') {
      updateImplementedHighlights(e.detail.tags || []);
    }
  });

  renderFunctionFilters();
  const implementedHidden = document.getElementById('implemented_hidden');
  if (implementedHidden && implementedHidden.value) {
    try { updateImplementedHighlights(JSON.parse(implementedHidden.value)); } catch (_) {}
  }
  refresh();
  info.textContent = `${allNodes.length} use cases · ${allEdges.length} relationships · drag to pan · scroll to zoom · click a node`;
});
