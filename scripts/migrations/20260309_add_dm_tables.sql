USE community_db;

CREATE TABLE IF NOT EXISTS dm_rooms (
    roomId INT AUTO_INCREMENT PRIMARY KEY,
    userAEmail VARCHAR(255) NOT NULL,
    userBEmail VARCHAR(255) NOT NULL,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_dm_room_pair (userAEmail, userBEmail),
    FOREIGN KEY (userAEmail) REFERENCES users(email) ON DELETE CASCADE,
    FOREIGN KEY (userBEmail) REFERENCES users(email) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dm_messages (
    messageId INT AUTO_INCREMENT PRIMARY KEY,
    roomId INT NOT NULL,
    senderEmail VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dm_messages_room_created (roomId, createdAt, messageId),
    FOREIGN KEY (roomId) REFERENCES dm_rooms(roomId) ON DELETE CASCADE,
    FOREIGN KEY (senderEmail) REFERENCES users(email) ON DELETE CASCADE
);
