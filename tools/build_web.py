#!/usr/bin/env python3
"""인쇄용 index-pdf.html에서 웹 페이지 index.html을 만든다.

내용은 index-pdf.html에서만 고치고, 이 스크립트로 index.html을 다시 만든다.
그림(svg)과 표는 그대로 가져오고 배치·스타일·목차만 웹에 맞게 바꾼다.

사용: python3 tools/build_web.py
"""
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = (ROOT / "index-pdf.html").read_text(encoding="utf-8")

# 인쇄용 스타일에서 색 토큰, 범례 색, 그림 스타일은 그대로 가져온다
style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
tokens = re.search(r":root \{.*?\n\}", style, re.S).group(0)
legend_css = "\n".join(l for l in style.splitlines() if l.startswith(".l-"))
fig_css = style[style.index("/* 구성도 */"):]

body = re.search(r'<div class="sheet">(.*)</div>\s*</body>', src, re.S).group(1)
body = re.sub(r"<!--.*?-->\n?", "", body, flags=re.S)
title = re.search(r"<h1>(.*?)</h1>", body).group(1)
sub = re.search(r'<p class="sub">(.*?)</p>', body).group(1)
legend = re.search(r'<div class="legend">.*?</div>', body, re.S).group(0)
body = body[body.index("<h2"):]

# 좁은 화면에서는 표와 그림만 옆으로 밀리게 감싼다. 칸이 많은 표는 너무 좁아지지 않게 칸 수를 표시한다
def table(m):
    first = re.search(r"<tr>(.*?)</tr>", m.group(0), re.S).group(1)
    n = sum(int(c or 1) for c in re.findall(r'<t[hd](?: [^>]*?colspan="(\d+)")?[^>]*>', first))
    t = m.group(0).replace("<table>", f'<table class="c{min(n, 4)}">', 1) if n >= 3 else m.group(0)
    return f'<div class="tbl">{t}</div>'


body = re.sub(r"<table>.*?</table>", table, body, flags=re.S)
body = re.sub(r"<svg .*?</svg>", lambda m: f'<div class="fig">{m.group(0)}</div>', body, flags=re.S)


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def summary(m):
    # "무엇에 대한 장인가 ... 핵심 ..."을 두 줄로 나누고 머리말을 꼬리표로
    inner = m.group(1)
    paras = re.split(r"\s*(?=<b>핵심</b>)", inner)
    out = []
    for p in paras:
        p = re.sub(r"^<b>(.*?)</b>\s*", r'<span class="lbl">\1</span>', p)
        out.append(f"<p>{p}</p>")
    return '<div class="summary">' + "".join(out) + "</div>"


chapters = []  # (id, 번호, 이름, 개요, [(id, 절 이름)])
sections = []
for ci, part in enumerate((p for p in re.split(r"(?=<h2)", body) if p.strip()), 1):
    h2 = re.match(r"<h2[^>]*>(.*?)</h2>", part)
    num, name = h2.group(1).split(". ", 1)
    cid = f"c{ci}"
    lead = re.search(r'<div class="summary"><b>.*?</b>(.*?)(?:<b>핵심</b>|</div>)', part, re.S)
    subs = []

    def h3(m):
        sid = f"{cid}-{len(subs) + 1}"
        subs.append((sid, m.group(1)))
        return f'<h3 id="{sid}">{m.group(1)}<a class="hash" href="#{sid}" aria-label="이 절 링크">#</a></h3>'

    part = re.sub(r"<h3>(.*?)</h3>", h3, part)
    part = part.replace(h2.group(0), f'<h2 id="{cid}"><span class="num">{num}</span>{name}</h2>', 1)
    part = re.sub(r'<div class="summary">(.*?)</div>', summary, part, count=1, flags=re.S)
    chapters.append((cid, num, name, plain(lead.group(1)) if lead else "", subs))
    sections.append(f'<section class="chapter">\n{part.strip()}\n</section>')

nav = []
for cid, num, name, _, subs in chapters:
    items = "".join(f'<li><a href="#{sid}">{s}</a></li>' for sid, s in subs)
    nav.append(f'<li><a class="ch" href="#{cid}"><span class="no">{num}</span>{name}</a><ol>{items}</ol></li>')

