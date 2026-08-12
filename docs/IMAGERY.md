# Imagery

Charts and tables are how a document shows what happened. This is about the
other kind of image — the cover, the section opener, the texture — and about
generating one when there is nothing to photograph.

## The default answer is no

Most documents are better with no decorative image than with a mediocre one. A
generic illustration does not read as neutral; it reads as *nobody thought
about this page*. It is the visual equivalent of filler text, and readers are
now extremely good at spotting it.

So the bar is: **can you say, in one sentence, what this image is doing that
the words are not?** "Setting the tone of a long read before the argument
starts" is an answer. "Breaking up the text" is not — that is what white space
and a section rule are for, and folio already has both.

## Never generate

These are not judgement calls.

**Anything a reader could take as data.** Numbers go in a real table; trends go
in a real chart built from real figures. This includes a picture that merely
*resembles* a chart in the background of a plate. If it has the shape of
evidence, it will be read as evidence.

**Anything with text in it.** Image models still malform words, and the first
thing anyone reaches for is an architecture diagram — which would ship with
garbled labels in a technical document. Diagrams are SVG, drawn deliberately,
same path as charts. No exceptions for "just a label" or "just a number".

**Anything evidentiary.** No photograph of a real place, person, product, or
screen. A generated image of "our facility" or "the team" is a factual claim
about the world, and a false one. Screenshots are captured, never generated.

**Logos and marks.** Someone else's identity is not yours to synthesise.

## Where it earns its place

- **Covers.** The strongest case by far. A cover is explicitly atmosphere, the
  reader knows it, and there is rarely anything real to photograph.
- **Section openers** in a long editorial document, where a plate marks a
  change of subject the way a chapter page does.
- **A conceptual plate in an essay**, where the argument is abstract and an
  image can hold a mood the prose is not trying to carry.

That is the whole list. Notice that none of them are "next to the paragraph
about X".

## Theme fit

| theme | imagery |
|---|---|
| `editorial` | Yes — it is built on scale contrast and white space, and takes a plate well. |
| `report` | Cover only, usually. Interior plates read as padding in a document meant to be decided from. |
| `technical` | No. The theme exists to fit more on the page; a plate is dead weight. |
| `minimal` | No. It is built on having nothing to hide behind, and an illustration is hiding. |

## Generating one with Codex

Codex ships an `imagegen` skill. The built-in path needs no API key; the
scripted CLI fallback needs `OPENAI_API_KEY` and is not the path to reach for.

```bash
codex exec "Use the imagegen skill. Generate a 1536x640 image: \
matte risograph-style print in two inks, deep navy and pale blue, \
overlapping geometric strata like a cross-section, visible paper grain, \
no gradients, no text, no people, no logos. \
Save it to /abs/path/to/project/art/opener.png"
```

Codex saves to `$CODEX_HOME/generated_images/...` by default, so name an
absolute destination in the project or the asset ends up outside it.

### Prompting so it does not look generated

The tell of a stock AI image is that it illustrates a *concept*. Prompt for a
**medium and a process** instead, and let the abstraction do the work.

| instead of | ask for |
|---|---|
| "innovation and connectivity" | "two-ink risograph print, overlapping strata, paper grain" |
| "a team collaborating" | nothing — use white space |
| "data flowing through a network" | "long-exposure light on matte black, single hue" |
| "futuristic technology background" | "cyanotype texture, deep blue, torn edge" |

Rules that follow from that:

- **Name the palette explicitly**, using the document's own brand colours. An
  unconstrained image will not sit next to your charts.
- **Ask for flat or matte.** The default house style of every image model is
  glossy 3D render, which is the single strongest "this was generated" signal.
- **Abstract beats literal.** A texture or a material never has to be
  factually right; a depicted scene always does.
- **State the aspect ratio** for the slot — a cover is roughly 2:3, a
  full-bleed opener nearer 3:1.
- **Say "no text, no people, no logos"** every time, even when it seems
  obvious.

### Resolution

Generate at print size, not screen size. A full-bleed A4 plate is 210mm wide —
about 2480px at 300dpi. `folio check` will flag an image drawn beyond its
pixels (`image-upscaled`), but that rule is a floor, not a quality bar: it
tolerates roughly 96dpi. Clearing the check is not the same as looking good on
paper.

## Placing it

Every generated image is a `.plate`, never a `<figure>`:

```html
<div class="plate bleed">
  <img src="art/opener.png" alt="Abstract navy strata in a two-ink print">
  <span class="credit">Generated illustration</span>
</div>
```

- **`alt` is required.** Describe what is there, not why it is there.
- **Credit it.** `Generated illustration` is honest and costs one line. A
  reader who cannot tell what is synthetic will assume everything might be.
- **Full-bleed must be a raster.** A gradient inside an SVG silently fails to
  paint in `.bleed` — see `folio gotchas`. PNG is what image models produce
  anyway, so this mostly takes care of itself.
- `folio check` enforces the boundary: a plate carrying a figure number is
  flagged, and so is a figure without one.

## Then look at it

Run `folio build document.html --check` and open the page images it writes.
Two questions the checker cannot answer:

1. Does the image look generated? If you hesitate, it does. Cut it or redo it.
2. Does the page read better *with* it than without? Delete it and compare. A
   surprising amount of the time, without wins.
