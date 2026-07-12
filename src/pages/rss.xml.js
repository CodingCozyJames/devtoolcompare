import { getCollection } from 'astro:content';

export async function GET(context) {
  const articles = await getCollection('articles');
  const site = context.site || 'https://devtoolcompare.com';
  const items = articles
    .sort((a, b) => b.data.pubDate.getTime() - a.data.pubDate.getTime())
    .map(
      (a) => `
    <item>
      <title><![CDATA[${a.data.title}]]></title>
      <description><![CDATA[${a.data.description}]]></description>
      <link>${site}/article/${a.id}/</link>
      <guid>${site}/article/${a.id}/</guid>
      <pubDate>${a.data.pubDate.toUTCString()}</pubDate>
      ${a.data.tags.map((t) => `<category>${t}</category>`).join('\n      ')}
    </item>`
    )
    .join('\n');

  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>DevToolCompare</title>
    <description>Honest developer tool & SaaS comparisons</description>
    <link>${site}</link>
    <atom:link href="${site}/rss.xml" rel="self" type="application/rss+xml"/>
    <language>en-us</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>${items}
  </channel>
</rss>`,
    {
      headers: { 'Content-Type': 'application/xml; charset=utf-8' },
    }
  );
}