import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_UL_ITEM_RE = re.compile(r"^\s*[-*]\s+(.+)$")
_OL_ITEM_RE = re.compile(r"^\s*\d+\.\s+(.+)$")


def _render_inline(text):
    text = escape(text)
    text = _INLINE_CODE_RE.sub(r"<code>\1</code>", text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    text = _LINK_RE.sub(r'<a href="\2" rel="noopener noreferrer">\1</a>', text)
    return text


def _render_table(lines):
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if "|" not in stripped:
            return ""
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return ""

    # Skip markdown separator line if present: |---|---|
    header = rows[0]
    body_start = 1
    if all(re.fullmatch(r":?-{2,}:?", c or "") for c in rows[1]):
        body_start = 2

    html = ["<table>", "<thead><tr>"]
    html.extend(f"<th>{_render_inline(cell)}</th>" for cell in header)
    html.append("</tr></thead><tbody>")
    for row in rows[body_start:]:
        html.append("<tr>")
        html.extend(f"<td>{_render_inline(cell)}</td>" for cell in row)
        html.append("</tr>")
    html.append("</tbody></table>")
    return "".join(html)


@register.filter
def render_article_markdown(value):
    text = (value or "").replace("\r\n", "\n")
    lines = text.split("\n")
    html = []
    paragraph = []
    list_items = []
    list_tag = None
    table_lines = []

    def flush_paragraph():
        if paragraph:
            joined = " ".join(part.strip() for part in paragraph if part.strip())
            if joined:
                html.append(f"<p>{_render_inline(joined)}</p>")
            paragraph.clear()

    def flush_list():
        nonlocal list_tag
        if list_items and list_tag:
            html.append(f"<{list_tag}>")
            html.extend(f"<li>{item}</li>" for item in list_items)
            html.append(f"</{list_tag}>")
        list_items.clear()
        list_tag = None

    def flush_table():
        if table_lines:
            rendered = _render_table(table_lines)
            if rendered:
                html.append(rendered)
            else:
                for row in table_lines:
                    if row.strip():
                        html.append(f"<p>{_render_inline(row.strip())}</p>")
            table_lines.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            flush_list()
            flush_table()
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            flush_paragraph()
            flush_list()
            flush_table()
            level = min(len(heading.group(1)), 4)
            html.append(f"<h{level}>{_render_inline(heading.group(2).strip())}</h{level}>")
            continue

        if "|" in stripped and stripped.count("|") >= 2:
            flush_paragraph()
            flush_list()
            table_lines.append(stripped)
            continue
        flush_table()

        ul_match = _UL_ITEM_RE.match(stripped)
        if ul_match:
            flush_paragraph()
            if list_tag not in (None, "ul"):
                flush_list()
            list_tag = "ul"
            list_items.append(_render_inline(ul_match.group(1)))
            continue

        ol_match = _OL_ITEM_RE.match(stripped)
        if ol_match:
            flush_paragraph()
            if list_tag not in (None, "ol"):
                flush_list()
            list_tag = "ol"
            list_items.append(_render_inline(ol_match.group(1)))
            continue

        flush_list()
        paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    flush_table()
    return mark_safe("\n".join(html))
