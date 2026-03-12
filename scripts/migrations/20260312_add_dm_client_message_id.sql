SET @column_exists := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'dm_messages'
      AND COLUMN_NAME = 'clientMessageId'
);

SET @add_column_sql := IF(
    @column_exists = 0,
    'ALTER TABLE dm_messages ADD COLUMN clientMessageId VARCHAR(64) NULL AFTER senderEmail',
    'SELECT 1'
);
PREPARE stmt_add_column FROM @add_column_sql;
EXECUTE stmt_add_column;
DEALLOCATE PREPARE stmt_add_column;

UPDATE dm_messages
SET clientMessageId = CONCAT('legacy-', messageId)
WHERE clientMessageId IS NULL OR clientMessageId = '';

ALTER TABLE dm_messages
MODIFY COLUMN clientMessageId VARCHAR(64) NOT NULL;

SET @unique_index_exists := (
    SELECT COUNT(*)
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'dm_messages'
      AND INDEX_NAME = 'unique_dm_message_client'
);

SET @add_unique_index_sql := IF(
    @unique_index_exists = 0,
    'ALTER TABLE dm_messages ADD CONSTRAINT unique_dm_message_client UNIQUE (roomId, senderEmail, clientMessageId)',
    'SELECT 1'
);
PREPARE stmt_add_unique_index FROM @add_unique_index_sql;
EXECUTE stmt_add_unique_index;
DEALLOCATE PREPARE stmt_add_unique_index;
