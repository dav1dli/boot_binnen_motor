#!/usr/bin/env python3
"""Generate German chapter files for chapters 2, 3, 4 from book_de.html."""
import re, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if False else "/Users/davidliderman/Documents/boot_binnen_motor"

with open(os.path.join(ROOT, "content/de/book_de.html"), encoding="utf-8") as f:
    TXT = f.read()

bk_re = re.compile(r'<a[^>]*id="(bookmark\d+)"[^>]*></a>')
POS = sorted([(m.group(1), m.start()) for m in bk_re.finditer(TXT)], key=lambda x: x[1])
PMAP = {n: p for n, p in POS}

def find_heading_start(p):
    head_match = list(re.finditer(r'<h[1-6][^>]*>', TXT[:p]))
    return head_match[-1].start() if head_match else p

def section(start_bk, end_bk):
    s = find_heading_start(PMAP[start_bk])
    e = find_heading_start(PMAP[end_bk])
    return TXT[s:e]

# Cleanup pass — preserve original text, fix OCR artefacts, strip OCR-export wrappers
def cleanup(s):
    # Empty bookmark anchors — drop
    s = re.sub(r'<a id="bookmark\d+"></a>', '', s)
    # span wrappers — unwrap
    s = re.sub(r'<span[^>]*>([^<]*)</span>', r'\1', s)
    # aside wrappers — unwrap (OCR used them as page-break markers)
    s = re.sub(r'</?aside[^>]*>', '', s)
    # figure → keep as div-less; figcaption → italic paragraph
    s = re.sub(r'<figcaption>', '<p><em>', s)
    s = re.sub(r'</figcaption>', '</em></p>', s)
    s = re.sub(r'</?figure[^>]*>', '', s)
    # OCR artefacts
    fixes = [
        (r'\bk W\b', 'kW'),
        (r'\bSp FV\b', 'SpFV'),
        (r'\bRhein Sch PVO\b', 'RheinSchPVO'),
        (r'\bMosel Sch PVO\b', 'MoselSchPVO'),
        (r'\bDonau Sch PVO\b', 'DonauSchPVO'),
        (r'\bBin Sch Str O\b', 'BinSchStrO'),
        (r'\bBodensee Sch O\b', 'BodenseeSchO'),
        (r'\bSee Sch Str O\b', 'SeeSchStrO'),
        (r'\bWasser-\s*straße\b', 'Wasserstraße'),
        (r'\bKfz-Führer-\s*scheins\b', 'Kfz-Führerscheins'),
        (r'\bWeblein-\s*stek\b', 'Webleinstek'),
        (r'\beinerim\b', 'einer im'),
        (r'\boderzu\b', 'oder zu'),
        (r'\bgegenübersollte\b', 'gegenüber sollte'),
        (r'\bvon denenjeweils\b', 'von denen jeweils'),
        (r'einer/s Rettungsweste/ Sicherheitsgurtes', 'einer Rettungsweste / eines Sicherheitsgurtes'),
        (r'\bm<sup>z</sup>', 'm<sup>2</sup>'),
        (r'\bm<sup>!</sup>', 'm<sup>3</sup>'),
        (r'(\d)m<sup>2</sup>(?=Segel)', r'\1 m<sup>2</sup> '),
        (r'\bUberholer\b', 'Überholer'),
        (r'\bUberholen\b', 'Überholen'),
        (r'\bvordem\b', 'vor dem'),
        (r'\bvor\s*dem\s*Heck\b', 'vor dem Heck'),
        (r'\bAchtknoten,\s*Rundtörn', 'Achtknoten, Rundtörn'),
        (r'OOverschmidt', 'Overschmidt'),
        (r'□', ''),
        (r'\bFragen;\s*und Antworten', 'Fragen- und Antworten'),
        (r'»großer Fahrt«\s*-', '»großer Fahrt« –'),
        (r'(?<=[a-zäöüß0-9])-\s*\n\s*(?=[a-zäöüß])', ''),  # de-hyphenate line breaks
    ]
    for pat, rep in fixes:
        s = re.sub(pat, rep, s)
    # Collapse runs of empty whitespace tags
    s = re.sub(r'<p>\s*</p>', '', s)
    s = re.sub(r'<ul[^>]*>\s*</ul>', '', s)
    return s

