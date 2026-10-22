# DESIGN.md — Design System for Agents

> Read this file before writing or editing any UI. Follow it strictly. Do not introduce colors, fonts, radii, or shadows that are not defined here. Hex values were sampled by eye from reference screenshots, so treat them as the source of truth and tune only here.

## 1. Design intent

**Editorial display type meets utilitarian mono numerics, soft platinum layers, and a single electric lime accent that drives every primary moment.**

- Calm, daylight canvas. Light platinum background, white cards, one dark "hero" panel for contrast.
- Lime is the ONLY accent. If something is not the primary action, a highlight, or positive data, it is not lime.
- Big confident headlines, tiny quiet labels, tabular mono numbers.
- Feels like a pro analytics desk tool: dense but airy, never decorative.

## 2. Color tokens

```css
:root {
  /* Surfaces */
  --bg:            #E8ECF0;  /* page, platinum */
  --bg-grad-top:   #F1F5EC;  /* faint lime-tinted wash at top of page */
  --surface:       #FFFFFF;  /* cards */
  --surface-2:     #F0F3F6;  /* inset panels, inputs, chart wells */
  --surface-3:     #E4E9EE;  /* segmented-control track, hover */
  --border:        #E3E8ED;  /* hairlines on white */

  /* Ink */
  --ink:           #0B1014;  /* headlines, ink buttons, dark panels */
  --ink-2:         #121A1F;  /* dark panel secondary */
  --text:          #1A2329;  /* body on light */
  --muted:         #6B7785;  /* secondary text, labels (slate) */
  --faint:         #9AA5B1;  /* placeholders, disabled text */

  /* Accent (lime) */
  --lime:          #D8FF3E;  /* primary accent, buttons, highlights */
  --lime-strong:   #A9CC1E;  /* chart bars, secondary lime, icons on light */
  --lime-soft:     #EEFFB0;  /* chip/pill tint, disabled primary, chart fill */
  --lime-glow:     rgba(216, 255, 62, 0.45); /* button/CTA glow shadow */

  /* Semantic data colors (deltas only) */
  --pos:           #3E9B2F;  --pos-bg: #E6F6C8;
  --neg:           #D9473F;  --neg-bg: #FBE4E1;

  /* Dark hero panel */
  --hero-bg:       #0A0F12;
  --hero-glow:     radial-gradient(60% 60% at 85% 0%, rgba(168,204,30,.28), transparent 70%);
  --hero-card:     rgba(255,255,255,.04); /* glass card on dark, 1px border rgba(255,255,255,.08) */
  --hero-text:     #FFFFFF;
  --hero-muted:    #8C98A4;
}
```

**Color rules**
1. Text on lime is always `--ink`. Never white on lime.
2. Lime fill = primary action, active toggle, key highlight, positive KPI chip. Max 1 to 2 lime-filled elements per viewport section.
3. Red/green only for numeric deltas (+2.84%, -0.62%). Never for buttons or decoration.
4. Dark panels: ink background, white text, lime for the one key number or CTA.
5. Contrast: muted text must stay readable; do not go lighter than `--faint` and only for placeholders.

## 3. Typography

| Role | Font | Weight | Notes |
|---|---|---|---|
| Display / headlines | **Instrument Sans** | 600-700 | Tight tracking (-0.03em), line-height 0.95-1.05 |
| UI / body | **Inter** | 400-600 | 14-16px body, 12-13px labels |
| Numbers / tickers / data | **JetBrains Mono** | 400-600 | Always `font-variant-numeric: tabular-nums` |

```css
--font-display: "Instrument Sans", "Inter", system-ui, sans-serif;
--font-ui:      "Inter", system-ui, sans-serif;
--font-mono:    "JetBrains Mono", ui-monospace, monospace;
```

**Scale**
- Hero H1: `clamp(44px, 7vw, 88px)`, display 700
- Section H2: 32-44px, display 700
- Card title: 16-18px, Inter 600
- Body: 14-16px, Inter 400, `--muted` for secondary
- Label / caption: 11-12px, Inter 500, `--muted`
- Eyebrow / ticker (e.g. `VOLT / USD · 1M`): 11px mono, uppercase, letter-spacing 0.08em, `--muted`
- Big KPI number: 40-56px, display 700 (hero metric) or mono 600 (inline stats)
- Small KPI: 18-24px mono 600 with a 12px muted unit label beside it

**Signature move: the highlighted word.** One key word per headline gets a lime marker block behind it:
```css
.mark {
  background: linear-gradient(transparent 55%, var(--lime) 55%);
  padding: 0 .08em;
}
```
On dark backgrounds the key phrase is instead colored `--lime` (no block). Use once per headline, never more.

## 4. Shape, spacing, elevation

- **Radius:** cards 20-24px, inner panels 14-16px, inputs 10-12px, buttons/chips/tabs fully round (999px), checkboxes 6px.
- **Spacing scale (px):** 4, 8, 12, 16, 20, 24, 32, 48, 64. Card padding 20-24px. Grid gap 16-20px.
- **Borders:** 1px `--border` on white cards, or none with shadow. Dark glass cards use 1px `rgba(255,255,255,.08)`.
- **Shadows (soft, never hard black):**
  - Card: `0 1px 2px rgba(11,16,20,.04), 0 8px 24px rgba(11,16,20,.06)`
  - Primary button/CTA glow: `0 6px 20px var(--lime-glow)`
  - Dark hero: no shadow, use the lime radial glow in a corner.
- **Layout:** max-width ~1100-1200px, centered. Bento grids of cards (3-up feature row, 2-col dashboard: main chart left, watchlist/order right). Page sits on `--bg`, content on white cards with generous outer margin.

## 5. Components

