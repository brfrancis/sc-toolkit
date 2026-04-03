# sc-toolkit

A collection of Python tools for Solutions Consulting in AI — demo environment generators, data pipeline utilities, and workflow automation for pre-sales and GTM execution.

Built and maintained by [Ben Francis](https://www.linkedin.com/in/ben-r-francis) | PhD Biostatistics | EMEA Solutions Consulting Lead, Indico Data

---

## What this is

Day-to-day Solutions Consulting in AI involves a lot of repetitive but high-stakes work: building client-specific demo environments, normalising messy data, simulating extraction outputs to validate POC designs. These tools exist because doing that work manually is slow, inconsistent, and doesn't scale across a pipeline of enterprise accounts.

Everything here is built to solve a real SC problem. If it's in this repo, it's been used in a live engagement or built directly from one.

---

## Tools

### Demo landing page
A branded, client-specific HTML landing page for a demo session.

**Inputs:** Client name · use case · key extraction fields · stakeholder focus 
**Output:** A clean, hosted landing page scoped to the client's workflow and value drivers  
**Live:** [Hosted on PythonAnywhere](#) *(link added on deployment)*

---

### CDR data warehousing
*(In development)*  
Accepts an JSON of extractions of CDR fields into a staging or Bronze layer of a data warehouse and returns examples of Silver and Gold level output.

**Inputs:** Excel file (multi-tab supported) · target schema definition  
**Output:** Normalised CSV with mapped headers, flagged anomalies, and a conformance summary  
**Live:** *(coming soon)*

---

### Blueprint use case tagging
*(In development)*  

**Inputs:** *(coming soon)* 
**Output:** *(coming soon)* 
**Live:** *(coming soon)*

---

## Background

These tools sit at the intersection of domain knowledge and applied AI — specifically the London Market workflows around underwriting submission processing, delegated authority, and claims.

The extraction patterns and field definitions draw on work across 8+ proof of concepts covering submission triage, bordereaux normalisation, and claims automation for London Market and global insurers. Field schemas are generalised and synthetic — no client data is included in this repository.

For the thinking behind this work, see my [Substack](https://substack.com/@benfrancis) *(link added on launch)* and [LinkedIn](https://www.linkedin.com/in/ben-r-francis).

---

## Stack

- Python 3.x
- Flask (demo tools)
- pandas (data pipeline utilities)
- Hosted on PythonAnywhere

---

## Usage

Each tool has its own directory with a `README.md` covering setup, inputs, outputs, and example usage. Start there.

```
sc-toolkit/
├── demo-landing-page/
├── CDR-data-warehouse/
├── blueprint-use-case/
└── utils/
```

---

## License

MIT — see [LICENSE](LICENSE)