cards = "".join(
    f'<a class="card" href="#{cid}"><span class="no">{num}장</span><span class="tt">{name}</span>'
    f'<span class="ds">{html.escape(lead)}</span></a>'
    for cid, num, name, lead, _ in chapters
)

CSS = tokens + """
:root { --top-h: 56px; --side-w: 280px; --tint: #eef3fb; --tint-s: #d3e0f4; }
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: calc(var(--top-h) + 16px); }
body {
  margin: 0; background: #fff; color: var(--fg);
  font-family: "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif;
  font-size: 15.5px; line-height: 1.7; -webkit-font-smoothing: antialiased;
}
a { color: var(--head); }

/* 위 막대 */
.topbar {
  position: sticky; top: 0; z-index: 30; height: var(--top-h);
  display: flex; align-items: center; gap: 12px; padding: 0 max(20px, calc((100% - 1320px) / 2 + 20px));
  background: rgba(255,255,255,.92); backdrop-filter: saturate(1.4) blur(8px);
  border-bottom: 1px solid var(--line);
}
.brand { font-weight: 800; font-size: 16px; color: var(--fg); text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.spacer { flex: 1; }
.btn {
  display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 12px; flex: none;
  border: 1px solid var(--line); border-radius: 8px; background: #fff; color: var(--fg);
  font: inherit; font-size: 14px; text-decoration: none; cursor: pointer;
}
.btn:hover { border-color: var(--head); color: var(--head); }
.menu-btn { display: none; }

/* 목차 + 본문 */
.layout { display: grid; grid-template-columns: var(--side-w) minmax(0, 1fr); max-width: 1320px; margin: 0 auto; }
.side {
  position: sticky; top: var(--top-h); align-self: start; height: calc(100vh - var(--top-h)); overflow-y: auto;
  padding: 24px 14px 40px 18px; border-right: 1px solid var(--line); font-size: 14px; line-height: 1.45;
}
.side .cap { font-size: 12px; font-weight: 700; color: var(--muted); letter-spacing: .04em; margin: 0 0 6px 10px; }
.side ol { list-style: none; margin: 0; padding: 0; }
.side a { display: block; padding: 5px 10px; border-radius: 6px; color: var(--muted); text-decoration: none; }
.side a:hover { background: var(--panel); color: var(--fg); }
.side a.ch { display: flex; gap: 8px; color: var(--fg); font-weight: 700; margin-top: 8px; }
.side a.ch .no { color: var(--accent); }
.side ol ol a { padding-left: 30px; font-size: 13.5px; }
.side a.cur { background: var(--tint); }
.side a.active { background: var(--tint); color: var(--head); font-weight: 700; }
.side .legend-box { margin: 24px 0 0; padding: 12px 14px; border: 1px solid var(--line); border-radius: 10px; }
.side .legend { flex-direction: column; gap: 6px; }

main { padding: 40px 48px 120px; min-width: 0; }
.content { max-width: 940px; }

/* 첫 화면 */
.hero h1 { font-size: 32px; line-height: 1.25; margin: 0 0 8px; letter-spacing: -.01em; }
.hero .sub { font-size: 17px; color: var(--muted); margin: 0 0 18px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin: 24px 0 0; }
.card {
  display: flex; flex-direction: column; gap: 2px; padding: 14px 16px; border: 1px solid var(--line); border-radius: 12px;
  color: var(--fg); text-decoration: none; background: #fff; transition: border-color .15s, box-shadow .15s;
}
.card:hover { border-color: var(--head); box-shadow: 0 4px 14px rgba(31,79,160,.12); }
.card .no { font-size: 12px; font-weight: 800; color: var(--accent); }
.card .tt { font-weight: 700; line-height: 1.4; }
.card .ds { font-size: 13px; color: var(--muted); line-height: 1.55; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }

/* 장·절 */
section.chapter { margin-top: 64px; padding-top: 48px; border-top: 1px solid var(--line); }
h2 { font-size: 26px; line-height: 1.3; margin: 0 0 16px; display: flex; align-items: center; gap: 12px; }
h2 .num { display: inline-grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; background: var(--fg); color: #fff; font-size: 18px; flex: none; }
h3 { font-size: 19px; line-height: 1.4; color: var(--head); margin: 44px 0 12px; }
h3 .hash { margin-left: 8px; color: var(--zone-s); text-decoration: none; opacity: 0; transition: opacity .15s; }
h3:hover .hash, h3 .hash:focus { opacity: 1; }
h4 { font-size: 15.5px; margin: 0 0 6px; }
p { margin: 8px 0; }
ul { margin: 6px 0 12px; padding-left: 20px; }
li { margin: 3px 0; }
.n { color: var(--accent); font-weight: 700; }

.summary { background: var(--tint); border: 1px solid var(--tint-s); border-radius: 12px; padding: 12px 18px; }
.summary p { margin: 4px 0; }
.summary .lbl {
  display: inline-block; margin-right: 8px; padding: 0 10px; border-radius: 999px; vertical-align: 1px;
  font-size: 12px; font-weight: 800; color: var(--head); background: #fff; border: 1px solid var(--tint-s);
}
.key { background: var(--panel); border-left: 4px solid var(--accent); border-radius: 0 10px 10px 0; padding: 12px 16px; margin: 14px 0 20px; }
.cols { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; margin: 14px 0 20px; align-items: start; }
.box { border: 1px solid var(--line); border-radius: 12px; padding: 14px 18px; height: 100%; }
.box ul { margin: 0; }

/* 표 */
.tbl { overflow-x: auto; margin: 14px 0 20px; border: 1px solid var(--line); border-radius: 12px; }
.cols .tbl { margin: 0 0 12px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; line-height: 1.55; }
th, td { padding: 8px 12px; border-bottom: 1px solid var(--line); border-right: 1px solid var(--line); vertical-align: top; text-align: left; }
tr > :last-child { border-right: none; }
tr:last-child > * { border-bottom: none; }
th { background: var(--panel); font-weight: 700; white-space: nowrap; }
th.grp { background: var(--tint); color: var(--head); font-size: 13px; white-space: normal; }
td.k { white-space: nowrap; font-weight: 700; }
td.c { white-space: nowrap; color: var(--muted); }

/* 그림 */
figure { margin: 16px 0 24px; }
.fig { border: 1px solid var(--line); border-radius: 12px; padding: 16px; background: #fff; overflow-x: auto; }
.fig svg { display: block; width: 100%; height: auto; min-width: 660px; }
figcaption { font-size: 14px; color: var(--muted); margin-top: 10px; line-height: 1.65; }
pre { background: #1f2630; color: #e6edf3; border-radius: 10px; padding: 14px 16px; font-size: 13px; line-height: 1.55; overflow-x: auto; margin: 0 0 12px; }
p.c { font-size: 13.5px; color: var(--muted); }

/* 범례 */
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 13px; color: var(--muted); }
.legend span { display: inline-flex; align-items: center; gap: 7px; }
.legend i { width: 18px; height: 12px; border-radius: 3px; border: 1.5px solid; display: inline-block; flex: none; }
""" + legend_css + """

.totop {
  position: fixed; right: 20px; bottom: 20px; z-index: 20; width: 44px; height: 44px; border-radius: 50%;
  border: 1px solid var(--line); background: #fff; color: var(--fg); font-size: 18px; cursor: pointer;
  box-shadow: 0 2px 10px rgba(0,0,0,.12); opacity: 0; pointer-events: none; transition: opacity .2s;
}
.totop.show { opacity: 1; pointer-events: auto; }
.scrim { display: none; }

@media (max-width: 1100px) { main { padding: 32px 28px 100px; } }
@media (max-width: 960px) {
  .layout { grid-template-columns: 1fr; }
  .menu-btn { display: inline-flex; }
  .side {
    position: fixed; top: var(--top-h); left: 0; bottom: 0; z-index: 25; height: auto; width: min(320px, 86vw);
    background: #fff; transform: translateX(-100%); transition: transform .2s; box-shadow: 4px 0 18px rgba(0,0,0,.12);
  }
  body.nav-open .side { transform: none; }
  body.nav-open .scrim { display: block; position: fixed; inset: var(--top-h) 0 0 0; z-index: 24; background: rgba(0,0,0,.25); }
}
@media (max-width: 720px) {
  main { padding: 24px 16px 96px; }
  .topbar { padding: 0 12px; gap: 8px; }
  .hero h1 { font-size: 26px; }
  .hero .sub { font-size: 15px; }
  h2 { font-size: 22px; }
  h3 { font-size: 18px; margin-top: 36px; }
  .cols { grid-template-columns: minmax(0, 1fr); }
  table.c3 { min-width: 520px; }
  table.c4 { min-width: 640px; }
  section.chapter { margin-top: 48px; padding-top: 36px; }
}
@media print {
  .topbar, .side, .totop, .scrim { display: none !important; }
  .layout { display: block; }
  main { padding: 0; }
}

""" + fig_css

