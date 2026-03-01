# 과제 9~11 실행 증빙

최종 업데이트: 2026-03-01 (KST)

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

- CI 성공(run):
  - [22544670598](https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544670598)
- CI 실패(run, 게이트 차단 검증):
  - [22544406601](https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544406601)
  - 실패 SHA: `9d03e4f...`
  - 확인 내용: 해당 SHA 기준 `deploy-ec2` 자동 실행 없음

## 과제 11: GitHub Actions -> EC2 자동배포

- push -> ci -> deploy 자동 성공 사이클:
  - CI: [22544670598](https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544670598)
  - Deploy EC2: [22544690983](https://github.com/hahark-ops/2-junsu-community-be/actions/runs/22544690983)
- 배포 후 헬스:
  - SSM 원격 실행으로 `curl http://127.0.0.1/` 확인
  - 결과: `HTTP/1.1 200 OK`
