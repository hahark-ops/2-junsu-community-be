-- 데이터베이스 생성 (없으면 생성)
CREATE DATABASE IF NOT EXISTS community_db;
USE community_db;

-- 1. 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    userId INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NOT NULL UNIQUE,
    profileimage TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
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
    FOREIGN KEY (userEmail) REFERENCES users(email) ON DELETE CASCADE
);
