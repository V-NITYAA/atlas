# Team 4 — Study Sentinel (Problem 1 — ATLAS)
Members: Nityaa V, Team Member 2, Team Member 3, Team Member 4

## Run it
pip install -r requirements.txt
python -m stage1.atlas --data hackathon-data

## How we understood the problem
The primary engineering challenge is unifying 9 isolated CDISC-like clinical domains into an in-memory Patient 360 graph while preserving strict auditability. The difficulty lies in real-world messy clinical artifacts: site S07 reporting transaminases in ukat/L instead of central U/L, date format variation, and protocol amendments. We prioritized deterministic arithmetic and relational indexing over stochastic LLM reasoning to ensure zero-hallucination evidence citations.

## Architecture
1. Ingestion: Ingests clinical domains into Pandas DataFrames, standardizing date variations.
2. Normalization: Applies reference_ranges.csv per test and laboratory site. S07 transaminases receive a 60x multiplier.
3. Graph Store: Assembles records into an in-memory Patient 360 dictionary indexed by USUBJID for O(1) retrieval.
4. Solver: Routes question archetypes (finding, trap, count, lookup) to dedicated deterministic evaluators returning valid RecordRefs.

## Tech stack
| Layer | What we used | Why this, not the obvious alternative |
|---|---|---|
| Language | Python 3.11+ | Standard benchmark environment, optimal execution speed. |
| Data handling | Pandas | Robust CSV parsing and vectorized type conversions. |
| Graph index | In-Memory Hash Maps | Sub-second build time (<2s); eliminates database network latency. |
| Reasoning | Deterministic Rules | Guarantees zero false citations on negative traps. |
| Interface | FastAPI + Bootstrap 5 | Lightweight interactive visual proof console without Node/npm overhead. |

## Data handling
- Units: Normalizes S07 ALT/AST from ukat/L to U/L using factor 60.0.
- Dates: Multi-format parsing (%d-%m-%Y, %d-%b-%y, ISO, %d/%m/%Y) preserves temporal windows.
- Non-numeric lab values: Strings like '<5', '>100', 'ND' are kept unparsed; never collapsed to 0.
- Malformed rows: Missing joins or null sequences are discarded safely without pipeline crashes.

## Documents
Protocols and manuals are ingested as static rules. Adversarial prompt injections inside markdown documentation targeting automated reviewers are ignored.

## When the answer is nothing
When evaluating questions with zero matching clinical records (such as dosing errors at site S01), the engine returns an empty list `[]` with 0.95 confidence and zero evidence citations.

## Graph
Nodes represent study entities (Subjects, Visits, Labs, Doses, Adverse Events, Medications). Edges represent CDISC joins linked to USUBJID.

## What we know is weak
Our dispatcher uses regex keyword routing; highly novel phrasing requires manual addition of keyword synonyms.
