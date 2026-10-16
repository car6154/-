---
name: ui-ux-polisher
description: Guidelines for modern, high-density, professional UI/UX design (dark/light themes, typography, dashboard ergonomics, and visual hierarchy) in React + Tailwind/CSS apps.
---

# UI/UX Polisher Best Practices

## 1. Professional Data-Dense Layouts
- **Hierarchy & Contrast**: Distinguish primary numbers (e.g. 추천입찰가, 예상마진) with strong typography (`font-bold`, large scale) while keeping secondary labels subtle (`text-gray-400` or muted tones).
- **Consistent Color Semantics**:
  - Positive / Profit: Calibrated green (not pure neon green).
  - Negative / Risk: Refined amber or crimson red.
  - Neutral / Information: Slate blue or cool grey.
- **Table Ergonomics**: Use subtle row hovering, sticky headers for long lists, and explicit numeric alignment (right-align currency and quantities).

## 2. Interactive Micro-polish
- **Loading & Skeleton States**: Never leave blank white screens during data fetching. Provide smooth pulsing skeletons matching table/card layouts.
- **Empty States**: If search or filter returns no data, provide informative empty state cards with actionable clear-filter buttons instead of empty voids.
- **Visual Feedback**: Buttons and interactive controls must have clear `:hover`, `:active`, and `:focus-visible` styles with smooth transition durations (150-200ms).

## 3. Responsive Cockpit Design
- Ensure dense dashboards (e.g. Bidding Cockpit) maintain readability across 1080p, 1440p, and multi-monitor setups without horizontal clipping or awkward wrapping.
