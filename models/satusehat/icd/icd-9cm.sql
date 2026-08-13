MODEL (
  name bronze.icd_9cm,
  kind VIEW,
  grain (CODE, VERSION)
);

SELECT
  CODE,
  DISPLAY,
  VERSION
FROM read_csv('seeds/icd/ICD-9CM.csv') AS src(CODE, DISPLAY, VERSION);