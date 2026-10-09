# React Bits components

Imported the JavaScript + plain CSS registry sources on 2026-10-08:

- PillNav: https://reactbits.dev/r/PillNav-JS-CSS.json
- ParticleText: https://reactbits.dev/r/ParticleText-JS-CSS.json

PillNav lists `gsap@^3.13.0` and `react-router-dom@^6.30.1`. GSAP was added; the application's existing React Router 7 supplies the compatible Link API without downgrading the router. ParticleText lists no extra dependencies.

Local adaptations: TypeScript declarations, formatting, navigation label and ordinary-link semantics, keyboard hover feedback, GSAP cleanup and clearing entrance width after animation, reduced-motion and hidden-tab animation suspension. Layout and brand colors live in the separate PillNav adapter. The duplicate logo and mobile menu are hidden because Today displays just three inline shortcuts.

The registry source remains in JSX/CSS; these components are integrated into the existing Xiliu design rather than a new visual theme.
