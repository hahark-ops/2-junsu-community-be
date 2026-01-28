from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

def test_upload_flow():
    # 1. 로그인
    print("1. Logging in...")
    login_resp = client.post("/v1/auth/login", json={
        "email": "user1@test.com",
        "password": "Password123!"
    })
    
    if login_resp.status_code != 200:
        print(f"Login Failed: {login_resp.status_code}, {login_resp.text}")
        return

    print("Login Success!")
    
    # 2. 파일 생성
    with open("test.jpg", "wb") as f:
        f.write(b"fake image content")
        
    # 3. 파일 업로드
    print("2. Uploading file...")
    with open("test.jpg", "rb") as f:
        files = {"file": ("test.jpg", f, "image/jpeg")}
        data = {"type": "post"}
        # 쿠키는 TestClient가 자동으로 처리하거나, 명시적으로 전달 필요할 수 있음
        # TestClient는 세션 쿠키를 자동으로 유지하지 않을 수 있으므로 headers/cookies 전달
        # 하지만 API 문서상 쿠키 사용.
        # client.cookies contains cookies from login
        resp = client.post("/v1/files/upload", files=files, data=data)
        
    if resp.status_code == 201:
        print(f"Upload Success! Response: {resp.json()}")
    else:
        print(f"Upload Failed: {resp.status_code}, {resp.text}")

if __name__ == "__main__":
    test_upload_flow()
