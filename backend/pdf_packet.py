"""
BCAD Protest Evidence Packet Generator
=======================================
Produces a 4-page PDF the homeowner attaches to their BCAD E-File protest
or hands to the appraiser at the informal hearing:

  Page 1 — Cover summary (subject + recommended value + savings)
  Page 2 — Comparable properties grid (unequal appraisal evidence)
  Page 3 — Methodology disclosure (transparency for ARB credibility)
  Page 4 — Filing instructions (what to do with this packet)

Grounds asserted: Tex. Tax Code §41.43(b)(3) — unequal appraisal.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import date


def _fmt_money(v):
    if v is None: return '—'
    return f"${v:,.0f}"


def _fmt_pct(v):
    if v is None: return '—'
    return f"{v:.1f}%"


def build_packet(analysis, out_path: str, product_name: str = "Bexar Protest Helper"):
    """Build the evidence packet PDF.

    `analysis` is a CompAnalysis dataclass instance from comp_engine.analyze().
    """
    if not analysis.is_protestable:
        raise ValueError(f"Cannot build packet: not protestable ({analysis.reason})")

    doc = SimpleDocTemplate(out_path, pagesize=letter,
                            leftMargin=0.65*inch, rightMargin=0.65*inch,
                            topMargin=0.55*inch, bottomMargin=0.55*inch)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=styles['Heading1'], fontSize=18,
                        spaceAfter=4, textColor=colors.HexColor('#1a3a5c'))
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=13,
                        spaceBefore=12, spaceAfter=6,
                        textColor=colors.HexColor('#1a3a5c'))
    body = ParagraphStyle('body', parent=styles['BodyText'], fontSize=10,
                          leading=13, spaceAfter=6)
    small = ParagraphStyle('small', parent=styles['BodyText'], fontSize=8.5,
                           leading=11, textColor=colors.grey)
    bignum = ParagraphStyle('bignum', parent=styles['BodyText'], fontSize=22,
                            leading=24, textColor=colors.HexColor('#0a7c2a'),
                            alignment=TA_CENTER)

    story = []
    s = analysis.subject

    # ===== PAGE 1: COVER =====
    story.append(Paragraph(f"<b>Property Tax Protest Evidence Packet</b>", h1))
    story.append(Paragraph(f"Prepared {date.today():%B %d, %Y} &nbsp;·&nbsp; "
                           f"Tax Year {s.get('Year', 2026)} &nbsp;·&nbsp; "
                           f"Bexar Central Appraisal District",
                           small))
    story.append(Spacer(1, 0.18*inch))

    # Subject info table
    subj_tbl = Table([
        ['Property Address', s.get('SitusAddress', '')],
        ['Owner of Record', s.get('OwnerFullName', '')],
        ['BCAD Property ID', str(s.get('PropertyId', ''))],
        ['Geographic ID', s.get('GeoId', '') or ''],
        ['Legal Description', s.get('LegalDescription', '')[:80]],
    ], colWidths=[1.6*inch, 5.0*inch])
    subj_tbl.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), 'Helvetica', 10),
        ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 10),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#555')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-2), 0.25, colors.HexColor('#ddd')),
    ]))
    story.append(subj_tbl)
    story.append(Spacer(1, 0.22*inch))

    # Headline savings panel
    headline_tbl = Table([
        ['BCAD\nAppraised Value', 'Recommended\nValue', 'Estimated\nReduction',
         'Estimated Annual\nTax Savings'],
        [_fmt_money(s['AppraisedValue']), _fmt_money(analysis.target_value),
         f"{_fmt_money(analysis.estimated_reduction)}\n({_fmt_pct(analysis.estimated_pct_reduction)})",
         _fmt_money(analysis.estimated_annual_tax_savings)],
    ], colWidths=[1.65*inch]*4, rowHeights=[0.45*inch, 0.55*inch])
    headline_tbl.setStyle(TableStyle([
        ('FONT', (0,0), (-1,0), 'Helvetica', 9),
        ('FONT', (0,1), (-1,1), 'Helvetica-Bold', 13),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#666')),
        ('TEXTCOLOR', (2,1), (2,1), colors.HexColor('#0a7c2a')),
        ('TEXTCOLOR', (3,1), (3,1), colors.HexColor('#0a7c2a')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f6fa')),
        ('LINEABOVE', (0,1), (-1,1), 0.5, colors.HexColor('#cbd5e0')),
        ('LINEBELOW', (0,1), (-1,1), 1, colors.HexColor('#1a3a5c')),
        ('LINEBEFORE', (0,0), (0,-1), 1, colors.HexColor('#1a3a5c')),
        ('LINEAFTER', (-1,0), (-1,-1), 1, colors.HexColor('#1a3a5c')),
        ('LINEABOVE', (0,0), (-1,0), 1, colors.HexColor('#1a3a5c')),
    ]))
    story.append(headline_tbl)
    story.append(Spacer(1, 0.22*inch))

    story.append(Paragraph("<b>Protest Grounds</b>", h2))
    story.append(Paragraph(
        "<b>Unequal Appraisal</b> under Texas Tax Code §41.43(b)(3). The subject "
        f"property's appraised value of <b>{_fmt_money(s['AppraisedValue'])}</b> "
        f"exceeds the median appraised value of <b>{_fmt_money(analysis.median_appraised)}</b> "
        f"calculated from <b>{analysis.comp_count_total} comparable properties</b> "
        f"in the same {('city block and block' if analysis.geography_tier_used == 'CB+BLK' else 'city block')}. "
        "The taxpayer requests adjustment of the appraised value to the median "
        f"of the comparable properties: <b>{_fmt_money(analysis.target_value)}</b>.",
        body))
    story.append(Spacer(1, 0.05*inch))
    story.append(Paragraph(
        f"Bexar County&apos;s 2024 informal hearing success rate was <b>99.19%</b>. "
        "Because Bexar County moved to biennial appraisal in 2026, the value established "
        "in this protest will serve as the baseline for tax year 2027 as well — making "
        "this protest worth approximately twice a normal year&apos;s savings.",
        body))
    story.append(PageBreak())

    # ===== PAGE 2: COMP GRID =====
    story.append(Paragraph("Comparable Properties — Unequal Appraisal Evidence", h1))
    story.append(Paragraph(
        f"The following {len(analysis.comps)} properties are the lowest-appraised "
        f"comparable properties within the same "
        f"{('city block and block (BLK)' if analysis.geography_tier_used == 'CB+BLK' else 'city block (CB)')} "
        "as the subject. Under Tex. Tax Code §41.43(b)(3), the appraised value of "
        "the subject should be no greater than the median of these properties.",
        body))
    story.append(Spacer(1, 0.12*inch))

    # Subject highlight row + comp rows
    header = ['#', 'Property Address', 'BCAD Appraised', 'Market Value', 'Diff vs Subject']
    rows = [header]
    rows.append([
        '★', f"SUBJECT — {s['SitusAddress']}",
        _fmt_money(s['AppraisedValue']),
        _fmt_money(s.get('MarketValue')),
        '—',
    ])
    for i, c in enumerate(analysis.comps, 1):
        diff = c['appraised_value'] - s['AppraisedValue']
        diff_str = f"{'+' if diff >= 0 else '−'}{_fmt_money(abs(diff))}"
        rows.append([
            str(i), c['situs_address'],
            _fmt_money(c['appraised_value']),
            _fmt_money(c.get('market_value')),
            diff_str,
        ])
    # Median row
    rows.append(['', 'MEDIAN OF COMPARABLES',
                 _fmt_money(analysis.median_appraised),
                 _fmt_money(analysis.median_market) if analysis.median_market else '—',
                 ''])

    comp_tbl = Table(rows, colWidths=[0.3*inch, 3.0*inch, 1.2*inch, 1.2*inch, 1.0*inch])
    comp_tbl.setStyle(TableStyle([
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('FONT', (0,1), (-1,-2), 'Helvetica', 9),
        ('FONT', (0,1), (-1,1), 'Helvetica-Bold', 9),
        ('FONT', (0,-1), (-1,-1), 'Helvetica-Bold', 9.5),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a3a5c')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#fff4d6')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e8f4ea')),
        ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor('#0a7c2a')),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#ccc')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(comp_tbl)
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        f"<b>Median appraised value of comparables: {_fmt_money(analysis.median_appraised)}</b><br/>"
        f"<b>Subject&apos;s current appraised value: {_fmt_money(s['AppraisedValue'])}</b><br/>"
        f"<b>Requested adjustment: reduce to {_fmt_money(analysis.target_value)} "
        f"(a reduction of {_fmt_money(analysis.estimated_reduction)}, "
        f"{_fmt_pct(analysis.estimated_pct_reduction)}).</b>",
        body))
    story.append(PageBreak())

    # ===== PAGE 3: METHODOLOGY =====
    story.append(Paragraph("Methodology & Data Source", h1))
    story.append(Paragraph(
        "<b>Data source.</b> All property values and identifiers in this packet "
        "were retrieved from the 2026 Bexar Central Appraisal District (BCAD) "
        "certified appraisal roll. Values are stated as of January 1, 2026, the "
        "Texas statutory valuation date.",
        body))
    story.append(Paragraph(
        "<b>Comparable selection.</b> Comparable properties were selected from the "
        "same City Block (CB) as the subject, "
        f"{'further restricted to the same Block (BLK)' if analysis.geography_tier_used == 'CB+BLK' else 'as identified in the BCAD legal description'}, "
        "and filtered to a reasonable value range to exclude properties of "
        "materially different type. A minimum of five comparables was required "
        f"to perform the analysis; {analysis.comp_count_total} comparables were identified for this property.",
        body))
    story.append(Paragraph(
        "<b>Value calculation.</b> The recommended value is the median appraised "
        "value of the comparable property set. The median is the standard measure "
        "used in Texas unequal-appraisal protests because it is resistant to "
        "outliers and matches the statutory framing of Tex. Tax Code §41.43(b)(3).",
        body))
    story.append(Paragraph(
        "<b>Limitations.</b> The BCAD appraisal roll does not publish square "
        "footage, year built, lot size, or property condition. Comparable selection "
        "therefore relies on geographic proximity (same City Block) and value-band "
        "filtering as proxies for similarity. The taxpayer should review each "
        "listed comparable and may strengthen the case at the hearing by noting "
        "any condition, size, or feature differences favorable to a lower value. "
        "If the appraisal district produces comparables of its own showing a "
        "higher median, the taxpayer may rebut by emphasizing the closest-"
        "geography comparables from this packet.",
        body))
    story.append(Paragraph(
        "<b>Tax savings estimate.</b> Estimated annual tax savings are calculated "
        "using a blended Bexar County effective tax rate of 2.03%, consistent with "
        "the 2024 county-wide average. The taxpayer&apos;s actual savings will depend "
        "on the exact combined rate of overlapping taxing entities (school district, "
        "municipal, county, special districts) and any applicable exemptions.",
        body))
    story.append(Paragraph(
        f"<i>This packet was prepared by {product_name}. It is provided as evidence "
        "the taxpayer may submit to BCAD in support of their own protest under "
        f"Tex. Tax Code §41.41. {product_name} is not acting as the taxpayer&apos;s agent "
        "of record (Form 50-162 is not filed); the taxpayer remains responsible for "
        "filing the Notice of Protest (Form 50-132) and presenting their case.</i>",
        small))
    story.append(PageBreak())

    # ===== PAGE 4: HOW TO FILE =====
    story.append(Paragraph("How to File Your Protest Using This Packet", h1))
    story.append(Paragraph(
        "<b>You must file before Friday, May 15, 2026 at 11:59 PM Central.</b> "
        "Late filings are accepted only with documented good cause and at the ARB&apos;s "
        "discretion.",
        body))
    story.append(Spacer(1, 0.1*inch))

    steps = [
        ("Step 1 — File the Notice of Protest (Form 50-132)",
         "Fastest: go to <b>bcad.org</b> and click &quot;E-File Your Protest.&quot; You will need "
         "your Owner ID and PIN, which appear on your Notice of Appraised Value "
         "(NOAV). If you did not receive an NOAV, you can still file — go to "
         "bcad.org, look up your property, and request the PIN. <br/><br/>"
         "On Form 50-132, check <b>BOTH</b> of these boxes to preserve all your rights:<br/>"
         "&nbsp;&nbsp;☑ Incorrect appraised (market) value<br/>"
         "&nbsp;&nbsp;☑ Value is unequal compared with other properties"),

        ("Step 2 — Upload this packet as your evidence",
         "On the E-File portal, attach this PDF as supporting evidence. Also check "
         "the box requesting BCAD&apos;s evidence under Tex. Tax Code §41.461. "
         "BCAD must give you their comparables 14 days before the hearing."),

        ("Step 3 — Attend the informal hearing",
         "BCAD will schedule a phone, video, or in-person informal hearing, "
         "usually 30–90 days after you file. The appraiser will offer a value. "
         "<b>99.19% of Bexar County informal protests result in a reduction.</b> "
         "Bring this packet, plus any photos of property condition issues or "
         "recent repair estimates. If you reject the appraiser&apos;s offer, ask them "
         "to note it on the record and proceed to a formal ARB hearing."),

        ("Step 4 — Pay your taxes by January 31, 2027",
         "Filing a protest does not delay your tax payment deadline. Pay the "
         "amount based on BCAD&apos;s current value to avoid penalty; any overpayment "
         "from a successful protest will be refunded."),
    ]
    for title, text in steps:
        story.append(Paragraph(f"<b>{title}</b>", h2))
        story.append(Paragraph(text, body))

    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<b>BCAD contact:</b> 411 N. Frio Street, San Antonio, TX 78207 · "
        "(210) 224-2432 · bcad.org · help@bcad.org",
        small))

    doc.build(story)
    return out_path
