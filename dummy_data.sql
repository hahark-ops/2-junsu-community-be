USE community_db;

-- ============================================
-- 1. 사용자 (Users) 추가
-- 비밀번호는 모두 'Password123!' (평문 저장 가정)
-- ============================================
INSERT IGNORE INTO users (email, password, nickname) VALUES 
('alice@example.com', 'Password123!', 'Alice'),
('bob@example.com', 'Password123!', 'Bob'),
('charlie@example.com', 'Password123!', 'Charlie'),
('david@example.com', 'Password123!', 'David'),
('eve@example.com', 'Password123!', 'Eve');

-- ============================================
-- 2. 게시글 (Posts) 추가
-- ============================================
INSERT INTO posts (user_id, title, content, view_count, created_at) VALUES 
((SELECT id FROM users WHERE email='alice@example.com'), '안녕하세요! 가입 인사 드립니다.', '커뮤니티가 참 깔끔하고 좋네요. 앞으로 잘 부탁드립니다!', 15, NOW()),
((SELECT id FROM users WHERE email='bob@example.com'), '오늘 점심 메뉴 추천받아요', '회사 근처에서 뭐 먹을지 매일 고민이네요. 다들 뭐 드시나요?', 42, NOW() - INTERVAL 1 HOUR),
((SELECT id FROM users WHERE email='charlie@example.com'), 'FastAPI 공부 중인데 질문 있습니다', 'Dependency Injection 부분이 조금 헷갈리는데 좋은 자료 있을까요?', 8, NOW() - INTERVAL 2 HOUR),
((SELECT id FROM users WHERE email='david@example.com'), '주말에 볼만한 넷플릭스 영화 추천', '스릴러 장르 좋아합니다. 추천 부탁드려요~', 25, NOW() - INTERVAL 1 DAY),
((SELECT id FROM users WHERE email='eve@example.com'), '개발자 노트북 맥북 vs 그램', '이동이 잦은 편인데 어떤게 좋을까요? 추천해주세요.', 105, NOW() - INTERVAL 2 DAY),
((SELECT id FROM users WHERE email='alice@example.com'), '여행 사진 공유합니다', '작년에 다녀온 제주도 사진입니다. 또 가고 싶네요.', 56, NOW() - INTERVAL 3 DAY),
((SELECT id FROM users WHERE email='bob@example.com'), '퇴근하고 싶다...', '아직 수요일이라니 믿기지가 않습니다.', 10, NOW() - INTERVAL 4 DAY),
((SELECT id FROM users WHERE email='charlie@example.com'), 'MySQL 쿼리 튜닝 팁 공유', '인덱스만 잘 타도 속도가 엄청 빨라지네요.', 88, NOW() - INTERVAL 5 DAY);

-- ============================================
-- 3. 댓글 (Comments) 추가
-- ============================================
-- '안녕하세요! 가입 인사 드립니다.' 글에 대한 댓글
INSERT INTO comments (post_id, user_id, content) 
SELECT id, (SELECT id FROM users WHERE email='bob@example.com'), '환영합니다! 활동 많이 해주세요~'
FROM posts WHERE title = '안녕하세요! 가입 인사 드립니다.';

INSERT INTO comments (post_id, user_id, content) 
SELECT id, (SELECT id FROM users WHERE email='charlie@example.com'), '반갑습니다!'
FROM posts WHERE title = '안녕하세요! 가입 인사 드립니다.';

-- '오늘 점심 메뉴 추천받아요' 글에 대한 댓글
INSERT INTO comments (post_id, user_id, content) 
SELECT id, (SELECT id FROM users WHERE email='david@example.com'), '날씨도 쌀쌀한데 뜨끈한 국밥 어떠세요?'
FROM posts WHERE title = '오늘 점심 메뉴 추천받아요';

INSERT INTO comments (post_id, user_id, content) 
SELECT id, (SELECT id FROM users WHERE email='eve@example.com'), '저는 오늘 제육볶음 먹었습니다.'
FROM posts WHERE title = '오늘 점심 메뉴 추천받아요';

-- '개발자 노트북 맥북 vs 그램' 글에 대한 댓글
INSERT INTO comments (post_id, user_id, content) 
SELECT id, (SELECT id FROM users WHERE email='alice@example.com'), '개발용이면 맥북이 국룰이죠!'
FROM posts WHERE title = '개발자 노트북 맥북 vs 그램';

INSERT INTO comments (post_id, user_id, content) 
SELECT id, (SELECT id FROM users WHERE email='bob@example.com'), '가벼운게 최고면 그램도 좋습니다.'
FROM posts WHERE title = '개발자 노트북 맥북 vs 그램';

-- ============================================
-- 4. 좋아요 (Post Likes) 추가
-- ============================================
-- '개발자 노트북 맥북 vs 그램' 글에 좋아요 3개
INSERT INTO post_likes (post_id, user_id)
SELECT p.id, u.id 
FROM posts p, users u 
WHERE p.title = '개발자 노트북 맥북 vs 그램' AND u.email IN ('alice@example.com', 'bob@example.com', 'charlie@example.com');

-- 'MySQL 쿼리 튜닝 팁 공유' 글에 좋아요 2개
INSERT INTO post_likes (post_id, user_id)
SELECT p.id, u.id 
FROM posts p, users u 
WHERE p.title = 'MySQL 쿼리 튜닝 팁 공유' AND u.email IN ('david@example.com', 'eve@example.com');

-- ============================================
-- 5. 결과 확인
-- ============================================
SELECT 'Dummy data inserted successfully!' as result;
SELECT * FROM users;
SELECT * FROM posts;
