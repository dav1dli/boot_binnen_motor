#!/usr/bin/env python3
"""Generate German chapter files for chapters 5–10 and 12 from book_de.html.
Chapter 11 (DER AMTLICHE FRAGENKATALOG) is intentionally skipped — that text is
publicly available and easier to insert manually."""
import re, os
ROOT = "/Users/davidliderman/Documents/boot_binnen_motor"

with open(os.path.join(ROOT, "content/de/book_de.html"), encoding="utf-8") as f:
    TXT = f.read()

bk_re = re.compile(r'<a[^>]*id="(bookmark\d+)"[^>]*></a>')
POS = sorted([(m.group(1), m.start()) for m in bk_re.finditer(TXT)], key=lambda x: x[1])
PMAP = {n: p for n, p in POS}

def head_start(p):
    head_match = list(re.finditer(r'<h[1-6][^>]*>', TXT[:p]))
    return head_match[-1].start() if head_match else p

def aside_start(p):
    """Walk back to nearest <aside><p> wrapper that opens this small heading."""
    asd = list(re.finditer(r'<aside>', TXT[:p]))
    return asd[-1].start() if asd else p

def resolve(marker):
    """marker: ('bk', 'bookmarkN') | ('hpos', regex) | ('apos', regex) | ('pos', int)"""
    kind = marker[0]
    if kind == 'bk':
        return head_start(PMAP[marker[1]])
    if kind == 'pos':
        return marker[1]
    pat = marker[1]
    m = re.search(pat, TXT)
    if not m:
        raise ValueError(f"pattern not found: {pat}")
    if kind == 'hpos':
        return head_start(m.start())
    if kind == 'apos':
        return aside_start(m.start())
    return m.start()

def section(start, end):
    return TXT[resolve(start):resolve(end)]

def cleanup(s):
    s = re.sub(r'<a id="bookmark\d+"></a>', '', s)
    s = re.sub(r'<span[^>]*>([^<]*)</span>', r'\1', s)
    s = re.sub(r'</?aside[^>]*>', '', s)
    s = re.sub(r'<figcaption>', '<p><em>', s)
    s = re.sub(r'</figcaption>', '</em></p>', s)
    s = re.sub(r'</?figure[^>]*>', '', s)
    fixes = [
        (r'\bk W\b', 'kW'), (r'\bSp FV\b', 'SpFV'),
        (r'\bRhein Sch PVO\b', 'RheinSchPVO'),
        (r'\bMosel Sch PVO\b', 'MoselSchPVO'),
        (r'\bDonau Sch PVO\b', 'DonauSchPVO'),
        (r'\bBin Sch Str O\b', 'BinSchStrO'),
        (r'\bBodensee Sch O\b', 'BodenseeSchO'),
        (r'\bSee Sch Str O\b', 'SeeSchStrO'),
        (r'\bWasser-\s*straße\b', 'Wasserstraße'),
        (r'\bWasserstrahl-\s*antrieb\b', 'Wasserstrahlantrieb'),
        (r'\beinerim\b', 'einer im'),
        (r'\boderzu\b', 'oder zu'),
        (r'\bgegenübersollte\b', 'gegenüber sollte'),
        (r'\bvon denenjeweils\b', 'von denen jeweils'),
        (r'\bm<sup>z</sup>', 'm<sup>2</sup>'),
        (r'\bm<sup>!</sup>', 'm<sup>3</sup>'),
        (r'\bUberholer\b', 'Überholer'),
        (r'\bUberholen\b', 'Überholen'),
        (r'\bvordem\b', 'vor dem'),
        (r'OOverschmidt', 'Overschmidt'),
        (r'□', ''),
    ]
    for pat, rep in fixes:
        s = re.sub(pat, rep, s)
    s = re.sub(r'<p>\s*</p>', '', s)
    s = re.sub(r'<ul[^>]*>\s*</ul>', '', s)
    return s

def make_h1(s, bk_id):
    return re.sub(r'<h[1-3][^>]*>([^<]+)</h[1-3]>',
                  rf'  <h1 style="font-weight:normal;"><a id="{bk_id}"></a>\1</h1>',
                  s, count=1)

