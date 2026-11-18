"""data/benefits.json -> dist/ (index.html, data.json, b/<id>.html, about.html, feed.xml, sitemap.xml, robots.txt, ads.txt)"""
import json, os, re, html, shutil, datetime, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from PIL import Image, ImageDraw, ImageFont
    _FONT_DIR = "/usr/share/fonts/opentype/noto"
    FONT_B = f"{_FONT_DIR}/NotoSansCJK-Bold.ttc" if os.path.exists(f"{_FONT_DIR}/NotoSansCJK-Bold.ttc") else None
    FONT_R = f"{_FONT_DIR}/NotoSansCJK-Regular.ttc" if os.path.exists(f"{_FONT_DIR}/NotoSansCJK-Regular.ttc") else None
    HAS_PIL = bool(FONT_B and FONT_R)
except Exception:
    HAS_PIL = False
    FONT_B = FONT_R = None

BRAND = "지원금 나침반"
KAKAO_URL = "https://pf.kakao.com/_QeNNX"
YOUTUBE_URL = "https://www.youtube.com/channel/UC4QMDavBjLRgQjFY9gvgPnA"
WP_URL = "https://acoustic42.com"

def make_card(path, org, main, sub):
    """링크 미리보기(OG)용 카드 이미지 1200x630 생성. 실패하면 False (빌드는 계속)."""
    if not HAS_PIL: return False
    try:
        W, H = 1200, 630
        NAVY, BLACK, GRAY = (27, 58, 107), (17, 17, 17), (110, 110, 110)
        img = Image.new("RGB", (W, H), (255, 255, 255))
        d = ImageDraw.Draw(img)
        def fit(text, fp, size, min_size=30):
            while size > min_size:
                f = ImageFont.truetype(fp, size)
                if d.textbbox((0, 0), text, font=f)[2] <= 1080: return f
                size -= 4
            return ImageFont.truetype(fp, min_size)
        def center(text, y, f, fill):
            b = d.textbbox((0, 0), text, font=f)
            d.text(((W - (b[2] - b[0])) / 2 - b[0], y), text, font=f, fill=fill)
        d.rectangle([0, 0, W, 84], fill=NAVY)
        center(BRAND, 22, ImageFont.truetype(FONT_B, 38), (255, 255, 255))
        center(org, 150, fit(org, FONT_B, 76), NAVY)
        center(main, 262, fit(main, FONT_B, 108), BLACK)
        d.line([300, 440, 900, 440], fill=(200, 208, 220), width=3)
        center(sub, 472, fit(sub, FONT_R, 44, 26), GRAY)
        d.rectangle([0, H - 26, W, H], fill=NAVY)
        img.save(path, optimize=True)
        return True
    except Exception:
        return False

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SITE = os.environ.get("SITE_URL", "https://example.com").rstrip("/")
ADS = os.environ.get("ADSENSE_CLIENT", "")
D = json.load(open(f"{ROOT}/data/benefits.json", encoding="utf-8"))
TODAY = datetime.date.today()
e = lambda v: html.escape(str(v or "")).strip()

def rich(s):
    out, lvl = [], 0
    for L in re.split(r"\r?\n", s or ""):
        L = L.strip()
        if not L: continue
        m1 = re.match(r"^(?:[○●□■ㅇ]|\d+\.(?!\d)|[①-⑳])\s*(.*)", L); m2 = re.match(r"^(?:[-·ㆍ]|\d+\))\s*(.*)", L); mn = re.match(r"^(?:※|\*)\s*(.*)", L)
        if mn:
            out += ["</ul>"] * lvl; lvl = 0; out.append(f'<p class="note">※ {e(mn.group(1))}</p>')
        elif m1 or m2:
            want = 1 if m1 else 2
            while lvl < want: out.append('<ul class="l%d">' % (lvl + 1)); lvl += 1
            while lvl > want: out.append("</ul>"); lvl -= 1
            out.append(f"<li>{e((m1 or m2).group(1))}</li>")
        else:
            out += ["</ul>"] * lvl; lvl = 0; out.append(f"<p>{e(L)}</p>")
    out += ["</ul>"] * lvl
    return "".join(out)

