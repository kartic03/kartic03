<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./dist/header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./dist/header-light.svg">
  <img alt="Kartic — wet lab and computation, de novo peptide design" src="./dist/header-dark.svg" width="880">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./dist/code-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./dist/code-light.svg">
  <img alt="Repositories, each backing a manuscript" src="./dist/code-dark.svg" width="880">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./dist/shooter-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./dist/shooter-light.svg">
  <img alt="Contribution calendar as an arcade shooter: empty days destroyed, contribution pattern revealed" src="./dist/shooter-dark.svg" width="880">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./dist/footer-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./dist/footer-light.svg">
  <img alt="Contact" src="./dist/footer-dark.svg" width="880">
</picture>

<!--
  Every panel is generated, not hand-drawn.

    header.py     profile card; language shares come from the GitHub API and
                  the avatar is inlined as a data URI, because an SVG that
                  references an external image renders empty once GitHub
                  proxies it through Camo
    panels.py     code and footer
    shooter.py    contribution calendar as an arcade shooter
    preview.py    stacks every panel into one page for review

  Cut from the page but still in the source, each one line from returning:
  structure.py (de novo design cascade), and research() and toolchain() in
  panels.py.

  Regenerate everything:   python build.py
  Rebuild one panel:       python shooter.py --user kartic03

  .github/workflows/build.yml refreshes the data-driven panels daily.
-->
