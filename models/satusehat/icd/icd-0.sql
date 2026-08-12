MODEL (
  name reference.icd_0,
  kind FULL,
  grain ('code', 'sab')
);

-- Tabel Referensi ICD-0 dari SatuSehat Resmi
-- Sumber: Google Sheet resmi Kemenkes (lihat link di bawah)
-- FULL refresh tiap run -- mencerminkan kondisi sheet TERKINI persis,
-- termasuk kode yang di-retire (tidak nyangkut selamanya seperti kalau pakai incremental upsert)

SELECT
  NULLIF(TRIM('CODE'), '') AS 'code',
  NULLIF(TRIM('STR'), '') AS 'str',
  NULLIF(TRIM('SAB'), '') AS 'sab'
FROM read_csv('seeds/icd/ICD-0.csv')
WHERE CODE IS NOT NULL AND TRIM('CODE') != ''  -- buang baris kosong/header artifact
QUALIFY ROW_NUMBER() OVER (PARTITION BY TRIM('CODE'), TRIM('SAB') ORDER BY TRIM('STR')) = 1  -- jaga-jaga kalau ada baris duplikat di sheet (sering terjadi di sheet yang diedit manual)