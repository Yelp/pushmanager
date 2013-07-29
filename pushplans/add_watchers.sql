/*
Add watchers column to push_requests.
*/

# MySQL Syntax
ALTER TABLE `push_requests`
  ADD COLUMN `watchers` text default NULL AFTER `description`;

/* ROLLBACK COMMANDS

ALTER TABLE `push_requests`
  DROP COLUMN `watchers`;

*/

# Sqlite3 Syntax
# WARNING: BACKUP DATABASE FIRST!
# sqlite3 has no rollback equivalent for add column
/*
ALTER TABLE 'push_requests'
  ADD COLUMN 'watchers' VARCHAR;
*/
