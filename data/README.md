# Animated GitHub profile cards

A Python SVG renderer for the `RiteshRagav/RiteshRagav` profile README. It generates animated SVG cards with inline CSS keyframes, SVG SMIL, optional subsetted WOFF fonts, and a reduced-motion fallback.

## Render locally

```bash
python -m pip install -r requirements.txt
python generate_cards.py
STATIC=1 python generate_cards.py  # render final frames without animation
```

Optional font: place a licensed `.ttf` at `assets/fonts/brand.ttf`. If `pyftsubset` is installed (via `fonttools[woff]`), the script subsets it and embeds the WOFF as a base64 data URI. Otherwise it uses a system sans-serif fallback.

## Profile README

Replace the contents of the profile repository's `README.md` with:

```markdown
<p align="center">
  <img src="cards/01-hero.svg" width="100%">
</p>

<p align="center">
  <img src="cards/02-links.svg" width="100%">
</p>

<p align="center">
  <img src="cards/03-activity.svg" width="100%">
</p>

<p align="center">
  <img src="cards/repo-01-paymentorchestrator.svg" width="100%">
</p>

<p align="center">
  <img src="cards/repo-02-clouddoctor.svg" width="100%">
</p>

<p align="center">
  <img src="cards/repo-03-retail-location-bi.svg" width="100%">
</p>

<p align="center">
  <img src="cards/repo-04-observal.svg" width="100%">
</p>

<p align="center">
  <img src="cards/repo-05-mobility-dreamer.svg" width="100%">
</p>

<p align="center">
  <img src="cards/99-contribution-graph.svg" width="100%">
</p>
```

## Contribution data and automation

`.github/workflows/profile-cards.yml` refreshes `data/contributions.json` daily using GitHub GraphQL, renders all SVGs, and commits changed data/cards. It also supports manual runs from the Actions tab. The workflow requires repository Actions permissions to write contents.

The contribution fetcher reads only the public contribution calendar for `RiteshRagav`; no contribution counts are hard-coded. The initial JSON is intentionally empty until the first successful workflow run.

## Customization

Edit `PROFILE`, `TILES`, and `FEATURED` near the top of `generate_cards.py`. Each featured entry must use a real repository URL. The current five cards are based on the repository names, descriptions and languages supplied for this profile. The `caracal` repository is intentionally excluded. The Portfolio link tile is a website shortcut, not a featured repository card.

GitHub renders SVGs inside README image tags, but client-side animation support can vary. The SVGs contain no JavaScript or external runtime assets and disable motion for `prefers-reduced-motion`. Use `STATIC=1` for screenshot-ready final frames.
