MODEL (
  name reference.icd_pm,
  kind VIEW,
  grain (CODE, VERSION)
);

SELECT
  CODE,
  DISPLAY,
  VERSION
FROM read_csv('seeds/icd/ICD-PM.csv') AS src(CODE, DISPLAY, VERSION);