def parse_deadline(raw):
    """신청기한 원문 -> (kind, end_date). kind: always|dated|etc"""
    s = (raw or "").strip()
    if not s: return ("etc", None)
    if "상시" in s: return ("always", None)
    dates = []
    for m in re.finditer(r"(20\d{2})[-./년 ]\s*(\d{1,2})[-./월 ]\s*(\d{1,2})", s):
        try: dates.append(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError: pass
    for m in re.finditer(r"\b(20\d{2})(\d{2})(\d{2})\b", s):
        try: dates.append(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError: pass
    if dates: return ("dated", max(dates))
    return ("etc", None)

items = []
for r in D["data"]:
    kind, end = parse_deadline(r.get("deadline"))
    dd = (end - TODAY).days if end else None
    items.append({**r, "id": re.sub(r"[^A-Za-z0-9_-]", "", str(r["id"])), "dkind": kind,
                  "end": end, "dd": dd})
# 기본 정렬: 마감 임박(미래) -> 상시(조회수) -> 기타 -> 지난 마감
def sort_key(x):
    if x["dkind"] == "dated" and (x["dd"] or 0) >= 0: return (0, x["dd"], -x["views"])
    if x["dkind"] == "always": return (1, 0, -x["views"])
    if x["dkind"] == "etc": return (2, 0, -x["views"])
    return (3, -(x["dd"] or 0), -x["views"])
items.sort(key=sort_key)

def dlab(x):
    if x["dkind"] == "always": return "상시신청"
    if x["dkind"] == "dated":
        base = f'{x["end"].month}월 {x["end"].day}일 마감'
        if x["dd"] is None: return base
        if x["dd"] < 0: return base + " (기간 지남)"
        if x["dd"] == 0: return "오늘 마감"
        if x["dd"] <= 30: return f'D-{x["dd"]} · ' + base
        return base
    raw = (x.get("deadline") or "기관 확인").strip()
    return raw if len(raw) <= 24 else raw[:24] + "…"

ADHEAD = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADS}" crossorigin="anonymous"></script>' if ADS else ""
GA = os.environ.get("GA_ID", "GT-NSSSWH8S")
GAHEAD = f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","{GA}");</script>' if GA else ""
# 광고 단위는 사이트당 1개 코드를 전 자리에 공용 (사용자 결정 2026-11-12). 값이 없으면 자동광고만 동작.
AD_SLOT = os.environ.get("AD_SLOT", "")
def ad(pos):
    if not (ADS and AD_SLOT): return ""
    return (f'<div class="adslot"><ins class="adsbygoogle" style="display:block" data-ad-client="{ADS}" '
            f'data-ad-slot="{AD_SLOT}" data-ad-format="auto" data-full-width-responsive="true"></ins>'
            f'<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>')
try:
    CSS = open(f"{ROOT}/templates/style.css", encoding="utf-8").read()
except Exception:
    CSS = ""
SAMPLE = '<div class="sample">⚠ 예시 데이터입니다. 실제 데이터가 아니며, API 연결 후 실제 지원금으로 바뀝니다.</div>' if D.get("sample") else ""
FOOT = f'''<footer>출처: 행정안전부 대한민국 공공서비스(혜택) 정보 (공공데이터포털·정부24 보조금24). 지원 자격과 신청 기한은 바뀌 수 있으니 신청 전 반드시 정부24 원문에서 다시 확인하세요.<br>업데이트: {e(D.get("generated_at"))} · <a href="{SITE}/about.html">사이트 소개·출처</a></footer>'''

def channels_box():
    return (f'<section class="card2"><h2>놓치지 않게 받아보기</h2>'
            f'<a class="cpa" href="{KAKAO_URL}" target="_blank" rel="noopener">📢 카톡 채널 「정책 나침반」 추가하기<small>새 지원금과 마감 소식을 카톡으로 알려드려요</small></a>'
            f'<a class="cpa" href="{YOUTUBE_URL}" target="_blank" rel="noopener">🎬 지원금 나침반TV (유튜브)<small>지원금을 영상으로 쉽게 풀어드려요</small></a>'
            f'<a class="cpa" href="{WP_URL}" target="_blank" rel="noopener">📖 지식온에서 해설 글 보기<small>지원금·정책을 글로 자세히 정리해요</small></a></section>')

def page(title, desc, body, canonical, extra="", ogimg=""):
    OGIMG = f'<meta property="og:image" content="{ogimg}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">' if ogimg else ""
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{canonical}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">{OGIMG}{ADHEAD}{GAHEAD}{extra}<style>{CSS}</style></head><body>{SAMPLE}{body}
{FOOT}</body></html>'''

out = f"{ROOT}/dist"; shutil.rmtree(out, ignore_errors=True); os.makedirs(f"{out}/b"); os.makedirs(f"{out}/cards")
OGMAP = {}
for i, x in enumerate(items):
    folds = ""
    for k, v in (("지원대상", x.get("target")), ("선정기준", x.get("criteria")), ("지원내용", x.get("content")),
                 ("신청방법", x.get("how")), ("구비서류", x.get("docs")), ("근거 법령", x.get("law"))):
        if v and str(v).strip(): folds += f'<details class="fold" open><summary>{k}</summary><div class="fb">{rich(v)}</div></details>'
    tels = [t.strip() for t in re.split(r"\|\|", x.get("tel") or "") if t.strip()]
    tel_html = "".join(f"<li>{e(t)}</li>" for t in tels)
    if tel_html: folds += f'<details class="fold"><summary>전화문의</summary><div class="fb"><ul class="l1">{tel_html}</ul></div></details>'
    btns = ""
    if x.get("online_url"): btns += f'<a class="pb main" style="flex:1 1 220px;text-align:center;padding:17px 16px;font-size:18px" href="{e(x["online_url"])}" target="_blank" rel="nofollow noopener">온라인 신청하기</a>'
    if x.get("url"): btns += f'<a class="pb" style="flex:1 1 220px;text-align:center;padding:17px 16px;font-size:17px" href="{e(x["url"])}" target="_blank" rel="nofollow noopener">정부24에서 자세히 보기</a>'
    rel = [y for y in items if y["id"] != x["id"] and y.get("field") and y.get("field") == x.get("field")]
    rel.sort(key=lambda y: -y["views"]); rel = rel[:6]
    urgent = [y for y in items if y["id"] != x["id"] and y["dkind"] == "dated" and y["dd"] is not None and 0 <= y["dd"] <= 30][:5]
    body = f'''<header class="top"><a href="../">← {BRAND}</a></header><main class="detail">
<p class="crumb">{e(x.get("org_type"))} · {e(x.get("field"))}</p><h1>{e(x["name"])}</h1>
<p>{e(x.get("summary"))}</p>
<section class="hero">
<div class="h"><small>소관기관</small><strong>{e(x.get("org"))}</strong></div>
<div class="h"><small>신청기한</small><strong class="money">{e(dlab(x))}</strong></div>
<div class="h"><small>지원유형</small><strong>{e(x.get("support_type") or x.get("user_type") or "공고문 참조")}</strong></div>
<div class="mini"><span>🏢 접수: {e(x.get("apply_org") or x.get("org"))}</span><span>👤 {e(x.get("user_type"))}</span></div></section>
{f'<div class="pbtns" style="margin:14px 0">{btns}</div>' if btns else ""}
{ad("detail-top")}
{folds}
{ad("detail-mid")}
{channels_box()}
{f'<section class="card2 rel"><h2>같은 분야 지원금</h2>' + "".join(f'<a href="{y["id"]}.html"><strong>{e(y["name"])}</strong><span>{e(y.get("org"))} · {e(dlab(y))}</span></a>' for y in rel) + '</section>' if rel else ""}
{f'<section class="card2 rel"><h2>⏰ 마감 임박 지원금</h2>' + "".join(f'<a href="{y["id"]}.html"><strong>{e(y["name"])}</strong><span>{e(y.get("org"))} · {e(dlab(y))}</span></a>' for y in urgent) + '</section>' if urgent else ""}
{ad("detail-bottom")}</main>'''
    title = f'{x["name"]} | {x.get("org")} | {BRAND}'
    desc = f'{x["name"]}. {x.get("summary") or ""} 신청기한 {dlab(x)}, {x.get("org")}.'[:155]
    ld = json.dumps({"@context": "https://schema.org", "@type": "GovernmentService", "name": x["name"],
        "provider": {"@type": "GovernmentOrganization", "name": x.get("org")},
        "serviceType": x.get("field"), "description": x.get("summary") or x["name"]}, ensure_ascii=False)
    main_txt = x["name"] if len(x["name"]) <= 22 else x["name"][:22] + "…"
    sub_txt = f'{dlab(x)} · {x.get("org")} · {x.get("field")}'
    card_ok = make_card(f'{out}/cards/{x["id"]}.png', x.get("org") or BRAND, main_txt, sub_txt)
    OGMAP[x["id"]] = (title, desc, f'{SITE}/cards/{x["id"]}.png' if card_ok else "")
    open(f'{out}/b/{x["id"]}.html', "w", encoding="utf-8").write(page(title, desc, body, f'{SITE}/b/{x["id"]}.html', f'<script type="application/ld+json">{ld}</script>', f'{SITE}/cards/{x["id"]}.png' if card_ok else ""))

LITE = [{"id": x["id"], "name": x["name"], "org": x.get("org"), "field": x.get("field"), "utype": x.get("user_type"),
         "stype": x.get("support_type"), "dk": x["dkind"], "dd": x["dd"], "dl": dlab(x), "views": x["views"],
         "summary": (x.get("summary") or "")[:80]} for x in items]
json.dump(LITE, open(f"{out}/data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
FIELDS = sorted({x["field"] for x in items if x.get("field")})
UTYPES = sorted({x["user_type"] for x in items if x.get("user_type")})
STYPES = sorted({x["support_type"] for x in items if x.get("support_type")})
opt = lambda xs: "".join(f"<option>{e(v)}</option>" for v in xs)
body = f'''<header class="top"><h1>{BRAND}</h1><p>정부·지자체 지원금과 보조금, 마감 임박순으로 한눈에</p></header><main>
<input id="q" type="search" placeholder="지원금 이름, 기관, 내용 검색">
<div class="row"><select id="f"><option value="">분야 전체</option>{opt(FIELDS)}</select><select id="u"><option value="">대상 전체</option>{opt(UTYPES)}</select>
<select id="t"><option value="">지원유형 전체</option>{opt(STYPES)}</select><select id="d"><option value="">기한 전체</option><option value="30">30일 내 마감</option><option value="always">상시신청만</option></select></div>
<p id="cnt"></p>{ad("list-top")}<div id="list"></div><button id="more">더 보기</button>
{channels_box()}</main>
<script>{open(f"{ROOT}/templates/app.js", encoding="utf-8").read()}</script>'''
default_ok = make_card(f"{out}/cards/default.png", BRAND, "정부 지원금·보조금 모음", "마감 임박순으로 한눈에 확인")
open(f"{out}/index.html", "w", encoding="utf-8").write(page(f"{BRAND} | 정부 지원금·보조금·혜택 마감순 모음", "정부 부처와 지자체의 지원금, 보조금, 바우처 혜택을 분야·대상별로 찾아보세요. 신청기한과 신청방법까지 한 페이지에서 확인합니다.", body, f"{SITE}/", "", f"{SITE}/cards/default.png" if default_ok else ""))

about_body = f'''<header class="top"><a href="./">← {BRAND}</a></header><main class="detail">
<h1>사이트 소개·출처</h1>
<p>{BRAND}는 정부 부처, 지방자치단체, 공공기관, 교육청이 제공하는 지원금·보조금·바우처 등 공공서비스(혜택) 정보를 모아 보여주는 안내 사이트입니다.</p>
<details class="fold" open><summary>데이터 출처</summary><div class="fb"><p>행정안전부 「대한민국 공공서비스(혜택) 정보」 (공공데이터포털 data.go.kr, 정부24 보조금24)를 매일 수집해 반영합니다. 각 지원금의 상세 페이지에는 정부24 원문 링크를 함께 둡니다.</p></div></details>
<details class="fold" open><summary>이용 시 주의</summary><div class="fb"><p>지원 자격, 금액, 신청 기한은 기관 사정에 따라 바뀔 수 있습니다. 실제 신청 전에는 반드시 정부24 원문이나 소관기관 안내에서 최신 내용을 다시 확인하세요. 이 사이트는 신청을 대행하지 않으며, 신청은 정부24 또는 접수기관에서 직접 하셔야 합니다.</p></div></details>
<details class="fold" open><summary>함께 운영하는 채널</summary><div class="fb"><p>유튜브 「지원금 나침반TV」, 카카오톡 채널 「정책 나침반」, 해설 블로그 「지식온」을 함께 운영합니다.</p></div></details>
{channels_box()}</main>'''
open(f"{out}/about.html", "w", encoding="utf-8").write(page(f"사이트 소개·출처 | {BRAND}", f"{BRAND}의 데이터 출처와 이용 안내입니다.", about_body, f"{SITE}/about.html"))

def xesc(s): return html.escape(str(s or ""), quote=False)
recent = sorted(items, key=lambda x: x.get("updated") or "", reverse=True)[:50]
feed_items = "".join(f'<item><title>{xesc(x["name"])}</title><link>{SITE}/b/{x["id"]}.html</link><guid>{SITE}/b/{x["id"]}.html</guid><description>{xesc(x.get("summary"))}</description></item>' for x in recent)
open(f"{out}/feed.xml", "w", encoding="utf-8").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{BRAND}</title><link>{SITE}/</link><description>정부 지원금·보조금 안내</description>{feed_items}</channel></rss>')
urls = [f"{SITE}/", f"{SITE}/about.html"] + [f'{SITE}/b/{x["id"]}.html' for x in items]
open(f"{out}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>" for u in urls) + "</urlset>")
open(f"{out}/robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
if ADS: open(f"{out}/ads.txt", "w").write(f"google.com, {ADS.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n")
if os.environ.get("CNAME"): open(f"{out}/CNAME", "w").write(os.environ["CNAME"])
# ===== 옛 ID 링크 보존 스텁 (jobs-site와 동일 구조) =====
try:
    REDIR = json.load(open(f"{ROOT}/data/redirects.json", encoding="utf-8"))
except Exception:
    REDIR = {}
HOME_OG = (f"{BRAND} | 정부 지원금·보조금·혜택 마감순 모음", "정부 부처와 지자체의 지원금, 보조금, 바우처 혜택을 분야·대상별로 찾아보세요.", f"{SITE}/cards/default.png" if default_ok else "")
nstub = 0
for old, new in REDIR.items():
    if old in OGMAP: continue
    if new and new in OGMAP:
        t, dsc, ogi = OGMAP[new]; target = f"{SITE}/b/{new}.html"
    else:
        t, dsc, ogi = HOME_OG; target = f"{SITE}/"
    stub_body = f'''<main class="detail"><h1>페이지 주소가 바뀌었습니다</h1><p>찾으시는 페이지 주소가 변경되어 자동으로 이동합니다. 이동하지 않으면 아래 링크를 눌러주세요.</p><p><a href="{target}">→ 이동된 페이지 보기</a></p></main>'''
    extra = f'<meta http-equiv="refresh" content="0; url={target}"><script>location.replace("{target}")</script>'
    open(f'{out}/b/{old}.html', "w", encoding="utf-8").write(page(t, dsc, stub_body, target, extra, ogi))
    nstub += 1
print("built", len(items), "| redirect stubs:", nstub)
