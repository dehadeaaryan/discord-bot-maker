import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ url }) => ({
  siteOrigin: url.origin,
  pageUrl: new URL(url.pathname, url.origin).href
});
