export function fuzzyScore(query: string, value: string) {
  const needle = query.trim().toLocaleLowerCase().replace(/\s+/g, "");
  const haystack = value.toLocaleLowerCase().replace(/\s+/g, "");
  if (!needle) return 1;
  if (haystack.includes(needle)) return 3 + needle.length / Math.max(1, haystack.length);
  const common = [...new Set(needle)].filter(char => haystack.includes(char)).length;
  return common / Math.max(new Set(needle).size, new Set(haystack).size, 1);
}

export function fuzzyRows<T>(rows: T[], query: string, label: (item: T) => string, limit = 20) {
  return rows.map(item => ({ item, score: fuzzyScore(query, label(item)) }))
    .filter(row => !query.trim() || row.score >= 0.35)
    .sort((left, right) => right.score - left.score || label(left.item).localeCompare(label(right.item)))
    .slice(0, limit).map(row => row.item);
}
