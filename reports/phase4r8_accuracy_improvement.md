# PHASE 4R8.0 FINAL RECOMMENDATION ACCURACY REPORT

## 1. K Ablation Results
| Candidate Pool (K) | Final Rec Accuracy | Hit@1 | Recall@100 | Identity Lineage |
| :--- | :--- | :--- | :--- | :--- |
| 10 | 8/19 = 42.11% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| 15 | 8/19 = 42.11% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| 20 | 8/19 = 42.11% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| 30 | 8/19 = 42.11% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| 50 | 7/19 = 36.84% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| 75 | 7/19 = 36.84% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| 100 | 7/19 = 36.84% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |

## 2. Component Ablation
| Configuration | Final Rec Accuracy | Hit@1 | Recall@100 | Identity Lineage |
| :--- | :--- | :--- | :--- | :--- |
| R7_Baseline | 8/19 = 42.11% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| Arbitration_Only | 8/19 = 42.11% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| Ambiguity_Only | 8/19 = 42.11% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |
| Combined | 8/19 = 42.11% | 10/19 = 52.63% | 18/19 = 94.74% | 18/19 = 94.74% |

## 3. Per-Query Improvement Table (12 Lost Recommendations in R7)
| Req ID | Expected Standard | R7 Final | R8 Combined Final | R7 Stage Rank | R8 Result | Change Responsible | Human Review |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| T001-R002 | IS 15905 : 2011; IS 1239 (Part 1) : 2004 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T001-R003 | IS 15622 : 2017 | NONE | NONE | 7 | STILL LOST | Combined Fix | False |
| T001-R004 | IS 2556 (Part 1 to 17); IS 781 : 1984; IS 774 : 2021 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T002-R003 | IS 6392 : 1971; IS 2712 : 2020 | NONE | NONE | 2 | STILL LOST | Combined Fix | False |
| T003-R001 | IS/IEC 61439-3 : 2012; IS 10322 (Part 5 / Sec 5) : 2013 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T004-R002 | IS 7098 (Part 1) : 1988; IS 1255 : 1983 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T004-R005 | IS 5039 : 1983; IS/IEC 61439-5 : 2014 | NONE | NONE | 18 | STILL LOST | Combined Fix | False |
| T005-R001 | IS 3043 : 2018; IS 7098 (Part 1) : 1988; IS 1293 : 2019 | NONE | NONE | 61 | STILL LOST | Combined Fix | False |
| T006-R001 | IS 16088 : 2016 | NONE | NONE | None | STILL LOST | Combined Fix | False |
| T007-R003 | IS 2491 : 2013; IS 15000 : 2013 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T009-R001 | SP 30 : 2023; IS 732 : 2019 | NONE | NONE | 10 | STILL LOST | Combined Fix | False |
| T010-R001 | IS 458 : 2021; IS 783 : 1985; IS 14333 : 1996 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T011-R001 | IS 7098 (Part 1) : 1988; IS 1255 : 1983 | NONE | NONE | 61 | STILL LOST | Combined Fix | False |
| T012-R002 | IS 1661 : 1972; IS 269 : 2015 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T012-R003 | IS 1239 (Part 2) : 1992; IS 778 : 1984 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T013-R002 | IS/IEC 61800-2 : 2015; IS/IEC 61439-2 : 2011 | NONE | NONE | 4 | STILL LOST | Combined Fix | False |
| T013-R003 | IS 14164 : 2008; IS 8183 : 1993 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |
| T014-R002 | IS/IEC 60034-1 : 2017; IS 5120 : 1977 | NONE | NONE | 39 | STILL LOST | Combined Fix | False |
| T020-R001 | IS 15778 : 2007; IS 1239 (Part 1) : 2004 | NONE | NONE | 1 | STILL LOST | Combined Fix | False |

Total Recovered: 0/19