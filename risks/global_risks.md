# ⚠️ Global Risk Registry

| Risk ID | Description | Probability | Impact | Mitigation Strategy | Owner | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| G-01 | API Rate Limiting | 4 | 5 | Implement exponential backoff | @backend | Open |
| G-02 | Third-party vendor delay | 3 | 4 | Multi-sourcing | @procurement | Open |
| G-03 | Local Storage limit | 1 | 2 | Automated log rotation | @devops | Closed |
| G-04 | Key rotation failure | 2 | 5 | Automated IAM testing | @security | Open |
| G-05 | DB Sync Latency | 5 | 3 | Setup Read-Replicas | @dba | Open |