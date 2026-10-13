export type SearchLocation = { scope: 'script' | 'corpus'; query: string; filter: string };

export function readSearchLocation(url: URL): SearchLocation {
  return {
    scope: !url.hash && ['all', 'corpus'].includes(url.searchParams.get('scope') ?? '') ? 'corpus' : 'script',
    query: url.hash ? '' : url.searchParams.get('q') ?? '',
    filter: url.searchParams.get('filter') ?? 'all',
  };
}

export function writeSearchLocation(url: URL, state: SearchLocation): URL {
  const next = new URL(url);
  if (state.scope === 'corpus') next.searchParams.set('scope', 'all');
  else next.searchParams.delete('scope');
  if (state.query) next.searchParams.set('q', state.query);
  else next.searchParams.delete('q');
  if (state.scope === 'corpus' && state.filter !== 'all') next.searchParams.set('filter', state.filter);
  else next.searchParams.delete('filter');
  if (state.scope === 'corpus' || state.query) next.hash = '';
  return next;
}
