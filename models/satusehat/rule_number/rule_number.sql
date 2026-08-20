MODEL (
  name reference.rule_number,
  kind VIEW,
  grain (rule_number, version)
);

SELECT
  "Rule No #" as rule_number,
  Path as path,
  "Terminologi Used" as terminologi_used,
  "Deskripsi Error" as deskripsi_error,
  "Last Update" as last_update,
  Version as version
FROM read_csv('seeds/rule_number.csv') AS src(
    "Rule No #", 
    Path, 
    "Terminologi Used", 
    "Deskripsi Error", 
    "Last Update", 
    Version);