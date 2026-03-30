# Quality Scan Report: THE DEMOGRAPHIC TIDE v14

**Scanned:** March 30, 2026
**Status:** Near-final capstone thesis, due April 10

---

## 1. Numbers, Percentages, and Dollar Amounts

### 1A. Crossover probability inconsistencies (CRITICAL)

The overall demographic crossover probability is stated differently in different places:

| Location | Value |
|---|---|
| Section 5.1 body text | 22,804 of 25,000 = **91.2%** |
| Section 5.4 TDF sensitivity baseline | **91.1%** ("rises from 91.1% to 100%") |
| Table A7, Mid scenario | **90.6%** |

These three numbers should be the same figure (the probability of at least one negative demographic net flow year by 2050 under the base/mid case). One or more is wrong.

Additionally, the range across immigration scenarios is stated as "89.1% to 91.5%" in Section 4.2 and Section 5.1, but Table A7 shows Mid = 90.6%, High = 89.1%, Low = 91.5%. The weighted average (40/30/30) of those table values would be ~90.3%, not 91.2%. Reconcile all four occurrences.

### 1B. DC net flow timing inconsistencies (HIGH)

The thesis makes three different claims about when DC equity mutual fund flows turned negative:

| Location | Claim |
|---|---|
| Section 1.2 (line ~126) | "Net contributions have been negative every year since **2020**" |
| Section 5.1 (line ~347) | "has been negative every year since **2019**, running -$93 billion in 2019" |
| Section 6.4 (line ~491) | "have been negative since at least **2015**" |
| Section 7 / Conclusion (line ~501) | "DC mutual fund flows have been negative since **2020**" |

These appear to describe different things (total DC net contributions vs. equity mutual fund flows vs. DC equity mutual fund flows), but the distinctions are not always clear from context. The reader will see "since 2019," "since 2020," and "since 2015" and wonder which is correct.

### 1C. Buyback crossover probability: 4.5% vs 4.3% (MEDIUM)

- Section 5.2 and multiple other locations: buyback-adjusted crossover probability is **4.5%** (= 1,115/25,000)
- Section 6.3 (line ~475): "increases the total-flow crossover probability from **4.3%** to 5.5%"

If the base case is 4.5% (1,115/25,000), why does the halved-buyback sensitivity test start from 4.3%? Either the base case figure is rounded differently or this is an error.

### 1D. "Six data sources" (LOW)

Section 1.3 (line ~130): "Section 3 describes the **six** data sources and their limitations." Table 1 lists approximately 16 distinct sources. This is presumably meant to refer to six *primary* sources or six *categories*, but as written it contradicts the table.

### 1E. Household debt: $12.4 trillion in 2006 (LOW, verify)

Section 6.4 (line ~481): "U.S. total household debt has risen from approximately $12.4 trillion in 2006 to $18.8 trillion by late 2025." The pre-crisis household debt peak was closer to $12.7T in 2008 (NY Fed data). In 2006 specifically, it was closer to $11.5-12.0T. Verify the $12.4T figure and year.

---

## 2. Citation / Reference Cross-Check

### 2A. Orphan reference (no in-text citation)

- **Aipinas, A. (2026).** The GitHub repository reference has no parenthetical in-text citation. The repository URL appears in the text body (Section 3, Appendix A), but there is no "(Aipinas, 2026)" citation anywhere. Either add one or note it is intentionally uncited.

### 2B. All other citations verified

Every other in-text citation has a matching reference entry, and every reference entry has at least one in-text citation. The institutional citations (ICI, BLS, Census Bureau, Fed, IRS, Bloomberg, FactSet, Morningstar, Damodaran, EBRI/ICI, S&P Dow Jones) and legislation entries (Pension Protection Act, SECURE 2.0 Act) all have matching references.

---

## 3. Cross-References

### 3A. All cross-references verified as existing

Every "Section X.X", "Table X", "Figure X", "Appendix Table AX", and "Appendix Figure A-X" reference in the text points to a heading, table, or figure that exists in the document. No dangling references were found.

### 3B. Duplicate heading: "Data Sources and Calibration" (MEDIUM)

The heading "Data Sources and Calibration" appears twice:
- As the title of Table 1 (line ~182)
- As a subsection heading for Section 3.1 (line ~206)

