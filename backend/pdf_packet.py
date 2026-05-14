"""
Evidence packet generator for supported county appraisal appeals.
"""

from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_money(v, fallback="N/A"):
    if v is None:
        return fallback
    return f"${v:,.0f}"


def _fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v:.1f}%"


def _same_area_label(analysis):
    return analysis.geography_tier_used or "same local comp area"


def _county_specific_steps(county):
    if county["id"] == "bexar":
        return [
            (
                "Step 1 - File the Notice of Protest",
                "Go to bcad.org and use the E-File protest portal. You will need "
                "your Owner ID and PIN from your Notice of Appraised Value. On "
                "Form 50-132, preserve both market value and unequal appraisal "
                "grounds if they apply.",
            ),
            (
                "Step 2 - Upload this packet",
                "Attach this PDF as supporting evidence. It summarizes comparable "
                "properties and the median value calculation for the subject.",
            ),
            (
                "Step 3 - Attend the informal hearing",
                "Bring this packet plus any photos, repair estimates, recent sale "
                "documents, or condition details that support a lower value.",
            ),
        ]

    return [
        (
            "Step 1 - File the real property appeal",
            "Use the Arapahoe County Assessor appeal process at arapahoeco.gov/"
            "assessor. The residential appeal deadline shown by the county for "
            "2026 is June 8, 2026.",
        ),
        (
            "Step 2 - Include comparable evidence",
            "Attach or reference this packet as a comparable-value screen. It is "
            "strongest when paired with recent sales, condition photos, or other "
            "property-specific evidence.",
        ),
        (
            "Step 3 - Keep the county response",
            "Save the Assessor's determination and any evidence they provide. If "
            "you disagree, follow the next appeal instructions listed by the county.",
        ),
    ]


