"""Small plotting defaults and explicit layout checks for this public project.

This module was written for the public release. It does not vendor the
math-modeling Skill's plotting implementation.
"""
from __future__ import annotations

import math
import matplotlib as mpl
from matplotlib import font_manager


PALETTE = {
    "primary": "#0072B2",
    "contrast": "#D55E00",
    "positive": "#009E73",
    "accent": "#CC79A7",
}


def apply_publication_style(language="zh"):
    installed = {font.name for font in font_manager.fontManager.ttflist}
    candidates = ["PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei",
                  "WenQuanYi Zen Hei", "DejaVu Sans"]
    chosen = [name for name in candidates if name in installed]
    if language != "zh":
        chosen = ["DejaVu Sans"]
    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": chosen,
        "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
        "axes.unicode_minus": False, "axes.spines.top": False,
        "axes.spines.right": False, "axes.linewidth": 0.7,
        "lines.linewidth": 1.2, "pdf.fonttype": 42, "ps.fonttype": 42,
        "svg.fonttype": "none", "savefig.facecolor": "white",
    })


def audit_layout(fig):
    """Check axes, titles, annotations and legends against the figure canvas.

This is a bounds check, not a substitute for viewing the exported figure.
"""
    # PingFang's supplied semibold face is weight 600. Request that face
    # explicitly instead of asking the PDF/SVG font exporter for absent 700.
    if ("PingFang SC" in mpl.rcParams["font.sans-serif"]
            and any(font.name == "PingFang SC"
                    for font in font_manager.fontManager.ttflist)):
        for text in fig.findobj(match=mpl.text.Text):
            if text.get_fontweight() == "bold":
                text.set_fontweight(600)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    issues = []
    for index, axis in enumerate(fig.axes):
        box = axis.get_position()
        if min(box.x0, box.y0) < -1e-5 or max(box.x1, box.y1) > 1.00001:
            issues.append(f"axes {index}: outside canvas")
        texts = [axis.xaxis.label, axis.yaxis.label, axis.title,
                 axis._left_title, axis._right_title, *axis.texts]
        legend = axis.get_legend()
        if legend is not None:
            texts.extend(legend.get_texts())
        for text in texts:
            if not text.get_visible() or not text.get_text().strip():
                continue
            bounds = text.get_window_extent(renderer)
            if (bounds.x0 < canvas.x0 - 2 or bounds.y0 < canvas.y0 - 2
                    or bounds.x1 > canvas.x1 + 2 or bounds.y1 > canvas.y1 + 2):
                issues.append(f"axes {index}: label outside canvas: {text.get_text()}")
    return issues


def audit_design(fig):
    """Check finite dimensions, axes presence, and legible text size."""
    issues = []
    if not all(math.isfinite(float(x)) and x > 0 for x in fig.get_size_inches()):
        issues.append("figure dimensions must be positive and finite")
    if not fig.axes:
        issues.append("figure has no axes")
    for index, axis in enumerate(fig.axes):
        labels = [axis.xaxis.label, axis.yaxis.label, axis.title,
                  *axis.get_xticklabels(), *axis.get_yticklabels(), *axis.texts]
        for label in labels:
            if label.get_visible() and label.get_text().strip() and label.get_fontsize() < 6:
                issues.append(f"axes {index}: text smaller than 6 pt")
    return issues
