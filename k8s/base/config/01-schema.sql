-- 데이터베이스 생성 (없으면 생성)
CREATE DATABASE IF NOT EXISTS community_db;
USE community_db;

-- 1. 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    userId INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- bcrypt 해시 저장
    nickname VARCHAR(50) NOT NULL UNIQUE,
    profileimage TEXT,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. 게시글 테이블
CREATE TABLE IF NOT EXISTS posts (
    postId INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    fileUrl TEXT,
    writer VARCHAR(50) NOT NULL, -- 닉네임 (비정규화)
    writerEmail VARCHAR(255) NOT NULL, -- 이메일 (FK 역할)
    viewCount INT DEFAULT 0,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (writerEmail) REFERENCES users(email) ON DELETE CASCADE
);

-- 3. 댓글 테이블
CREATE TABLE IF NOT EXISTS comments (
    commentId INT AUTO_INCREMENT PRIMARY KEY,
    postId INT NOT NULL,
    content TEXT NOT NULL,
    writer VARCHAR(50) NOT NULL, -- 닉네임 (비정규화)
    writerEmail VARCHAR(255) NOT NULL, -- 이메일 (FK 역할)
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (postId) REFERENCES posts(postId) ON DELETE CASCADE,
    FOREIGN KEY (writerEmail) REFERENCES users(email) ON DELETE CASCADE
);

-- 4. 좋아요 테이블
CREATE TABLE IF NOT EXISTS likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    postId INT NOT NULL,
    userEmail VARCHAR(255) NOT NULL,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_like (postId, userEmail),
    FOREIGN KEY (postId) REFERENCES posts(postId) ON DELETE CASCADE,
    FOREIGN KEY (userEmail) REFERENCES users(email) ON DELETE CASCADE
);

-- 5. 세션 테이블 (선택 사항: DB 세션 사용 시)
CREATE TABLE IF NOT EXISTS sessions (
    sessionId VARCHAR(255) PRIMARY KEY,
    userEmail VARCHAR(255) NOT NULL,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    expiresAt DATETIME NOT NULL,
    INDEX idx_sessions_expiresAt (expiresAt),
    FOREIGN KEY (userEmail) REFERENCES users(email) ON DELETE CASCADE
);

-- 6. 1:1 DM 방 테이블
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

-- 7. DM 메시지 테이블
CREATE TABLE IF NOT EXISTS dm_messages (
    messageId INT AUTO_INCREMENT PRIMARY KEY,
    roomId INT NOT NULL,
    senderEmail VARCHAR(255) NOT NULL,
    clientMessageId VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    realtimePublishedAt DATETIME DEFAULT NULL,
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_dm_message_client (roomId, senderEmail, clientMessageId),
    INDEX idx_dm_messages_room_created (roomId, createdAt, messageId),
    FOREIGN KEY (roomId) REFERENCES dm_rooms(roomId) ON DELETE CASCADE,
    FOREIGN KEY (senderEmail) REFERENCES users(email) ON DELETE CASCADE
);

-- 8. DM 읽음 상태 테이블
CREATE TABLE IF NOT EXISTS dm_room_reads (
    roomId INT NOT NULL,
    userEmail VARCHAR(255) NOT NULL,
    lastReadMessageId INT DEFAULT NULL,
    lastReadAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (roomId, userEmail),
    FOREIGN KEY (roomId) REFERENCES dm_rooms(roomId) ON DELETE CASCADE,
    FOREIGN KEY (userEmail) REFERENCES users(email) ON DELETE CASCADE,
    FOREIGN KEY (lastReadMessageId) REFERENCES dm_messages(messageId) ON DELETE SET NULL
);

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