def promote_aside_heading(s, text, h_level='h2', bk_id=None):
    """Convert <p>TEXT</p> wrapped originally in <aside> into proper heading."""
    anchor = f'<a id="{bk_id}"></a>' if bk_id else ''
    return re.sub(rf'<p>\s*{re.escape(text)}\s*</p>',
                  rf'  <{h_level}>{anchor}{text}</{h_level}>',
                  s, count=1, flags=re.I)

def strip_de_imgs(s):
    return re.sub(r'<img[^>]*src="Sportbootfu08hrerschein Binnen Motor[^"]*"[^/]*/>', '', s)

STYLE_BLOCK = '''  <style>
    body {
      font-family: Georgia, "Times New Roman", serif;
      font-size: 16px;
      line-height: 1.65;
      max-width: 850px;
      margin: 40px auto;
      padding: 0 20px;
      color: #222;
    }

    h1,
    h2,
    h3 {
      margin-top: 1.6em;
      font-weight: normal;
    }

    h1 {
      font-size: 2rem;
    }

    h2 {
      font-size: 1.5rem;
    }

    h3 {
      font-size: 1.25rem;
    }

    p {
      margin: 0.8em 0;
    }

    aside {
      font-size: 0.95em;
      background: #f7f7f7;
      padding: 10px 12px;
      margin: 1em 0;
      border-left: 4px solid #ccc;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 1.2em 0;
      font-size: 0.95em;
    }

    td,
    th {
      border: 1px solid #ccc;
      padding: 8px;
      vertical-align: top;
    }

    img {
      max-width: 100%;
      height: auto;
      display: block;
      margin: 1.2em auto;
    }
  </style>'''

def wrap(title, body_inner, prev=None, idx='sbf-binnen-de-01_1.html', nxt=None):
    nav = []
    if prev: nav.append(f'<a href="{prev}">Zurück</a>')
    if idx:  nav.append(f'<a href="{idx}">Inhalt</a>')
    if nxt:  nav.append(f'<a href="{nxt}">Vorwärts</a>')
    nav_html = '  <p>' + ' '.join(nav) + '</p>\n' if nav else ''
    return f'''<html>

<head>
  <meta content="text/html; charset=utf-8" http-equiv="content-type" />
  <title>{title}</title>
{STYLE_BLOCK}
</head>

<body>
{body_inner}
{nav_html}</body>

</html>
'''

def write(name, content):
    p = os.path.join(ROOT, "content/de", name)
    open(p, "w", encoding="utf-8").write(content)
    print(f"  wrote {name}")

def imgs_block(names, prefix='../../images/'):
    return '\n'.join(f'  <img alt="" src="{prefix}{n}" />' for n in names) + '\n'

OCR_NOTE = '\n  <p><em>Hinweis: Bilder und Bildunterschriften aus der Originalausgabe; einzelne Tafelzeichen-Beschriftungen entstammen dem unverbesserten OCR und können Fehler enthalten.</em></p>\n'

# ============== CHAPTER 5 ==============
# 05: RUND UMS BOOT chapter intro + Baumaterial. Pre-bookmark26 content. Use BAUMATERIAL pos as start.
sec = section(('apos', r'DAS BAUMATERIAL'), ('apos', r'BOOTSTYPEN'))
sec = cleanup(sec)
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_rund_ums_boot"></a>RUND UMS BOOT</h1>\n' \
      + '  <h2><a id="bookmark_baumaterial"></a>DAS BAUMATERIAL</h2>\n' + sec
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-122.jpg','SBF-binnen-motor-121.jpg','SBF-binnen-motor-123.jpg'])
write('sbf-binnen-de-05.html', wrap('Sportbootführerschein Binnen – Rund ums Boot', sec,
    prev='sbf-binnen-de-04_2.html', nxt='sbf-binnen-de-05_1.html'))

# 05_1: Bootstypen — between BOOTSTYPEN aside and bookmark26 (VERDRÄNGER)
sec = section(('apos', r'BOOTSTYPEN'), ('bk', 'bookmark26'))
sec = cleanup(sec)
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_bootstypen"></a>BOOTSTYPEN</h1>\n' + sec
# Promote subtype names to h2
for st in ['Schlauchboote','Außenborder-Sportboote','Innenborder-Sportboote',
          'Daycruiser','Halbkajüte','Kajütboote oder Kreuzer','Motoryachten']:
    sec = re.sub(rf'<p>\s*{re.escape(st)}\s*</p>', rf'  <h2>{st}</h2>', sec, count=1)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-124.jpg','SBF-binnen-motor-125.jpg',
                    'SBF-binnen-motor-126.jpg','SBF-binnen-motor-128.jpg','SBF-binnen-motor-127.jpg'])
