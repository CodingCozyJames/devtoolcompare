import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

BASE = Path(__file__).resolve().parent.parent
DRAFTS = BASE / "src" / "content" / "drafts"
ARTICLES = BASE / "src" / "content" / "articles"
REJECTED = BASE / "src" / "content" / "rejected"

app = FastAPI(title="DevToolCompare Admin")
app.mount("/static", StaticFiles(directory=BASE / "admin" / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "admin" / "templates")
templates.env.cache = None


def parse_frontmatter(text: str) -> dict:
    data = {}
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        end = 1
        while end < len(lines) and lines[end].strip() != "---":
            line = lines[end]
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("[") and val.endswith("]"):
                    inner = val[1:-1].strip()
                    val = [v.strip().strip('"').strip("'") for v in inner.split(",")] if inner else []
                elif val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                data[key] = val
            end += 1
    return data


def read_draft_file(path: Path) -> dict:
    text = path.read_text()
    meta = parse_frontmatter(text)
    body = text.split("---", 2)[-1].strip() if text.count("---") >= 2 else text
    return {"text": text, "meta": meta, "body": body}


def get_drafts():
    drafts = []
    if not DRAFTS.exists():
        return drafts
    for f in sorted(DRAFTS.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        info = read_draft_file(f)
        wc = len(info["body"].split())
        drafts.append({
            "filename": f.name,
            "slug": f.stem,
            "title": info["meta"].get("title", f.stem),
            "description": info["meta"].get("description", ""),
            "category": info["meta"].get("category", "Uncategorized"),
            "tags": info["meta"].get("tags", []),
            "compared_tools": info["meta"].get("comparedTools", []),
            "word_count": wc,
            "reading_time": max(1, round(wc / 200)),
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d, %Y %H:%M"),
            "created_ts": f.stat().st_mtime,
            "preview": info["body"][:500].strip(),
            "full_body": info["body"],
        })
    return drafts


def get_rejected():
    items = []
    if not REJECTED.exists():
        return items
    for f in sorted(REJECTED.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        info = read_draft_file(f)
        reason = ""
        if info["body"].endswith(">"):
            pass
        lines = info["body"].split("\n")
        for l in reversed(lines):
            if l.strip().startswith("> **Rejection reason:**"):
                reason = l.strip().replace("> **Rejection reason:** ", "")
                break
        items.append({
            "filename": f.name,
            "title": info["meta"].get("title", f.stem),
            "category": info["meta"].get("category", "Uncategorized"),
            "reason": reason,
            "rejected": datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d, %Y %H:%M"),
        })
    return items


def get_published():
    if not ARTICLES.exists():
        return []
    cats = {}
    for f in ARTICLES.glob("*.md"):
        info = read_draft_file(f)
        cat = info["meta"].get("category", "Uncategorized")
        cats[cat] = cats.get(cat, 0) + 1
    return {"total": sum(cats.values()), "by_category": cats}


def git_commit(message: str):
    try:
        subprocess.run(["git", "add", "-A"], cwd=BASE, capture_output=True, timeout=30)
        r = subprocess.run(["git", "commit", "-m", message], cwd=BASE, capture_output=True, timeout=30)
        return True, r.returncode  # True = ran without error, 0 = had something to commit
    except Exception as e:
        return False, str(e)


def redirect_with_message(url: str, msg: str, level: str = "success"):
    return RedirectResponse(url=f"{url}?msg={msg}&level={level}", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, msg: str = "", level: str = "success"):
    drafts = get_drafts()
    rejected = get_rejected()
    published = get_published()
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "drafts": drafts,
        "rejected": rejected,
        "published": published,
        "draft_count": len(drafts),
        "flash": {"msg": msg, "level": level} if msg else None,
    })


@app.post("/approve/{filename}")
async def approve(filename: str):
    src = DRAFTS / filename
    if not src.exists():
        return redirect_with_message("/", f"Draft {filename} not found", "error")
    dst = ARTICLES / filename
    shutil.move(str(src), str(dst))
    ok, code = git_commit(f"publish: {filename}")
    if ok:
        return redirect_with_message("/", f"✅ Published: {filename}")
    return redirect_with_message("/", f"✅ Published (git skipped — {code})", "warning")


@app.post("/reject/{filename}")
async def reject(filename: str):
    src = DRAFTS / filename
    if not src.exists():
        return redirect_with_message("/", f"Draft {filename} not found", "error")
    dst = REJECTED / filename
    shutil.move(str(src), str(dst))
    return redirect_with_message("/", f"Rejected: {filename}", "info")


@app.post("/reject-with-reason/{filename}")
async def reject_with_reason(filename: str, reason: str = Form(...)):
    src = DRAFTS / filename
    if not src.exists():
        return redirect_with_message("/", f"Draft {filename} not found", "error")
    text = src.read_text()
    text += f"\n\n> **Rejection reason:** {reason}\n"
    dst = REJECTED / filename
    dst.write_text(text)
    src.unlink()
    return redirect_with_message("/", f"Rejected: {filename} — \"{reason}\"", "info")


@app.post("/restore/{filename}")
async def restore(filename: str):
    src = REJECTED / filename
    if not src.exists():
        return redirect_with_message("/", f"Rejected item {filename} not found", "error")
    dst = DRAFTS / filename
    # Strip rejection note if present
    text = src.read_text()
    lines = text.split("\n")
    clean = [l for l in lines if not l.strip().startswith("> **Rejection reason:")]
    dst.write_text("\n".join(clean))
    src.unlink()
    return redirect_with_message("/", f"Restored: {filename}")


@app.get("/api/drafts")
async def api_drafts():
    return get_drafts()


@app.get("/preview/{filename}")
async def preview(filename: str):
    src = DRAFTS / filename
    if not src.exists():
        return HTMLResponse("Not found", status_code=404)
    info = read_draft_file(src)
    meta = info["meta"]
    html = f"""<article class="preview-article">
      <div class="preview-meta">
        <span class="preview-cat">{meta.get("category", "")}</span>
        <span class="preview-date">{datetime.fromtimestamp(src.stat().st_mtime).strftime("%b %d, %Y")}</span>
      </div>
      <h1 class="preview-title">{meta.get("title", src.stem)}</h1>
      <p class="preview-desc">{meta.get("description", "")}</p>
      <div class="preview-body">{info["body"]}</div>
    </article>"""
    return HTMLResponse(html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3001)