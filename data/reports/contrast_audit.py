#!/usr/bin/env python3
# Read-only contrast audit for the Ameen Games palette. No project files modified.
def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

def rel_lum(hex_color):
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

def ratio(fg, bg):
    l1, l2 = rel_lum(fg), rel_lum(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)

PAIRS = [
    ("text-primary #e8e8f0", "bg-primary  #0f0f1a", "#e8e8f0", "#0f0f1a"),
    ("text-primary #e8e8f0", "bg-card     #16213e", "#e8e8f0", "#16213e"),
    ("text-secondary #a0a0b8", "bg-card   #16213e", "#a0a0b8", "#16213e"),
    ("text-muted #6b6b80", "bg-card     #16213e", "#6b6b80", "#16213e"),
    ("accent-gold #f59e0b", "bg-card     #16213e", "#f59e0b", "#16213e"),
    ("accent-gold #f59e0b", "bg-primary  #0f0f1a", "#f59e0b", "#0f0f1a"),
    ("accent-blue #3b82f6", "bg-card     #16213e", "#3b82f6", "#16213e"),
    ("text-primary #e8e8f0", "bg-secondary #1a1a2e", "#e8e8f0", "#1a1a2e"),
    ("text-secondary #a0a0b8", "bg-primary #0f0f1a", "#a0a0b8", "#0f0f1a"),
    ("white #ffffff (btn-primary)", "gradient blue->purple ~#5f6fe8", "#ffffff", "#5f6fe8"),
]

print(f"{'pair':48} {'ratio':>7}  AA-normal(4.5)  AA-large(3.0)")
for name, _, fg, bg in PAIRS:
    r = ratio(fg, bg)
    print(f"{name:48} {r:7.2f}  {'PASS' if r>=4.5 else 'FAIL':14}  {'PASS' if r>=3.0 else 'FAIL'}")

# What would text-muted need to reach AA normal?
for cand in ["#6b6b80", "#8a8a9e", "#9a9ab0", "#a0a0b8"]:
    print(f"muted candidate {cand} on bg-card: {ratio(cand,'#16213e'):.2f}")