def build_packet(analysis, out_path: str, product_name: str = "Property Protest Helper"):
    """Build an evidence packet PDF from comp_engine.CompAnalysis."""
    if not analysis.is_protestable:
        raise ValueError(f"Cannot build packet: not protestable ({analysis.reason})")

    county = analysis.county
    s = analysis.subject
    assessor_short = county["assessor_short"]

    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "h1",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=4,
        textColor=colors.HexColor("#1a3a5c"),
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#1a3a5c"),
    )
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=13, spaceAfter=6)
    small = ParagraphStyle(
        "small",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
        textColor=colors.grey,
    )
    bignum = ParagraphStyle(
        "bignum",
        parent=styles["BodyText"],
        fontSize=22,
        leading=24,
        textColor=colors.HexColor("#0a7c2a"),
        alignment=TA_CENTER,
    )

    story = []

    story.append(Paragraph("<b>Property Valuation Evidence Packet</b>", h1))
    story.append(
        Paragraph(
            f"Prepared {date.today():%B %d, %Y} | Tax Year {s.get('Year', 2026)} | "
            f"{county['assessor_label']}",
            small,
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    subject_rows = [
        ["Property Address", s.get("SitusAddress", "")],
        ["Owner of Record", s.get("OwnerFullName", "")],
        [county["property_id_label"], str(s.get("PropertyId", ""))],
        ["Geo/PIN", s.get("GeoId", "") or ""],
    ]
    if county["id"] == "arapahoe":
        subject_rows.append(["Neighborhood", s.get("Neighborhood", "") or ""])
        subject_rows.append(["Property Type", s.get("PropertyUse", "") or ""])
    else:
        subject_rows.append(["Legal Description", (s.get("LegalDescription", "") or "")[:90]])

    subj_tbl = Table(subject_rows, colWidths=[1.65 * inch, 5.0 * inch])
    subj_tbl.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 10),
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#ddd")),
            ]
        )
    )
    story.append(subj_tbl)
    story.append(Spacer(1, 0.22 * inch))

    savings_label = "Estimated Annual Tax Savings" if analysis.estimated_annual_tax_savings is not None else "Tax Savings"
    headline_tbl = Table(
        [
            [
                f"{assessor_short}\nValue",
                "Recommended\nValue",
                "Estimated\nReduction",
                savings_label.replace(" ", "\n", 1),
            ],
            [
                _fmt_money(s.get("AppraisedValue")),
                _fmt_money(analysis.target_value),
                f"{_fmt_money(analysis.estimated_reduction)}\n({_fmt_pct(analysis.estimated_pct_reduction)})",
                _fmt_money(analysis.estimated_annual_tax_savings, "Varies by tax district"),
            ],
        ],
        colWidths=[1.65 * inch] * 4,
        rowHeights=[0.45 * inch, 0.62 * inch],
    )
    headline_tbl.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica", 9),
                ("FONT", (0, 1), (-1, 1), "Helvetica-Bold", 12),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#666")),
                ("TEXTCOLOR", (2, 1), (3, 1), colors.HexColor("#0a7c2a")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f6fa")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ]
        )
    )
    story.append(headline_tbl)
    story.append(Spacer(1, 0.22 * inch))

    story.append(Paragraph("<b>Why this property may have a case</b>", h2))
    story.append(
        Paragraph(
            f"The subject property's value of <b>{_fmt_money(s.get('AppraisedValue'))}</b> "
            f"exceeds the median value of <b>{_fmt_money(analysis.median_appraised)}</b> "
            f"from <b>{analysis.comp_count_total} comparable properties</b> in the "
            f"<b>{_same_area_label(analysis)}</b> comp set. This packet requests a "
            f"value adjustment to <b>{_fmt_money(analysis.target_value)}</b> based on "
            f"{county['evidence_basis']}.",
            body,
        )
    )
    story.append(
        Paragraph(
            "This is a data-driven screen, not a final appraisal. The strongest "
            "appeal combines comparable-value evidence with any property-specific "
            "facts such as condition, recent purchase price, repair estimates, or "
            "nearby sales.",
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("Comparable Properties", h1))
    story.append(
        Paragraph(
            f"The comparables below are selected from the {county['label']} appraisal "
            f"data using the tightest supported geography for this county: "
            f"<b>{_same_area_label(analysis)}</b>. The table emphasizes the lower end "
            "of the valid comp set because those properties support the requested "
            "median-value adjustment.",
            body,
        )
    )
    story.append(Spacer(1, 0.12 * inch))

    header = ["#", "Property Address", f"{assessor_short} Value", "Assessed", "Diff vs Subject"]
    rows = [header]
    rows.append(
        [
            "*",
            f"SUBJECT - {s.get('SitusAddress', '')}",
            _fmt_money(s.get("AppraisedValue")),
            _fmt_money(s.get("AssessedValue")),
            "-",
        ]
    )
    for i, c in enumerate(analysis.comps, 1):
        diff = c["appraised_value"] - s["AppraisedValue"]
        diff_str = f"{'+' if diff >= 0 else '-'}{_fmt_money(abs(diff))}"
        rows.append(
            [
                str(i),
                c["situs_address"],
                _fmt_money(c["appraised_value"]),
                _fmt_money(c.get("assessed_value")),
                diff_str,
            ]
        )
    rows.append(
        [
            "",
            "MEDIAN OF COMPARABLES",
            _fmt_money(analysis.median_appraised),
            "",
            "",
        ]
    )

    comp_tbl = Table(rows, colWidths=[0.3 * inch, 3.25 * inch, 1.15 * inch, 1.0 * inch, 1.0 * inch])
    comp_tbl.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
                ("FONT", (0, 1), (-1, -2), "Helvetica", 8.2),
                ("FONT", (0, 1), (-1, 1), "Helvetica-Bold", 8.5),
                ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fff4d6")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f4ea")),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#0a7c2a")),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ccc")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(comp_tbl)
    story.append(Spacer(1, 0.15 * inch))
    story.append(
        Paragraph(
            f"<b>Requested adjustment:</b> reduce from {_fmt_money(s.get('AppraisedValue'))} "
            f"to {_fmt_money(analysis.target_value)}, a reduction of "
            f"{_fmt_money(analysis.estimated_reduction)} "
            f"({_fmt_pct(analysis.estimated_pct_reduction)}).",
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("Methodology & Filing Notes", h1))
    story.append(
        Paragraph(
            f"<b>Data source.</b> Values and identifiers in this packet come from "
            f"{county['data_source']}. The analysis uses the assessor-published "
            "appraisal roll and does not independently inspect the property.",
            body,
        )
    )
    story.append(
        Paragraph(
            f"<b>Comp selection.</b> For {county['label']}, comparable properties are "
            f"drawn from the <b>{_same_area_label(analysis)}</b> group and filtered "
            "to a value band around the subject property. A minimum of five comps is "
            "required before the tool generates a packet.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Calculation.</b> The recommended value is the median appraised value "
            "of the comp set. Median-based comparison is used because it is less "
            "sensitive to outliers than an average.",
            body,
        )
    )
    story.append(
        Paragraph(
            "<b>Limitations.</b> Public appraisal rolls may omit square footage, "
            "condition, remodels, view, basement details, or other characteristics "
            "that affect value. Review each comp before filing and add any evidence "
            "that makes your property less valuable than the assessor's estimate.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))

    for title, text in _county_specific_steps(county):
        story.append(Paragraph(f"<b>{title}</b>", h2))
        story.append(Paragraph(text, body))

    story.append(Spacer(1, 0.15 * inch))
    story.append(
        Paragraph(
            f"Prepared by {product_name}. Built with public county appraisal data. "
            f"Not affiliated with or endorsed by {county['assessor_label']}.",
            small,
        )
    )

    doc.build(story)
    return out_path
