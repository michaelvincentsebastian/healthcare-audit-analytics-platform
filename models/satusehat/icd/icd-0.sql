MODEL (
  name bronze.icd_0,
  kind VIEW,
  grain (CODE, SAB)
);

SELECT
  CODE,
  STR,
  SAB
FROM read_csv('seeds/icd/ICD-0.csv') AS src(CODE, STR, SAB);