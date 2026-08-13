MODEL (
  name gold.audit_check_identity_patient_uid_format,
  kind FULL,
  grain (finding_id)
);

-- Rule: CTL-IDENT-PAT-FORMAT-001 | rule_basis: UNVERIFIED
--
-- INI FORMAT CHECK SAJA, BUKAN VALIDASI NIK RESMI. Field uid di silver.tabPatient polanya mirip
-- NIK (16 digit, ada DDMMYY di tengah), tapi pemilik data sendiri tidak yakin apakah ini benar
-- NIK atau ID internal lain -- lihat 02_control-matrix-final.md. Jangan naikkan rule_basis ini ke
-- REGULATION/SATUSEHAT_INTEROPERABILITY tanpa konfirmasi definisi field dari pemilik data.
--
-- Applicability: hanya Patient dengan uid terisi.

SELECT
  md5('NA' || '|CTL-IDENT-PAT-FORMAT-001|Patient|' || t.name) AS finding_id,
  CAST(NULL AS VARCHAR)                       AS audit_run_id,
  'CTL-IDENT-PAT-FORMAT-001'                  AS rule_id,
  1                                            AS rule_version,
  'Patient Identity & Identifier Integrity'   AS audit_domain,
  'Identity - UID Format'                     AS focus_area,
  'Patient'                                    AS entity_type,
  t.name                                       AS entity_id,
  t.name                                       AS patient_id,
  CAST(NULL AS VARCHAR)                       AS encounter_id,
  t.uid                                        AS actual_value,
  '16 digit numerik (format-check saja, bukan validasi NIK resmi)' AS expected_value,
  'LOW'                                        AS severity,
  'OPEN'                                       AS status,
  current_timestamp                            AS detected_at,
  CAST(NULL AS TIMESTAMP)                     AS resolved_at,
  'Frappe'                                      AS source_system,
  t.name                                       AS source_record_id,
  'silver.tabPatient:name=' || t.name AS evidence_reference,
  'Patient.uid (''' || t.uid || ''') tidak berformat 16 digit numerik. Catatan: ini format-check saja -- definisi resmi field uid belum dikonfirmasi (lihat rule_basis = UNVERIFIED)' AS explanation,
  CAST(NULL AS VARCHAR)                       AS reviewer_id,
  CAST(NULL AS VARCHAR)                       AS review_note,
  CAST(NULL AS VARCHAR)                       AS resolution_code
FROM silver.tabPatient t
WHERE t.uid IS NOT NULL
  AND TRIM(t.uid) != ''
  AND NOT regexp_matches(TRIM(t.uid), '^[0-9]{16}$')