write('sbf-binnen-de-05_1.html', wrap('Sportbootführerschein Binnen – Bootstypen', sec,
    prev='sbf-binnen-de-05.html', nxt='sbf-binnen-de-05_2.html'))

# 05_2 VERDRÄNGER UND GLEITER (bookmark26..29) with subs 27, 28
sec = section(('bk','bookmark26'), ('bk','bookmark29'))
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark26')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Rumpfgeschwindigkeit[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark27"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Dynamischer Auftrieb[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark28"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-129.jpg','SBF-binnen-motor-130.jpg',
                    'SBF-binnen-motor-131.jpg','SBF-binnen-motor-132.jpg'])
write('sbf-binnen-de-05_2.html', wrap('Sportbootführerschein Binnen – Verdränger und Gleiter', sec,
    prev='sbf-binnen-de-05_1.html', nxt='sbf-binnen-de-06.html'))

# ============== CHAPTER 6 ==============
# 06 chapter intro + MOTORENKUNDE (bookmark29..32)
sec = section(('bk','bookmark29'), ('bk','bookmark32'))
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark29')
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_bootsmotor"></a>DER BOOTSMOTOR</h1>\n' \
      + sec.replace('<h1 ', '<h2 ', 1).replace('</h1>', '</h2>', 1)
# Re-add as h1 not h2 because our title above is h1; chapter intro section. Keep as h2.
sec = re.sub(r'<h[2-6][^>]*>([^<]*Benzin- und Dieselmotor[^<]*)</h[2-6]>',
             r'  <h3><a id="bookmark30"></a>\1</h3>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Zweitakter und Viertakter[^<]*)</h[2-6]>',
             r'  <h3><a id="bookmark31"></a>\1</h3>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor_1-133.jpg','SBF-binnen-motor-135.jpg','SBF-binnen-motor-136.png'])
write('sbf-binnen-de-06.html', wrap('Sportbootführerschein Binnen – Der Bootsmotor', sec,
    prev='sbf-binnen-de-05_2.html', nxt='sbf-binnen-de-06_1.html'))

# 06_1 DER AUSSENBORDMOTOR (bookmark32..35) + Außenborderbedienung 33 + Außenbordertrimm 34
sec = section(('bk','bookmark32'), ('bk','bookmark35'))
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark32')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Außenborderbedienung[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark33"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Außenbordertrimm[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark34"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-137.jpg','SBF-binnen-motor-138.jpg'])
write('sbf-binnen-de-06_1.html', wrap('Sportbootführerschein Binnen – Der Außenbordmotor', sec,
    prev='sbf-binnen-de-06.html', nxt='sbf-binnen-de-06_2.html'))

# 06_2 ANTRIEBSANLAGEN UND GETRIEBE (bookmark35..37) + Schaltung 36
sec = section(('bk','bookmark35'), ('bk','bookmark37'))
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark35')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Schaltung[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark36"></a>\1</h2>', sec)
# Promote Z-Antrieb / V-Antrieb / Wasserstrahlantrieb / Wellenanlage subheadings
for st in ['Der Z-Antrieb','Die konventionelle Wellenanlage','Der V-Antrieb','Der Wasserstrahlantrieb']:
    sec = re.sub(rf'<p>\s*{re.escape(st)}\s*</p>', rf'  <h3>{st}</h3>', sec, count=1)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-140.jpg','SBF-binnen-motor-139.jpg',
                    'SBF-binnen-motor-141.jpg','SBF-binnen-motor-142.jpg'])
write('sbf-binnen-de-06_2.html', wrap('Sportbootführerschein Binnen – Antriebsanlagen und Getriebe', sec,
    prev='sbf-binnen-de-06_1.html', nxt='sbf-binnen-de-06_3.html'))

# 06_3 KÜHLSYSTEM (37..38)
sec = section(('bk','bookmark37'), ('bk','bookmark38'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark37'); sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor_1-142.jpg'])
write('sbf-binnen-de-06_3.html', wrap('Sportbootführerschein Binnen – Kühlsystem', sec,
    prev='sbf-binnen-de-06_2.html', nxt='sbf-binnen-de-06_4.html'))

