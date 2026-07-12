# DevToolCompare — Operator Manual

Automated dev tool comparison site with AI-powered draft generation and manual approval dashboard.

## Architecture

```
[Hermes Cron] ────► src/content/drafts/ ──► [Admin Dashboard] ──► src/content/articles/ ──► [Astro Build] ──► [Cloudflare Pages]
     │                      │                        │                        │
     │              Pending review              Approve/Reject            Auto-published
  Mon/Wed/Fri           buttons                                            
```

- **Cron job** writes drafts to `src/content/drafts/`
- **Dashboard** (`:3001`) lists pending drafts for your review
- **Approve** moves draft → `articles/`, git push → Cloudflare auto-deploys
- **Reject** moves to `src/content/rejected/`

## Quick Start

```bash
# Start both dev server + admin dashboard
bash dev.sh

# Or individually:
npx astro dev                                # Site: http://localhost:4321
.venv/bin/python admin/app.py                # Admin: http://127.0.0.1:3001
```

## Admin Dashboard

Open `http://127.0.0.1:3001` to see pending drafts.

Each draft card shows:
- Category + word count + creation time
- Title + description + tags
- Collapsible content preview
- **Approve & Publish** — moves to articles/ and deploys
- **Reject** or **Reject with reason** — moves to rejected/

After approval, the article is committed + pushed to GitHub. Cloudflare Pages auto-deploys within seconds.

## Content Pipeline

### Auto-generation (cron)

Schedule: **Mon / Wed / Fri at 8:00 AM**

The cron job researches trending dev tool topics, writes a 1000-1500 word comparison, and saves it as a draft. You review and approve on the dashboard.

Cron management:
```bash
hermes cron list                           # Check status
hermes cron update --job-id <id>           # Modify schedule
hermes cron run --job-id <id>              # Run immediately
hermes cron pause --job-id <id>            # Pause generation
hermes cron remove --job-id <id>           # Remove
```

### Draft format

Drafts are markdown with frontmatter:

```yaml
---
title: "ToolA vs ToolB vs ToolC: Comparison (2026)"
description: "Meta description for SEO, 150-160 chars."
pubDate: 2026-07-11
category: "DevOps & Monitoring"
tags: ["tool-a", "tool-b", "tool-c", "category"]
comparedTools: ["ToolA", "ToolB", "ToolC"]
featured: false
---

Content here...
```

### Adding drafts manually

Write a markdown file to `src/content/drafts/` with valid frontmatter. It appears on the dashboard immediately.

### Publishing manually (via terminal)

```bash
# Quick publish
mv src/content/drafts/my-draft.md src/content/articles/
git add -A && git commit -m "publish: my-draft"
git push
```

## Site Structure

```
src/
├── content.config.ts        # Astro v7 content collections config
├── content/
│   ├── articles/            # Published articles (public site)
│   ├── drafts/              # Pending review (dashboard only)
│   └── rejected/            # Rejected drafts (reference)
├── layouts/
│   ├── BaseLayout.astro     # Global layout: dark theme, nav, footer
│   └── ArticleLayout.astro  # Article page: breadcrumb, metadata, affiliate disclosure
├── pages/
│   ├── index.astro          # Homepage: featured + latest
│   ├── blog.astro           # Article listing with category filters
│   ├── article/[slug].astro # Per-article static page
│   ├── about.astro          # About + affiliate disclosure
│   └── rss.xml.js           # RSS feed (auto-discovers new articles)
└── styles/
    └── global.css           # Tailwind + custom article/component styles

admin/
├── app.py                   # FastAPI dashboard server (port 3001)
├── static/admin.css         # Dashboard dark theme
└── templates/dashboard.html # Dashboard template (Jinja2)
```

## Deployment (one-time setup)

### 1. GitHub
```bash
# Create repo on github.com first, then:
git remote add origin git@github.com:YOUR_USER/devtoolcompare.git
git branch -M main
git push -u origin main
```

### 2. Cloudflare Pages
1. Go to Cloudflare Dashboard → Pages → Create a project
2. Connect your GitHub repo
3. Build settings:
   - Framework preset: **Astro**
   - Build command: `npm run build`
   - Build output: `dist`
4. Deploy

### 3. Domain (optional)
Add a custom domain in Cloudflare Pages settings. Update `astro.config.mjs`:
```js
site: 'https://yourdomain.com',
```

Re-run cloudflare pages or update env variable.

## Affiliate Programs to Join

| Program | Commission | URL |
|---------|-----------|-----|
| Vercel | 30% recurring (1st yr) | vercel.com/affiliates |
| Supabase | 20% recurring | supabase.com/partners |
| DigitalOcean | $100/sale | digitalocean.com/affiliates |
| Semrush | $200/sale | impact.com |
| ShareASale | General SaaS | shareasale.com |
| Impact | General SaaS | impact.com |

Embed affiliate links in articles using the disclosure box pattern:
```html
<div class="affiliate-box">
**Recommended:** [Try ToolName](https://affiliate.link) 
</div>
```

## Build & Deploy Commands

```bash
npm run build                # Build site to dist/
npm run dev                  # Dev server at :4321
npm run preview              # Preview production build
```

## Adding new content types

1. Create a new Astro page in `src/pages/`
2. Add styles to `src/styles/global.css`
3. Rebuild

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dashboard won't start | `lsof -ti:3001 \| xargs kill` then restart |
| Build fails "module not found" | Check import paths use correct depth `../../` from nested pages |
| Content not rendering | Verify `render()` is imported from `astro:content` (not called on entry directly) |
| Cron not firing | `hermes cron list` to check status; `hermes cron run --job-id <id>` to test |
| Affiliate links not working | Check disclosure is in article layout, links use `rel="nofollow"` |
| Draft not appearing on dashboard | Check file is `.md` with valid frontmatter, no `---` syntax errors |
| Python 3.14 / Jinja2 issues | Make sure `.venv` is active. `pip install "jinja2<3.1.6" "starlette<1.3"` if needed |

## Files to know

```
devtoolcompare/
├── README.md                 ← This file
├── dev.sh                    ← Launch dev + dashboard together
├── admin/start.sh            ← Launch dashboard only
├── admin/app.py              ← Dashboard server
├── src/content.config.ts     ← Content collection schema
├── astro.config.mjs          ← Astro config (site URL, integrations)
└── .venv/                    ← Python venv for dashboard
```