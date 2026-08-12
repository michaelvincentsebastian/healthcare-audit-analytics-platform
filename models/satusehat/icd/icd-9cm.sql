MODEL (
  name reference.icd_9cm,
  kind FULL,
  grain ('code', 'version')
);

-- Tabel Referensi ICD-9-CM dari SatuSehat Resmi
-- Sumber: Google Sheet resmi Kemenkes (lihat link di bawah)
-- FULL refresh tiap run -- mencerminkan kondisi sheet TERKINI persis,
-- termasuk kode yang di-retire (tidak nyangkut selamanya seperti kalau pakai incremental upsert)

SELECT
  NULLIF(TRIM(CODE), '') AS 'code',
  NULLIF(TRIM(DISPLAY), '') AS 'display',
  NULLIF(TRIM(VERSION), '') AS 'version'
FROM read_csv('seeds/icd/ICD-9CM.csv')
WHERE CODE IS NOT NULL AND TRIM(CODE) != ''  -- buang baris kosong/header artifact
QUALIFY ROW_NUMBER() OVER (PARTITION BY TRIM(CODE), TRIM(VERSION) ORDER BY TRIM(DISPLAY)) = 1  -- jaga-jaga kalau ada baris duplikat di sheet (sering terjadi di sheet yang diedit manual)