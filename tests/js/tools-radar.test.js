'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../../docs/assets/js/tools-radar-core.js');

const tools = [
  {
    id: 'codex-1',
    name: 'Codex CLI',
    name_zh: 'Codex 命令行',
    summary_zh: 'AI 编程 Agent',
    use_case_zh: '修改代码',
    category: 'ai-coding',
    kind: 'cli',
    pricing: 'freemium',
    status: 'verified',
    score: 95,
    tags: ['OpenAI'],
    aliases: ['codex'],
    community_signals: { stars: 1000 },
    updated_at: '2026-07-26T00:00:00Z'
  },
  {
    id: 'mcp-1',
    name: 'Search MCP',
    name_zh: '搜索 MCP',
    summary_zh: '检索研究资料',
    use_case_zh: '搜索论文',
    category: 'search-research',
    kind: 'mcp',
    pricing: 'free',
    status: 'watch',
    score: 70,
    tags: ['MCP'],
    aliases: [],
    community_signals: { mentions: 20 },
    updated_at: '2026-07-27T00:00:00Z'
  },
  {
    id: 'bad-1',
    name: 'Rejected Tool',
    name_zh: '已拒绝工具',
    summary_zh: '不展示',
    category: 'other',
    kind: 'app',
    pricing: 'unknown',
    status: 'rejected',
    score: -100,
    tags: [],
    aliases: [],
    community_signals: {},
    updated_at: '2026-07-20T00:00:00Z'
  }
];

test('Chinese and English search terms match the same tool', () => {
  assert.equal(core.matchesQuery(tools[0], '编程'), true);
  assert.equal(core.matchesQuery(tools[0], 'codex openai'), true);
  assert.equal(core.matchesQuery(tools[0], '物理'), false);
});

test('default filter hides rejected tools and supports verified grouping', () => {
  assert.deepEqual(core.filterTools(tools, {}, []).map((tool) => tool.id), ['codex-1', 'mcp-1']);
  assert.deepEqual(
    core.filterTools(tools, { status: 'recommended' }, []).map((tool) => tool.id),
    ['codex-1']
  );
  assert.deepEqual(
    core.filterTools(tools, { status: 'rejected' }, []).map((tool) => tool.id),
    ['bad-1']
  );
});

test('sort modes prioritize verified, newest, community, and free as requested', () => {
  assert.equal(core.sortTools(tools.slice(0, 2), 'recommended')[0].id, 'codex-1');
  assert.equal(core.sortTools(tools.slice(0, 2), 'newest')[0].id, 'mcp-1');
  assert.equal(core.sortTools(tools.slice(0, 2), 'community')[0].id, 'codex-1');
  assert.equal(core.sortTools(tools.slice(0, 2), 'free')[0].id, 'mcp-1');
});

test('favorites persist locally and tolerate invalid storage data', () => {
  const values = new Map();
  const storage = {
    getItem: (key) => values.get(key),
    setItem: (key, value) => values.set(key, value)
  };
  assert.deepEqual(core.toggleFavorite(storage, 'codex-1'), ['codex-1']);
  assert.deepEqual(core.readFavorites(storage), ['codex-1']);
  assert.deepEqual(core.toggleFavorite(storage, 'codex-1'), []);
  values.set('horizon-tool-favorites-v1', '{bad');
  assert.deepEqual(core.readFavorites(storage), []);
});

test('only credential-free HTTPS links are accepted by the renderer', () => {
  assert.ok(core.safeHttpsUrl('https://example.com/tool'));
  assert.equal(core.safeHttpsUrl('http://example.com/tool'), '');
  assert.equal(core.safeHttpsUrl('javascript:alert(1)'), '');
  assert.equal(core.safeHttpsUrl('https://user:secret@example.com/tool'), '');
});
