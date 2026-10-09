# Xiliu display typography

Selected direction: lightweight handwriting for branding and the Today greeting. Body text and controls continue to use the user's reading-font preference.

- `xiliu-script.woff2`: Allura Regular, from https://github.com/google/fonts/tree/main/ofl/allura. Converted to WOFF2 and internally renamed Xiliu Script; original license in `Allura-OFL.txt`.
- `xiliu-headlines.woff2`: LXGW WenKai Lite Light v1.522, from https://github.com/lxgw/LxgwWenKai-Lite. Small subset for the fixed Chinese greeting and brand text, internally renamed Xiliu Headlines.
- `xiliu-handwriting.woff2`: the same upstream Light font, subset to basic Latin, Chinese punctuation, CJK unified ideographs and fullwidth characters; internally renamed Xiliu Handwriting. Provides dynamic nickname characters beyond the small headline subset. Original license in `LXGWWenKai-OFL.txt`.

Both upstream fonts use SIL OFL 1.1; keep the license files with redistributed assets. The changed font names respect the reserved upstream names. WOFF2 files are served locally; no third-party font request or system font installation is needed. The script font and 7 KB headline subset are preloaded; the larger Chinese fallback loads only when additional glyphs are needed.

Launch uses the script font for the particle gathering phase, then a smooth text wordmark. Both reduced-motion and ordinary rendering show the same readable text. The final page follows the approved visual direction rather than treating the generated mockup as an exact font file.