# Replace original heading h2/h3 with h1 + bookmark id
def make_h1(s, bk_id, level_pat=r'<h[1-3][^>]*>([^<]+)</h[1-3]>'):
    return re.sub(level_pat,
                  rf'  <h1 style="font-weight:normal;"><a id="{bk_id}"></a>\1</h1>',
                  s, count=1)

# Drop figure-image blocks that reference Sportbootfu08hrerschein Binnen Motor-N.png/jpg
# (these are the broken-quality OCR-source image refs; RU file provides clean ones)
def strip_de_imgs(s):
    s = re.sub(r'<img[^>]*src="Sportbootfu08hrerschein Binnen Motor[^"]*"[^/]*/>', '', s)
    return s

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
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  wrote {name}")

# === Per-file generation ===

# 02_1
sec = section('bookmark2', 'bookmark3')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark3')
sec = strip_de_imgs(sec)
# Insert RU image SBF-binnen-motor-7.jpg after first 2 list items (matches RU structure)
# Easier: prepend image block before the closing of the </h1>'s following bullet list
body = sec + '\n  <img alt="" src="../../images/SBF-binnen-motor-7.jpg" style="width:139pt;height:60pt;" />\n'
# Actually better to keep RU positioning: image was inside the original figure, between two ul blocks. Place after the first <ul>.
# Simpler: just trust the cleaned flow — image at top after h1.
# Reorder: pull the image up right after the heading.
# Simple: replace last appearance with empty, prepend img after </h1>.
body = re.sub(r'\n  <img alt="" src="\.\./\.\./images/SBF-binnen-motor-7\.jpg"[^/]*/>\n$', '', body)
body = re.sub(r'(</h1>)', r'\1\n  <img alt="" src="../../images/SBF-binnen-motor-7.jpg" style="width:139pt;height:60pt;" />', body, count=1)
write('sbf-binnen-de-02_1.html', wrap(
    'Sportbootführerschein Binnen – Wie bekommt man den Führerschein?',
    body, prev='sbf-binnen-de-02.html', nxt='sbf-binnen-de-02_2.html'))

# 02_2
sec = section('bookmark3', 'bookmark4')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark4')
sec = strip_de_imgs(sec)
write('sbf-binnen-de-02_2.html', wrap(
    'Sportbootführerschein Binnen – Die Prüfung',
    sec, prev='sbf-binnen-de-02_1.html', nxt='sbf-binnen-de-02_3.html'))

# 02_3
sec = section('bookmark4', 'bookmark5')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark5')
sec = strip_de_imgs(sec)
write('sbf-binnen-de-02_3.html', wrap(
    'Sportbootführerschein Binnen – Der Entzug des Führerscheins',
    sec, prev='sbf-binnen-de-02_2.html', nxt='sbf-binnen-de-03.html'))

# 03 — Verkehrsvorschriften (chapter intro)
# RU 03 has chapter title VERKEHRSKUNDE then h1 ПРАВИЛА ДВИЖЕНИЯ. DE only has VERKEHRSVORSCHRIFTEN at bookmark5.
sec = section('bookmark5', 'bookmark6')
sec = cleanup(sec)
# Make double heading: chapter title VERKEHRSKUNDE + section title DIE VERKEHRSVORSCHRIFTEN
sec = make_h1(sec, 'bookmark6_root')  # placeholder
sec = re.sub(r'<h1[^>]*><a id="bookmark6_root"></a>([^<]+)</h1>',
             r'  <h1 style="font-weight:normal;"><a id="bookmark5_chapter"></a>VERKEHRSKUNDE</h1>\n  <h2><a id="bookmark5"></a>\1</h2>',
             sec, count=1)
sec = strip_de_imgs(sec)
# Add RU images at end (SBF-binnen-motor-8 + 9)
sec += '\n  <img alt="" src="../../images/SBF-binnen-motor-8.jpg" />\n  <img alt="" src="../../images/SBF-binnen-motor-9.jpg" />\n'
write('sbf-binnen-de-03.html', wrap(
    'Sportbootführerschein Binnen – Verkehrsvorschriften',
    sec, prev='sbf-binnen-de-02_3.html', nxt='sbf-binnen-de-03_1.html'))

