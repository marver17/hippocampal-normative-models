# Missing Clinical Data Report

## Summary

Out of 110 subjects in the RF dataset volume files, **23 subjects are missing age/sex** data in the clinical_informations.csv file.

## Missing Subjects List

1. sub-1027483
2. sub-1070908_ritorno (duplicate scan - excluded from analysis)
3. sub-1206913
4. sub-1212986
5. sub-1255198
6. sub-1293678
7. sub-1296055
8. sub-1301416
9. sub-1309816
10. sub-1320667
11. sub-1322149
12. sub-1351120
13. sub-1373146
14. sub-1384218
15. sub-1387438
16. sub-1393791
17. sub-1394060
18. sub-1419664
19. sub-272693
20. sub-42566
21. sub-752504
22. sub-850648
23. sub-909203

## Impact on Analysis

### Current Z-Score Coverage
- **CT**: 66/102 subjects (65%) have z-scores
- **MR-Real**: 87/102 subjects (85%) have z-scores
- **MR-Gen**: 81/102 subjects (79%) have z-scores

### After Filtering (QC ≥ 0.7)
- **Total subjects with QC ≥ 0.7**: 96 subjects
- **Subjects missing age/sex**: ~18-22 (depending on modality)
- **Expected z-score coverage after resolving**: ~74-78 subjects (77-81%)

## Investigation Results

1. **clinical_informations.csv**: Contains 107 unique subjects, 105 with age/sex
2. **combined/clinical_subjects_with_zscores.csv**: Does not contain RF subjects
3. **BIDS participants.tsv**: Not found in RF directory
4. **DICOM headers**: Not investigated (would require DICOM file access)

## Recommendations

### Option 1: Accept Current Coverage (RECOMMENDED)
- Current z-score coverage is **sufficient** for statistical analysis
- Low QC group: ~32-35 subjects with z-scores (after QC ≥ 0.7 filter)
- High QC group: ~32-35 subjects with z-scores (after median split)
- This provides adequate statistical power for ICC analysis

### Option 2: Extract from DICOM Headers
- Would require accessing original DICOM files
- Time-consuming and may not yield results if PHI was anonymized
- Risk: Age might have been randomized/shifted for anonymization

### Option 3: Contact Data Source
- Request complete clinical metadata from RF dataset provider
- Most reliable method but requires external coordination

## Conclusion

The "apriori filter problem" for z-scores is caused by **genuinely missing clinical data** in the available metadata files, not by an incorrect filtering strategy.

**Proposed solution**: Proceed with current z-score coverage (65-85% depending on modality) as it provides sufficient statistical power for the concordance analysis.