This may confuse readers. Consider differentiating them (e.g., the table title could remain as is, and the subsection could drop the redundant heading since it immediately follows the table).

---

## 4. Heading Numbering

### 4A. Body headings stripped of numbers (FORMATTING ISSUE)

The Table of Contents shows correct sequential numbering (1, 1.1, 1.2 ... 7), but the actual body headings have been **stripped of their section numbers**. For example:
- TOC says "1. Introduction" but the body heading is just "Introduction"
- TOC says "2.1 The Demographic Asset Meltdown Debate" but the body heading is just "The Demographic Asset Meltdown Debate"

This is true for all major and minor headings. This may be intentional formatting, but verify against your department's style requirements. Most capstone theses expect numbered headings in the body to match the TOC.

### 4B. Module numbering in Section 4.2 (CRITICAL)

The Five-Module Pipeline subsection uses a numbered list, but the numbering is broken:
- "2. The Five-Module Pipeline" (this is the section heading, but numbered "2." instead of being unnumbered or "4.2")
- "1. Module 1: Demographic Projections"
- "2. Module 2: Inflow Estimation"
- Module 3 appears as a paragraph starting with "Module 3: Outflow Estimation" but **lacks the list number "3."**
- "4. Module 4: Net Flow Aggregation..."
- "5. Module 5: Price Impact Estimation..."

So the visible numbering goes 1, 2, [missing 3], 4, 5. Module 3 lost its list number.

---

## 5. Orphaned Placeholders

### 5A. Empty square brackets: [] (HIGH)

There are **18 instances** of empty square brackets `[]` in the document. These are image placeholders where figures should be embedded. They appear before every figure caption:

- Line 5 (title page), Line 116 (before Figure 1), Line 212 (before Figure 2), Line 304 (before Figure 3), Line 349 (before Figure 4), Line 355 (before Figure 5), Line 361 (before Figure 6), Line 365 (before Figure 7), Line 375 (before Figure 8), Line 401 (before Figure 9), Line 405 (before Figure 10), Line 411 (before Figure 11), Line 417 (before Figure 12), Line 425 (before Figure 13), Line 429 (before Figure 14), Line 435 (before Figure 15), Line 684 (Figure A-1), Line 688 (Figure A-2)

If these are image placeholders that render correctly in Word but are extracted as empty brackets by the parser, this is likely fine. But verify that all 17 figures and the title page image actually display when you open the .docx.

### 5B. No [INSERT], [TODO], [Surname], or similar placeholders found

The scan found zero instances of common placeholder tags. Clean on this front.

---

## 6. Em Dashes

### 6A. Three em dashes found in Table A2

The em dash character (U+2014: —) appears three times, all in Table A2 (Module 3: Outflow Parameters), in the "RMD Rate" column for ages 55-59, 60-64, and 65-72, where it is used to indicate "not applicable" (voluntary rate exceeds RMD). The table note explains: "Dashes indicate voluntary rate exceeds RMD."

If your style guide requires zero em dashes, replace these with "n/a" or an en dash. Note: the rest of the document correctly uses en dashes (–) for ranges and minus signs throughout.

---

## 7. Colons as Clause Connectors

### 7A. One flagged instance

**Line ~124 (Section 1.2):** "The tools to connect them are recent**:** the Gabaix-Koijen multiplier was circulated in 2021..."

This is a colon connecting two independent clauses (the text before the colon could stand alone, and the text after the colon is also a complete sentence). All other colons in the body text introduce lists, labels, definitions, or follow dependent fragments, and are standard usage. Reference titles and subtitles (e.g., "Business Intelligence: Passive equity assets...") are excluded as they are not clause connectors.

---

## Summary of Issues by Severity

| Severity | Count | Issues |
|---|---|---|
| CRITICAL | 2 | Crossover probability mismatch (91.2% vs 91.1% vs 90.6%); Module 3 missing list number |
| HIGH | 2 | DC flow timing inconsistency (2015/2019/2020); 18 empty bracket placeholders (verify images render) |
| MEDIUM | 2 | Buyback probability 4.5% vs 4.3%; duplicate "Data Sources and Calibration" heading |
| LOW | 3 | "Six data sources" count; household debt figure; Aipinas (2026) orphan reference |
| STYLE | 3 | Body headings unnumbered vs TOC; 3 em dashes in Table A2; 1 colon clause connector |
