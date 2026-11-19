import html
from xml.sax.saxutils import quoteattr

from cms_backend.db.collection import LibraryBookData
from cms_backend.db.models import Collection
from cms_backend.utils.filename import construct_download_url

_BYTES_PER_UNIT = 1024


def _format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return ""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < _BYTES_PER_UNIT:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= _BYTES_PER_UNIT
    return f"{size:.1f} TB"


def build_collection_demo_html(
    collection: Collection, entries: list[LibraryBookData]
) -> str:
    title = html.escape(collection.name)
    rows: list[str] = []
    for entry in entries:
        book, zim_title, download_base_url, path, filename = entry
        zim_meta = book.zim_metadata or {}
        book_title = html.escape(
            zim_title.title or zim_meta.get("Title") or zim_meta.get("Name") or filename
        )
        description = html.escape(
            zim_title.description or zim_meta.get("Description") or ""
        )
        language = html.escape(zim_title.language or zim_meta.get("Language") or "")
        date = html.escape(book.date or zim_meta.get("Date") or "")
        flavour = html.escape(book.flavour or "")
        size = html.escape(_format_size(book.size))
        illustration = zim_title.illustration_48x48_at_1 or zim_meta.get(
            "Illustration_48x48@1"
        )
        if illustration:
            src = quoteattr("data:image/png;base64," + illustration)
            img = f'<img class="icon" alt="" src={src}>'
        else:
            img = '<span class="icon empty" aria-hidden="true"></span>'

        actions: list[str] = []
        if download_base_url:
            download_url = construct_download_url(download_base_url, path, filename)
            href = quoteattr(download_url)
            actions.append(f'<a class="btn" href={href} rel="noopener">Download</a>')
        if collection.view_base_url and book.transition_status is None:
            filename_without_suffix = (
                filename[:-4] if filename.endswith(".zim") else filename
            )
            view_url = f"{collection.view_base_url}{filename_without_suffix}"
            href = quoteattr(view_url)
            actions.append(
                '<a class="btn primary" '
                f'href={href} target="_blank" rel="noopener">Browse</a>'
            )
        actions_html = " ".join(actions) if actions else '<span class="muted">—</span>'

        meta_parts = [p for p in (language, date, size, flavour) if p]
        meta_html = " · ".join(meta_parts)
        rows.append(
            "<tr>"
            '<td class="title-cell">'
            f'{img}<div><div class="book-title">{book_title}</div>'
            f'<div class="desc">{description}</div></div></td>'
            f'<td class="meta">{meta_html}</td>'
            f'<td class="actions">{actions_html}</td>'
            "</tr>"
        )

    if rows:
        table = (
            "<table><thead><tr>"
            "<th>Title</th><th>Details</th><th>Links</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )
    else:
        table = (
            '<p class="empty-state">'
            "No books are currently available in this collection."
            "</p>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} - ZIM collection</title>
  <style>
    :root{{--bg:#f6f8fb;--card:#fff;--text:#1f2937;--muted:#6b7280;
      --line:#e5e7eb;--accent:#2563eb;--accent-hover:#1d4ed8}}
    *{{box-sizing:border-box}}
    body{{margin:0;font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
      background:var(--bg);color:var(--text)}}
    .wrap{{max-width:1100px;margin:0 auto;padding:32px 20px}}
    h1{{margin:0 0 6px;font-size:1.75rem}}
    .sub{{color:var(--muted);margin:0 0 24px}}
    table{{width:100%;border-collapse:collapse;background:var(--card);
      border:1px solid var(--line);border-radius:10px;overflow:hidden}}
    th,td{{padding:14px 16px;text-align:left;vertical-align:top;
      border-top:1px solid var(--line)}}
    th{{background:#fafbfc;color:var(--muted);font-weight:600;font-size:.85rem;
      text-transform:uppercase;letter-spacing:.03em;border-top:0}}
    .title-cell{{display:flex;gap:12px;align-items:flex-start}}
    .icon{{width:48px;height:48px;flex:0 0 48px;border-radius:6px;
      object-fit:contain;background:#fff;border:1px solid var(--line)}}
    .icon.empty{{display:inline-block;background:#f3f4f6}}
    .book-title{{font-weight:600}}
    .desc{{color:var(--muted);font-size:.92rem;margin-top:2px}}
    .meta{{color:var(--muted);white-space:nowrap;font-size:.92rem}}
    .actions{{white-space:nowrap}}
    .btn{{display:inline-block;padding:6px 12px;border:1px solid var(--line);
      border-radius:7px;text-decoration:none;color:var(--text);
      background:#fff;font-size:.9rem}}
    .btn:hover{{border-color:#cbd5e1}}
    .btn.primary{{background:var(--accent);border-color:var(--accent);color:#fff}}
    .btn.primary:hover{{background:var(--accent-hover)}}
    .btn+.btn{{margin-left:6px}}
    .muted{{color:var(--muted)}}
    .empty-state{{background:var(--card);border:1px solid var(--line);
      border-radius:10px;padding:24px;color:var(--muted)}}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{title}</h1>
    <p class="sub">Available ZIM files in this collection</p>
    {table}
  </div>
</body>
</html>
"""
