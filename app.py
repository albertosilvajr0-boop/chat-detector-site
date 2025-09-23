from flask import Flask, request, render_template_string, send_file, redirect, url_for
import requests, re, csv, io, json, os, time, html as htmlmod
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse, urljoin

app = Flask(__name__)

# ================= Fetch (browser-like, 403-tolerant) =================
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"

def _headers(netloc):
    return {
        "User-Agent": UA, "Accept": ACCEPT, "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache", "Pragma": "no-cache", "Referer": f"https://{netloc}/",
    }

def robust_fetch(url):
    s = requests.Session()
    try:
        r = s.get(url, headers=_headers(urlparse(url).netloc), timeout=30, allow_redirects=True)
        r.raise_for_status()
        if r.text:
            return r.text
    except Exception:
        pass
    # last resort: read-only proxy
    p = urlparse(url)
    prox = f"https://r.jina.ai/http://{p.netloc}{p.path or '/'}"
    r = s.get(prox, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.text

# ================= Helpers =================
VIN_RE   = re.compile(r"\b([A-HJ-NPR-Z0-9]{17})\b")
PRICE_RE = re.compile(r"\$\s?\d[\d,]{3,}(?:\.\d{2})?", re.I)

# labels to PREFER (strongly) vs AVOID (strongly)
PREFER_NEAR = [
    r"\bfinal\s*price\b", r"\b(our|your|dealer|store|alpine)\s*price\b",
    r"\bbest\s*price\b", r"\binternet\s*price\b", r"\be[-\s]?price\b",
    r"\bsale\s*price\b", r"\bclear\s*price\b", r"\btoday'?s?\s*price\b",
]
PREFER_IN_ID_CLASS = [
    "final", "best", "internet", "eprice", "e-price", "sale", "clear",
    "yourprice", "ourprice", "dealerprice", "alpine", "vdp", "pricebox"
]
AVOID_NEAR = [
    r"\bmsrp\b", r"\bsavings?\b", r"\bdiscount(s|ed)?\b", r"\brebate(s)?\b",
    r"\bper\s*(mo|month)\b", r"\bpayment\b", r"\bdown\b", r"\bdue\s*(at|on)\s*sign(ing)?\b",
    r"\blease\b", r"\bfinance\b", r"\bapr\b", r"\bestimat", r"\bbook\b", r"\btrade\b"
]
AVOID_IN_ID_CLASS = [
    "msrp", "savings", "discount", "rebate", "payment", "permonth", "per-mo",
    "lease", "finance", "apr", "down", "due", "estimate"
]

EXCLUDE_PATH = ("blog","news","coupon","finance","service","parts","privacy","terms","contact")
VDP_HINT = ("vehicle","vin","stock","details","inventory","new-","used-")

def _norm_abs(base, href):
    if not href: return None
    href = htmlmod.unescape(href.strip())
    if href.startswith("http"): return href
    if href.startswith("//"):   return f"{urlparse(base).scheme}:{href}"
    if href.startswith("/"):    return f"{urlparse(base).scheme}://{urlparse(base).netloc}{href}"
    return urljoin(base, href)

def _base(u):
    p = urlparse(u); return f"{p.scheme}://{p.netloc}"

def _looks_404(html):
    l = (html or "").lower()
    return "page not found" in l and "vehicle" not in l

# ================= Price pickers =================
def _jsonld_vin_price(soup):
    """Return first (vin, price) from JSON-LD Vehicle/Product offers, or ('','')."""
    for tag in soup.find_all("script", attrs={"type":"application/ld+json"}):
        raw = tag.string or tag.text or ""
        try:
            data = json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
        except Exception:
            continue
        objs = data if isinstance(data, list) else [data]
        for o in objs:
            t = o.get("@type")
            if isinstance(t, list): t = ",".join(map(str,t))
            if not t or ("Vehicle" not in str(t) and "Product" not in str(t)): 
                continue
            vin = o.get("vehicleIdentificationNumber") or o.get("vin") or ""
            price = ""
            off = o.get("offers")
            if isinstance(off, dict):
                price = off.get("price") or (off.get("priceSpecification") or {}).get("price") or ""
            elif isinstance(off, list):
                for k in off:
                    price = k.get("price") or ""
                    if price: break
            if price and not str(price).startswith("$"): price = "$"+str(price)
            if vin and price:
                return vin, price, "jsonld:offers.price"
    return "", "", ""

def _score_context(text):
    score = 0
    low = text.lower()
    for pat in PREFER_NEAR:
        if re.search(pat, low): score += 6
    for pat in AVOID_NEAR:
        if re.search(pat, low): score -= 6
    return score

def _choose_best_price(soup):
    """Pick the best price by scoring candidates with labels & context; returns (price, label)."""
    candidates = []

    # 1) markup with itemprop=price (often the true transactional price)
    itemp = soup.find(attrs={"itemprop":"price"}) or soup.find("meta", attrs={"itemprop":"price"})
    if itemp:
        pv = itemp.get("content") or itemp.get_text(" ", strip=True)
        if pv:
            val = pv if str(pv).startswith("$") else f""
            candidates.append((val, "itemprop=price", 10))

    # 2) scan elements whose id/class mentions price/amount
    for el in soup.find_all(True):
        idstr  = (el.get("id") or "").lower()
        clstr  = " ".join(el.get("class") or []).lower()
        bucket = idstr + " " + clstr
        if any(k in bucket for k in ("price","amount","final","best","internet","eprice","e-price","your","our","dealer","vdp","alpine")):
            txt = el.get_text(" ", strip=True)
            if not txt: continue
            for m in PRICE_RE.finditer(txt):
                val = m.group(0)
                left  = txt[max(0, m.start()-60):m.start()]
                right = txt[m.end():m.end()+60]
                ctx = (left + " " + right)
                score = 0
                # id/class preferences
                if any(k in bucket for k in PREFER_IN_ID_CLASS): score += 6
                if any(k in bucket for k in AVOID_IN_ID_CLASS):  score -= 8
                # text context
                score += _score_context(ctx)
                candidates.append((val, f"node:{(idstr or clstr)[:40]}", score))

    # 3) page-wide fallback: near strong labels like "Final Price"
    page_txt = soup.get_text(" ", strip=True)[:300000]
    for m in PRICE_RE.finditer(page_txt):
        val = m.group(0)
        left  = page_txt[max(0, m.start()-50):m.start()]
        right = page_txt[m.end():m.end()+50]
        score = _score_context(left + " " + right) - 4  # slight penalty for being a generic match
        candidates.append((val, "page-context", score))

    if not candidates:
        return "", ""

    # pick the highest score; break ties by preferring larger number (usually the price vs monthly)
    def _to_num(v):
        try:
            return float(re.sub(r"[^\d.]", "", v))
        except Exception:
            return 0.0

    candidates.sort(key=lambda x: (x[2], _to_num(x[0])), reverse=True)
    best = candidates[0]
    # hard guardrails: reject if clearly looks like msrp/savings nearby (score too low)
    if best[2] < 1:
        return "", ""
    return best[0], best[1]

def _extract_vin_price_from_vdp(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    mvin = VIN_RE.search(text)
    if not mvin:
        return "", "", "", soup

    # JSON-LD first (but many platforms put MSRP there; we only use it if nothing better)
    jvin, jprice, jsrc = _jsonld_vin_price(soup)

    price, src = _choose_best_price(soup)
    if price:
        return mvin.group(1), price, src, soup
    if jvin and jprice:
        return jvin, jprice, jsrc, soup

    return mvin.group(1), "", "", soup

# ================= DealerOn HTML sitemap (VDP discovery) =================
def _discover_html_sitemap(url):
    base = _base(url)
    for path in ("/sitemap.aspx", "/sitemap", "/site-map"):
        test = base + path
        try:
            html = robust_fetch(test)
            if "<a" in html:
                return test, html
        except Exception:
            pass
    return None, None

def _vdps_from_html_sitemap(sitemap_url, html):
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(sitemap_url).netloc
    urls, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = _norm_abs(sitemap_url, a["href"])
        if not href: continue
        pu = urlparse(href)
        if pu.netloc != host: continue
        path = pu.path.lower()
        if any(seg in path for seg in EXCLUDE_PATH): continue
        spaghetti = (pu.path + "?" + pu.query).upper()
        if VIN_RE.search(spaghetti) or any(h in path for h in VDP_HINT):
            if href not in seen:
                seen.add(href); urls.append(href)
    return urls

# ================= Main extraction (VIN + best price + label source) =================
def extract_vdp_rows(url, limit=500):
    sm_url, sm_html = _discover_html_sitemap(url)
    vdp_urls = _vdps_from_html_sitemap(sm_url, sm_html)[:limit] if sm_html else [url]

    rows, seen_vins, host = [], set(), urlparse(url).netloc
    for u in vdp_urls:
        if urlparse(u).netloc != host: continue
        try:
            html = robust_fetch(u)
            if _looks_404(html): continue
            vin, price, label, soup = _extract_vin_price_from_vdp(html)
            if vin and price and vin not in seen_vins:
                seen_vins.add(vin)
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                rows.append({"vin": vin, "price": price, "label": label, "url": u, "title": title})
        except Exception:
            continue
        time.sleep(0.02)
    return rows

# ================= UI =================
TEMPLATE = """
<!doctype html><html><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/>
<title>Vendor Detector</title>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:40px}
 .box{max-width:1200px;margin:auto;padding:24px;border:1px solid #ddd;border-radius:12px}
 input[type=text]{width:100%;padding:12px 14px;font-size:16px;border:1px solid #bbb;border-radius:8px}
 button{margin-top:12px;padding:10px 16px;font-size:16px;border-radius:8px;border:0;background:#111;color:#fff;cursor:pointer}
 table{border-collapse:collapse;width:100%;margin-top:12px}
 th,td{border:1px solid #eee;padding:8px 10px;text-align:left;font-size:14px;vertical-align:top}
 th{background:#fafafa}
 .row{display:flex;gap:10px;align-items:center;margin-top:8px;flex-wrap:wrap}
 .small{width:120px}
 .muted{color:#666;font-size:14px}
</style></head>
<body><div class='box'>
  <h1>Vendor Detector <span style="font-size:12px;background:#eef;padding:4px 8px;border-radius:999px;margin-left:6px">self-learning</span></h1>
  <form method="post" action="{{ url_for('prices') }}">
    <label><strong>Paste a URL</strong> (with or without https://)</label><br/>
    <input name="url" type="text" placeholder="https://alpinenissan.com" value="{{ url|e }}">
    <div class="row">
      <label>Limit <input class="small" type="number" name="limit" min="50" max="1000" value="{{ limit or 500 }}"></label>
    </div>
    <button type="submit">Find vehicle prices (VDP: VIN + Final/Best/Internet/etc.)</button>
  </form>
</div></body></html>
"""

PRICES_TEMPLATE = """
<!doctype html><html><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width,initial-scale=1'/>
<title>Vehicle Models & Prices</title>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:40px}
 .box{max-width:1200px;margin:auto;padding:24px;border:1px solid #ddd;border-radius:12px}
 table{border-collapse:collapse;width:100%;margin-top:12px}
 th,td{border:1px solid #eee;padding:8px 10px;text-align:left;font-size:14px;vertical-align:top}
 th{background:#fafafa}
 a{color:#0b5fff;text-decoration:none} a:hover{text-decoration:underline}
 .muted{color:#666;font-size:14px}
 button{margin-top:12px;padding:10px 16px;font-size:16px;border-radius:8px;border:0;background:#111;color:#fff;cursor:pointer}
</style></head>
<body><div class='box'>
  <h1>Vehicle Models & Prices</h1>
  <p class="muted">Reports only **true VDPs** where we found a VIN and a price. The price shown prefers labels like “Final/Best/Internet/E-Price/Our/Your/Dealer/Alpine Price” and avoids “MSRP/Savings/Discount/Payment/Lease/Finance”.</p>
  {% if rows %}
    <table>
      <tr><th>VIN</th><th>Price</th><th>Picked From</th><th>URL</th><th>Title</th></tr>
      {% for r in rows %}
      <tr>
        <td>{{ r.vin }}</td>
        <td>{{ r.price }}</td>
        <td>{{ r.label }}</td>
        <td><a href="{{ r.url }}" target="_blank" rel="noopener">open</a></td>
        <td>{{ r.title }}</td>
      </tr>
      {% endfor %}
    </table>
    <form method="post" action="{{ url_for('export_prices') }}" style="margin-top:12px;">
      <input type="hidden" name="url" value="{{ url|e }}">
      <input type="hidden" name="limit" value="{{ limit or 500 }}">
      <button type="submit">Download prices CSV</button>
    </form>
  {% else %}
    <p><em>No VDPs with VIN + a confident price found. Try raising the limit.</em></p>
  {% endif %}
</div></body></html>
"""

# ================= Routes =================
@app.route("/", methods=["GET"])
def home():
    return render_template_string(TEMPLATE, url="", limit=500)

@app.route("/prices", methods=["POST"])
def prices():
    url = (request.form.get("url") or "").strip()
    try: limit = max(50, min(1000, int(request.form.get("limit") or 500)))
    except Exception: limit = 500
    if not re.match(r"^https?://", url): url = "https://" + url
    rows = extract_vdp_rows(url, limit=limit)
    return render_template_string(PRICES_TEMPLATE, rows=rows, url=url, limit=limit)

@app.route("/export_prices", methods=["POST"])
def export_prices():
    url = (request.form.get("url") or "").strip()
    try: limit = max(50, min(1000, int(request.form.get("limit") or 500)))
    except Exception: limit = 500
    if not re.match(r"^https?://", url): url = "https://" + url
    rows = extract_vdp_rows(url, limit=limit)
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["URL Scanned", url]); w.writerow(["Scope", "HTML sitemap + VDP validation"]); w.writerow(["VDPs Reported", len(rows)]); w.writerow([])
    w.writerow(["VIN","Price","PickedFrom","VDP URL","Title"])
    for r in rows: w.writerow([r["vin"], r["price"], r["label"], r["url"], r["title"]])
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8")), mimetype="text/csv", as_attachment=True, download_name="vehicle_prices.csv")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