# 03_1 Kleinfahrzeuge
sec = section('bookmark6', 'bookmark7')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark6')
sec = strip_de_imgs(sec)
sec += '\n  <img alt="" src="../../images/SBF-binnen-motor-10.jpg" />\n'
write('sbf-binnen-de-03_1.html', wrap(
    'Sportbootführerschein Binnen – Kleinfahrzeuge',
    sec, prev='sbf-binnen-de-03.html', nxt='sbf-binnen-de-03_2.html'))

# 03_2 Führerscheine (table)
sec = section('bookmark7', 'bookmark8')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark7')
sec = strip_de_imgs(sec)
write('sbf-binnen-de-03_2.html', wrap(
    'Sportbootführerschein Binnen – Führerscheine',
    sec, prev='sbf-binnen-de-03_1.html', nxt='sbf-binnen-de-03_3.html'))

# 03_3 Schiffsführung und Sorgfaltspflicht
sec = section('bookmark8', 'bookmark9')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark8')
sec = strip_de_imgs(sec)
# Convert the inline "Merke" paragraphs into proper <aside>
sec = re.sub(r'<p>Merke</p>\s*<p>([^<]+)</p>',
             r'<aside><p><strong>Merke</strong></p><p>\1</p></aside>', sec)
write('sbf-binnen-de-03_3.html', wrap(
    'Sportbootführerschein Binnen – Schiffsführung und Sorgfaltspflicht',
    sec, prev='sbf-binnen-de-03_2.html', nxt='sbf-binnen-de-03_4.html'))

# 03_4 Geschwindigkeitsbeschränkungen
sec = section('bookmark9', 'bookmark10')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark9')
sec = strip_de_imgs(sec)
# Add Hochwasser as h2
sec = re.sub(r'<p>Hochwasser</p>', r'  <h2>Hochwasser</h2>', sec)
write('sbf-binnen-de-03_4.html', wrap(
    'Sportbootführerschein Binnen – Geschwindigkeitsbeschränkungen',
    sec, prev='sbf-binnen-de-03_3.html', nxt='sbf-binnen-de-03_5.html'))

# 03_5 GEBOTS-, VERBOTS-, HINWEISSCHILDER (image-heavy: the OCR caption text is unreadable)
# Strategy: keep the original German prose between the dropped DE image refs, dropping
# garbled caption fragments. Then attach the cleaner RU image set.
sec_full = section('bookmark10', 'bookmark11')
sec_full = cleanup(sec_full)
sec_full = make_h1(sec_full, 'bookmark10')
# Drop DE image refs (we'll use RU's)
sec_full = strip_de_imgs(sec_full)
# At this point sec_full has heading + many short caption <p>s + the AUSWEICHREGELN section.
# Split at AUSWEICHREGELN
idx_aw = sec_full.find('AUSWEICHREGELN')
if idx_aw == -1:
    sec_05 = sec_full
    sec_06 = ''
else:
    # back up to start of <p> containing AUSWEICHREGELN
    p_open = sec_full.rfind('<p>', 0, idx_aw)
    sec_05 = sec_full[:p_open]
    sec_06 = sec_full[p_open:]
