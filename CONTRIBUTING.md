# Contributing to folio

## The one rule

**New components belong in the design system, never inline in a document.**

That is the entire point of the project. A one-off style in one document is how
a design system stops meaning anything — the next person copies it, and within
a month there is no system. If you need something that does not exist, add it
to `src/folio/assets/folio.css` *and* document it in `docs/COMPONENTS.md` in
the same pull request.

Before adding: check `folio components` carefully. Most "missing" components
already exist under a different name.

## Setup

```bash
git clone https://github.com/abhirajsingh101/folio
cd folio
pip install -e ".[dev,charts,weasyprint]"
folio doctor          # confirms native libraries are present
pytest
```

If `folio doctor` reports missing native libraries, it prints the exact command
for your platform. That output is the fix — please do not work around it, since
reproducing what a new user sees is valuable.

## Before you open a PR

```bash
ruff check src tests
ruff format src tests
pytest
```

CI runs on Linux, macOS and Windows across Python 3.10 and 3.13. It also runs a
**degraded job** with no native libraries at all, which must still pass — folio
is required to remain useful on a machine where WeasyPrint cannot load.

## Changing the stylesheet

Rendering bugs here are silent: the PDF is valid and merely looks wrong. So a
stylesheet change is not done until you have *looked* at it.

```bash
cd examples/quarterly-report
folio build document.html
pdftoppm -png -r 100 document.pdf /tmp/p && ls /tmp/p*
```

Check every page, not just the one you were working on. Print layout is
global — a change to table padding can strand two rows on an empty page four
sections later.

If you find a new silent failure mode, add it to `docs/GOTCHAS.md`. That file
is the accumulated cost of debugging this renderer and is arguably more
valuable than the CSS.

## Design principles

1. **Fewer, better components.** Every addition is a thing users must learn and
   maintainers must keep working. A component earns its place by being needed
   in documents nobody has written yet.
2. **One brand hook.** `--brand` should carry most projects. If a change makes
   people override five variables, the default was wrong.
3. **Degrade, never crash.** Missing fonts fall back. A missing renderer falls
   back. Anything folio cannot do, it should say plainly and continue.
4. **Never lie about fidelity.** The Chromium renderer announces what it cannot
   do. Any future renderer must too.

## Scope

folio makes design-led documents. It is not a Markdown converter, a slide tool,
a LaTeX replacement for academic submission, or a PDF *reader*. Proposals that
broaden it in those directions will likely be declined, kindly.

## Reporting bugs

Include: your OS, `folio doctor` output, `folio --version`, and a minimal
`document.html` that reproduces the problem. For a layout bug, attach the
rendered PNG — describing a spacing issue in prose almost never works.