JS = """
(() => {
  const side = document.getElementById('side');
  const btn = document.querySelector('.menu-btn');
  const setNav = open => { document.body.classList.toggle('nav-open', open); btn.setAttribute('aria-expanded', String(open)); };
  btn.addEventListener('click', () => setNav(!document.body.classList.contains('nav-open')));
  document.querySelector('.scrim').addEventListener('click', () => setNav(false));
  side.addEventListener('click', e => { if (e.target.closest('a')) setNav(false); });

  // 지금 읽는 장·절을 목차에 표시
  const links = new Map([...side.querySelectorAll('a[href^="#"]')].map(a => [a.hash.slice(1), a]));
  const heads = [...document.querySelectorAll('h2[id], h3[id]')];
  const totop = document.querySelector('.totop');
  totop.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));
  let ticking = false;
  const spy = () => {
    ticking = false;
    let cur = null;
    for (const h of heads) { if (h.getBoundingClientRect().top < 160) cur = h; else break; }
    side.querySelectorAll('a.active, a.cur').forEach(a => a.classList.remove('active', 'cur'));
    if (cur) {
      const ch = cur.closest('section').querySelector('h2');
      links.get(ch.id)?.classList.add(cur === ch ? 'active' : 'cur');
      const a = links.get(cur.id);
      if (a) {
        a.classList.add('active');
        if (a.offsetTop < side.scrollTop + 40 || a.offsetTop > side.scrollTop + side.clientHeight - 80) {
          side.scrollTop = a.offsetTop - side.clientHeight / 3;
        }
      }
    }
    totop.classList.toggle('show', scrollY > 800);
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(spy); } }, { passive: true });
  spy();
})();
"""

