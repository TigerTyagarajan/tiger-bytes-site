#!/usr/bin/env python3
"""Temporary one-off builder for the travel essay publish.
Reads the two source markdown files in the repo root, the photo
record in SELECTIONS.md, and the head/CSS of
leading-with-curiosity.html, and generates:
  - what-the-world-has-taught-me.html (root)
  - posts/*.html (16 preserved LinkedIn posts)
and inserts the essay card into index.html's Beyond Work section.
This file is deleted by the publishing workflow after it runs.
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path('.')
ESSAY_FILE = ROOT / 'what-the-world-has-taught-me.html'


def esc(s):
    return html.escape(s, quote=True)


def md_inline(s):
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return s


def clean_quote(line):
    line = line.strip()
    if line.startswith('"'):
        line = line[1:].lstrip()
    if line.endswith('"'):
        line = line[:-1].rstrip()
    return line.strip()


def paras_to_html(lines):
    out = []
    ul = []

    def flush_ul():
        nonlocal ul
        if ul:
            items = ''.join('<li>' + md_inline(x) + '</li>' for x in ul)
            out.append('<ul>' + items + '</ul>')
            ul = []
    for ln in lines:
        if ln.startswith('- '):
            ul.append(ln[2:].strip())
        else:
            flush_ul()
            out.append('<p>' + md_inline(ln) + '</p>')
    flush_ul()
    return '\n'.join(out)


def load_alt_texts():
    alts = {}
    text = (ROOT / 'SELECTIONS.md').read_text(encoding='utf-8')
    for line in text.splitlines():
        m = re.search(r'\*\*([^*]+\.jpg)\*\*\W+(.*)$', line)
        if m:
            alts[m.group(1).strip()] = m.group(2).strip()
    return alts


def head_for(title, url, description):
    head = TEMPLATE_HEAD
    head = re.sub(r'<title>.*?</title>', '<title>' + esc(title) + ' \u2014 Tiger Bytes</title>', head, count=1, flags=re.S)
    head = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + esc(description) + m.group(2), head, count=1)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda m: m.group(1) + esc(title) + m.group(2), head, count=1)
    head = re.sub(r'(<meta property="og:url" content=")[^"]*(")', lambda m: m.group(1) + esc(url) + m.group(2), head, count=1)
    head = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + esc(description) + m.group(2), head, count=1)
    head = re.sub(r'(<meta name="twitter:title" content=")[^"]*(")', lambda m: m.group(1) + esc(title) + m.group(2), head, count=1)
    head = re.sub(r'(<meta name="twitter:description" content=")[^"]*(")', lambda m: m.group(1) + esc(description) + m.group(2), head, count=1)
    return head


EXTRA_CSS = (
    '<style>\n'
    '.travel-photo{margin:28px 0 8px}\n'
    '.travel-photo img{width:100%;height:auto;display:block}\n'
    '.travel-photo figcaption{font-family:var(--sans);font-size:.82rem;color:#5f5f5f;letter-spacing:.05em;margin-top:10px}\n'
    '.post-link{margin-top:26px}\n'
    '.post-link a,.back-link a{color:#e8590c;font-weight:600;text-decoration:none}\n'
    '.post-link a:hover,.back-link a:hover{text-decoration:underline}\n'
    '</style>\n'
)


def make_page(title, url, description, date_line, kicker, body_html, footer_note):
    head = head_for(title, url, description)
    head = head.replace('</head>', EXTRA_CSS + '</head>')
    parts = []
    parts.append('<!doctype html>')
    parts.append('<html lang="en">')
    parts.append(head)
    parts.append('<body>')
    parts.append('<div class="page">')
    parts.append('<header class="masthead">')
    parts.append('<p style="font-size:.85rem;color:#5f5f5f;letter-spacing:.06em;margin:0 0 10px;">' + esc(date_line) + '</p>')
    parts.append('<p class="kicker">' + esc(kicker) + '</p>')
    parts.append('<h1>' + esc(title) + '</h1>')
    parts.append('<div class="rule"></div>')
    parts.append('</header>')
    parts.append('<main>')
    parts.append(body_html)
    parts.append('</main>')
    parts.append('<footer><p style="text-align:center;font-size:.85rem;color:#5f5f5f;margin:36px 0 8px;">' + esc(footer_note) + '</p></footer>')
    parts.append('</div>')
    parts.append('</body>')
    parts.append('</html>')
    return '\n'.join(parts) + '\n'


def figure(fn, caption=None):
    alt = ALT.get(fn, fn)
    cap = ''
    if caption:
        cap = '<figcaption>' + esc(caption) + '</figcaption>'
    return ('<figure class="travel-photo"><img src="/assets/' + esc(fn) +
            '" alt="' + esc(alt) + '" loading="lazy">' + cap + '</figure>')


POST_SLUGS = [
    'coimbatore-dec-2023', 'delhi-red-fort-jan-2024', 'boston-mar-2024',
    'wales-may-2024', 'istanbul-sep-2024', 'belgrade-oct-2024',
    'lisbon-melting-pot-oct-2024', 'lisbon-move-apr-2025',
    'lisbon-first-week-apr-2025', 'warsaw-may-2025', 'japan-nov-2025',
    'singapore-nov-2025', 'sri-lanka-29-cities-jan-2026', 'obidos-may-2026',
    'lisbon-16-months-aug-2026', 'australia-aug-2026',
]
POST_TITLES = [
    'Coimbatore \u2014 tier-3 and tier-4 India',
    'Delhi \u2014 the Red Fort at night',
    'Boston \u2014 a city of innovation',
    'Wales \u2014 five thousand years of history',
    'Istanbul \u2014 at the crossroads of civilisations',
    'Belgrade \u2014 engineering talent and 7,000 years of history',
    'Lisbon \u2014 a melting pot of cultures',
    'Lisbon \u2014 moving to a new home',
    'Lisbon \u2014 my first week in a new home',
    'Warsaw \u2014 science, music and resilience',
    'Japan \u2014 twenty-nine cities in 2025',
    'Singapore \u2014 safety, trust and a city that works',
    'Sri Lanka \u2014 twenty-nine cities in 2025',
    '\u00d3bidos \u2014 a book town built to last',
    'Lisbon \u2014 sixteen months on',
    'Australia \u2014 Sydney, sandstone and the Opera House',
]
POST_PHOTOS = {
    'coimbatore-dec-2023': ['coimbatore-best-buy-dec-2023.jpg', 'coimbatore-new-apartments-dec-2023.jpg'],
    'delhi-red-fort-jan-2024': ['delhi-red-fort-night-jan-2024.jpg', 'delhi-red-fort-performance-jan-2024.jpg'],
    'boston-mar-2024': ['boston-mit-dome-mar-2024.jpg', 'boston-mit-sloan-atrium-mar-2024.jpg'],
    'wales-may-2024': ['wales-pentre-ifan-may-2024.jpg', 'wales-castle-may-2024.jpg'],
    'istanbul-sep-2024': ['istanbul-bosphorus-sunset-sep-2024.jpg', 'istanbul-old-new-street-sep-2024.jpg'],
    'belgrade-oct-2024': ['belgrade-tesla-museum-oct-2024.jpg', 'belgrade-tesla-reading-oct-2024.jpg'],
    'lisbon-melting-pot-oct-2024': ['lisbon-ponte-cristo-rei-oct-2024.jpg', 'lisbon-marques-pombal-oct-2024.jpg', 'lisbon-gloria-funicular-night-oct-2024.jpg'],
    'lisbon-move-apr-2025': [],
    'lisbon-first-week-apr-2025': ['lisbon-monsanto-aqueduct-apr-2025.jpg', 'lisbon-rossio-apr-2025.jpg'],
    'warsaw-may-2025': ['warsaw-copernicus-centre-may-2025.jpg', 'warsaw-pilsudski-square-may-2025.jpg'],
    'japan-nov-2025': ['japan-reflecting-pool-nov-2025.jpg', 'japan-shinkansen-platform-nov-2025.jpg', 'japan-zojoji-tokyo-tower-nov-2025.jpg'],
    'singapore-nov-2025': ['singapore-safety-banner-nov-2025.jpg', 'singapore-marina-bay-nov-2025.jpg'],
    'sri-lanka-29-cities-jan-2026': ['29-cities-2025-collage.jpg', 'sri-lanka-sage-statue.jpg', 'sri-lanka-vatadage.jpg'],
    'obidos-may-2026': ['obidos-church-bookshop-may-2026.jpg', 'obidos-castle-walls-may-2026.jpg'],
    'australia-aug-2026': ['sydney-opera-house-night-aug-2026.jpg', 'sydney-sandstone-aug-2026.jpg'],
    'lisbon-16-months-aug-2026': [],
}
STOP_TO_POST = {
    'Coimbatore \u2014 December 2023': 'coimbatore-dec-2023',
    'Delhi \u2014 December 2023': 'delhi-red-fort-jan-2024',
    'Boston \u2014 March 2024': 'boston-mar-2024',
    'Wales \u2014 May 2024': 'wales-may-2024',
    'Istanbul \u2014 September 2024': 'istanbul-sep-2024',
    'Belgrade \u2014 October 2024': 'belgrade-oct-2024',
    'Lisbon, first look \u2014 October 2024': 'lisbon-melting-pot-oct-2024',
    'Lisbon becomes home \u2014 April 2025': 'lisbon-first-week-apr-2025',
    'Warsaw \u2014 May 2025': 'warsaw-may-2025',
    'Japan \u2014 November 2025': 'japan-nov-2025',
    'Singapore \u2014 November 2025': 'singapore-nov-2025',
    'Sri Lanka \u2014 January 2026': 'sri-lanka-29-cities-jan-2026',
    '\u00d3bidos \u2014 May 2026': 'obidos-may-2026',
    'Australia \u2014 August 2026': 'australia-aug-2026',
    'Lisbon, sixteen months on \u2014 August 2026': 'lisbon-16-months-aug-2026',
}
CAPTIONS = {
    'Coimbatore \u2014 December 2023': 'Coimbatore \u2014 December 2023',
    'Delhi \u2014 December 2023': 'Delhi \u2014 December 2023',
    'Boston \u2014 March 2024': 'Boston \u2014 March 2024',
    'Wales \u2014 May 2024': 'Wales \u2014 May 2024',
    'Istanbul \u2014 September 2024': 'Istanbul \u2014 September 2024',
    'Belgrade \u2014 October 2024': 'Belgrade \u2014 October 2024',
    'Lisbon, first look \u2014 October 2024': 'Lisbon \u2014 October 2024',
    'Lisbon becomes home \u2014 April 2025': 'Lisbon \u2014 April 2025',
    'Warsaw \u2014 May 2025': 'Warsaw \u2014 May 2025',
    'Japan \u2014 November 2025': 'Japan \u2014 November 2025',
    'Singapore \u2014 November 2025': 'Singapore \u2014 November 2025',
    'Sri Lanka \u2014 January 2026': 'Sri Lanka \u2014 January 2026',
    '\u00d3bidos \u2014 May 2026': '\u00d3bidos \u2014 May 2026',
    'Australia \u2014 August 2026': 'Australia \u2014 August 2026',
}
COLLAGE_CAPTION = '2025 travels \u2014 twenty-nine cities in fourteen countries on three continents'


def parse_essay():
    text = (ROOT / 'travel-learnings-essay-draft-v2.md').read_text(encoding='utf-8')
    text = text.split('## Production notes')[0]
    sections = []
    cur = {'heading': None, 'items': []}
    sections.append(cur)
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('### '):
            cur = {'heading': line[4:].strip(), 'items': []}
            sections.append(cur)
            continue
        if line.startswith('## '):
            cur = {'heading': line[3:].strip(), 'items': []}
            sections.append(cur)
            continue
        if line.startswith('#'):
            continue
        if line.startswith('[Photos: ') and line.endswith(']'):
            inner = line[len('[Photos: '):-1]
            if ' \u2014 ' in inner:
                _place, files_str = inner.split(' \u2014 ', 1)
            else:
                files_str = inner
            files = [f.strip() for f in files_str.split('\u00b7') if f.strip()]
            cur['items'].append(('photos', files))
            continue
        if line.startswith('[Photo: ') and line.endswith(']'):
            inner = line[len('[Photo: '):-1]
            fn = inner.split(' \u2014 ', 1)[0].strip()
            cur['items'].append(('photo', [fn]))
            continue
        cur['items'].append(('p', line))
    return sections


def parse_posts():
    text = (ROOT / 'travel-posts-full-text.md').read_text(encoding='utf-8')
    chunks = re.split(r'(?m)^## ', text)
    posts = []
    for chunk in chunks[1:]:
        lines = chunk.splitlines()
        heading = lines[0].strip()
        date_line = ''
        body = []
        for ln in lines[1:]:
            s = ln.strip()
            if s.startswith('Post date:'):
                date_line = s
                continue
            if not s:
                continue
            cleaned = clean_quote(ln)
            if cleaned:
                body.append(cleaned)
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_line)
        if not m:
            raise ValueError('no date in post: ' + heading)
        import datetime as _dt
        dt = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        full_date = dt.strftime('%B ') + str(dt.day) + dt.strftime(', %Y')
        posts.append({'heading': heading, 'date': full_date, 'iso': dt.isoformat(), 'body': body})
    return posts


def build_essay(sections):
    out = []
    photo_count = 0
    for sec in sections:
        heading = sec['heading']
        parts = ['<section class="layer">']
        if heading:
            left = heading.rsplit(' \u2014 ', 1)[0] if ' \u2014 ' in heading else heading
            parts.append('<div class="layer-head"><p class="layer-kicker">' + esc(heading.upper()) + '</p><h2>' + esc(left) + '</h2></div>')
        for kind, val in sec['items']:
            if kind == 'p':
                parts.append('<p>' + md_inline(val) + '</p>')
            elif kind == 'photo':
                for fn in val:
                    photo_count += 1
                    parts.append(figure(fn, COLLAGE_CAPTION if fn == '29-cities-2025-collage.jpg' else None))
            elif kind == 'photos':
                cap = CAPTIONS.get(heading) if heading else None
                for i, fn in enumerate(val):
                    photo_count += 1
                    parts.append(figure(fn, cap if i == 0 else None))
        if heading is None:
            parts.append('<p class="post-link"><a href="/posts/lisbon-move-apr-2025.html">Read the original post \u2192</a></p>')
        elif heading in STOP_TO_POST:
            slug = STOP_TO_POST[heading]
            parts.append('<p class="post-link"><a href="/posts/' + slug + '.html">Read the original post \u2192</a></p>')
        parts.append('</section>')
        out.append('\n'.join(parts))
    print('essay sections:', len(sections), 'photos:', photo_count)
    if photo_count != 31:
        raise ValueError('essay photo count is %d, expected 31' % photo_count)
    return '\n'.join(out)


def build_posts(posts):
    (ROOT / 'posts').mkdir(exist_ok=True)
    if len(posts) != 16:
        raise ValueError('parsed %d posts, expected 16' % len(posts))
    for post, slug, title in zip(posts, POST_SLUGS, POST_TITLES):
        body = paras_to_html(post['body'])
        figs = []
        for fn in POST_PHOTOS[slug]:
            figs.append(figure(fn))
        body_html = '<section class="layer">\n' + body
        if figs:
            body_html += '\n' + '\n'.join(figs)
        body_html += ('\n<p class="back-link"><a href="/what-the-world-has-taught-me.html">'
                      '\u2190 Back to: What the World Has Taught Me</a></p>\n</section>')
        url = 'https://tigertyagarajan.com/posts/' + slug + '.html'
        desc = title + ' \u2014 originally posted on LinkedIn ' + post['date'] + ', preserved on Tiger Bytes.'
        page = make_page(title, url, desc, post['date'], 'ORIGINALLY POSTED ON LINKEDIN', body_html,
                         'Originally posted on LinkedIn \u2014 preserved here on Tiger Bytes.')
        (ROOT / 'posts' / (slug + '.html')).write_text(page, encoding='utf-8')
        print('post', slug, post['date'], len(post['body']), 'paragraphs/lines,', len(POST_PHOTOS[slug]), 'photos')
    print('posts total photos:', sum(len(v) for v in POST_PHOTOS.values()))


def edit_index():
    idx = (ROOT / 'index.html').read_text(encoding='utf-8')
    card = ('<article class="card"><span class="tag">TRAVEL</span><h3>What the World Has Taught Me</h3>'
            '<p>Sixteen stops, three years, one lesson \u2014 a life of travel, done properly, is not a collection of places. It is an education.</p>'
            '<p><a class="btn btn-accent" href="/what-the-world-has-taught-me.html">Read the essay \u2192</a></p></article>')
    marker = '<section id="beyond"><div class="wrap"><h2>Beyond work</h2><div class="grid">'
    if idx.count(marker) != 1:
        raise ValueError('beyond section marker count is %d' % idx.count(marker))
    if 'what-the-world-has-taught-me.html' in idx:
        raise ValueError('index already links the essay')
    new = idx.replace(marker, marker + card, 1)
    if len(new) - len(idx) != len(card):
        raise ValueError('index edit changed more than the card')
    (ROOT / 'index.html').write_text(new, encoding='utf-8')
    print('index card inserted, bytes added:', len(card))


def check_no_leaks(pages):
    bad = ['[Photos:', '[Photo:', 'Production notes', 'URN:', 'per Tiger', 'corkboard, placed here']
    for name, content in pages:
        for b in bad:
            if b in content:
                raise ValueError('leaked marker in ' + name + ': ' + b)


def main():
    global ALT, TEMPLATE_HEAD
    tpl = (ROOT / 'leading-with-curiosity.html').read_text(encoding='utf-8')
    m = re.search(r'<head.*?</head>', tpl, re.S)
    if not m:
        raise ValueError('no head in template')
    TEMPLATE_HEAD = m.group(0)
    ALT = load_alt_texts()
    print('alt texts loaded:', len(ALT))
    for slug, files in POST_PHOTOS.items():
        for fn in files:
            if not (ROOT / 'assets' / fn).exists():
                raise ValueError('missing asset: ' + fn)
    sections = parse_essay()
    headings = [s['heading'] for s in sections if s['heading']]
    print('essay headings:', headings)
    missing = [h for h in STOP_TO_POST if h not in headings]
    if missing:
        raise ValueError('stop headings not found in essay: ' + str(missing))
    essay_body = build_essay(sections)
    desc = ('What the World Has Taught Me \u2014 sixteen stops, three years, one lesson: '
            'a life of travel, done properly, is not a collection of places. It is an education.')
    essay_page = make_page('What the World Has Taught Me',
                          'https://tigertyagarajan.com/what-the-world-has-taught-me.html',
                          desc, 'November 7, 2026', 'BEYOND WORK \u00b7 TRAVEL', essay_body,
                          'What the World Has Taught Me \u2014 a Tiger Bytes essay.')
    ESSAY_FILE.write_text(essay_page, encoding='utf-8')
    posts = parse_posts()
    for p in posts:
        print('parsed post:', p['heading'], p['date'])
    build_posts(posts)
    edit_index()
    pages = [('essay', essay_page)]
    for slug in POST_SLUGS:
        pages.append((slug, (ROOT / 'posts' / (slug + '.html')).read_text(encoding='utf-8')))
    check_no_leaks(pages)
    print('BUILD OK')


if __name__ == '__main__':
    main()
