---
name: Financial Intelligence Interface
colors:
  surface: '#f9f9ff'
  surface-dim: '#cfdaf2'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f3ff'
  surface-container: '#e7eeff'
  surface-container-high: '#dee8ff'
  surface-container-highest: '#d8e3fb'
  on-surface: '#111c2d'
  on-surface-variant: '#3c4a43'
  inverse-surface: '#263143'
  inverse-on-surface: '#ecf1ff'
  outline: '#6c7a72'
  outline-variant: '#bbcac1'
  surface-tint: '#006c4f'
  primary: '#006c4f'
  on-primary: '#ffffff'
  primary-container: '#00b889'
  on-primary-container: '#00412e'
  inverse-primary: '#4cdeac'
  secondary: '#8b5000'
  on-secondary: '#ffffff'
  secondary-container: '#ff9800'
  on-secondary-container: '#653900'
  tertiary: '#a33c36'
  on-tertiary: '#ffffff'
  tertiary-container: '#f97d73'
  on-tertiary-container: '#6f1615'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#6dfbc7'
  primary-fixed-dim: '#4cdeac'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#ffdcbe'
  secondary-fixed-dim: '#ffb870'
  on-secondary-fixed: '#2c1600'
  on-secondary-fixed-variant: '#693c00'
  tertiary-fixed: '#ffdad6'
  tertiary-fixed-dim: '#ffb4ac'
  on-tertiary-fixed: '#410003'
  on-tertiary-fixed-variant: '#832521'
  background: '#f9f9ff'
  on-background: '#111c2d'
  surface-variant: '#d8e3fb'
typography:
  display:
    fontFamily: Outfit
    fontSize: 40px
    fontWeight: '600'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Outfit
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
  container_max: 1200px
  gutter: 24px
  margin_mobile: 16px
---

## Brand & Style

This design system is built for clarity, speed, and trust in the financial technology space. It adopts a **Modern Minimalist** aesthetic with **Card-based** information architecture to decompose complex mutual fund data into digestible units.

The target audience consists of both novice and seasoned investors who require a high-signal, low-noise environment for financial inquiry. The UI evokes a sense of precision and reliability through ample whitespace, a restrained color palette, and a focus on content hierarchy. Interactions are intentional and smooth, utilizing subtle transitions to guide the user's focus without distraction.

## Colors

The color strategy centers on "Emerald Green" to symbolize growth and financial health. The palette is strictly divided between light and dark modes to maintain optimal contrast ratios for financial data readability.

- **Primary:** Used for actionable elements, progress indicators, and brand presence.
- **Warning:** Reserved for risk disclosures, market volatility alerts, and critical fund notices.
- **Neutral:** A range of slates and greys used to define structure and text hierarchy.
- **Surface & Background:** Defined by subtle shifts in value to create depth without relying on heavy shadows.

## Typography

This design system uses a dual-font strategy. **Outfit** is utilized for headlines and display text to provide a modern, geometric character that feels premium and approachable. **Inter** is the workhorse for body text and data, chosen for its exceptional legibility and systematic feel at small sizes.

Large display titles should use tighter letter spacing to maintain visual tension. All body text should adhere to a strict 1.5x line-height ratio to ensure maximum readability during long-form FAQ consumption.

## Layout & Spacing

The system employs a **Fluid Grid** model with a 12-column structure for desktop and a single-column stack for mobile. 

- **Grid:** Use a 24px gutter for desktop layouts to give fund cards room to breathe.
- **Rhythm:** All spacing must be a multiple of 4px. Use 16px (md) for internal card padding and 24px (lg) for vertical section spacing.
- **Responsive:** On mobile devices, side margins compress to 16px. Cards should span the full width of the container minus margins.
- **Sticky Header:** The header is fixed at the top with a backdrop-blur (12px) and a bottom border to maintain context during long scrolls.

## Elevation & Depth

Hierarchy is established through **Tonal Layers** and **Low-contrast Outlines** rather than aggressive shadows.

- **Level 0 (Background):** The base canvas.
- **Level 1 (Surface):** Default card state. Uses a 1px solid border (Solid Slate in Dark, Soft Silver in Light).
- **Level 2 (Elevated):** Hover states or active modals. In Dark Mode, this uses a slightly lighter fill (#2A2F3A); in Light Mode, a very soft, diffused shadow (0px 4px 12px rgba(0,0,0,0.05)) is applied.
- **Transitions:** All theme-related property changes (background-color, border-color) must use a 0.3s ease-in-out transition for a smooth user experience.

## Shapes

The shape language is defined by **High Roundedness**, leaning into a friendly and modern aesthetic that reduces the perceived complexity of financial data.

- **Buttons & Chips:** Always use the maximum `rounded-xl` or "Pill" shape.
- **Cards:** Use `rounded-lg` (1rem / 16px) to create a soft container for data.
- **Input Fields:** Use `rounded-md` (0.5rem / 8px) to distinguish functional areas from decorative ones.
- **Message Bubbles:** User bubbles feature high rounding on three corners with a sharper corner (4px) on the bottom-right to indicate origin.

## Components

### Buttons & Navigation
- **Primary Button:** Pill-shaped, Emerald Green background, Soft White text. High-contrast and centered for primary calls to action.
- **Ghost Button:** Pill-shaped, primary color border, no fill. Used for secondary actions like "View More."
- **Sticky Header:** Contains the assistant name and theme toggle. Must remain visible at `z-index: 100`.

### Cards & Grid
- **Onboarding Cards:** Arranged in a responsive grid. Each card features a 24px icon, a `headline-md` title, and `body-md` description.
- **FAQ Item:** A card that expands vertically on tap. Ensure the border color intensifies when the item is expanded.

### Messaging Interface
- **Assistant Bubbles:** Surface color background with a primary left-border accent.
- **User Bubbles:** Emerald Green background with white text.
- **Typing Indicator:** Three animated dots using the `text_low` color.

### Inputs
- **Search Bar:** Large, pill-shaped input with a 16px left-padding and a magnifying glass icon. Background matches the Surface color to stand out from the Background color.