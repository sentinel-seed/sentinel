# Sentinel Papers

Technical reports and academic papers documenting Sentinel Alignment Seeds.

## Available Papers

### Technical Reports (Internal)

| Version | Date | Purpose |
|---------|------|---------|
| [PAPER_v1.md](./PAPER_v1.md) | November 2025 | Release notes for v1 (THS protocol) |
| [PAPER_v2.md](./PAPER_v2.md) | December 2025 | Release notes for v2 (THSP protocol) |

### Academic Papers (External)

| Paper | Date | Purpose |
|-------|------|---------|
| [PAPER_arxiv.tex](./PAPER_arxiv.tex) | December 2025 | arXiv submission — Teleological Alignment |

## Paper Distinction

- **PAPER_v2.md**: Technical documentation for developers. "Here's what changed and how to use it."
- **PAPER_arxiv.tex**: Academic contribution for researchers. "Here's why teleological alignment matters and our empirical evidence."

## arXiv Submission

The `PAPER_arxiv.tex` introduces **Teleological Alignment** as a concept:
- **Thesis:** Harm avoidance is necessary but insufficient; AI must serve legitimate purposes
- **Contribution:** THSP protocol with Purpose gate
- **Evidence:** +25% improvement on embodied AI (BadRobot)

```bash
# Compile
pdflatex PAPER_arxiv.tex
bibtex PAPER_arxiv
pdflatex PAPER_arxiv.tex
pdflatex PAPER_arxiv.tex
```

**Category:** `cs.AI` (Artificial Intelligence) or `cs.CL` (Computation and Language)

## Versioning Policy

Each major seed release is accompanied by a technical paper documenting:
- Methodology and benchmark results
- Comparison with previous versions
- Key innovations and design decisions
- Limitations and future work

## Research Archive

Failed experiments are documented in `wip/RESEARCH_ARCHIVE.md` to prevent repetition and inform future research.

---

*Sentinel Team*