# 06_4 PROPELLER (38..42)
sec = section(('bk','bookmark38'), ('bk','bookmark42'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark38')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Durchmesser und Steigung[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark39"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Rechtsgängig und rechtsdrehend[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark40"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Radeffekt[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark41"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-145.jpg','SBF-binnen-motor-146.png','SBF-binnen-motor-147.jpg'])
write('sbf-binnen-de-06_4.html', wrap('Sportbootführerschein Binnen – Propeller', sec,
    prev='sbf-binnen-de-06_3.html', nxt='sbf-binnen-de-06_5.html'))

# 06_5 DIE STEUERUNG (42..43)
sec = section(('bk','bookmark42'), ('bk','bookmark43'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark42'); sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor_1-146.jpg','SBF-binnen-motor-148.jpg'])
write('sbf-binnen-de-06_5.html', wrap('Sportbootführerschein Binnen – Die Steuerung', sec,
    prev='sbf-binnen-de-06_4.html', nxt='sbf-binnen-de-06_6.html'))

# 06_6 DIE TANKANLAGE (43..45) + Tanken 44
sec = section(('bk','bookmark43'), ('bk','bookmark45'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark43')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Tanken[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark44"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-149.png','SBF-binnen-motor-149.jpg'])
write('sbf-binnen-de-06_6.html', wrap('Sportbootführerschein Binnen – Die Tankanlage', sec,
    prev='sbf-binnen-de-06_5.html', nxt='sbf-binnen-de-06_7.html'))

# 06_7 GASANLAGEN (45..46)
sec = section(('bk','bookmark45'), ('bk','bookmark46'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark45'); sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-150.jpg'])
write('sbf-binnen-de-06_7.html', wrap('Sportbootführerschein Binnen – Gasanlagen', sec,
    prev='sbf-binnen-de-06_6.html', nxt='sbf-binnen-de-06_8.html'))

# 06_8 BORDBATTERIE + Landstrom (BORDBATTERIE pos..bookmark47)
sec = section(('apos', r'DIE BORDBATTERIE'), ('bk','bookmark47'))
sec = cleanup(sec)
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_bordbatterie"></a>DIE BORDBATTERIE</h1>\n' \
      + re.sub(r'<p>\s*DIE BORDBATTERIE\s*</p>', '', sec, count=1)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Landstrom[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark46"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
write('sbf-binnen-de-06_8.html', wrap('Sportbootführerschein Binnen – Die Bordbatterie', sec,
    prev='sbf-binnen-de-06_7.html', nxt='sbf-binnen-de-06_9.html'))

# 06_9 SICHERHEITSAUSRÜSTUNG (47..48)
sec = section(('bk','bookmark47'), ('bk','bookmark48'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark47'); sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-151.jpg','SBF-binnen-motor_1-152.jpg'])
write('sbf-binnen-de-06_9.html', wrap('Sportbootführerschein Binnen – Sicherheitsausrüstung', sec,
    prev='sbf-binnen-de-06_8.html', nxt='sbf-binnen-de-06_10.html'))

# 06_10 BRANDSCHUTZ (48..51) + Feuerlöscher 49 + Feuerbekämpfung 50
sec = section(('bk','bookmark48'), ('bk','bookmark51'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark48')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Feuerlöscher[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark49"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Feuerbekämpfung[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark50"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor_1-153.jpg','SBF-binnen-motor-154.jpg'])
write('sbf-binnen-de-06_10.html', wrap('Sportbootführerschein Binnen – Brandschutz', sec,
    prev='sbf-binnen-de-06_9.html', nxt='sbf-binnen-de-06_11.html'))

