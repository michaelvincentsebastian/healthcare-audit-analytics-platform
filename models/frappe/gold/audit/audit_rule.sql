MODEL (
  name gold.audit_rule,
  kind FULL,
  grain (rule_id)
);

-- Rule Registry -- Healthcare Compliance Audit.
-- Single source of truth untuk semua audit rule + provenance-nya. TIDAK ADA rule yang boleh
-- di-hardcode di check model tanpa row di sini terlebih dahulu (lihat PRD Section 2 & 3).
--
-- Pola sama seperti models/satusehat/icd/*.sql: FULL refresh dari CSV via read_csv, bukan
-- SQLMesh native `kind SEED` (tidak dipakai di tempat lain di repo ini -- konsistensi dengan
-- pola yang sudah ada lebih diutamakan).
--
-- `rule_expression` adalah POINTER (path relatif ke check model), BUKAN SQL yang di-embed --
-- logic asli tetap hidup satu tempat saja di models/frappe/gold/audit/checks/*.sql, supaya tidak
-- ada dua sumber kebenaran yang bisa saling drift.
--
-- Baris dengan status = 'BLOCKED' (lihat CTL-IDENT-PAT-COMPLETE-001) SENGAJA tidak punya check
-- model yang berjalan -- rule-nya tercatat di registry supaya provenance-nya visible ke auditor,
-- tapi tidak menghasilkan finding apa pun sampai field list dikonfirmasi pemilik data.

-- Catatan: standard_version di-CAST ke VARCHAR eksplisit karena DuckDB read_csv auto-infer
-- kolom itu sebagai BIGINT (semua nilai saat ini numerik, mis. "2010") -- kalau dibiarkan,
-- TRIM() akan gagal binding. Cast eksplisit mencegah ini pecah lagi kalau baris baru ditambah.

SELECT
  rule_id,
  rule_name,
  description,
  audit_domain,
  focus_area,
  rule_basis,
  NULLIF(TRIM(authority_name), '') AS authority_name,
  NULLIF(TRIM(authority_reference), '') AS authority_reference,
  NULLIF(TRIM(standard_name), '') AS standard_name,
  NULLIF(TRIM(CAST(standard_version AS VARCHAR)), '') AS standard_version,
  rule_expression,
  severity,
  CAST(effective_from AS DATE) AS effective_from,
  CAST(NULLIF(TRIM(effective_to), '') AS DATE) AS effective_to,
  status,
  CAST(version AS INTEGER) AS version,
  CAST(created_at AS TIMESTAMP) AS created_at,
  CAST(updated_at AS TIMESTAMP) AS updated_at
FROM read_csv('seeds/audit/rule_registry.csv') AS src(rule_id, rule_name, description, audit_domain, focus_area, rule_basis, authority_name, authority_reference, standard_name, standard_version, rule_expression, severity, effective_from, effective_to, status, version, created_at, updated_at)
