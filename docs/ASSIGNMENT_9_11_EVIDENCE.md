# 과제 9~11 실행 증빙

최종 업데이트: 2026-03-16 (KST)

## 과제 9: 인프라 제거 후 Terraform 재구축

- 로컬 증빙 폴더:
  - `/Users/junsu/Desktop/2-junsu-community-be/evidence/assignment9-20260301-204358`
- 핵심 파일:
  - `11-destroy-final.txt` (destroy 성공)
  - `12-state-after-destroy.txt` (destroy 후 state 비움)
  - `20-apply-final.txt` (apply 성공)
  - `21-output-after.txt` (재구축 output)
  - `22-state-after-apply.txt` (재구축 state 목록)
  - `23-resource-status-after-apply.txt` (EC2/ALB/Lambda/APIGW 상태)

## 과제 10: 테스트코드 -> CI 게이트

- 테스트 자산
  - 백엔드: `/Users/junsu/Desktop/2-junsu-community-be/tests`
    - `pytest + TestClient`
    - coverage gate: `--cov-fail-under=70`
  - 프론트엔드: `/Users/junsu/Desktop/2-junsu-community-fe/tests/e2e`
    - `Playwright E2E`
    - 시나리오: 회원가입/로그인/프로필 수정/탈퇴 후 재가입/게시글/댓글/좋아요/DM/unread
  - 보조 smoke:
    - `/Users/junsu/Desktop/2-junsu-community-be/scripts/qa_ec2_smoke.sh`
- 로컬 검증 결과
  - 백엔드: `48 passed`, coverage `71.30%`
  - 프론트엔드: `npm run test:e2e -- --list` 기준 3개 E2E 시나리오 인식 확인
- CI 완료 기준
  - `python-compile` 통과
  - `be-pytest` 통과
  - `compose-config` 통과
  - `integration-stack`에서 `qa_ec2_smoke.sh` + Playwright E2E 통과
- 배포 게이트 의미
  - `deploy-ec2`는 `ci` green 이후에만 실행
  - 즉, 정식 테스트코드와 E2E가 실패하면 자동 배포가 차단됨

## 과제 11: GitHub Actions -> EC2 자동배포

- push -> ci -> deploy 자동 성공 사이클:
  - CI: [22544670598](https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544670598)
  - Deploy EC2: [22544690983](https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544690983)
- 배포 후 헬스:
  - SSM 원격 실행으로 `curl http://127.0.0.1/` 확인
  - 결과: `HTTP/1.1 200 OK`
