USE community_db;

-- ============================================
-- 0. 기존 데이터 초기화 (싹 지우기)
-- ============================================
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE comments;
TRUNCATE TABLE post_likes;
TRUNCATE TABLE files;
TRUNCATE TABLE posts;
TRUNCATE TABLE users;
TRUNCATE TABLE sessions;
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 1. 프로시저 생성
-- ============================================
DROP PROCEDURE IF EXISTS generate_dummy_data;

DELIMITER $$

CREATE PROCEDURE generate_dummy_data()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE user_count INT DEFAULT 100;    -- 사용자 100명
    DECLARE post_count INT DEFAULT 10000;  -- 게시글 1만개
    DECLARE comment_count INT DEFAULT 20000; -- 댓글 2만개
    
    -- 1. 사용자 100명 생성
    SET i = 1;
    WHILE i <= user_count DO
        INSERT IGNORE INTO users (email, password, nickname) 
        VALUES (
            CONCAT('user', i, '@test.com'), 
            'Password123!', 
            CONCAT('User', i)
        );
        SET i = i + 1;
    END WHILE;

    -- 2. 게시글 10,000개 생성
    SET i = 1;
    WHILE i <= post_count DO
        INSERT INTO posts (user_id, title, content, view_count, created_at)
        VALUES (
            (FLOOR(1 + RAND() * user_count)), -- 1~100 사이 랜덤 유저
            CONCAT('게시글 제목 - ', i),
            CONCAT('이것은 ', i, '번째 게시글 내용입니다. 데이터베이스 성능 테스트를 위한 더미 데이터입니다.'),
            FLOOR(RAND() * 1000), -- 0~999 랜덤 조회수
            DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 365) DAY) -- 최근 1년 내 랜덤 날짜
        );
        SET i = i + 1;
    END WHILE;

    -- 3. 댓글 20,000개 생성
    SET i = 1;
    WHILE i <= comment_count DO
        INSERT INTO comments (post_id, user_id, content, created_at)
        VALUES (
            (FLOOR(1 + RAND() * post_count)), -- 1~10000 사이 랜덤 게시글
            (FLOOR(1 + RAND() * user_count)), -- 1~100 사이 랜덤 유저
            CONCAT('댓글 내용입니다 - ', i),
            DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 365) DAY)
        );
        SET i = i + 1;
    END WHILE;

    -- 4. 좋아요 랜덤 생성 (약 5000개)
    SET i = 1;
    WHILE i <= 5000 DO
        INSERT IGNORE INTO post_likes (post_id, user_id)
        VALUES (
            (FLOOR(1 + RAND() * post_count)),
            (FLOOR(1 + RAND() * user_count))
        );
        SET i = i + 1;
    END WHILE;

END$$

DELIMITER ;

-- ============================================
-- 2. 프로시저 실행
-- ============================================
CALL generate_dummy_data();

-- ============================================
-- 3. 결과 확인
-- ============================================
SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(*) as post_count FROM posts;
SELECT COUNT(*) as comment_count FROM comments;
