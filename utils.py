# utils.py

import re

# 1. 이메일 형식 검사
def validate_email(email: str) -> bool:
    email_regex = r'^[a-zA-Z0-9+_\-.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(email_regex, email))

# 2. 비밀번호 강도 검사
# 조건: 영문, 숫자, 특수문자 포함, 8~20자
def validate_password(password: str) -> bool:
    if len(password) < 8 or len(password) > 20:
        return False
    
    # 정규식: 영문(?=.*[A-Za-z]), 숫자(?=.*\d), 특수문자(?=.*[@$!%*#?&]) 각각 최소 1개 포함
    pw_regex = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]+$'
    return bool(re.match(pw_regex, password))

# 3. 닉네임 형식 검사
# 조건: 공백이나 특수문자 불가 (한글, 영문, 숫자만 허용)
def validate_nickname(nickname: str) -> bool:
    # ^[가-힣a-zA-Z0-9]+$ -> 한글, 영대소문자, 숫자만 있으면 통과
    nickname_regex = r'^[가-힣a-zA-Z0-9]+$'
    return bool(re.match(nickname_regex, nickname))