page = f"""<!doctype html>
<!-- tools/build_web.py가 index-pdf.html에서 만든 파일입니다. 내용은 index-pdf.html에서 고치세요. -->
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{html.escape(plain(sub))}">
<style>
{CSS}
</style>
</head>
<body>
<header class="topbar">
<button class="btn menu-btn" type="button" aria-controls="side" aria-expanded="false">☰ 목차</button>
<a class="brand" href="#">{title}</a>
<span class="spacer"></span>
<a class="btn" href="index-pdf.html">인쇄용 A4</a>
</header>
<div class="layout">
<nav class="side" id="side" aria-label="목차">
<p class="cap">목차</p>
<ol>{"".join(nav)}</ol>
<div class="legend-box"><p class="cap">그림 범례</p>{legend}</div>
</nav>
<main>
<div class="content">
<div class="hero">
<h1>{title}</h1>
<p class="sub">{sub}</p>
{legend}
<div class="cards">{cards}</div>
</div>
{chr(10).join(sections)}
</div>
</main>
</div>
<div class="scrim"></div>
<button class="totop" type="button" aria-label="맨 위로">↑</button>
<script>{JS}</script>
</body>
</html>
"""

(ROOT / "index.html").write_text(page, encoding="utf-8")
print(f"index.html: 장 {len(chapters)}개, 절 {sum(len(c[4]) for c in chapters)}개, 그림 {page.count('<svg ')}개, 표 {page.count('<table')}개")
