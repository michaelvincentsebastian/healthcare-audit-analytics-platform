MODEL (
  name bronze.icd_mm,
  kind VIEW,
  grain (CODE, VERSION)
);

SELECT
  LEVEL,
  CODE,
  DISPLAY,
  VERSION
FROM read_csv('seeds/icd/ICD-MM.csv') AS src(LEVEL, CODE, DISPLAY, VERSION);