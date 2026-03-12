ALTER TABLE web_push_subscriptions
    ADD COLUMN endpointHash CHAR(64) NULL AFTER endpoint;

UPDATE web_push_subscriptions
SET endpointHash = SHA2(endpoint, 256)
WHERE endpointHash IS NULL OR endpointHash = '';

ALTER TABLE web_push_subscriptions
    MODIFY COLUMN endpointHash CHAR(64) NOT NULL;

ALTER TABLE web_push_subscriptions
    DROP INDEX unique_web_push_endpoint,
    ADD UNIQUE KEY unique_web_push_endpoint_hash (endpointHash);
