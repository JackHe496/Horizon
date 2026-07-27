(function () {
  'use strict';

  var core = window.HorizonRadarCore;
  var root = document.querySelector('[data-radar-mode]');
  if (!core || !root) return;

  var mode = root.getAttribute('data-radar-mode');
  var dataBase = root.getAttribute('data-data-base') || '/assets/data';
  var favorites = core.readFavorites(window.localStorage);
  var allTools = [];

  var LABELS = {
    categories: {
      'ai-coding': 'AI 编程',
      'codex-ecosystem': 'Skills / Plugins / MCP',
      'productivity-learning': '效率与学习',
      'agents-automation': 'Agents / 自动化',
      'search-research': '搜索与研究',
      'data-analysis': '数据分析',
      other: '其他'
    },
    pricing: {
      free: '免费',
      freemium: '免费增值',
      paid: '付费',
      unknown: '价格待核'
    },
    maturity: {
      experimental: '实验',
      beta: 'Beta',
      stable: '稳定',
      mature: '成熟',
      unknown: '待核'
    },
    maintenance: {
      active: '活跃维护',
      maintained: '维护中',
      stale: '低活跃',
      archived: '已归档',
      unknown: '待核'
    },
    risk: {
      none: '无',
      low: '低',
      medium: '中',
      high: '高',
      critical: '极高'
    }
  };

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text !== 'undefined') node.textContent = text;
    return node;
  }

  function safeLink(url, text, className) {
    var href = core.safeHttpsUrl(url);
    if (!href) return element('span', className || '', text);
    var link = element('a', className || '', text);
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    return link;
  }

  function favoriteButton(tool) {
    var button = element('button', 'favorite-button', favorites.indexOf(tool.id) !== -1 ? '★' : '☆');
    button.type = 'button';
    button.setAttribute('aria-label', favorites.indexOf(tool.id) !== -1 ? '取消收藏' : '收藏');
    if (favorites.indexOf(tool.id) !== -1) button.classList.add('is-favorite');
    button.addEventListener('click', function () {
      favorites = core.toggleFavorite(window.localStorage, tool.id);
      renderCurrent();
    });
    return button;
  }

  function installDetails(tool) {
    var details = element('details', '');
    var summary = element('summary', '', '安装、兼容性、风险与证据');
    details.appendChild(summary);
    var body = element('div', 'tool-details');

    var useCase = element('p', '');
    useCase.appendChild(element('strong', '', '用途：'));
    useCase.appendChild(document.createTextNode(tool.use_case_zh || '待补充'));
    body.appendChild(useCase);

    if (tool.install && tool.install.command) {
      var installBox = element('div', 'install-box');
      installBox.appendChild(element('code', '', tool.install.command));
      var copy = element('button', 'copy-button', '只复制');
      copy.type = 'button';
      copy.setAttribute('aria-label', '复制安装命令，不执行');
      copy.addEventListener('click', function () {
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
          copy.textContent = '请手动复制';
          return;
        }
        navigator.clipboard.writeText(tool.install.command).then(function () {
          copy.textContent = '已复制';
          window.setTimeout(function () { copy.textContent = '只复制'; }, 1500);
        }).catch(function () {
          copy.textContent = '复制失败';
        });
      });
      installBox.appendChild(copy);
      body.appendChild(installBox);
    }

    if (tool.install && tool.install.note_zh) {
      body.appendChild(element('p', '', tool.install.note_zh));
    }
    var risk = element('p', 'risk-line');
    risk.appendChild(element('strong', '', '权限风险 ' + (LABELS.risk[tool.permission_risk] || tool.permission_risk) + '：'));
    risk.appendChild(document.createTextNode(tool.risk_note_zh || '安装前核查权限。'));
    body.appendChild(risk);

    var compatibility = (tool.compatibility || []).join(' · ');
    if (compatibility) {
      var compatible = element('p', '');
      compatible.appendChild(element('strong', '', '兼容：'));
      compatible.appendChild(document.createTextNode(compatibility));
      body.appendChild(compatible);
    }

    var evidenceList = element('ul', 'evidence-list');
    (tool.evidence || []).forEach(function (evidence) {
      var item = element('li', '');
      item.appendChild(safeLink(evidence.url, evidence.source_name || evidence.source_id));
      if (evidence.excerpt) item.appendChild(document.createTextNode(' · ' + evidence.excerpt));
      evidenceList.appendChild(item);
    });
    if (evidenceList.children.length) body.appendChild(evidenceList);
    details.appendChild(body);
    return details;
  }

  function toolCard(tool) {
    var card = element('article', 'tool-card');
    card.setAttribute('data-tool-id', tool.id);

    var top = element('div', 'tool-card__top');
    top.appendChild(element('span', 'status-badge status-badge--' + tool.status, tool.status));
    top.appendChild(element('span', 'price-badge', LABELS.pricing[tool.pricing] || tool.pricing));
    top.appendChild(favoriteButton(tool));
    card.appendChild(top);

    var heading = element('h3', '');
    heading.appendChild(safeLink(tool.homepage, tool.name_zh || tool.name));
    card.appendChild(heading);
    if (tool.name_zh && core.normalize(tool.name_zh) !== core.normalize(tool.name)) {
      card.appendChild(element('p', 'tool-card__english', tool.name));
    }
    card.appendChild(element('p', 'tool-card__summary', tool.summary_zh));

    var tags = element('div', 'tool-tags');
    [LABELS.categories[tool.category] || tool.category, tool.kind].concat(tool.tags || []).slice(0, 4)
      .forEach(function (tag) { if (tag) tags.appendChild(element('span', '', tag)); });
    card.appendChild(tags);

    var meta = element('div', 'tool-meta');
    var maturity = element('span', '', 'MATURITY');
    maturity.appendChild(element('strong', '', LABELS.maturity[tool.maturity] || tool.maturity));
    meta.appendChild(maturity);
    var maintenance = element('span', '', 'MAINTENANCE');
    maintenance.appendChild(element('strong', '', LABELS.maintenance[tool.maintenance] || tool.maintenance));
    meta.appendChild(maintenance);
    var sources = element('span', '', 'EVIDENCE');
    sources.appendChild(element('strong', '', String(tool.source_count || (tool.evidence || []).length) + ' 个来源'));
    meta.appendChild(sources);
    var risk = element('span', '', 'RISK');
    risk.appendChild(element('strong', '', LABELS.risk[tool.permission_risk] || tool.permission_risk));
    meta.appendChild(risk);
    card.appendChild(meta);
    card.appendChild(installDetails(tool));
    return card;
  }

  function renderList(container, tools) {
    container.replaceChildren();
    tools.forEach(function (tool) { container.appendChild(toolCard(tool)); });
  }

  function updateTimestamp(generatedAt) {
    document.querySelectorAll('[data-radar-updated]').forEach(function (node) {
      var date = new Date(generatedAt);
      node.textContent = Number.isNaN(date.getTime())
        ? '数据更新时间待核'
        : 'DATA UPDATED · ' + date.toLocaleString('zh-CN', { hour12: false });
    });
  }

  function renderDirectory() {
    var query = document.getElementById('radar-search').value;
    var category = document.getElementById('radar-category').value;
    var status = document.getElementById('radar-status').value;
    var pricing = document.getElementById('radar-pricing').value;
    var sort = document.getElementById('radar-sort').value;
    var filtered = core.filterTools(allTools, {
      query: query,
      category: category,
      status: status,
      pricing: pricing
    }, favorites);
    filtered = core.sortTools(filtered, sort);
    renderList(document.querySelector('[data-radar-list="directory"]'), filtered);
    document.getElementById('radar-count').textContent = 'SHOWING ' + filtered.length + ' / ' + allTools.length + ' TOOLS';
  }

  function renderFavorites() {
    var tools = allTools.filter(function (tool) { return favorites.indexOf(tool.id) !== -1; });
    renderList(document.querySelector('[data-radar-list="favorites"]'), core.sortTools(tools, 'recommended'));
    document.querySelector('[data-radar-empty]').hidden = tools.length !== 0;
  }

  function renderCurrent() {
    if (mode === 'directory') renderDirectory();
    if (mode === 'favorites') renderFavorites();
    if (mode === 'daily' || mode === 'weekly') {
      renderList(document.querySelector('[data-radar-list="' + mode + '"]'), allTools);
    }
    if (mode === 'home') {
      document.querySelectorAll('[data-radar-list]').forEach(function (container) {
        var listMode = container.getAttribute('data-radar-list');
        var tools = container.__radarTools || [];
        renderList(container, tools);
      });
    }
  }

  function setupDirectory() {
    var params = new URLSearchParams(window.location.search);
    ['category', 'status', 'pricing'].forEach(function (key) {
      var value = params.get(key);
      var control = document.getElementById('radar-' + key);
      if (value && control && Array.from(control.options).some(function (option) { return option.value === value; })) {
        control.value = value;
      }
    });
    ['radar-search', 'radar-category', 'radar-status', 'radar-pricing', 'radar-sort']
      .forEach(function (id) {
        document.getElementById(id).addEventListener('input', renderDirectory);
      });
    document.getElementById('radar-clear').addEventListener('click', function () {
      document.getElementById('radar-search').value = '';
      document.getElementById('radar-category').value = '';
      document.getElementById('radar-status').value = '';
      document.getElementById('radar-pricing').value = '';
      document.getElementById('radar-sort').value = 'recommended';
      renderDirectory();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === '/' && document.activeElement.tagName !== 'INPUT') {
        event.preventDefault();
        document.getElementById('radar-search').focus();
      }
    });
  }

  function fetchJson(name) {
    return fetch(dataBase.replace(/\/$/, '') + '/' + name + '.json', {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' }
    }).then(function (response) {
      if (!response.ok) throw new Error('Radar data unavailable');
      return response.json();
    });
  }

  function showError() {
    root.querySelectorAll('[data-radar-list]').forEach(function (container) {
      container.replaceChildren(element('p', 'notice', '工具数据暂时不可用，请稍后刷新。原日报不受影响。'));
    });
    document.querySelectorAll('[data-radar-updated]').forEach(function (node) {
      node.textContent = 'DATA UNAVAILABLE';
    });
  }

  if (mode === 'home') {
    Promise.all([fetchJson('tools'), fetchJson('daily'), fetchJson('weekly')])
      .then(function (payloads) {
        var catalog = payloads[0];
        var daily = payloads[1];
        var weekly = payloads[2];
        document.getElementById('stat-tools').textContent = catalog.stats.tool_count;
        document.getElementById('stat-verified').textContent = catalog.stats.verified_count;
        var freePercent = catalog.stats.tool_count
          ? Math.round(catalog.stats.free_first_count / catalog.stats.tool_count * 100)
          : 0;
        document.getElementById('stat-free').textContent = freePercent + '%';
        document.getElementById('stat-sources').textContent = catalog.stats.source_count;
        document.querySelector('[data-radar-list="daily"]').__radarTools = daily.tools;
        document.querySelector('[data-radar-list="weekly"]').__radarTools = weekly.tools;
        updateTimestamp(catalog.generated_at);
        renderCurrent();
      })
      .catch(showError);
  } else {
    var dataName = mode === 'daily' || mode === 'weekly' ? mode : 'tools';
    fetchJson(dataName).then(function (payload) {
      allTools = payload.tools || [];
      updateTimestamp(payload.generated_at);
      if (mode === 'directory') setupDirectory();
      renderCurrent();
    }).catch(showError);
  }
})();