# Add a note that captions of signage need manual review
sec_05_body = sec_05 + (
    '\n  <p><em>Hinweis: Die folgenden Tafelzeichen werden mit den Original-Bildern aus '
    'dem Lehrbuch wiedergegeben. Die Beschriftungen entstammen dem unverbesserten OCR und '
    'können Übertragungsfehler enthalten.</em></p>\n'
)
# Append RU image list for 03_5
ru_imgs_03_5 = [
    'wasserski.png','wassermotorrad.png',
    'SBF-binnen-motor-12.jpg','SBF-binnen-motor-13.jpg',
    'SBF-binnen-motor-14.jpg','SBF-binnen-motor-15.jpg',
    'SBF-binnen-motor-16.jpg','SBF-binnen-motor-17.jpg',
    'SBF-binnen-motor-18.jpg','SBF-binnen-motor-19.jpg',
    'SBF-binnen-motor-20.jpg',
    'explosivestoffe.png','verboteneeinfahrt.png','haltegebot.png',
    'SBF-binnen-motor-22.jpg','SBF-binnen-motor-23.jpg','SBF-binnen-motor-24.jpg',
    'SBF-binnen-motor-25.jpg','SBF-binnen-motor-26.jpg','SBF-binnen-motor-27.jpg',
    'SBF-binnen-motor-28.jpg','SBF-binnen-motor-29.jpg',
    'maxgeschw.png',
    'SBF-binnen-motor-30.jpg','SBF-binnen-motor-31.jpg',
    'SBF-binnen-motor_1-32_1.jpg','SBF-binnen-motor_1-32_2.jpg','SBF-binnen-motor-33.jpg',
    'gebot_langer_ton.png',
    'SBF-binnen-motor_1-16.jpg','SBF-binnen-motor_1-22.jpg',
    'SBF-binnen-motor-35.jpg','SBF-binnen-motor-36.jpg','SBF-binnen-motor-37.jpg',
]
sec_05_body += '\n'.join(f'  <img alt="" src="../../images/{n}" />' for n in ru_imgs_03_5) + '\n'
write('sbf-binnen-de-03_5.html', wrap(
    'Sportbootführerschein Binnen – Gebots-, Verbots-, Hinweisschilder',
    sec_05_body, prev='sbf-binnen-de-03_4.html', nxt='sbf-binnen-de-03_6.html'))

# 03_6 AUSWEICHREGELN (within bookmark10..11 range but no own anchor in DE)
# Extract from where AUSWEICHREGELN appears to the Überholen heading
idx_ub = sec_06.find('Überholen')
if idx_ub != -1:
    # find <p>Überholen heading start
    p_o = sec_06.rfind('<p>', 0, idx_ub)
    sec_06_body = sec_06[:p_o]
    sec_07_body = sec_06[p_o:]
else:
    sec_06_body = sec_06
    sec_07_body = ''
# Convert AUSWEICHREGELN paragraph into h1
sec_06_body = re.sub(r'<p>\s*AUSWEICHREGELN\s*</p>',
                     r'  <h1 style="font-weight:normal;"><a id="bookmark10_ausweichregeln"></a>AUSWEICHREGELN</h1>',
                     sec_06_body, count=1)
ru_imgs_03_6 = [
    'SBF-binnen-motor-38.jpg','SBF-binnen-motor-39.jpg','SBF-binnen-motor-40.jpg',
    'SBF-binnen-motor-41.jpg',
    'kreuzend.png','segelboot-motorboot-weiss.png',
    'SBF-binnen-motor-42.jpg','SBF-binnen-motor-43.jpg',
    'fahrwasser_kreuz.jpg','segelboot-motorboot-ufer.png',
    'SBF-binnen-motor_1-45.jpg','SBF-binnen-motor_1-47.jpg',
    'SBF-binnen-motor-48.jpg','SBF-binnen-motor-50.jpg',
]
sec_06_body += '\n' + '\n'.join(f'  <img alt="" src="../../images/{n}" />' for n in ru_imgs_03_6) + '\n'
write('sbf-binnen-de-03_6.html', wrap(
    'Sportbootführerschein Binnen – Ausweichregeln',
    sec_06_body, prev='sbf-binnen-de-03_5.html', nxt='sbf-binnen-de-03_7.html'))

# 03_7 Überholen (rest of bookmark10..11 range)
sec_07_body = re.sub(r'<p>\s*Überholen\s*</p>',
                     r'  <h1 style="font-weight:normal;"><a id="bookmark10_ueberholen"></a>Überholen</h1>',
                     sec_07_body, count=1)
sec_07_body += '\n  <img alt="" src="../../images/SBF-binnen-motor-51.jpg" />\n'
write('sbf-binnen-de-03_7.html', wrap(
    'Sportbootführerschein Binnen – Überholen',
    sec_07_body, prev='sbf-binnen-de-03_6.html', nxt='sbf-binnen-de-03_8.html'))