### Buttons (all pill-shaped, 40-44px tall, Inter 600 14px)
| Variant | Style |
|---|---|
| **Primary** | bg `--lime`, text `--ink`, lime glow shadow, optional leading/trailing arrow icon |
| **Secondary** | bg white, 1px `--border`, text `--ink` |
| **Ink** | bg `--ink`, text white, optional lock icon |
| **Ghost** | transparent, text `--ink`, hover `--surface-2` |
| **Disabled** | bg `--lime-soft`, text `--faint`, no glow, `cursor: not-allowed` |

Hover: primary brightens slightly and lifts 1px; others get `--surface-2`. Focus: 2px `--ink` outline offset 2px.

### Chips and badges (pill, 22-26px tall, 11-12px text)
- **Delta chip positive:** `--pos-bg` or `--lime` bg, `--ink`/`--pos` text, up-right arrow icon, mono value
- **Delta chip negative:** `--neg-bg` bg, `--neg` text, down arrow
- **Status chip (Live):** `--surface-2` bg, small lime dot, ink text
- **Neutral/outline chip:** white, 1px border
- **Dark chip (Halted):** `--ink` bg, white text

### Tabs and segmented controls
Track: `--surface-2`/`--surface-3`, pill, 4px inner padding. Active segment: white pill with subtle shadow, ink text weight 600. Inactive: `--muted`. Used for ranges (1D 1W 1M 6M YTD All) and views (Board / List / Calendar).

### Inputs and fields
Bg `--surface-2`, no border (or 1px `--border`), radius 10-12px, 40px tall, placeholder `--faint`. Leading search icon. Numeric inputs use mono. Helper text 11px `--muted` below (for example, "Press / to focus from anywhere").

### Checkboxes
18px rounded square (6px). Checked: `--lime` fill with ink check mark. Unchecked: white with 1px border. Label 13-14px.

### Cards
- **Feature card:** white, 20px radius, icon in a 32px `--surface-2` rounded square, title 16px 600, 2-line muted description, hairline divider, then a mono stat (`98.4%`) with a small muted label.
- **Highlighted feature card:** same layout, bg `--lime`, text `--ink`. Use for exactly one card in a row.
- **KPI tile (inset):** `--surface-2`, radius 14px, muted label on top, bold mono value, tiny delta below (green/red).
- **Dark pricing/CTA card:** `--ink` bg, white title, big lime price (`$48`) with small muted unit, checklist with muted check icons, full-width lime pill CTA with glow.
- **List rows (watchlist, activity):** avatar/ticker chip (28px circle, `--surface-2`, lime variant for the active one), name + muted subtitle on left, mono price and colored delta right-aligned. Rows separated by whitespace or hairlines, no heavy borders.

### Navigation
Top nav is a dark ink pill (fully rounded) floating over the page: logo mark (lime rounded square with bolt icon) + wordmark, nav items with small icons (active item has a lighter ink pill behind it), right side has "Sign in" text link and a lime "Get started" pill. Light-mode footer is a white rounded bar with logo left and muted links right.

### Hero (dark panel)
Radius 24-28px, `--hero-bg` with lime radial glow top right. Left: H1 (white with lime key phrase), muted paragraph, primary lime button + secondary dark outlined button. Below: 3 to 4 stats (white bold number, muted label) separated by a hairline. Right: a glass card with small title and icon row.

## 6. Data visualization

- **Sparkline bars:** equal-width rounded-top bars in a repeating mix of `--ink`, `--lime`, `--lime-strong`. Used as decorative KPI sparkline.
- **Area/line chart:** 2px `--ink` line, fill is a vertical gradient from `--lime-soft` (top, ~60% opacity) to transparent, end point is a 10px lime dot with 2px ink stroke. Light horizontal gridlines only, no vertical gridlines, axis labels 11px muted.
- **Waterfall charts:** increases `--lime-strong`, decreases `--ink` or `--neg`, totals `--ink`.
- Chart wells sit on `--surface-2` with radius 14-16px.
- Always show the big current value (mono or display) above the chart with a delta chip, and a muted sub-label such as "+$1,824.40 last 7d".

## 7. Iconography
Outline icons, 16-18px, 1.5px stroke (Lucide style), color `--muted` or `--ink`. Logo mark is a lime rounded square with a dark bolt. Never use filled multi-color icons or emoji in UI.

## 8. Motion
Subtle only: 150-200ms ease-out on hover/focus, 1px lift on buttons, fade/slide-up 8px on card entry. Live indicators may pulse the lime dot. No bouncing, no parallax.

## 9. Do / Don't

**Do**
- Use one lime highlight word per headline.
- Keep numbers in tabular mono, right-aligned in lists.
- Mix white cards with `--surface-2` inset panels for depth instead of borders.
- Keep copy short and confident (for example, "A reliable tool for successful trading.").

**Don't**
- Add a second accent color (no blue, purple, orange).
- Use pure black `#000` or pure grey shadows; use `--ink` and tinted shadows.
- Put white text on lime, or lime text on white.
- Use sharp corners, heavy borders, gradients other than the defined glow/fill, or stock illustrations.
- Fill the page with lime; it must stay rare so it stays electric.

## 10. Agent checklist (run before finishing any UI task)
1. Colors only from section 2 tokens? Lime used sparingly?
2. Three fonts only, numbers in mono with tabular figures?
3. Radii, spacing, shadows from section 4?
4. Buttons, chips, tabs, inputs match section 5 exactly?
5. Charts follow section 6?
6. Responsive: cards stack on mobile, hero H1 scales with `clamp`, tap targets at least 40px?
7. Accessible: visible focus ring, text contrast at least 4.5:1, state not conveyed by color alone (add arrow icons to deltas)?