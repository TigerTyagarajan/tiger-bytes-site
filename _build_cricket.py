#!/usr/bin/env python3
"""Temporary one-off builder for the cricket essay publish.
Reads cricket-leadership-essay-draft-v2.md, cricket-posts-full-text.md
and SELECTIONS.md in the repo root, plus the head/CSS of
leading-with-curiosity.html, and generates:
  - what-cricket-has-taught-me-about-leadership.html (root)
  - posts/*.html (16 preserved posts)
and inserts one essay card into index.html's Beyond Work section,
immediately after the travel essay card.
This file is deleted by the publishing workflow after it runs.
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path('.')
EM = '\u2014'
EN = '\u2013'
ARROW_R = '\u2192'
ARROW_L = '\u2190'
MIDDLE_DOT = '\u00b7'

ESSAY_FILE = ROOT / 'what-cricket-has-taught-me-about-leadership.html'
ESSAY_TITLE = 'What Cricket Has Taught Me About Leadership'
ESSAY_DATE = 'November 8, 2026'
ESSAY_KICKER = 'BEYOND WORK ' + MIDDLE_DOT + ' CRICKET'
ESSAY_DESC = ("Sixteen years of watching cricket, and the lessons it keeps "
              "teaching about leading people " + EM + " from a 2010 blog post "
              "to a summer's day at Lord's.")
HERO_FILE = 'lords-panorama-2026-07-10.jpg'

CAPTIONS = {
    'lords-panorama-2026-07-10.jpg': ("The wide Lord's panorama, Media Centre centred, ground nearly empty "
        + EM + " Friday, July 10, 2026, the first women's Test match at Lord's, India v England."),
    'tiger-at-lords-2009-06-21.jpg': ("Tiger in sunglasses in the foreground, Lord's outfield and the old Grand Stand behind, "
        "'ICC World Twenty20' signage on the stands " + EM + " Sunday, June 21, 2009."),
    'india-pakistan-champions-trophy-tv-2025-02-23-a.jpg': ("The TV in Gurgaon during the Champions Trophy match in Dubai: Shaheen Afridi bowling, "
        "India 2" + EN + "0 at 0.4 overs chasing 242, and the JioHotstar counter on screen reading '35.1 Cr views' "
        + EM + " Sunday, February 23, 2025."),
    'three-screens-new-york-2025-04-13.jpg': ("The living room: IPL (Mumbai, #63) on the TV via Willow, Newcastle v Man United on the MacBook, "
        "and the Bahrain F1 race on the iPhone " + EM + " Sunday, April 13, 2025, New York."),
    'womens-world-cup-win-tv-2025-11-02.jpg': ("The TV at the moment of the win: Star Sports 2 LIVE, the team celebrating under the ticker "
        "'INDIA BECOME THE 4TH TEAM TO WIN THE ICC WOMEN'S CRICKET WORLD CUP' " + EM + " November 2, 2025."),
    'oval-womens-t20-world-cup-2026-06-30.jpg': ("The Kia Oval pavilion and crowd under a huge summer sky, ICC Women's T20 World Cup signage "
        "on the stands " + EM + " Tuesday, June 30, 2026."),
    'lords-womens-test-teams-2026-07-10.jpg': ("The two women's teams walking out behind the trophy, flame cannons firing "
        + EM + " Friday, July 10, 2026, the first women's Test match at Lord's, India v England."),
}

SECTION_PHOTOS = {
    0: 'tiger-at-lords-2009-06-21.jpg',
    3: 'india-pakistan-champions-trophy-tv-2025-02-23-a.jpg',
    4: 'three-screens-new-york-2025-04-13.jpg',
    5: 'womens-world-cup-win-tv-2025-11-02.jpg',
    9: 'oval-womens-t20-world-cup-2026-06-30.jpg',
    10: 'lords-womens-test-teams-2026-07-10.jpg',
}

SECTION_POSTS = {
    0: ['leading-with-cricket-jan-2010'],
    1: ['kane-williamson-jul-2019', 'kohli-tendulkar-nov-2023', 'yashasvi-jaiswal-feb-2024'],
    2: ['gambhir-press-conference-jan-2025'],
    3: ['india-pakistan-feb-2025', 'ipl-acquired-mar-2025'],
    4: ['three-screens-apr-2025'],
    5: ['womens-team-nov-2025', 'womens-world-cup-win-nov-2025'],
    6: ['bad-leader-nov-2025'],
    7: ['ashes-technology-dec-2025'],
    8: ['calcutta-cup-feb-2026'],
    9: ['july-in-london-jun-2026'],
    10: ['the-vow-jul-2026', 'lords-jul-2026'],
}

DATE_TO_SLUG = {
    '2010-01-31': 'leading-with-cricket-jan-2010',
    '2019-07-21': 'kane-williamson-jul-2019',
    '2023-11-16': 'kohli-tendulkar-nov-2023',
    '2024-02-03': 'yashasvi-jaiswal-feb-2024',
    '2025-01-05': 'gambhir-press-conference-jan-2025',
    '2025-02-23': 'india-pakistan-feb-2025',
    '2025-03-24': 'ipl-acquired-mar-2025',
    '2025-04-13': 'three-screens-apr-2025',
    '2025-11-01': 'womens-team-nov-2025',
    '2025-11-02': 'womens-world-cup-win-nov-2025',
    '2025-11-26': 'bad-leader-nov-2025',
    '2025-12-18': 'ashes-technology-dec-2025',
    '2026-02-14': 'calcutta-cup-feb-2026',
    '2026-06-30': 'july-in-london-jun-2026',
    '2026-07-09': 'the-vow-jul-2026',
    '2026-07-19': 'lords-jul-2026',
}

EXTRA_CSS = """<style>
.travel-photo{margin:28px 0 8px}
.travel-photo img{width:100%;height:auto;display:block}
.travel-photo figcaption{font-family:var(--sans);font-size:.82rem;color:#5f5f5f;letter-spacing:.05em;margin-top:10px}
.post-link{margin-top:26px}
.post-link a,.back-link a{color:#e8590c;font-weight:600;text-decoration:none}
.post-link a:hover,.back-link a:hover{text-decoration:underline}
</style>"""

def esc(s):
    return html.escape(s, quote=True)

def esc_text(s):
    return html.escape(s, quote=False)

def md_inline(s):
    s = esc_text(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return s

def clean_quote(line):
    line = line.strip()
    if line.startswith('"'):
        line = line[1:].lstrip()
    if line.endswith('"'):
        line = line[:-1].rstrip()
    return line.strip()

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

def fmt_date(iso):
    y, m, d = iso.split('-')
    return '%s %d, %s' % (MONTHS[int(m) - 1], int(d), y)

def blocks_to_html(blocks):
    out = []
    for kind, val in blocks:
        if kind == 'p':
            out.append('<p>' + md_inline(val) + '</p>')
        elif kind == 'lead':
            out.append('<p><em>' + md_inline(val) + '</em></p>')
        elif kind == 'ol':
            items = ''.join('<li>' + md_inline(x) + '</li>' for x in val)
            out.append('<ol>' + items + '</ol>')
        elif kind == 'ul':
            items = ''.join('<li>' + md_inline(x) + '</li>' for x in val)
            out.append('<ul>' + items + '</ul>')
    return '\n'.join(out)

def parse_blocks(lines):
    blocks = []
    buf = []
    def flush():
        if buf:
            blocks.append(('p', ' '.join(buf)))
            buf.clear()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            flush()
            i += 1
            continue
        m = re.match(r'^(\d+)\.\s+(.*)$', line)
        if m:
            flush()
            items = []
            while i < len(lines):
                m2 = re.match(r'^(\d+)\.\s+(.*)$', lines[i])
                if not m2:
                    break
                items.append(m2.group(2).strip())
                i += 1
            blocks.append(('ol', items))
            continue
        if line.startswith('- '):
            flush()
            items = []
            while i < len(lines) and lines[i].startswith('- '):
                items.append(lines[i][2:].strip())
                i += 1
            blocks.append(('ul', items))
            continue
        if line.startswith('*') and line.endswith('*') and len(line) > 2:
            flush()
            blocks.append(('lead', line[1:-1].strip()))
            i += 1
            continue
        buf.append(line)
        i += 1
    flush()
    return blocks

def parse_essay(text):
    lines = text.splitlines()
    sections = []
    cur = {'heading': None, 'kicker': None, 'title': None, 'lines': []}
    sections.append(cur)
    started = False
    for raw in lines:
        line = raw.strip()
        if not started:
            if line == '---':
                started = True
            continue
        if line == '---':
            continue
        if line.startswith('## Notes'):
            break
        if line.startswith('## '):
            cur = {'heading': line[3:].strip(), 'kicker': None, 'title': None, 'lines': []}
            sections.append(cur)
            continue
        cur['lines'].append(line)
    assert started, 'essay draft header separator not found'
    for sec in sections:
        if sec['heading'] is not None:
            parts = sec['heading'].split(' ' + EM + ' ', 1)
            assert len(parts) == 2, 'heading has no em-dash split: %r' % sec['heading']
            sec['title'] = parts[0]
            sec['kicker'] = sec['heading']
        sec['blocks'] = parse_blocks(sec['lines'])
    return sections

POST_HEAD_RE = re.compile(r'^##\s+(.+?)\s+' + re.escape(EM) + r'\s+(\d{4})-(\d{2})-(\d{2})\s*$')

def parse_posts(text):
    posts = []
    cur = None
    for raw in text.splitlines():
        line = raw.strip()
        m = POST_HEAD_RE.match(line)
        if m:
            cur = {'title': m.group(1), 'date': '%s-%s-%s' % (m.group(2), m.group(3), m.group(4)),
                   'source': 'LinkedIn', 'lines': []}
            posts.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith('Post date:'):
            if 'Blog:' in line:
                cur['source'] = 'Blogspot'
            continue
        cur['lines'].append(clean_quote(line))
    for post in posts:
        post['blocks'] = parse_blocks(post['lines'])
    return posts

_template = (ROOT / 'leading-with-curiosity.html').read_text(encoding='utf-8')
_m = re.search(r'<head.*?>.*?</head>', _template, re.S)
assert _m, 'no <head> in leading-with-curiosity.html'
TEMPLATE_HEAD = _m.group(0)

def make_page(page_title, h1, desc, date, kicker, body_html, footer_text):
    head = TEMPLATE_HEAD
    head = re.sub(r'<title>.*?</title>', '<title>' + esc(page_title) + '</title>', head, count=1, flags=re.S)
    head = re.sub(r'(<meta name="description" content=")[^"]*(")',
                  lambda mm: mm.group(1) + esc(desc) + mm.group(2), head, count=1)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*(")',
                  lambda mm: mm.group(1) + esc(page_title) + mm.group(2), head, count=1)
    head = re.sub(r'(<meta property="og:description" content=")[^"]*(")',
                  lambda mm: mm.group(1) + esc(desc) + mm.group(2), head, count=1)
    head = head.replace('</head>', EXTRA_CSS + '</head>')
    return ('<!doctype html>\n<html lang="en">\n' + head + '\n<body>\n<div class="page">\n'
            '<header class="masthead">\n'
            '<p style="font-size:.85rem;color:#5f5f5f;letter-spacing:.06em;margin:0 0 10px;">' + date + '</p>\n'
            '<p class="kicker">' + kicker + '</p>\n'
            '<h1>' + esc_text(h1) + '</h1>\n'
            '<div class="rule"></div>\n'
            '</header>\n<main>\n' + body_html + '\n</main>\n'
            '<footer><p style="text-align:center;font-size:.85rem;color:#5f5f5f;margin:36px 0 8px;">'
            + footer_text + '</p></footer>\n'
            '</div>\n</body>\n</html>\n')

def figure_html(filename):
    caption = CAPTIONS[filename]
    alt = caption.split(' ' + EM + ' ', 1)[0]
    return ('<figure class="travel-photo"><img src="assets/' + filename + '" alt="' + esc(alt) + '">'
            '<figcaption>' + esc_text(caption) + '</figcaption></figure>')

def post_link_html(slug):
    return '<p class="post-link"><a href="/posts/' + slug + '.html">Read the original post ' + ARROW_R + '</a></p>'

def build_essay(sections):
    parts = [figure_html(HERO_FILE)]
    for idx, sec in enumerate(sections):
        assert idx in SECTION_POSTS, 'no post mapping for section %d' % idx
        slugs = SECTION_POSTS[idx]
        groups = []
        cur_group = []
        for kind, val in sec['blocks']:
            if kind == 'lead':
                if cur_group:
                    groups.append(cur_group)
                cur_group = [(kind, val)]
            else:
                cur_group.append((kind, val))
        if cur_group:
            groups.append(cur_group)
        assert len(groups) == len(slugs), (
            'section %d (%s): %d groups but %d post slugs' % (idx, sec['heading'], len(groups), len(slugs)))
        html_parts = ['<section class="layer">']
        if sec['heading'] is not None:
            html_parts.append('<div class="layer-head"><p class="layer-kicker">' + esc_text(sec['kicker']) + '</p><h2>' + esc_text(sec['title']) + '</h2></div>')
        if idx in SECTION_PHOTOS:
            html_parts.append(figure_html(SECTION_PHOTOS[idx]))
        for group, slug in zip(groups, slugs):
            html_parts.append(blocks_to_html(group))
            html_parts.append(post_link_html(slug))
        html_parts.append('</section>')
        parts.append('\n'.join(html_parts))
    body = '\n'.join(parts)
    return make_page(ESSAY_TITLE + ' ' + EM + ' Tiger Bytes', ESSAY_TITLE, ESSAY_DESC,
                     ESSAY_DATE, ESSAY_KICKER, body,
                     ESSAY_TITLE + ' ' + EM + ' a Tiger Bytes essay.')

def build_post(post):
    slug = DATE_TO_SLUG[post['date']]
    source = post['source']
    kicker = 'ORIGINALLY POSTED ON ' + ('BLOGSPOT' if source == 'Blogspot' else 'LINKEDIN')
    footer = 'Originally posted on ' + source + ' ' + EM + ' preserved here on Tiger Bytes.'
    body = ('<section class="layer">\n' + blocks_to_html(post['blocks'])
            + '\n<p class="back-link"><a href="/what-cricket-has-taught-me-about-leadership.html">'
            + ARROW_L + ' Back to: ' + ESSAY_TITLE + '</a></p>\n</section>')
    return slug, make_page(post['title'] + ' ' + EM + ' Tiger Bytes', post['title'],
                           post['title'], fmt_date(post['date']), kicker, body, footer)

def edit_index():
    path = ROOT / 'index.html'
    old = path.read_text(encoding='utf-8')
    assert old.count('what-cricket-has-taught-me-about-leadership.html') == 0, 'cricket card already in index'
    anchor = ('It is an education.</p><p><a class="btn btn-accent" href="/what-the-world-has-taught-me.html">'
              'Read the essay ' + ARROW_R + '</a></p></article>')
    assert old.count(anchor) == 1, 'travel card anchor found %d times, expected 1' % old.count(anchor)
    card = ('<article class="card"><span class="tag">Beyond Work</span><h3>' + ESSAY_TITLE + '</h3>'
            '<a class="card-visual" href="what-cricket-has-taught-me-about-leadership.html" aria-label="Open ' + ESSAY_TITLE + '">'
            '<img src="assets/lords-panorama-2026-07-10.jpg" alt="Lord\'s Cricket Ground panorama, July 10, 2026" loading="lazy"></a>'
            '<p>' + esc_text(ESSAY_DESC) + '</p>'
            '<p><a class="btn btn-accent" href="/what-cricket-has-taught-me-about-leadership.html">Read the essay ' + ARROW_R + '</a></p></article>')
    new = old.replace(anchor, anchor + card, 1)
    assert new.replace(card, '', 1) == old, 'index diff is not exactly the one card insertion'
    path.write_text(new, encoding='utf-8')
    print('index.html: %d -> %d bytes (one card inserted)' % (len(old), len(new)))

def main():
    for fn in list(CAPTIONS):
        p = ROOT / 'assets' / fn
        assert p.is_file() and p.stat().st_size > 0, 'missing asset %s' % fn
    spare = ROOT / 'assets' / 'india-pakistan-champions-trophy-tv-2025-02-23-b.jpg'
    assert not spare.exists(), 'spare b.jpg must not be in assets'
    essay_text = (ROOT / 'cricket-leadership-essay-draft-v2.md').read_text(encoding='utf-8')
    assert 'Notes for Tiger' in essay_text, 'unexpected essay draft file'
    sections = parse_essay(essay_text)
    assert len(sections) == 11, 'expected 11 sections, got %d' % len(sections)
    leads = [sum(1 for k, _ in s['blocks'] if k == 'lead') for s in sections]
    assert leads == [0, 3, 0, 2, 0, 2, 0, 0, 0, 0, 2], 'lead-in counts %r' % leads
    essay_html = build_essay(sections)
    assert 'Sixteen years ago' in essay_html, 'essay opener missing'
    assert 'Sports brings people together.' in essay_html, 'essay closing missing'
    assert 'Notes for Tiger' not in essay_html, 'notes leaked into essay page'
    assert 'v2 changes' not in essay_html, 'draft header leaked into essay page'
    assert 'data:image' not in essay_html, 'inlined image data in essay page'
    assert '-b.jpg' not in essay_html, 'spare photo referenced in essay page'
    assert essay_html.count('Read the original post') == 16, 'expected 16 post links, got %d' % essay_html.count('Read the original post')
    assert essay_html.count('<ol>') == 3, 'expected 3 numbered lists, got %d' % essay_html.count('<ol>')
    assert essay_html.count('<em>') == 9, 'expected 9 italic lead-ins, got %d' % essay_html.count('<em>')
    for fn in CAPTIONS:
        assert essay_html.count('assets/' + fn) == 1, 'photo %s referenced %d times in essay' % (fn, essay_html.count('assets/' + fn))
    for slug in DATE_TO_SLUG.values():
        assert ('/posts/' + slug + '.html') in essay_html, 'missing post link %s' % slug
    ESSAY_FILE.write_text(essay_html, encoding='utf-8')
    print('%s: %d bytes' % (ESSAY_FILE.name, len(essay_html)))
    posts_text = (ROOT / 'cricket-posts-full-text.md').read_text(encoding='utf-8')
    posts = parse_posts(posts_text)
    assert len(posts) == 16, 'expected 16 posts, got %d' % len(posts)
    assert set(p['date'] for p in posts) == set(DATE_TO_SLUG), 'post dates do not match slug map'
    for post in posts:
        assert post['blocks'], 'empty post %s' % post['date']
        slug, html_page = build_post(post)
        assert 'data:image' not in html_page
        assert post['title'] in html_page
        assert fmt_date(post['date']) in html_page
        assert '/what-cricket-has-taught-me-about-leadership.html' in html_page
        out = ROOT / 'posts' / (slug + '.html')
        out.write_text(html_page, encoding='utf-8')
        print('posts/%s.html: %d bytes (%s, %s)' % (slug, len(html_page), post['date'], post['source']))
    acquired = (ROOT / 'posts' / 'ipl-acquired-mar-2025.html').read_text(encoding='utf-8')
    assert 'IPL is the fastest-growing, most dynamic and most disruptive force' in acquired
    assert 'surpass the NFL' in acquired
    edit_index()
    print('BUILD OK: 1 essay page, 16 preserved posts, 1 homepage card')

if __name__ == '__main__':
    main()
