SET @like_unique_exists := (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'likes'
    AND INDEX_NAME = 'unique_like'
);

SET @sql := IF(
  @like_unique_exists = 0,
  'ALTER TABLE likes ADD CONSTRAINT unique_like UNIQUE (postId, userEmail)',
  'SELECT 1'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
