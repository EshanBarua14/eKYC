# M83: eKYC Load Test Suite

## Install
```bash
pip install locust
```

## Run headless (CI)
```bash
locust -f load_tests/locustfile.py \
       --host=http://localhost:8000 \
       --headless -u 500 -r 50 \
       --run-time 5m \
       --html load_tests/report_$(date +%Y%m%d).html \
       --csv  load_tests/results_$(date +%Y%m%d)
```

## Run with UI
```bash
locust -f load_tests/locustfile.py --host=http://localhost:8000
# Open http://localhost:8089
```

## SLA targets (BFIU production sign-off)
| Endpoint | p99 target | Error rate |
|----------|-----------|------------|
| /face/verify | < 3000ms | < 0.1% |
| /kyc/profile | < 2000ms | < 0.1% |
| /screening/check | < 1000ms | < 0.1% |
| Overall 500 users | — | < 1% |
