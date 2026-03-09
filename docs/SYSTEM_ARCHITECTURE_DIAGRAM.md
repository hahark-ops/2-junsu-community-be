# 시스템 아키텍처 설계도 (노션 붙여넣기용)

최종 업데이트: 2026-03-09 (KST)

## As-Is (현재 운영)

```mermaid
flowchart TD
    U(("사용자 웹 브라우저"))

    subgraph EC2_LAYER["Primary Runtime (Single EC2)"]
    direction TB
    EC2["EC2 (Ubuntu)"]
    NG["Docker: Nginx<br/>(Reverse Proxy)"]
    FE["Docker: FE"]
    BE["Docker: BE (FastAPI)"]
    MYSQL[("Docker: MySQL DB<br/>(Internal Docker Network)")]
    EC2 --> NG
    NG --> FE
    NG --> BE
    BE --> MYSQL
    end

    subgraph BE_LAMBDA_LAYER["BE Lambda Path (Assignment Evidence)"]
    direction TB
    APIGW_BE["API Gateway<br/>(community-dev-be-http-api)"]
    LAMBDA_BE["Lambda: community-dev-be-api"]
    DB_TARGET[("DB Target<br/>(RDS or db_host_override)")]
    APIGW_BE --> LAMBDA_BE
    LAMBDA_BE --> DB_TARGET
    end

    subgraph STORAGE_LAYER["Storage Layer"]
    direction TB
    S3[("Amazon S3<br/>(이미지 스토리지)")]
    APIGW_UPLOAD["API Gateway<br/>(upload-api)"]
    LAMBDA_UPLOAD["Lambda: upload handler"]
    APIGW_UPLOAD --> LAMBDA_UPLOAD
    LAMBDA_UPLOAD -. Presigned URL .-> S3
    end

    subgraph ANALYTICS_LAYER["Analytics Layer"]
    direction TB
    APIGW_ANALYTICS["API Gateway<br/>(/v1/analytics/health)"]
    LAMBDA_ANALYTICS["Lambda: analytics handler"]
    ATHENA[("Athena")]
    APIGW_ANALYTICS --> LAMBDA_ANALYTICS --> ATHENA
    end

    U -->|"1. 브라우저 접속 (HTTP)"| NG
    NG -->|"2. 일반 API (/v1/*)"| BE
    U -->|"3. 업로드 URL 요청"| BE
    BE -->|"4. 내부 호출 (X-Upload-Internal-Token)"| APIGW_UPLOAD
    U -->|"5. Presigned URL PUT"| S3
    U -->|"6. BE Lambda 검증 경로"| APIGW_BE
    U -->|"7. 분석 API"| APIGW_ANALYTICS

    classDef layer fill:#3b3f46,stroke:#8b8f96,color:#ffffff;
    classDef orange fill:#ff9800,stroke:#c77700,color:#ffffff;
    classDef blue fill:#2f74c0,stroke:#1e4f85,color:#ffffff;
    classDef light fill:#f2f2f2,stroke:#888,color:#333;

    class EC2_LAYER,BE_LAMBDA_LAYER,STORAGE_LAYER,ANALYTICS_LAYER layer;
    class APIGW_BE,LAMBDA_BE,APIGW_UPLOAD,LAMBDA_UPLOAD,APIGW_ANALYTICS,LAMBDA_ANALYTICS,S3 orange;
    class MYSQL blue;
    class EC2,NG,FE,BE light;
```

## To-Be (고가용성 목표)

```mermaid
flowchart TD
    U(("사용자 웹 브라우저"))

    subgraph EDGE["Edge Layer (Multi-AZ)"]
    direction TB
    ALB["ALB"]
    end

    subgraph APP["Application Layer (Auto Scaling or ECS)"]
    direction TB
    APPA["App Node A (AZ-a)"]
    APPB["App Node B (AZ-c)"]
    end

    subgraph DATA["Data Layer (Managed)"]
    direction TB
    RDS[("RDS MySQL<br/>(Multi-AZ)")]
    end

    subgraph SERVERLESS["Serverless Integrations"]
    direction TB
    APIGW["API Gateway"]
    LUP["Lambda: upload-url"]
    LAN["Lambda: analytics"]
    ATH[("Athena")]
    S3[("S3 Upload Bucket")]
    end

    U --> ALB
    ALB --> APPA
    ALB --> APPB
    APPA --> RDS
    APPB --> RDS

    U --> APIGW
    APIGW --> LUP
    APIGW --> LAN
    LUP --> S3
    U -->|"PUT to S3"| S3
    LAN --> ATH

    classDef layer fill:#3b3f46,stroke:#8b8f96,color:#ffffff;
    classDef orange fill:#ff9800,stroke:#c77700,color:#ffffff;
    classDef blue fill:#2f74c0,stroke:#1e4f85,color:#ffffff;
    classDef light fill:#f2f2f2,stroke:#888,color:#333;

    class EDGE,APP,DATA,SERVERLESS layer;
    class APIGW,LUP,LAN,S3,ATH orange;
    class RDS blue;
    class ALB,APPA,APPB light;
```

## 서비스 흐름 요약

1. 사용자 요청은 Nginx(현재) 또는 ALB(목표)로 진입한다.
2. 일반 API는 애플리케이션 컨테이너(FastAPI)로 라우팅된다.
3. 업로드는 BE(`/v1/files/upload-url`)가 API Gateway -> Lambda로 presigned URL을 발급받고, 브라우저가 그 URL로 S3에 직접 업로드한다.
   - 브라우저가 API Gateway upload 경로를 직접 호출하는 것은 내부 토큰 검증으로 차단된다.
4. 분석 API는 API Gateway -> Lambda -> Athena 경로로 처리한다.
5. BE Lambda 경로는 API Gateway -> Lambda -> 별도 DB 대상(RDS 또는 `db_host_override`)으로 연결된다.
