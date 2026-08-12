# AGENTS.md snippet

folio works with any agent that can run a command. Paste this into your global
or project `AGENTS.md` (Codex, Cursor, Aider, and anything else reading that
convention).

```markdown
## Documents and PDFs

- For any print-ready PDF (report, whitepaper, proposal, invoice, handbook),
  use `folio` rather than authoring a stylesheet or reaching for LaTeX.
- Commands: `folio doctor` (check the machine), `folio init` (scaffold
  document.html + charts.py), `folio build <file>` (render PDF + standalone
  HTML), `folio components` (component vocabulary).
- Read `folio components` before authoring and use only those classes. No
  inline styles, no `<style>` blocks. Per-project colour goes in a `brand.css`
  beside the source, which is appended after the design system and wins.
- Charts go through `from folio import theme`, sized in real inches at final
  printed width, emitted as SVG.
- Before debugging layout, run `folio gotchas`. The failure mode here is a
  valid PDF that looks wrong, not an error — always render a page to PNG and
  look at it before claiming success.
```
