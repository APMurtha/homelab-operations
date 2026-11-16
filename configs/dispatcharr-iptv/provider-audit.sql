-- PREPARED: file_path/credential fields checked against pinned 0.33.0 models.
-- Revalidate on a disposable copy after any image or schema change.
-- Never display provider URLs, JSON properties or credentials.
-- A fresh install includes a locked custom account and its default profile.
-- Fail closed on any extra account/profile, URL/upload/custom properties, or EPG
-- source. This narrowly permits the known built-in seed; it is not an importer.
BEGIN TRANSACTION READ ONLY;
WITH builtin_accounts AS (
    SELECT id FROM m3u_m3uaccount
    WHERE name = 'custom' AND locked AND is_active AND max_streams = 0
      AND COALESCE(server_url, '') = ''
      AND COALESCE(file_path, '') = ''
      AND COALESCE(username, '') = ''
      AND COALESCE(password, '') = ''
      AND COALESCE(custom_properties::jsonb, '{}'::jsonb) = '{}'::jsonb
), builtin_profiles AS (
    SELECT id FROM m3u_m3uaccountprofile
    WHERE m3u_account_id IN (SELECT id FROM builtin_accounts)
      AND name = 'custom Default' AND is_default AND is_active AND max_streams = 0
      AND search_pattern = '^(.*)$' AND replace_pattern = '$1'
      AND COALESCE(custom_properties::jsonb, '{}'::jsonb) = '{}'::jsonb
), counts AS (
    SELECT
      (SELECT count(*) FROM builtin_accounts) AS builtin_account_count,
      (SELECT count(*) FROM builtin_profiles) AS builtin_profile_count,
      (SELECT count(*) FROM m3u_m3uaccount) AS total_account_count,
      (SELECT count(*) FROM m3u_m3uaccountprofile) AS total_profile_count,
      (SELECT count(*) FROM epg_epgsource) AS total_epg_source_count
)
SELECT json_build_object(
    'builtin_account_count', builtin_account_count,
    'builtin_profile_count', builtin_profile_count,
    'unexpected_account_count', total_account_count - builtin_account_count,
    'unexpected_profile_count', total_profile_count - builtin_profile_count,
    'epg_source_count', total_epg_source_count,
    'audit_pass', builtin_account_count = 1 AND builtin_profile_count = 1
       AND total_account_count = 1 AND total_profile_count = 1
       AND total_epg_source_count = 0
) FROM counts;
ROLLBACK;
