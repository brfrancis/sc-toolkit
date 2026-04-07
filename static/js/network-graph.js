window.addEventListener('load', function () {

  const svgEl  = document.getElementById('uci-graph');
  const detail = document.getElementById('node-detail');
  const info   = document.getElementById('graph-info');
  const fnFilterList = document.getElementById('fn-filter-list');
  const statusFilterList = document.getElementById('status-filter-list');
  const searchInput = document.getElementById('uc-search');
  const datasetSelect = document.getElementById('dataset-select');
  const layout = document.querySelector('.uci-layout');
  const sideToggle = document.getElementById('side-toggle');
  const detailPane = document.getElementById('node-inspector-pane');
  const detailToggle = document.getElementById('detail-toggle');

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
    .attr('refX', 9)
    .attr('refY', 0)
    .attr('markerWidth', 5)
    .attr('markerHeight', 5)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#94a3b8')
    .attr('fill-opacity', 0.75);

  const g = svg.append('g');

  const zoomBehavior = d3.zoom()
    .scaleExtent([0.05, 4])
    .on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoomBehavior);

  const allNodes = GRAPH_DATA.nodes.map(d => ({ ...d }));
  const allEdges = GRAPH_DATA.edges.map(d => ({ ...d }));
  const nodeById = {};
  allNodes.forEach(n => nodeById[n.id] = n);
  const functionKeys = [...new Set(allNodes.map(n => n.function).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const functionColors = {};
  const reservedStatusColours = new Set([
    '#16a34a', '#166534',
    '#f59e0b', '#92400e',
    '#dc2626', '#991b1b',
  ]);

  function isReservedStatusColor(colour) {
    const rgb = d3.color(colour);
    if (!rgb) return false;
    const hex = rgb.formatHex().toLowerCase();
    if (reservedStatusColours.has(hex)) return true;

    const hsl = d3.hsl(rgb);
    if (Number.isNaN(hsl.h)) return false;
    const hue = (hsl.h + 360) % 360;

    const inRedBand = hue <= 20 || hue >= 340;
    const inAmberBand = hue >= 25 && hue <= 55;
    const inGreenBand = hue >= 90 && hue <= 160;
    return inRedBand || inAmberBand || inGreenBand;
  }

  const basePalette = [...d3.schemeTableau10, ...d3.schemeSet3]
    .map(colour => d3.color(colour)?.formatHex()?.toLowerCase() || colour)
    .filter(colour => !isReservedStatusColor(colour));

  function generateFunctionColour(index) {
    let hue = (210 + (index * 41)) % 360;
    let attempts = 0;
    while (attempts < 36) {
      const colour = d3.hsl(hue, 0.6, 0.5).formatHex();
      if (!isReservedStatusColor(colour)) return colour;
      hue = (hue + 17) % 360;
      attempts += 1;
    }
    return '#6366f1';
  }

  functionKeys.forEach((fn, index) => {
    if (index < basePalette.length) {
      functionColors[fn] = basePalette[index];
      return;
    }
    functionColors[fn] = generateFunctionColour(index);
  });
  const visibleFunctions = new Set(functionKeys);
  const functionToUseCases = {};
  functionKeys.forEach(fn => {
    functionToUseCases[fn] = allNodes
      .filter(node => node.function === fn)
      .map(node => node.id)
      .sort((a, b) => a.localeCompare(b));
  });
  const implementedIds = new Set();
  const vetoIds = new Set();
  const implementedConnections = new Set();
  const visibleStatuses = new Set(['implemented', 'adjacent', 'vetoed', 'none']);
  let statusFilterCountEls = {};
  let selectedNode = null;

  let searchTerm   = '';

  function nodeStatus(d) {
    if (vetoIds.has(d.id)) return 'vetoed';
    if (implementedIds.has(d.id)) return 'implemented';
    if (implementedConnections.has(d.id)) return 'adjacent';
    return 'none';
  }

  function statusVisible(d) {
    if (selectedNode === d) return true;
    return visibleStatuses.has(nodeStatus(d));
  }

  function nodeColor(d) {
    if (!visibleFunctions.has(d.function)) return '#94a3b8';
    return functionColors[d.function] || '#94a3b8';
  }

  function nodeOpacity(d) {
    if (!visibleFunctions.has(d.function)) return 0;
    if (!statusVisible(d)) return 0;
    if (searchTerm) return d.id.toLowerCase().includes(searchTerm.toLowerCase()) ? 1 : 0.12;
    return 0.85;
  }

  function nodeStroke(d) {
    if (vetoIds.has(d.id)) return '#dc2626';
    if (selectedNode === d) return '#1a1a1a';
    if (implementedIds.has(d.id)) return '#16a34a';
    if (implementedConnections.has(d.id)) return '#f59e0b';
    return '#fff';
  }

  function nodeStrokeWidth(d) {
    if (vetoIds.has(d.id)) return 2.4;
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
    if (!statusVisible(src) || !statusVisible(tgt)) return 0;
    return 0.2;
  }

  function edgeVisible(d) {
    return edgeOpacity(d) > 0;
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

  function edgeLinePosition(d) {
    const sx = d.source.x;
    const sy = d.source.y;
    const tx = d.target.x;
    const ty = d.target.y;
    const dx = tx - sx;
    const dy = ty - sy;
    const len = Math.hypot(dx, dy) || 1;
    const nodeRadius = 5;
    const arrowPadding = 8;
    const shorten = nodeRadius + arrowPadding;
    return {
      x1: sx,
      y1: sy,
      x2: tx - (dx / len) * shorten,
      y2: ty - (dy / len) * shorten,
    };
  }

  svg.on('click', () => deselectNode());

  sim.on('tick', () => {
    link
      .attr('x1', d => edgeLinePosition(d).x1).attr('y1', d => edgeLinePosition(d).y1)
      .attr('x2', d => edgeLinePosition(d).x2).attr('y2', d => edgeLinePosition(d).y2);
    node.attr('cx', d => d.x).attr('cy', d => d.y);
    label.attr('x', d => d.x).attr('y', d => d.y);
  });

  function refresh() {
    node
      .attr('fill', nodeColor)
      .attr('fill-opacity', nodeOpacity)
      .attr('display', d => (visibleFunctions.has(d.function) && statusVisible(d)) ? null : 'none');
    node.attr('stroke', nodeStroke).attr('stroke-width', nodeStrokeWidth);
    link
      .attr('stroke-opacity', edgeOpacity)
      .attr('display', d => (edgeVisible(d) ? null : 'none'))
      .attr('marker-end', d => (edgeVisible(d) ? 'url(#edge-arrow)' : null));
    label.attr('opacity', d => {
      if (!visibleFunctions.has(d.function)) return 0;
      if (!statusVisible(d)) return 0;
      if (searchTerm) return d.id.toLowerCase().includes(searchTerm.toLowerCase()) ? 0.95 : 0.08;
      return 0.6;
    }).attr('display', d => (visibleFunctions.has(d.function) && statusVisible(d)) ? null : 'none');
    updateStatusCounts();
  }

  function statusCounts() {
    const counts = { implemented: 0, adjacent: 0, vetoed: 0, none: 0 };
    allNodes.forEach(n => {
      const status = nodeStatus(n);
      if (counts[status] !== undefined) counts[status] += 1;
    });
    return counts;
  }

  function updateStatusCounts() {
    const counts = statusCounts();
    Object.entries(statusFilterCountEls).forEach(([key, el]) => {
      if (!el) return;
      el.textContent = `(${counts[key] || 0})`;
    });
  }

  function setDetailOpen(isOpen) {
    if (!layout || !detailPane) return;
    layout.classList.toggle('detail-open', isOpen);
    detailPane.classList.toggle('open', isOpen);
    if (detailToggle) {
      detailToggle.textContent = isOpen ? '⟩' : '⟨';
      detailToggle.setAttribute('aria-expanded', String(isOpen));
    }
  }

  function selectNode(d) {
    selectedNode = d;
    setDetailOpen(true);
    label.attr('font-weight', n => n === d ? 600 : 400);
    refresh();
    renderDetail(d);
  }

  function deselectNode() {
    selectedNode = null;
    label.attr('font-weight', 400);
    refresh();
    setDetailOpen(false);
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

    syncUseCaseStatusCheckboxes();
    refresh();
  }

  function updateVetoHighlights(rawVeto) {
    vetoIds.clear();
    const byNormalisedId = {};
    allNodes.forEach(n => { byNormalisedId[normaliseId(n.id)] = n.id; });

    rawVeto.forEach(name => {
      const exact = byNormalisedId[normaliseId(name)];
      if (exact) vetoIds.add(exact);
    });

    syncUseCaseStatusCheckboxes();
    refresh();
  }

  function renderFunctionFilters() {
    if (!fnFilterList) return;
    fnFilterList.innerHTML = '';
    functionKeys.forEach(fn => {
      const wrapper = document.createElement('div');
      wrapper.className = 'function-filter-group';

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
      const swatch = document.createElement('span');
      swatch.className = 'filter-color-dot';
      swatch.style.backgroundColor = functionColors[fn] || '#94a3b8';
      labelEl.appendChild(checkbox);
      labelEl.appendChild(swatch);
      labelEl.appendChild(text);
      wrapper.appendChild(labelEl);

      const useCaseList = document.createElement('div');
      useCaseList.className = 'function-usecase-list';
      (functionToUseCases[fn] || []).forEach(useCaseId => {
        const row = document.createElement('div');
        row.className = 'function-usecase-row';

        const nameBtn = document.createElement('button');
        nameBtn.type = 'button';
        nameBtn.className = 'function-usecase-name';
        nameBtn.textContent = useCaseId;
        nameBtn.addEventListener('click', () => {
          const nodeData = nodeById[useCaseId];
          if (!nodeData) return;
          selectNode(nodeData);
          if (nodeData.x != null && nodeData.y != null) {
            const targetTransform = d3.zoomIdentity.translate(width / 2 - nodeData.x, height / 2 - nodeData.y).scale(1.8);
            svg.transition().duration(350).call(zoomBehavior.transform, targetTransform);
          }
        });

        const statuses = document.createElement('div');
        statuses.className = 'function-usecase-statuses';
        const statusOptions = [
          { key: 'none', label: 'No status', colorClass: 'status-none' },
          { key: 'implemented', label: 'Already implemented', colorClass: 'status-implemented' },
          { key: 'vetoed', label: 'Vetoed', colorClass: 'status-vetoed' },
        ];

        statusOptions.forEach((option) => {
          const statusLabel = document.createElement('label');
          statusLabel.className = `function-usecase-status ${option.colorClass}`;
          statusLabel.title = option.label;

          const statusCheckbox = document.createElement('input');
          statusCheckbox.type = 'checkbox';
          statusCheckbox.dataset.useCaseId = useCaseId;
          statusCheckbox.dataset.status = option.key;
          statusCheckbox.addEventListener('change', () => {
            const isChecked = statusCheckbox.checked;
            row.querySelectorAll('input[type="checkbox"]').forEach((box) => {
              box.checked = false;
            });

            if (!isChecked || option.key === 'none') {
              vetoIds.delete(useCaseId);
              implementedIds.delete(useCaseId);
            } else if (option.key === 'implemented') {
              implementedIds.add(useCaseId);
              vetoIds.delete(useCaseId);
            } else if (option.key === 'vetoed') {
              vetoIds.add(useCaseId);
              implementedIds.delete(useCaseId);
            }

            syncUseCaseStatusCheckboxes();
            updateAdjacentFromImplemented();
            refresh();
          });

          const marker = document.createElement('span');
          marker.className = 'status-marker';
          marker.textContent = option.key === 'none' ? '○' : '●';
          statusLabel.appendChild(statusCheckbox);
          statusLabel.appendChild(marker);
          statuses.appendChild(statusLabel);
        });

        row.appendChild(nameBtn);
        row.appendChild(statuses);
        useCaseList.appendChild(row);
      });
      wrapper.appendChild(useCaseList);
      fnFilterList.appendChild(wrapper);
    });

    syncUseCaseStatusCheckboxes();
  }

  function renderStatusFilters() {
    if (!statusFilterList) return;
    const statusOptions = [
      { key: 'implemented', label: 'Already implemented' },
      { key: 'adjacent', label: 'Adjacent' },
      { key: 'vetoed', label: 'Vetoed' },
      { key: 'none', label: 'No status' },
    ];

    statusFilterList.innerHTML = '';
    statusFilterCountEls = {};
    statusOptions.forEach(option => {
      const labelEl = document.createElement('label');
      labelEl.className = 'filter-item';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = true;
      checkbox.value = option.key;
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) visibleStatuses.add(option.key);
        else visibleStatuses.delete(option.key);
        refresh();
      });

      const text = document.createElement('span');
      text.textContent = option.label;
      labelEl.appendChild(checkbox);
      if (option.key !== 'none') {
        const swatch = document.createElement('span');
        swatch.className = 'filter-color-dot';
        if (option.key === 'implemented') swatch.style.backgroundColor = '#16a34a';
        if (option.key === 'adjacent') swatch.style.backgroundColor = '#f59e0b';
        if (option.key === 'vetoed') swatch.style.backgroundColor = '#dc2626';
        labelEl.appendChild(swatch);
      }
      labelEl.appendChild(text);
      const count = document.createElement('span');
      count.className = 'status-filter-count';
      count.textContent = '(0)';
      labelEl.appendChild(count);
      statusFilterCountEls[option.key] = count;
      statusFilterList.appendChild(labelEl);
    });
    updateStatusCounts();
  }

  function updateAdjacentFromImplemented() {
    implementedConnections.clear();
    allEdges.forEach(e => {
      const src = e.source.id || e.source;
      const tgt = e.target.id || e.target;
      if (implementedIds.has(src) && !implementedIds.has(tgt)) implementedConnections.add(tgt);
      if (implementedIds.has(tgt) && !implementedIds.has(src)) implementedConnections.add(src);
    });
  }

  function syncUseCaseStatusCheckboxes() {
    if (!fnFilterList) return;
    fnFilterList.querySelectorAll('.function-usecase-row').forEach(row => {
      const useCaseId = row.querySelector('input[type="checkbox"]')?.dataset.useCaseId;
      if (!useCaseId) return;

      let activeStatus = 'none';
      if (vetoIds.has(useCaseId)) activeStatus = 'vetoed';
      else if (implementedIds.has(useCaseId)) activeStatus = 'implemented';

      row.querySelectorAll('input[type="checkbox"]').forEach((box) => {
        box.checked = box.dataset.status === activeStatus;
      });
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

    const safeDescription = (d.description || '').trim() || '--';

    detail.innerHTML = `
      <h3>${d.id}</h3>
      <div class="nd-meta">
        <span>${d.function}</span>
        <span>${d.department}</span>
      </div>
      <div class="nd-rels">
        <h4>Description</h4>
        <div class="nd-scope" style="font-size:12px;line-height:1.45;color:var(--text);margin-left:0;">${safeDescription}</div>
      </div>
      ${out.length ? `<div class="nd-rels"><h4>Leads to (${out.length})</h4>${outHtml}${out.length > 8 ? `<div class="nd-scope" style="padding-top:4px">+${out.length - 8} more</div>` : ''}</div>` : ''}
      ${into.length ? `<div class="nd-rels"><h4>Comes from (${into.length})</h4>${inHtml}${into.length > 8 ? `<div class="nd-scope" style="padding-top:4px">+${into.length - 8} more</div>` : ''}</div>` : ''}
      ${!out.length && !into.length ? '<div class="nd-scope" style="padding-top:8px">No relationships defined</div>' : ''}
    `;
  }

  if (searchInput) searchInput.addEventListener('input', e => {
    searchTerm = e.target.value.trim();
    refresh();
    if (searchTerm) {
      const match = allNodes.find(n => n.id.toLowerCase().includes(searchTerm.toLowerCase()));
      if (match && match.x) {
        svg.transition().duration(400).call(zoomBehavior.transform, d3.zoomIdentity.translate(width / 2 - match.x, height / 2 - match.y).scale(1.8));
      }
    }
  });

  if (datasetSelect) {
    datasetSelect.addEventListener('change', e => {
      const selectedDataset = e.target.value;
      const url = new URL(window.location.href);
      if (selectedDataset) url.searchParams.set('dataset', selectedDataset);
      if (typeof SELECTED_DATASET !== 'undefined' && selectedDataset === SELECTED_DATASET) return;
      window.location.assign(url.toString());
    });
  }

  if (detailToggle && layout) {
    detailToggle.addEventListener('click', () => {
      const open = !layout.classList.contains('detail-open');
      setDetailOpen(open);
      setTimeout(() => {
        width  = svgEl.parentElement.clientWidth  || 800;
        height = svgEl.parentElement.clientHeight || 600;
        svg.attr('width', width).attr('height', height);
        functionCenters = computeFunctionCenters();
        sim.force('center', d3.forceCenter(width / 2, height / 2)).alpha(0.18).restart();
      }, 180);
    });
  }

  if (sideToggle && layout) {
    sideToggle.addEventListener('click', () => {
      const collapsed = layout.classList.toggle('side-collapsed');
      sideToggle.textContent = collapsed ? '⟨' : '⟩';
      sideToggle.setAttribute('aria-expanded', String(!collapsed));
      setTimeout(() => {
        width  = svgEl.parentElement.clientWidth  || 800;
        height = svgEl.parentElement.clientHeight || 600;
        svg.attr('width', width).attr('height', height);
        functionCenters = computeFunctionCenters();
        sim.force('center', d3.forceCenter(width / 2, height / 2)).alpha(0.18).restart();
      }, 180);
    });
  }

  window.addEventListener('resize', () => {
    width  = svgEl.parentElement.clientWidth  || 800;
    height = svgEl.parentElement.clientHeight || 600;
    svg.attr('width', width).attr('height', height);
    functionCenters = computeFunctionCenters();
    sim.force('center', d3.forceCenter(width / 2, height / 2)).alpha(0.1).restart();
  });

  document.addEventListener('tag-input-change', e => {
    if (!e.detail || !e.detail.listId) return;
    if (e.detail.listId === 'implemented-list') updateImplementedHighlights(e.detail.tags || []);
    if (e.detail.listId === 'veto-list') updateVetoHighlights(e.detail.tags || []);
  });

  renderFunctionFilters();
  renderStatusFilters();
  refresh();
  info.textContent = `${allNodes.length} use cases · ${allEdges.length} relationships · drag to pan · scroll to zoom · click a node`;
});
