MODEL (
  name reference.icd_10,
  kind VIEW,
  grain (CODE, VERSION)
);

SELECT
  CODE,
  DISPLAY,
  VERSION
FROM read_csv('seeds/icd/ICD-10.csv') AS src(CODE, DISPLAY, VERSION);