# 06_11 Motorüberwachung (51..53) + Motorstörungen 52
sec = section(('bk','bookmark51'), ('bk','bookmark53'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark51')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Motorstörungen[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark52"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
write('sbf-binnen-de-06_11.html', wrap('Sportbootführerschein Binnen – Motorüberwachung', sec,
    prev='sbf-binnen-de-06_10.html', nxt='sbf-binnen-de-07.html'))

# ============== CHAPTER 7 ==============
# 07: chapter intro + ABLEGEN (Ablegen vom Steg) + Ablegen von der Boje (53)
# Pre-bookmark53 area starts after bookmark52 (Motorstörungen) end.
# We took 06_11 up to bookmark53; so 07 starts at bookmark53? But RU 07 includes
# "ABLEGEN VOM STEG" which comes BEFORE "Ablegen von der Boje".
# In DE source, "Ablegen vom Steg" appears at content pos. Let me search.
# Strategy: 07 = from "FAHREN MIT DEM MOTORBOOT" (no bookmark) or from end of 52 to bookmark54.
# Use the bookmark53 head start as the section root, but include the preceding
# text. It seems Ablegen vom Steg fragment isn't bookmarked. We'll grab from end
# of bookmark52's section to bookmark54. We already used end of 52→53 in 06_11.
# Instead: 07 = bookmark53..bookmark54 (which is just "Ablegen von der Boje" sub).
# Add chapter title and section heading manually.
sec = section(('bk','bookmark53'), ('bk','bookmark54'))
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark53')
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_fahren"></a>FAHREN MIT DEM MOTORBOOT</h1>\n' \
      '  <h2><a id="bookmark_ablegen"></a>ABLEGEN</h2>\n' + sec
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor_1-155.jpg','SBF-binnen-motor-158.jpg',
                    'SBF-binnen-motor-159.jpg','SBF-binnen-motor_1-158.jpg','SBF-binnen-motor_1-159.jpg'])
write('sbf-binnen-de-07.html', wrap('Sportbootführerschein Binnen – Fahren mit dem Motorboot', sec,
    prev='sbf-binnen-de-06_11.html', nxt='sbf-binnen-de-07_1.html'))

