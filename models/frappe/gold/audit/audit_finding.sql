MODEL (
  name gold.audit_finding,
  kind VIEW,
  grain (finding_id)
);

-- Audit Finding -- model sentral yang dibaca serving layer & dashboard.
--
-- STATUS PHASE 5: WIRED. UNION ALL dari seluruh check model AKTIF (8 rule, lihat
-- seeds/audit/rule_registry.csv status = ACTIVE): 7 check Priority 1 (Phase 3) + 1 check temporal
-- (Phase 4). Setiap check model menghasilkan baris berbentuk PERSIS 23 kolom yang sama seperti
-- kontrak di bawah -- lihat masing-masing models/frappe/gold/audit/checks/*.sql untuk rule logic,
-- applicability, dan provenance per check.
--
-- CTL-IDENT-PAT-COMPLETE-001 (status BLOCKED di rule_registry.csv) SENGAJA tidak punya cabang
-- UNION di sini -- rule-nya tercatat di gold.audit_rule untuk provenance, tapi tidak ada check
-- model yang jalan sampai field mandatory dikonfirmasi (lihat PHASE_ROADMAP.md open item #2).
--
-- BELUM SELESAI DI PHASE INI: kolom `audit_run_id` masih NULL (di-passthrough apa adanya dari
-- tiap check model) -- BUKAN bug, ini menunggu keputusan reproducibility-mechanism untuk
-- gold.audit_run (lihat PHASE5_REPORT.md, "Open item: audit_run wiring"). Jangan isi audit_run_id
-- dengan current_timestamp/UUID acak di sini sebelum keputusan itu dibuat -- akan menghasilkan
-- audit_run_id yang beda tiap kali VIEW ini di-query, bukan sekali per eksekusi suite.

SELECT * FROM gold.audit_check_identity_patient_uid_format
UNION ALL
SELECT * FROM gold.audit_check_reference_integrity_condition_encounter
UNION ALL
SELECT * FROM gold.audit_check_reference_integrity_observation_encounter
UNION ALL
SELECT * FROM gold.audit_check_reference_integrity_procedure_encounter
UNION ALL
SELECT * FROM gold.audit_check_structural_encounter_status
UNION ALL
SELECT * FROM gold.audit_check_temporal_encounter_period
UNION ALL
SELECT * FROM gold.audit_check_terminology_icd10_validity
UNION ALL
SELECT * FROM gold.audit_check_terminology_icd9cm_validity
