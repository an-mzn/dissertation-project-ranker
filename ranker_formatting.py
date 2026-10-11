"""Render a small text-only Markdown subset without executing HTML."""

import html
import re


def render_readable_description(text):
    """Support headings, paragraphs, and flat bullet/numbered lists.

    Inline Markdown, links, images, and raw HTML remain escaped literal text.
    """
    output, paragraph = [], []
    list_type = None

    def flush_paragraph():
        if paragraph:
            output.append('<p style="white-space:pre-wrap;">' + html.escape("\n".join(paragraph)) + '</p>')
            paragraph.clear()

    def close_list():
        nonlocal list_type
        if list_type:
            output.append(f'</{list_type}>')
            list_type = None

    for line in text.splitlines():
        heading = re.match(r'^\s{0,3}(#{1,6})\s+(.+)$', line)
        item = re.match(r'^\s*(?:[-+*]\s+|([0-9]+)[.)]\s+)(.+)$', line)
        if heading:
            flush_paragraph()
            close_list()
            level = min(6, len(heading[1]) + 3)
            output.append(f'<h{level}>' + html.escape(heading[2]) + f'</h{level}>')
        elif item:
            flush_paragraph()
            kind = 'ol' if item[1] else 'ul'
            if kind != list_type:
                close_list()
                start = f' start="{int(item[1])}"' if item[1] else ''
                output.append(f'<{kind}{start}>')
                list_type = kind
            output.append('<li>' + html.escape(item[2]) + '</li>')
        else:
            close_list()
            if line.strip():
                paragraph.append(line)
            else:
                flush_paragraph()
    flush_paragraph()
    close_list()
    return ''.join(output)
