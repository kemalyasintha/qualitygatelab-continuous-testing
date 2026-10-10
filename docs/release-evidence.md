# Release evidence and acceptance validation

QualityGateLab validates a change record, unit/integration reports, coverage and named gate acceptance cases before API packaging. It generates a source-linked manifest, a decision record and a UAT results table. This is a portfolio implementation of evidence review controls, not production compliance certification.

## Evidence flow

Update `compliance/change.json` for the reviewed change scope. It declares the change ID, summary, owner, recorded review, risk, rollback, findings and acceptance cases. It is a portfolio self-review record, not an authenticated security approval. Each acceptance case must match a passing test name in the actual CI reports.

`eng/run_uat.py` executes the Python gate tests and writes actual JUnit results. .NET unit and integration suites produce TRX and Cobertura reports. After migrations, tests and coverage succeed, `eng/evidence_gate.py build` copies the evidence into a new bundle, records SHA-256 hashes, binds it to the source revision and pipeline run, and validates it. Packaging proceeds only if validation succeeds.

The gate fails for missing mandatory evidence, empty/incomplete/failed/skipped reports, missing acceptance results, incomplete change documentation or review decisions, unresolved high/critical findings, overdue lower-severity findings, expired exceptions, closed findings without verification, low coverage, altered files, unsafe paths or the wrong source revision.

`security_findings` contains supplied findings; no scanner runs. An empty register does not prove the absence of vulnerabilities. Each finding needs `id`, `severity`, `owner`, `description`, `due_date`, `status`. Closed findings need `verification`. Exceptions need `exception.reviewer`, `exception.reason`, `exception.expires`, and a separate reviewer. Exceptions expire at the start of their listed date. Recorded identities are not authenticated.

## Bundle contents

| Output | Purpose |
| --- | --- |
| `change-record.json` | Change, review, risks, rollback, findings and acceptance mapping |
| `manifest.json` | Source revision, run, generation/evaluation time, artifact inventory and hashes |
| `unit`, `integration`, `coverage`, `uat` | Copies of actual input reports |
| `gate-result.json` | Decision, test counts and coverage; failure reason when rejected |
| `uat-results.csv` | Requirement-to-passing-test mapping on success |

Derived decision and CSV files are regenerated on verification; their source inputs are hashed. Manifests are not signed or immutable. Someone who can rewrite the manifest and all inputs can rewrite the bundle. Production requires trusted CI provenance and independently controlled retention.

## Run on Windows

From the repository root with Python 3.10+ and .NET 10:

```powershell
python eng/run_uat.py --output artifacts/test-results/uat/gate-uat.xml
dotnet restore
dotnet build --configuration Release --no-restore
dotnet tool restore
dotnet ef database update --project src/QualityGateLab.Api --startup-project src/QualityGateLab.Api --configuration Release --no-build --connection "Data Source=artifacts/migration-check.db"
dotnet test tests/QualityGateLab.UnitTests --configuration Release --no-build --settings tests/coverage.runsettings --collect:"XPlat Code Coverage" --logger "trx;LogFileName=unit-tests.trx" --results-directory artifacts/test-results/unit
dotnet test tests/QualityGateLab.IntegrationTests --configuration Release --no-build --settings tests/coverage.runsettings --collect:"XPlat Code Coverage" --logger "trx;LogFileName=integration-tests.trx" --results-directory artifacts/test-results/integration
$revision = git rev-parse HEAD
python eng/evidence_gate.py build --record compliance/change.json --source-revision $revision --run-id local-run-001 --unit-reports "artifacts/test-results/unit/**/*.trx" --integration-reports "artifacts/test-results/integration/**/*.trx" --coverage-reports "artifacts/test-results/**/coverage.cobertura.xml" --uat-reports "artifacts/test-results/uat/gate-uat.xml" --output artifacts/release-evidence
python eng/evidence_gate.py verify --source-revision $revision --output artifacts/release-evidence
```

Use fresh results and bundle directories for every run. `build` uses today's local policy evaluation date. `verify` uses the original evaluation date unless `--as-of YYYY-MM-DD` is provided. The fixture tests use fixed evaluation dates for reproducibility. Stale input reports cannot be independently identified from TRX alone; hosted pipelines use fresh result directories.

The source revision is supplied from the checkout identity. The gate does not prove that externally supplied reports were generated from that revision; trusted runners and pipeline isolation establish that provenance.

## UAT requirements

| ID | Requirement | Test |
| --- | --- | --- |
| UAT-01 | Complete reports produce source-linked evidence | `test_complete_bundle_passes` |
| UAT-02 | Missing evidence fails | `test_missing_category_fails` |
| UAT-03 | Unresolved high finding fails | `test_open_high_finding_fails` |
| UAT-04 | Expired exception fails | `test_expired_exception_fails` |
| UAT-05 | Modified evidence fails | `test_tampered_evidence_fails` |

These automated acceptance cases verify gate behaviour. They do not represent business-stakeholder sign-off. JUnit and the generated CSV show actual execution results.

## Governance and retention

Make `Validate release evidence` a required repository status check alongside the Azure Pipeline check. YAML alone does not enforce branch protection. Authenticated human approvals and production deployment gates remain future work. The repository builds and packages; it does not deploy to production.

Azure retains results and the bundle as `qualitygatelab-release-evidence`. GitHub retains evidence for 14 days. Set organization-specific retention before relying on artifacts for audits.
