"""Look and feel: colors, icons, chart template and small UI helpers.

The app is styled like a clean clinical chart: navy + teal, white "patient cards",
a heartbeat logo, and vital-sign style status colors (healthy / monitor / critical).
"""
from shiny import ui

# ---------- palette ----------
NAVY = "#0b3c5d"
PRIMARY = "#0e7490"     # medical teal-blue
TEAL = "#14b8a6"
MINT = "#ccfbf1"
GREEN = "#10b981"
AMBER = "#f59e0b"
RED = "#e11d48"
SLATE = "#64748b"
LIGHT = "#a5d8e6"
COLORWAY = [PRIMARY, TEAL, AMBER, "#6366f1", RED, GREEN, SLATE]

# ---------- icons (simple 24x24 stroke icons drawn for this app) ----------
_P = {
    "pulse": '<path d="M2 12h4l2-5 4 10 3-7 2 2h5"/>',
    "stethoscope": '<path d="M6 3v5a4 4 0 0 0 8 0V3"/><path d="M10 12v3a5 5 0 0 0 10 0v-2"/>'
                   '<circle cx="20" cy="11" r="2"/>',
    "heart": '<path d="M12 20s-7-4.4-9-9a4.5 4.5 0 0 1 9-3 4.5 4.5 0 0 1 9 3c-2 4.6-9 9-9 9z"/>',
    "wallet": '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/>'
              '<circle cx="16.5" cy="14.5" r="1"/>',
    "piggy": '<path d="M4 12a7 6 0 0 1 13-3h2l1 3-2 1v3h-2l-1 2h-2l-1-1h-3l-1 1H6l-1-2a6 6 0 0 1-1-4z"/>'
             '<circle cx="15" cy="11" r=".5"/>',
    "scale": '<path d="M12 4v16M5 20h14M4 8h16"/><path d="M4 8l-2 6h6zM20 8l-2 6h6z"/>',
    "hourglass": '<path d="M6 3h12M6 21h12M7 3c0 5 10 5 10 9s-10 4-10 9M17 3c0 5-10 5-10 9s10 4 10 9"/>',
    "brain": '<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a3 3 0 0 0-3-1z"/>'
             '<path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v4M12 17v.5"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "percent": '<path d="M5 19L19 5"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
    "map": '<path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "home": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M12 11v6M9 14h6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "check": '<path d="M5 12l5 5 9-10"/>',
    "dollar": '<path d="M12 2v20"/><path d="M17 6.5c-1-1.5-3-2-5-2-3 0-4.5 1.5-4.5 3.5 0 4.5 10 2.5 10 7.5 '
              '0 2-2 3.5-5 3.5-2.5 0-4.5-1-5.5-2.5"/>',
}


def icon(name, size=22, cls=""):
    return ui.HTML(
        f'<svg class="mdw-icon {cls}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{_P[name]}</svg>')


LOGO = ui.HTML(
    '<span class="mdw-logo"><svg width="34" height="34" viewBox="0 0 40 40" aria-hidden="true">'
    '<rect width="40" height="40" rx="10" fill="#ffffff22"/>'
    '<path d="M20 33s-11-6.5-13.5-13.5A6.6 6.6 0 0 1 20 13a6.6 6.6 0 0 1 13.5 6.5C31 26.5 20 33 20 33z" '
    'fill="#ffffff" opacity=".95"/>'
    '<path d="M8 22h6l2-4 3 7 3-10 2.5 7H32" fill="none" stroke="#0e7490" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    '<span class="mdw-brand">MD<b>Wealth</b><small>financial care for physicians</small></span></span>')

# ---------- value boxes: icon + color picked from the title ----------
_VB_RULES = [  # (keyword in title, icon, tone)
    ("net worth", "scale", "navy"), ("savings rate", "piggy", "teal"),
    ("debt", "alert", "amber"), ("horizon", "hourglass", "navy"),
    ("human capital", "brain", "teal"), ("chance", "target", "green"),
    ("change", "pulse", "amber"), ("typical", "chart", "navy"),
    ("real return", "trend", "teal"), ("worst", "alert", "red"),
    ("mix", "pulse", "navy"), ("gross", "dollar", "navy"),
    ("take-home", "wallet", "teal"), ("tax", "percent", "amber"),
    ("left to save", "piggy", "green"), ("rank", "map", "navy"),
    ("best state", "target", "teal"), ("buying beats", "home", "green"),
]


def vbox(title, value, *extra, **kw):
    """ui.value_box with a vital-sign style icon and color chosen from the title."""
    t = title.lower()
    ic, tone = next(((i, c) for k, i, c in _VB_RULES if k in t), ("pulse", "navy"))
    return ui.value_box(title, value, *extra, showcase=icon(ic, 30), class_=f"mdw-vb mdw-{tone}", **kw)


def tab_header(title, question, icon_name, tip=None):
    """Banner at the top of each tab: what this tab answers, in plain words."""
    return ui.div(
        ui.div(icon(icon_name, 30), class_="mdw-hero-icon"),
        ui.div(ui.h2(title), ui.p(question, class_="mdw-hero-q"),
               ui.p(tip, class_="mdw-hero-tip") if tip else None),
        class_="mdw-hero",
    )


# Vital-sign style status labels for the goals dashboard
STATUS_STYLE = {
    "On track": ("Healthy", "check", "ok"),
    "Behind": ("Monitor", "pulse", "warn"),
    "At risk": ("Critical", "alert", "bad"),
}


def register_plotly_template():
    """One chart style for every figure: clean white, teal colorway, readable fonts."""
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:
        return
    pio.templates["mdwealth"] = go.layout.Template(layout=dict(
        font=dict(family="Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
                  size=13, color="#1e293b"),
        colorway=COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1", linecolor="#cbd5e1"),
        yaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1", linecolor="#cbd5e1"),
        hoverlabel=dict(bgcolor="white", bordercolor=PRIMARY, font=dict(color="#0f172a")),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    ))
    pio.templates.default = "plotly_white+mdwealth"
