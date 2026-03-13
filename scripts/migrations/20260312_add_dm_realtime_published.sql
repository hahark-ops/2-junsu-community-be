SET @has_realtime_published_at := (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'dm_messages'
    AND COLUMN_NAME = 'realtimePublishedAt'
);

SET @add_realtime_published_at_sql := IF(
  @has_realtime_published_at = 0,
  'ALTER TABLE dm_messages ADD COLUMN realtimePublishedAt DATETIME DEFAULT NULL AFTER content',
  'SELECT 1'
);

PREPARE add_realtime_published_at_stmt FROM @add_realtime_published_at_sql;
EXECUTE add_realtime_published_at_stmt;
DEALLOCATE PREPARE add_realtime_published_at_stmt;