# 03_8 FAHRRINNEN- UND FAHRWASSERBEZEICHNUNGEN — image-heavy, severe OCR
sec = section('bookmark11', 'bookmark12')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark11')
sec = strip_de_imgs(sec)
sec += (
    '\n  <p><em>Hinweis: Die Beschriftungen der Tonnen- und Schifffahrtszeichen wurden '
    'aus dem unverbesserten OCR übernommen und können Übertragungsfehler enthalten.</em></p>\n'
)
ru_imgs_03_8 = [
    'linkesuferrechtesufer.png',
    'SBF-binnen-motor-52.jpg','SBF-binnen-motor-53.jpg','SBF-binnen-motor-54.jpg',
    'hindernislinks.png','SBF-binnen-motor-55.jpg','hindernisrechts.png',
    'SBF-binnen-motor-57.jpg','SBF-binnen-motor-58.jpg','SBF-binnen-motor-59.jpg',
    'SBF-binnen-motor-60.jpg',
]
sec += '\n'.join(f'  <img alt="" src="../../images/{n}" />' for n in ru_imgs_03_8) + '\n'
write('sbf-binnen-de-03_8.html', wrap(
    'Sportbootführerschein Binnen – Fahrrinnen- und Fahrwasserbezeichnungen',
    sec, prev='sbf-binnen-de-03_7.html', nxt='sbf-binnen-de-03_9.html'))

# 03_9 BRÜCKEN, WEHRE UND SPERRUNGEN — image-heavy.
# Note: the Schallsignale section in DE may end up at the tail of bookmark12 (no own anchor).
sec = section('bookmark12', 'bookmark13')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark12')
sec = strip_de_imgs(sec)
# Try to detect where SCHALLSIGNALE content begins — check for the word in sec.
# If found, split off into 03_10
sch_idx = sec.find('Schallsignal')
if sch_idx != -1:
    p_o = sec.rfind('<p>', 0, sch_idx)
    sec_09 = sec[:p_o]
    sec_10_seed = sec[p_o:]
else:
    sec_09 = sec
    sec_10_seed = ''
sec_09 += (
    '\n  <p><em>Hinweis: Die Tafelzeichen-Beschriftungen wurden aus dem unverbesserten '
    'OCR übernommen.</em></p>\n'
)
ru_imgs_03_9 = [
    'SBF-binnen-motor-61.jpg','SBF-binnen-motor-62.jpg',
    'empfohlenedurchfahrtmitgegenverkehr.png','empfohlenedurchfahrtohnegegenverkehr2.png',
    'signalisation-brueckendurchfahrt.png','durchfahrtzwischen.png','empfohlenedurchfahrtgruen.png',
    'SBF-binnen-motor-69.jpg','SBF-binnen-motor-70.jpg',
    'SBF-binnen-motor-66.jpg','SBF-binnen-motor-31.jpg',
    'SBF-binnen-motor-63.jpg','SBF-binnen-motor-64.jpg','SBF-binnen-motor-65.jpg',
    'SBF-binnen-motor-67.jpg','SBF-binnen-motor-68.jpg','SBF-binnen-motor-71.jpg',
]
sec_09 += '\n'.join(f'  <img alt="" src="../../images/{n}" />' for n in ru_imgs_03_9) + '\n'
write('sbf-binnen-de-03_9.html', wrap(
    'Sportbootführerschein Binnen – Brücken, Wehre und Sperrungen',
    sec_09, prev='sbf-binnen-de-03_8.html', nxt='sbf-binnen-de-03_10.html'))

# 03_10 SCHALLSIGNALE / Bleib-weg / Nebelsignale
# DE has no header for this. Use whatever leak we found, plus a placeholder note.
sec_10 = ''
if sec_10_seed:
    sec_10 = sec_10_seed
