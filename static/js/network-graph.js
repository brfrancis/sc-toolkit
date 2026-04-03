(function () {

  const COLORS = {
    'Finance':         '#3b82f6',
    'Supply Chain':    '#10b981',
    'IT':              '#f59e0b',
    'Marketing':       '#ec4899',
    'Human Resources': '#8b5cf6',
  };

  const svg    = d3.select('#uci-graph');
  const detail = document.getElementById('node-detail');
  const info   = document.getElementById('graph-info');

  let width  = svg.node().parentElement.clientWidth;
  let height = svg.node().parentElement.clientHeight;
  svg.attr('width', width).attr('height', height);

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

  let activeFilter = '';
  let searchTerm   = '';
  let selectedNode = null;

  function nodeColor(d) {
    if (activeFilter && d.function !== activeFilter) return '#94a3b8';
    return COLORS[d.function] || '#94a3b8';
  }

  function nodeOpacity(d) {
    if (searchTerm) {
      return d.id.toLowerCase().includes(searchTerm.toLowerCase()) ? 1 : 0.15;
    }
    if (activeFilter && d.function !== activeFilter) return 0.15;
    return 0.85;
  }

  function edgeOpacity(d) {
    if (activeFilter) {
      const src = nodeById[d.source.id || d.source];
      const tgt = nodeById[d.target.id || d.target];
      if (!src || !tgt) return 0;
      if (src.function !== activeFilter && tgt.function !== activeFilter) return 0;
    }
    return 0.25;
  }

  const sim = d3.forceSimulation(allNodes)
    .force('link',   d3.forceLink(allEdges).id(d => d.id).distance(60).strength(0.3))
    .force('charge', d3.forceManyBody().strength(-80))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide(14))
    .alphaDecay(0.02);

  const link = g.append('g')
    .selectAll('line')
    .data(allEdges)
    .join('line')
    .attr('stroke', '#94a3b8')
    .attr('stroke-width', 0.8)
    .attr('stroke-opacity', 0.25);

  const node = g.append('g')
    .selectAll('circle')
    .data(allNodes)
    .join('circle')
    .attr('r', 6)
    .attr('fill', nodeColor)
    .attr('fill-opacity', nodeOpacity)
    .attr('stroke', '#fff')
    .attr('stroke-width', 1)
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
    .attr('font-size', '9px')
    .attr('fill', 'var(--text-muted)')
    .attr('text-anchor', 'middle')
    .attr('dy', '1.8em')
    .style('pointer-events', 'none')
    .style('display', 'none');

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
    link.attr('stroke-opacity', edgeOpacity);
  }

  function selectNode(d) {
    selectedNode = d;
    node.attr('stroke', n => n === d ? '#1a1a1a' : '#fff').attr('stroke-width', n => n === d ? 2 : 1);
    label.style('display', n => n === d ? 'block' : 'none');
    renderDetail(d);
  }

  function deselectNode() {
    selectedNode = null;
    node.attr('stroke', '#fff').attr('stroke-width', 1);
    label.style('display', 'none');
    detail.innerHTML = '<div class="nd-empty">Click a node to see details and relationships.</div>';
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
      ${out.length ? `<div class="nd-rels"><h4>Leads to (${out.length})</h4>${outHtml}${out.length > 8 ? `<div class="nd-scope" style="padding-top:4px">+${out.length-8} more</div>` : ''}</div>` : ''}
      ${into.length ? `<div class="nd-rels"><h4>Comes from (${into.length})</h4>${inHtml}${into.length > 8 ? `<div class="nd-scope" style="padding-top:4px">+${into.length-8} more</div>` : ''}</div>` : ''}
      ${!out.length && !into.length ? '<div class="nd-scope" style="padding-top:8px">No relationships defined</div>' : ''}
    `;
  }

  document.getElementById('fn-filter').addEventListener('change', e => {
    activeFilter = e.target.value;
    refresh();
  });

  document.getElementById('uc-search').addEventListener('input', e => {
    searchTerm = e.target.value.trim();
    refresh();
    if (searchTerm) {
      const match = allNodes.find(n => n.id.toLowerCase().includes(searchTerm.toLowerCase()));
      if (match && match.x) {
        const t = d3.zoomTransform(svg.node());
        svg.transition().duration(400).call(
          d3.zoom().transform,
          d3.zoomIdentity.translate(width/2 - match.x, height/2 - match.y).scale(1.5)
        );
      }
    }
  });

  window.addEventListener('resize', () => {
    width  = svg.node().parentElement.clientWidth;
    height = svg.node().parentElement.clientHeight;
    svg.attr('width', width).attr('height', height);
    sim.force('center', d3.forceCenter(width/2, height/2)).alpha(0.1).restart();
  });

  info.textContent = `${allNodes.length} use cases · ${allEdges.length} relationships · drag to pan · scroll to zoom · click a node`;

})();
