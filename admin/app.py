import subprocess
import shutil
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
# Disable template cache for compatibility with Jinja2 3.1.6
templates.env.cache = None

def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown as a simple dict."""
    data = {}
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        end = 1
        while end < len(lines) and lines[end].strip() != "---":
            line = lines[end]
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if val.startswith("[") and val.endswith("]"):
                    val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
                data[key] = val
            end += 1
    return data

def get_drafts():
    """Return list of draft files with metadata."""
    drafts = []
    if not DRAFTS.exists():
        return drafts
    for f in sorted(DRAFTS.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = f.read_text()
        meta = parse_frontmatter(text)
        content_body = text.split("---", 2)[-1].strip() if text.count("---") >= 2 else text
        word_count = len(content_body.split())
        drafts.append({
            "filename": f.name,
            "slug": f.stem,
            "title": meta.get("title", f.stem),
            "description": meta.get("description", ""),
            "category": meta.get("category", "Uncategorized"),
            "tags": meta.get("tags", []),
            "word_count": word_count,
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d, %Y %H:%M"),
            "preview": content_body[:500].strip(),
        })
    return drafts

def get_rejected():
    """Return list of rejected files."""
    rejected = []
    if not REJECTED.exists():
        return rejected
    for f in sorted(REJECTED.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = f.read_text()
        meta = parse_frontmatter(text)
        rejected.append({
            "filename": f.name,
            "title": meta.get("title", f.stem),
            "category": meta.get("category", "Uncategorized"),
            "rejected": datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d, %Y %H:%M"),
        })
    return rejected

def git_commit_and_push(message: str):
    """Commit and push to GitHub."""
    try:
        subprocess.run(["git", "add", "-A"], cwd=BASE, capture_output=True, timeout=30)
        subprocess.run(["git", "commit", "-m", message], cwd=BASE, capture_output=True, timeout=30)
        result = subprocess.run(["git", "push"], cwd=BASE, capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        return False

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    drafts = get_drafts()
    rejected = get_rejected()
    published = len(list(ARTICLES.glob("*.md"))) if ARTICLES.exists() else 0
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "drafts": drafts,
        "rejected": rejected,
        "published_count": published,
        "draft_count": len(drafts),
    })

@app.post("/approve/{filename}")
async def approve(filename: str):
    src = DRAFTS / filename
    dst = ARTICLES / filename
    if src.exists():
        shutil.move(str(src), str(dst))
        git_commit_and_push(f"publish: {filename}")
    return RedirectResponse(url="/", status_code=303)

@app.post("/reject/{filename}")
async def reject(filename: str):
    src = DRAFTS / filename
    dst = REJECTED / filename
    if src.exists():
        shutil.move(str(src), str(dst))
    return RedirectResponse(url="/", status_code=303)

@app.post("/reject-with-reason/{filename}")
async def reject_with_reason(filename: str, reason: str = Form(...)):
    src = DRAFTS / filename
    dst = REJECTED / filename
    if src.exists():
        text = src.read_text()
        text += f"\n\n> **Rejection reason:** {reason}\n"
        dst.write_text(text)
        src.unlink()
    return RedirectResponse(url="/", status_code=303)

@app.get("/preview/{filename}")
async def preview(filename: str):
    """Return full article content for preview."""
    src = DRAFTS / filename
    if not src.exists():
        return HTMLResponse("Not found", status_code=404)
    text = src.read_text()
    body = text.split("---", 2)[-1].strip() if text.count("---") >= 2 else text
    return HTMLResponse(f"<pre style='white-space:pre-wrap;font-family:inherit;'>{body}</pre>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3001)