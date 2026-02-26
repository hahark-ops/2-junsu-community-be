-- 세션 만료(7일 TTL) 도입 마이그레이션
-- 실행 전: USE community_db;

SET @column_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'sessions'
      AND COLUMN_NAME = 'expiresAt'
);

SET @add_column_sql := IF(
    @column_exists = 0,
    'ALTER TABLE sessions ADD COLUMN expiresAt DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt_add_column FROM @add_column_sql;
EXECUTE stmt_add_column;
DEALLOCATE PREPARE stmt_add_column;

UPDATE sessions
SET expiresAt = DATE_ADD(createdAt, INTERVAL 7 DAY)
WHERE expiresAt IS NULL;

ALTER TABLE sessions
MODIFY COLUMN expiresAt DATETIME NOT NULL;

SET @index_exists := (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'sessions'
      AND INDEX_NAME = 'idx_sessions_expiresAt'
);

SET @add_index_sql := IF(
    @index_exists = 0,
    'ALTER TABLE sessions ADD INDEX idx_sessions_expiresAt (expiresAt)',
    'SELECT 1'
);
PREPARE stmt_add_index FROM @add_index_sql;
EXECUTE stmt_add_index;
DEALLOCATE PREPARE stmt_add_index;
