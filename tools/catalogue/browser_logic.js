/* Shared browser filtering/pagination rules, also exercised by Node tests. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CatalogueView = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function matches(row, filters) {
    const query = (filters.query || '').trim().toLowerCase();
    const searchable = row.search || [row.description, row.path, row.category, row.subcategory, row.catid].join(' ').toLowerCase();
    return (!filters.category || (row.category || 'Unclassified') === filters.category)
      && (!filters.library || row.library === filters.library)
      && (!filters.status || row.classification_status === filters.status)
      && (!filters.leaf || row.catid === filters.leaf)
      && (!filters.content || (row.content || 'unknown') === filters.content)
      && (!filters.trait || (row.acoustic_traits || []).includes(filters.trait))
      && (!filters.length || (row.duration != null && (filters.length === 'short' ? row.duration <= 6 : row.duration > 6)))
      && (!query || searchable.includes(query));
  }
  function deduplicate(input, showDuplicates) {
    if (showDuplicates) return input;
    const representatives = new Map();
    for (const row of input) {
      const key = row.duplicate_of || row.path;
      if (!representatives.has(key) || !row.duplicate_of) representatives.set(key, row.path);
    }
    return input.filter(row => representatives.get(row.duplicate_of || row.path) === row.path);
  }
  function filterRows(rows, filters) {
    return deduplicate(rows.filter(row => matches(row, filters)), filters.showDuplicates);
  }
  function categoryCounts(rows, filters) {
    // Only the category itself is ignored so the sidebar can show alternatives.
    // Every visible additional filter, including subcategory, affects counts.
    const context = {...filters, category: ''};
    const groups = new Map();
    for (const row of rows) {
      if (!matches(row, context)) continue;
      const category = row.category || 'Unclassified';
      if (!groups.has(category)) groups.set(category, new Set());
      groups.get(category).add(filters.showDuplicates ? row.path : row.duplicate_of || row.path);
    }
    return new Map([...groups].map(([name, paths]) => [name, paths.size]));
  }
  function paginate(rows, requestedPage, pageSize = 50) {
    if (!Number.isInteger(pageSize) || pageSize < 1) throw new Error('Invalid page size');
    const totalPages = Math.ceil(rows.length / pageSize);
    const page = Math.max(0, Math.min(Number.isFinite(requestedPage) ? Math.floor(requestedPage) : 0, Math.max(0, totalPages - 1)));
    const start = page * pageSize;
    return {page, totalPages, total: rows.length, first: rows.length ? start + 1 : 0,
      last: Math.min(start + pageSize, rows.length), items: rows.slice(start, start + pageSize),
      canPrevious: page > 0, canNext: page + 1 < totalPages};
  }
  return {matches, deduplicate, filterRows, categoryCounts, paginate};
});
