SET @has_is_deleted := (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'users'
    AND COLUMN_NAME = 'is_deleted'
);

SET @delete_soft_deleted_sql := IF(
  @has_is_deleted > 0,
  'DELETE FROM users WHERE is_deleted = 1',
  'SELECT 1'
);
PREPARE delete_soft_deleted_stmt FROM @delete_soft_deleted_sql;
EXECUTE delete_soft_deleted_stmt;
DEALLOCATE PREPARE delete_soft_deleted_stmt;

SET @drop_is_deleted_sql := IF(
  @has_is_deleted > 0,
  'ALTER TABLE users DROP COLUMN is_deleted',
  'SELECT 1'
);
PREPARE drop_is_deleted_stmt FROM @drop_is_deleted_sql;
EXECUTE drop_is_deleted_stmt;
DEALLOCATE PREPARE drop_is_deleted_stmt;
