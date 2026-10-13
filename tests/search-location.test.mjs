import test from 'node:test';
import assert from 'node:assert/strict';
import {readSearchLocation, writeSearchLocation} from '../app/script/search-location.ts';

test('search URLs survive reload and Back/Forward without losing edition or comparison', () => {
  for (const edition of ['original','all-ages']) {
    const base = new URL(`https://mao-tls.github.io/fate-stay-night/script/?script=0000&edition=${edition}${edition === 'original' ? '&compare=mirror-moon&errors=mirror-moon' : ''}`);
    const search = {scope:'corpus',query:'lightning 日本語',filter:'prologue'};
    const searchURL = writeSearchLocation(base, search);
    assert.deepEqual(readSearchLocation(searchURL), search);
    const contextURL = writeSearchLocation(base, {scope:'script',query:'',filter:'all'});
    contextURL.hash = 'page0';
    for (const url of [searchURL,contextURL,searchURL,contextURL]) {
      assert.equal(url.searchParams.get('edition'), edition);
      assert.equal(url.searchParams.get('compare'), edition === 'original' ? 'mirror-moon' : null);
      assert.deepEqual(readSearchLocation(url), url.hash ? {scope:'script',query:'',filter:'all'} : search);
    }
    assert.equal(contextURL.hash,'#page0');
  }
});

test('current-script search is shareable and a passage anchor opens its context', () => {
  const url = writeSearchLocation(new URL('https://example.test/script/?script=0000#page0'), {scope:'script',query:'moonlight',filter:'all'});
  assert.equal(url.hash,'');
  assert.deepEqual(readSearchLocation(url), {scope:'script',query:'moonlight',filter:'all'});
  url.hash = 'page2';
  assert.deepEqual(readSearchLocation(url), {scope:'script',query:'',filter:'all'});
});
