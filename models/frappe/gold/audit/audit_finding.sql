MODEL (
  name gold.audit_finding,
  kind VIEW,
  grain (finding_id)
);

-- Audit Finding -- model sentral yang dibaca serving layer & dashboard.
--
-- STATUS PHASE 2: SKELETON. Skema 23 kolom di bawah ini FINAL (lihat 03_data-model-specs.md
-- Section 3) dan sudah aman dipakai untuk membangun serving layer (Phase 6) & dashboard (Phase 7)
-- terhadap kontrak ini sekarang -- tapi model ini SELALU 0 baris sampai Phase 3-5 selesai:
--   Phase 3-4: 9 check model individual dibangun di models/frappe/gold/audit/checks/*.sql,
--              masing-masing menghasilkan baris dengan bentuk PERSIS sama seperti SELECT di bawah.
--   Phase 5:   SELECT ini diganti UNION ALL dari seluruh check model (pola persis seperti
--              gold.audit_finding = check_1 UNION ALL check_2 UNION ALL ...).
--
-- PENTING -- jangan disalahartikan (sama seperti catatan di audit_run.sql): 0 baris di sini
-- BUKAN "0 temuan / semua data compliant". Ini "belum ada check yang jalan sama sekali". Dashboard
-- (Phase 7) WAJIB membedakan dua kondisi ini secara eksplisit ke auditor -- jangan render
-- "0 findings" tanpa konteks status audit_run.

SELECT
  CAST(NULL AS VARCHAR)    AS finding_id,          -- hash deterministik (audit_run_id, rule_id, entity_type, entity_id)
  CAST(NULL AS VARCHAR)    AS audit_run_id,
  CAST(NULL AS VARCHAR)    AS rule_id,
  CAST(NULL AS INTEGER)    AS rule_version,         -- disalin dari audit_rule.version saat run, bukan live-join

  CAST(NULL AS VARCHAR)    AS audit_domain,         -- denormalized dari audit_rule
  CAST(NULL AS VARCHAR)    AS focus_area,           -- denormalized dari audit_rule
  CAST(NULL AS VARCHAR)    AS entity_type,          -- 'Condition' | 'Procedure' | 'Observation' | 'Encounter' | 'Patient'
  CAST(NULL AS VARCHAR)    AS entity_id,

  CAST(NULL AS VARCHAR)    AS patient_id,
  CAST(NULL AS VARCHAR)    AS encounter_id,

  CAST(NULL AS VARCHAR)    AS actual_value,
  CAST(NULL AS VARCHAR)    AS expected_value,

  CAST(NULL AS VARCHAR)    AS severity,             -- disalin dari audit_rule.severity saat run
  CAST(NULL AS VARCHAR)    AS status,               -- OPEN | REVIEWED | RESOLVED | FALSE_POSITIVE

  CAST(NULL AS TIMESTAMP)  AS detected_at,
  CAST(NULL AS TIMESTAMP)  AS resolved_at,

  CAST(NULL AS VARCHAR)    AS source_system,        -- 'clinic-satusehat' / 'Frappe'
  CAST(NULL AS VARCHAR)    AS source_record_id,      -- frappe_doc_name, untuk traceability ke SIMRS

  CAST(NULL AS VARCHAR)    AS evidence_reference,    -- pointer ke baris silver, mis. 'silver.condition_fhir_resource:<name>'
  CAST(NULL AS VARCHAR)    AS explanation,

  CAST(NULL AS VARCHAR)    AS reviewer_id,
  CAST(NULL AS VARCHAR)    AS review_note,
  CAST(NULL AS VARCHAR)    AS resolution_code
WHERE 1 = 0
