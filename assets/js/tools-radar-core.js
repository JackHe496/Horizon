(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.HorizonRadarCore = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  var STATUS_WEIGHT = {
    tried: 5,
    verified: 4,
    watch: 3,
    new: 2,
    rejected: 0
  };

  var PRICE_WEIGHT = {
    free: 4,
    freemium: 3,
    unknown: 2,
    paid: 1
  };

  function normalize(value) {
    return String(value || '')
      .normalize('NFKC')
      .toLocaleLowerCase()
      .replace(/\s+/g, ' ')
      .trim();
  }

  function searchText(tool) {
    return normalize([
      tool.name,
      tool.name_zh,
      tool.summary_zh,
      tool.use_case_zh,
      tool.category,
      tool.kind,
      (tool.tags || []).join(' '),
      (tool.aliases || []).join(' ')
    ].join(' '));
  }

  function matchesQuery(tool, query) {
    var terms = normalize(query).split(' ').filter(Boolean);
    if (!terms.length) return true;
    var haystack = searchText(tool);
    return terms.every(function (term) { return haystack.indexOf(term) !== -1; });
  }

  function numericSignal(tool) {
    return Object.keys(tool.community_signals || {}).reduce(function (total, key) {
      var value = tool.community_signals[key];
      return total + (typeof value === 'number' && Number.isFinite(value) ? value : 0);
    }, 0);
  }

  function filterTools(tools, state, favoriteIds) {
    state = state || {};
    favoriteIds = favoriteIds || [];
    return tools.filter(function (tool) {
      if (!matchesQuery(tool, state.query)) return false;
      if (state.category && tool.category !== state.category) return false;
      if (state.pricing && tool.pricing !== state.pricing) return false;
      if (state.status === 'recommended' && ['verified', 'tried'].indexOf(tool.status) === -1) return false;
      if (state.status && state.status !== 'recommended' && tool.status !== state.status) return false;
      if (state.favoritesOnly && favoriteIds.indexOf(tool.id) === -1) return false;
      if (!state.status && tool.status === 'rejected') return false;
      return true;
    });
  }

  function sortTools(tools, sort) {
    var result = tools.slice();
    result.sort(function (a, b) {
      if (sort === 'newest') {
        return Date.parse(b.updated_at || 0) - Date.parse(a.updated_at || 0) ||
          (b.score || 0) - (a.score || 0);
      }
      if (sort === 'community') {
        return numericSignal(b) - numericSignal(a) || (b.score || 0) - (a.score || 0);
      }
      if (sort === 'free') {
        return (PRICE_WEIGHT[b.pricing] || 0) - (PRICE_WEIGHT[a.pricing] || 0) ||
          (b.score || 0) - (a.score || 0);
      }
      if (sort === 'name') {
        return normalize(a.name_zh || a.name).localeCompare(normalize(b.name_zh || b.name), 'zh-CN');
      }
      return (STATUS_WEIGHT[b.status] || 0) - (STATUS_WEIGHT[a.status] || 0) ||
        (b.score || 0) - (a.score || 0) ||
        normalize(a.name).localeCompare(normalize(b.name));
    });
    return result;
  }

  function readFavorites(storage) {
    try {
      var parsed = JSON.parse(storage.getItem('horizon-tool-favorites-v1') || '[]');
      return Array.isArray(parsed) ? parsed.filter(function (item) {
        return typeof item === 'string';
      }) : [];
    } catch (error) {
      return [];
    }
  }

  function toggleFavorite(storage, id) {
    var favorites = readFavorites(storage);
    var index = favorites.indexOf(id);
    if (index === -1) favorites.push(id);
    else favorites.splice(index, 1);
    try {
      storage.setItem('horizon-tool-favorites-v1', JSON.stringify(favorites));
    } catch (error) {
      return favorites;
    }
    return favorites;
  }

  function safeHttpsUrl(value) {
    try {
      var parsed = new URL(value);
      return parsed.protocol === 'https:' && !parsed.username && !parsed.password ? parsed.href : '';
    } catch (error) {
      return '';
    }
  }

  return {
    filterTools: filterTools,
    matchesQuery: matchesQuery,
    normalize: normalize,
    numericSignal: numericSignal,
    readFavorites: readFavorites,
    safeHttpsUrl: safeHttpsUrl,
    sortTools: sortTools,
    toggleFavorite: toggleFavorite
  };
});
