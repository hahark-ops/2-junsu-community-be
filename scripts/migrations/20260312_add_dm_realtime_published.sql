ALTER TABLE dm_messages
    ADD COLUMN realtimePublishedAt DATETIME DEFAULT NULL AFTER content;
