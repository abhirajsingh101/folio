# Why WeasyPrint

folio renders with WeasyPrint. That was decided by building the same document
three times — not by preference.

## The experiment

One 11-page engineering progress report, built in WeasyPrint, Typst and LaTeX.
Identical content, identical figures (the same four SVGs, converted for LaTeX
because it cannot embed SVG), and identical typefaces in all three: P052 for
body, Inter for UI text, JetBrains Mono for code.

Charter was the original body face and had to be dropped: it exists on the test
machine only as a Type1 `.pfb`, which WeasyPrint reads and Typst cannot. Moving
all three to P052 kept the comparison honest.

## Results

| | WeasyPrint | Typst | LaTeX |
|---|---|---|---|
| Compile (3-run mean) | 2.04 s | **0.84 s** | 9.55 s |
| Source lines | 889 | 560 | **540** |
| Failed compiles before first PDF | **0** | 4 | 7 |
| Bugs hit while authoring | **6** | 7 | 12 + 1 blocker |
| Pages for identical content | 11 | **8** | 10 |
| SVG figures | native | native | must convert |
| Web output from same source | **yes** | no | no |

## What the numbers do not show

**LaTeX set the best page.** Its justified body is the most even of the three;
microtype's character protrusion is visible at the right margin if you look for
it. Typst is close behind and packs the same content into eight pages without
feeling cramped. WeasyPrint is a clear third on text colour — though you have
to be looking.

**LaTeX was also the most compact source**, at 540 lines against Typst's 560 and
HTML+CSS's 889. Verbosity was never LaTeX's problem. Reachability is: those 540
lines took seven failed compiles and a complete engine switch to arrive at.

**The environment nearly stopped LaTeX entirely.** On a machine with TeX Live
2023 installed, `luaotfload` was absent and there was no `xelatex`, so
`fontspec` — the modern font path — simply did not work. Reaching a first PDF
required switching to Tectonic, which downloads its own TeX distribution.
Diagnosing that cost more than any individual layout bug.

**The failure modes differ in kind.** Typst failed loudly: three hard errors
with line numbers, then it worked. WeasyPrint failed silently: five of its six
bugs produced a valid PDF that merely looked wrong. LaTeX did both.

## Why WeasyPrint won anyway

1. **Layout control.** The gradient cover with layered circles was four lines of
   CSS and a fight in the other two. Documents that are screenshot- and
   figure-heavy are a layout problem, not a typesetting problem.
2. **The edit loop.** Two seconds and a mental model that transfers from every
   web project. Under an agent, cost-per-revision *is* final quality, because it
   determines how many revisions actually happen.
3. **Dual output.** One source produces the PDF and a shareable HTML page.
   Structurally impossible in the other two.
4. **`@page` margin boxes.** Running headers, page counters and
   `target-counter` for contents pages work properly. This is also why folio's
   Chromium fallback is explicitly labelled degraded — Chromium implements
   almost none of it.

## When to use something else

- **Typst** if your documents drift toward long prose, mathematics, or anything
  book-shaped. It is genuinely excellent and the efficiency winner here.
- **LaTeX** when a journal or employer mandates a class file, or when a document
  is long enough that microtype's advantage compounds over hundreds of pages.

folio does not try to be those tools. It is for design-led documents where the
layout carries as much as the prose.
