CREATE TABLE IF NOT EXISTS web_push_subscriptions (
    subscriptionId INT AUTO_INCREMENT PRIMARY KEY,
    userEmail VARCHAR(255) NOT NULL,
    endpoint TEXT NOT NULL,
    endpointHash CHAR(64) NOT NULL,
    p256dh VARCHAR(255) NOT NULL,
    auth VARCHAR(255) NOT NULL,
    isActive TINYINT(1) NOT NULL DEFAULT 1,
    lastUsedAt DATETIME DEFAULT NULL,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_web_push_endpoint_hash (endpointHash),
    INDEX idx_web_push_user_active (userEmail, isActive),
    FOREIGN KEY (userEmail) REFERENCES users(email) ON DELETE CASCADE
);