# 07_1 Wenden auf engem Raum (54..55)
sec = section(('bk','bookmark54'), ('bk','bookmark55'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark54')
# DE has split "WENDEN AUf"+"ENGEM RAUM" — combine
sec = re.sub(
    r'<h1[^>]*><a id="bookmark54"></a>WENDEN AUf</h1>\s*<h[1-3][^>]*>ENGEM RAUM</h[1-3]>',
    r'  <h1 style="font-weight:normal;"><a id="bookmark54"></a>WENDEN AUF ENGEM RAUM</h1>',
    sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-163.jpg'])
write('sbf-binnen-de-07_1.html', wrap('Sportbootführerschein Binnen – Wenden auf engem Raum', sec,
    prev='sbf-binnen-de-07.html', nxt='sbf-binnen-de-07_2.html'))

# 07_2 ANLEGEN (55..57) + Anlegen an der Boje 56
sec = section(('bk','bookmark55'), ('bk','bookmark57'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark55')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Anlegen an der Boje[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark56"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-163.png','SBF-binnen-motor_1-164.jpg',
                    'SBF-binnen-motor_1-165.jpg','SBF-binnen-motor_1-166.jpg',
                    'SBF-binnen-motor-171.jpg','SBF-binnen-motor-172.jpg'])
write('sbf-binnen-de-07_2.html', wrap('Sportbootführerschein Binnen – Anlegen', sec,
    prev='sbf-binnen-de-07_1.html', nxt='sbf-binnen-de-07_3.html'))

# 07_3 MENSCH/BOJE ÜBER BORD (57..58)
sec = section(('bk','bookmark57'), ('bk','bookmark58'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark57'); sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor_1-169.jpg','SBF-binnen-motor-173.jpg',
                    'SBF-binnen-motor-174.jpg','SBF-binnen-motor-175.jpg','SBF-binnen-motor-176.jpg'])
write('sbf-binnen-de-07_3.html', wrap('Sportbootführerschein Binnen – Mensch/Boje über Bord', sec,
    prev='sbf-binnen-de-07_2.html', nxt='sbf-binnen-de-07_4.html'))

# 07_4 FAHREN IM STROM + Stromhäfen (FAHREN IM STROM aside pos..bookmark60)
sec = section(('apos', r'FAHREN IM STROM'), ('bk','bookmark60'))
sec = cleanup(sec)
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_fahren_im_strom"></a>FAHREN IM STROM</h1>\n' \
      + re.sub(r'<p>\s*FAHREN IM STROM\s*</p>', '', sec, count=1)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Stromhäfen[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark59"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-177.jpg','SBF-binnen-motor-178.jpg'])
write('sbf-binnen-de-07_4.html', wrap('Sportbootführerschein Binnen – Fahren im Strom', sec,
    prev='sbf-binnen-de-07_3.html', nxt='sbf-binnen-de-07_5.html'))

# 07_5 QUEREN VON BUG- UND HECKWELLEN (60..61)
sec = section(('bk','bookmark60'), ('bk','bookmark61'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark60'); sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-179.jpg','SBF-binnen-motor-180.jpg'])
write('sbf-binnen-de-07_5.html', wrap('Sportbootführerschein Binnen – Queren von Bug- und Heckwellen', sec,
    prev='sbf-binnen-de-07_4.html', nxt='sbf-binnen-de-07_6.html'))

# 07_6 SCHLEUSEN (61..63) + Schleusensignale + Schleusengebühren
sec = section(('bk','bookmark61'), ('bk','bookmark63'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark61')
# Promote Schleusensignale and Schleusengebühren if found
for st, bk in [('Schleusensignale','bookmark62_1'),('Schleusengebühren','bookmark62_2')]:
    sec = re.sub(rf'<p>\s*{re.escape(st)}\s*</p>', rf'  <h2><a id="{bk}"></a>{st}</h2>', sec, count=1)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-182.jpg','SBF-binnen-motor-181.jpg',
                    'SBF-binnen-motor_1-178.jpg','SBF-binnen-motor-182.png','SBF-binnen-motor_1-183.jpg'])
write('sbf-binnen-de-07_6.html', wrap('Sportbootführerschein Binnen – Schleusen', sec,
    prev='sbf-binnen-de-07_5.html', nxt='sbf-binnen-de-07_7.html'))

# 07_7 ANKER (63..67) + Ankertypen 64 + Ankerleine 65 + Ankerplatz 66
sec = section(('bk','bookmark63'), ('bk','bookmark67'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark63')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Die Ankertypen[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark64"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Ankerleine und Ankerkette[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark65"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Der Ankerplatz[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark66"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-186.png','SBF-binnen-motor-187.png','SBF-binnen-motor_1-188.jpg'])
write('sbf-binnen-de-07_7.html', wrap('Sportbootführerschein Binnen – Anker', sec,
    prev='sbf-binnen-de-07_6.html', nxt='sbf-binnen-de-07_8.html'))

# 07_8 ANKERMANÖVER + Ankern + Ankerlichten (ANKERMANÖVER pos..bookmark68)
sec = section(('apos', r'ANKERMANÖVER'), ('bk','bookmark68'))
sec = cleanup(sec)
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_ankermanoever"></a>ANKERMANÖVER</h1>\n' \
      + re.sub(r'<p>\s*ANKERMANÖVER\s*</p>', '', sec, count=1)
sec = re.sub(r'<p>\s*Das Ankern\s*</p>', r'  <h2><a id="bookmark66_2"></a>Das Ankern</h2>', sec, count=1)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Ankerlichten[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark67"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-189.jpg','SBF-binnen-motor_1-190.jpg'])
write('sbf-binnen-de-07_8.html', wrap('Sportbootführerschein Binnen – Ankermanöver', sec,
    prev='sbf-binnen-de-07_7.html', nxt='sbf-binnen-de-07_9.html'))

# 07_9 SCHLEPPEN (68..72) + Längsseits 69 + Wasserski 70 + Gesetzliche 71
sec = section(('bk','bookmark68'), ('bk','bookmark72'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark68')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Längsseits schleppen[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark69"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*WASSERSKI[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark70"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Gesetzliche Bestimmungen[^<]*)</h[2-6]>',
             r'  <h3><a id="bookmark71"></a>\1</h3>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-192.jpg','SBF-binnen-motor-193.jpg',
                    'SBF-binnen-motor-194.jpg','SBF-binnen-motor-195.jpg',
                    'SBF-binnen-motor-196.jpg','SBF-binnen-motor-197.jpg',
                    'SBF-binnen-motor-198.jpg','SBF-binnen-motor-199.jpg'])
write('sbf-binnen-de-07_9.html', wrap('Sportbootführerschein Binnen – Schleppen', sec,
    prev='sbf-binnen-de-07_8.html', nxt='sbf-binnen-de-07_10.html'))

# 07_10 HAVARIE (72..73)
sec = section(('bk','bookmark72'), ('bk','bookmark73'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark72'); sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-200.jpg'])
write('sbf-binnen-de-07_10.html', wrap('Sportbootführerschein Binnen – Havarie', sec,
    prev='sbf-binnen-de-07_9.html', nxt='sbf-binnen-de-08.html'))

# ============== CHAPTER 8 ==============
# RU 08 has H "ВЫСОКОЕ И НИЗКОЕ ДАВЛЕНИЕ" (Hoch und Tief) + LAND-/SEEWIND + Gewitter + Sturmwarnungen
# DE bookmark73 = LAND- UND SEEWIND, GEWITTER. Hoch und Tief is at "Hoch und Tief" pos.
sec = section(('apos', r'HOCH UND TIEF'), ('bk','bookmark76'))
sec = cleanup(sec)
# Replace heading "HOCH UND TIEF" para → h1
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_wetter_hoch"></a>WETTERKUNDE</h1>\n' \
      '  <h2><a id="bookmark_hoch_tief"></a>HOCH UND TIEF</h2>\n' \
      + re.sub(r'<p>\s*HOCH UND TIEF\s*</p>', '', sec, count=1)
sec = re.sub(r'<h[2-6][^>]*>([^<]*LAND- UND SEEWIND[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark73"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Gewitter[^<]*)</h[2-6]>',
             r'  <h3><a id="bookmark74"></a>\1</h3>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Sturmwarnungen[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark75"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor_1-200.jpg','SBF-binnen-motor-202.jpg','SBF-binnen-motor-203.jpg'])
write('sbf-binnen-de-08.html', wrap('Sportbootführerschein Binnen – Wetterkunde', sec,
    prev='sbf-binnen-de-07_10.html', nxt='sbf-binnen-de-09.html'))

# ============== CHAPTER 9 ==============
sec = section(('bk','bookmark76'), ('bk','bookmark78'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark76')
sec = re.sub(r'<h[2-6][^>]*>([^<]*10 Goldenen Regeln[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark77"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-204.jpg'])
write('sbf-binnen-de-09.html', wrap('Sportbootführerschein Binnen – Umweltschutz', sec,
    prev='sbf-binnen-de-08.html', nxt='sbf-binnen-de-10.html'))

# ============== CHAPTER 10 ==============
# 10 = bookmark78..bookmark82 (DER BOOTSTRANSPORT..before Fragenkatalog)
sec = section(('bk','bookmark78'), ('bk','bookmark82'))
sec = cleanup(sec); sec = make_h1(sec, 'bookmark78')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Der Trailer[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark79"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Fahrpraxis[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark80"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Ab- und Aufslippen[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark81"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-205.jpg','SBF-binnen-motor-205.png','SBF-binnen-motor-206.jpg'])
write('sbf-binnen-de-10.html', wrap('Sportbootführerschein Binnen – Bootstransport', sec,
    prev='sbf-binnen-de-09.html', nxt='sbf-binnen-de-12.html'))

# ============== CHAPTER 12 ==============
# 12 = bookmark90..end (KLEINES SEEMÄNNISCHES WÖRTERBUCH + STICHWORTVERZEICHNIS)
body_end_pos = TXT.rfind('</body>')
sec = TXT[head_start(PMAP['bookmark90']):body_end_pos]
sec = cleanup(sec); sec = make_h1(sec, 'bookmark90')
# STICHWORTVERZEICHNIS marker
sec = re.sub(r'<p>\s*STICHWORTVERZEICHNIS\s*</p>',
             r'  <h2><a id="bookmark91"></a>STICHWORTVERZEICHNIS</h2>', sec, count=1)
sec = strip_de_imgs(sec)
sec += imgs_block(['SBF-binnen-motor-263.jpg','SBF-binnen-motor-265.jpg',
                    'SBF-binnen-motor-267.jpg','SBF-binnen-motor-268.jpg'])
sec += '\n  <p><em>Hinweis: Wörterbuch und Stichwortverzeichnis aus dem unverbesserten OCR; Begriffsschreibweisen müssen mit der Druckausgabe abgeglichen werden.</em></p>\n'
write('sbf-binnen-de-12.html', wrap('Sportbootführerschein Binnen – Kleines Seemännisches Wörterbuch', sec,
    prev='sbf-binnen-de-10.html', nxt=None))

print("Done.")
