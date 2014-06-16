/*
Add conflicts column to push_requests
*/

# MySQL Syntax
ALTER TABLE `push_requests`
  ADD COLUMN `conflicts` text default NULL AFTER `tags`;

/* ROLLBACK COMMANDS

ALTER TABLE `push_requests`
  DROP COLUMN `conflicts`;

*/

# Sqlite3 Syntax
# WARNING: BACKUP DATABASE FIRST!
# sqlite3 has no rollback equivalent for add column
/*
ALTER TABLE 'push_requests'
  ADD COLUMN 'conflicts' VARCHAR;
*/
