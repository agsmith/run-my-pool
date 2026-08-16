# Capacity testing

The initial target is 700 registered users, not 700 simultaneous users. Test a lower environment in stages: 25, 50, 100, then 150 concurrent users. Hold each stage for five minutes and allow at least two minutes between stages so ECS scaling can stabilize.

```bash
python3 tools/capacity_test.py \
  --base-url https://staging.example.com \
  --token "$RMP_TEST_TOKEN" \
  --pool-id "$RMP_TEST_POOL_ID" \
  --users 50 \
  --rate 1 \
  --duration 300
```

This stage generates roughly 50 requests per second. The command fails when errors exceed 1% or p95 latency exceeds 750 ms. Use a dedicated test user and pool. Never include credentials in source control.

During a run, monitor:

- ALB target response time, HTTP 5xx, and healthy hosts
- ECS desired/running tasks, CPU, and memory
- RDS CPU, database connections, free memory, read/write latency, and slow-query logs
- application request duration and database timeout logs

The configured backend ceiling is four tasks. With `DB_POOL_SIZE=5` and `DB_MAX_OVERFLOW=5`, application demand is bounded to 40 database connections plus migrations and operational clients. Confirm this remains comfortably below the RDS `max_connections` value before raising either ceiling.

Production execution requires the explicit `--confirm-production` flag. Prefer staging. If production testing is necessary, start at 10 users, schedule it during a quiet window, and stop immediately on elevated errors or database saturation.
