/*
Add stagenv column to pushes
*/

# MySQL Syntax
ALTER TABLE `push_pushes`
  ADD COLUMN `stageenv` text default NULL AFTER `extra_pings`;

/* ROLLBACK COMMANDS

ALTER TABLE `push_pushes``
  DROP COLUMN `stageenv`;

*/

# Sqlite3 Syntax
# WARNING: BACKUP DATABASE FIRST!
# sqlite3 has no rollback equivalent for add column
/*
ALTER TABLE 'push_pushes'
  ADD COLUMN 'stageenv' VARCHAR;
*/
