CREATE TABLE IF NOT EXISTS dm_room_reads (
    roomId INT NOT NULL,
    userEmail VARCHAR(255) NOT NULL,
    lastReadMessageId INT DEFAULT NULL,
    lastReadAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (roomId, userEmail),
    CONSTRAINT fk_dm_room_reads_room
        FOREIGN KEY (roomId) REFERENCES dm_rooms(roomId) ON DELETE CASCADE,
    CONSTRAINT fk_dm_room_reads_user
        FOREIGN KEY (userEmail) REFERENCES users(email) ON DELETE CASCADE,
    CONSTRAINT fk_dm_room_reads_message
        FOREIGN KEY (lastReadMessageId) REFERENCES dm_messages(messageId) ON DELETE SET NULL
);