sec_10_body = (
    '  <h1 style="font-weight:normal;"><a id="bookmark_schallsignale"></a>SCHALLSIGNALE</h1>\n'
    + sec_10
    + ('\n  <p><em>Anmerkung: Im OCR-Export liegt für diesen Abschnitt nur stark '
       'beschädigter Text vor. Bitte mit der Original-Druckausgabe abgleichen.</em></p>\n')
)
ru_imgs_03_10 = ['SBF-binnen-motor-75.jpg','SBF-binnen-motor-76.jpg','SBF-binnen-motor-74.jpg']
sec_10_body += '\n'.join(f'  <img alt="" src="../../images/{n}" />' for n in ru_imgs_03_10) + '\n'
write('sbf-binnen-de-03_10.html', wrap(
    'Sportbootführerschein Binnen – Schallsignale',
    sec_10_body, prev='sbf-binnen-de-03_9.html', nxt='sbf-binnen-de-03_11.html'))

# 03_11 LICHTERFÜHRUNG (bookmark13..bookmark17)
sec = section('bookmark13', 'bookmark17')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark13')
# Promote subsection h-tags to h2 with bookmark ids
sec = re.sub(r'<h[2-6][^>]*>([^<]*Sportboote[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark14"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Berufsschiffe[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark15"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Gefährliche Güter[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark16"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += '\n  <p><em>Hinweis: Die Tafel- und Lichterzeichen-Beschriftungen entstammen dem unverbesserten OCR.</em></p>\n'
ru_imgs_03_11 = [
    'SBF-binnen-motor_1-77.jpg','SBF-binnen-motor-77.jpg',
    'Licht02.png','Licht01.png',
    'Sportbootfu08hrerschein Binnen Motor-83.png',
    'Sportbootfu08hrerschein Binnen Motor-85.png',
    'Sportbootfu08hrerschein Binnen Motor-80_1.png',
    'Sportbootfu08hrerschein Binnen Motor-84.png',
    'Sportbootfu08hrerschein Binnen Motor-86.png',
    'SBF-binnen-motor-87.jpg','SBF-binnen-motor-88.jpg',
    'SBF-binnen-motor_1-89.jpg','SBF-binnen-motor_1-90.jpg',
    'SBF-binnen-motor_1-91.jpg','SBF-binnen-motor_1-91.png',
    'SBF-binnen-motor-93.png','SBF-binnen-motor-94.jpg',
    'SBF-binnen-motor-92.png','SBF-binnen-motor-95.png','SBF-binnen-motor-94.png',
]
sec += '\n'.join(f'  <img alt="" src="../../images/{n}" />' for n in ru_imgs_03_11) + '\n'
write('sbf-binnen-de-03_11.html', wrap(
    'Sportbootführerschein Binnen – Lichterführung',
    sec, prev='sbf-binnen-de-03_10.html', nxt='sbf-binnen-de-03_12.html'))

# 03_12 TAG- UND NACHTSIGNALE (bookmark17..bookmark20)
sec = section('bookmark17', 'bookmark20')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark17')
sec = re.sub(r'<h[2-6][^>]*>([^<]*Begegnen[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark18"></a>\1</h2>', sec)
sec = re.sub(r'<h[2-6][^>]*>([^<]*Still-[^<]*)</h[2-6]>',
             r'  <h2><a id="bookmark19"></a>\1</h2>', sec)
sec = strip_de_imgs(sec)
sec += '\n  <p><em>Hinweis: Tafelzeichen-Beschriftungen aus dem unverbesserten OCR.</em></p>\n'
ru_imgs_03_12 = [
    'SBF-binnen-motor-95.jpg','SBF-binnen-motor-96.jpg',
    'SBF-binnen-motor-97.jpg','SBF-binnen-motor-98.jpg',
    'SBF-binnen-motor_1-101.jpg','SBF-binnen-motor-101.jpg',
    'SBF-binnen-motor-102.jpg','SBF-binnen-motor-103.jpg',
    'SBF-binnen-motor-104.jpg','SBF-binnen-motor-105.jpg',
    'SBF-binnen-motor_1-106.jpg','SBF-binnen-motor_1-107.jpg',
    'SBF-binnen-motor_1-108.jpg','SBF-binnen-motor-109.jpg','SBF-binnen-motor-110.jpg',
]
sec += '\n'.join(f'  <img alt="" src="../../images/{n}" />' for n in ru_imgs_03_12) + '\n'
write('sbf-binnen-de-03_12.html', wrap(
    'Sportbootführerschein Binnen – Tag- und Nachtsignale',
    sec, prev='sbf-binnen-de-03_11.html', nxt='sbf-binnen-de-03_13.html'))

# 03_13 Kennzeichnung + Binnenschifffahrtsfunk (bookmark20..bookmark21)
sec = section('bookmark20', 'bookmark21')
sec = cleanup(sec)
# Prepend KENNZEICHNUNG h1 (no DE bookmark for it but RU has heading)
# bookmark20 is "Binnenschifffahrtsfunk" so make Kennzeichnung from preceding text? Hmm.
# The DE source orders this differently. We'll treat bookmark20 onwards as Binnenschifffahrtsfunk.
sec = make_h1(sec, 'bookmark20')
sec = strip_de_imgs(sec)
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_kennzeichnung"></a>KENNZEICHNUNG</h1>\n' + sec
sec += '\n  <img alt="" src="../../images/SBF-binnen-motor-111.jpg" />\n'
write('sbf-binnen-de-03_13.html', wrap(
    'Sportbootführerschein Binnen – Kennzeichnung und Binnenschifffahrtsfunk',
    sec, prev='sbf-binnen-de-03_12.html', nxt='sbf-binnen-de-03_14.html'))

# 03_14 Verhalten in Häfen + Flaggenführung (bookmark21..bookmark23)
sec = section('bookmark21', 'bookmark23')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark21')
sec = strip_de_imgs(sec)
# Insert h1 VERHALTEN IN HÄFEN at start
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_haefen"></a>VERHALTEN IN HÄFEN</h1>\n' + sec
sec += '\n  <img alt="" src="../../images/SBF-binnen-motor-112.jpg" />\n'
sec += '  <img alt="" src="../../images/SBF-binnen-motor-113.png" />\n'
write('sbf-binnen-de-03_14.html', wrap(
    'Sportbootführerschein Binnen – Verhalten in Häfen, Flaggenführung',
    sec, prev='sbf-binnen-de-03_13.html', nxt='sbf-binnen-de-04.html'))

# 04 KNOTEN UND TAUWERK chapter intro + KNOTEN section
sec = section('bookmark23', 'bookmark24')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark23')
sec = strip_de_imgs(sec)
# Add chapter title above
sec = '  <h1 style="font-weight:normal;"><a id="bookmark_knoten_tauwerk"></a>KNOTEN UND TAUWERK</h1>\n' + sec
sec += '\n  <img alt="" src="../../images/SBF-binnen-motor-113.jpg" />\n'
sec += '  <img alt="" src="../../images/SBF-binnen-motor_1-115.jpg" />\n'
sec += '  <img alt="" src="../../images/SBF-binnen-motor_1-116.jpg" />\n'
write('sbf-binnen-de-04.html', wrap(
    'Sportbootführerschein Binnen – Knoten und Tauwerk',
    sec, prev='sbf-binnen-de-03_14.html', nxt='sbf-binnen-de-04_1.html'))

# 04_1 Tauwerk
sec = section('bookmark24', 'bookmark25')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark24')
sec = strip_de_imgs(sec)
sec += '\n  <img alt="" src="../../images/SBF-binnen-motor-117.jpg" />\n'
sec += '  <img alt="" src="../../images/SBF-binnen-motor-118.jpg" />\n'
write('sbf-binnen-de-04_1.html', wrap(
    'Sportbootführerschein Binnen – Tauwerk',
    sec, prev='sbf-binnen-de-04.html', nxt='sbf-binnen-de-04_2.html'))

# 04_2 Festmachen
sec = section('bookmark25', 'bookmark26')
sec = cleanup(sec)
sec = make_h1(sec, 'bookmark25')
sec = strip_de_imgs(sec)
sec += '\n  <img alt="" src="../../images/SBF-binnen-motor-119.jpg" />\n'
sec += '  <img alt="" src="../../images/SBF-binnen-motor-120.jpg" />\n'
write('sbf-binnen-de-04_2.html', wrap(
    'Sportbootführerschein Binnen – Festmachen',
    sec, prev='sbf-binnen-de-04_1.html', nxt=None))

print("Done.")
