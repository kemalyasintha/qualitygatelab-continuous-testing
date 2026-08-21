# Quality gate policy

QualityGateLab treats a pull request as releasable only when its automated checks pass. The Azure DevOps pipeline implements the build, migration, test, coverage and packaging controls. GitHub must be configured once to make the Azure Pipeline status a required merge check.

## Pipeline-enforced controls

The pipeline fails when any of these conditions occurs:

* NuGet restore or the Release build fails.
* The EF Core migrations cannot create a clean SQLite database.
* A unit or integration test fails.
* Test results or coverage reports are missing.
* The aggregate line coverage is below the configured threshold.
* The deployable API package cannot be produced.

The aggregate coverage calculation merges the unit and integration Cobertura reports by source file and line. It selects the `QualityGateLab.Api` package and excludes the test-project packages. A line is treated as covered when at least one test suite executes it, which prevents the same application line from being counted twice.

## Required GitHub ruleset

Configure this once in **Repository settings → Rules → Rulesets → New branch ruleset**:

1. Name the ruleset `main-quality-gates` and set it to **Active**.
2. Target the default branch (`main`).
3. Require a pull request before merging.
4. Require the Azure Pipeline status check `kemalyasintha.qualitygatelab-continuous-testing`.
5. Require the branch to be current before merging.
6. Require conversation resolution.
7. Block force pushes and branch deletion.
8. Require linear history when using squash merges.

This is a solo portfolio repository, so an external approval is not required. The pull-request workflow and automated checks remain required.

## Coverage threshold

The initial aggregate line-coverage threshold is configured in `azure-pipelines.yml` as `minimumLineCoverage`. Raise it intentionally as coverage improves; do not lower it merely to make a failing pull request pass.

Run the same check locally after collecting coverage:

```powershell
dotnet test --configuration Release `
  --collect:"XPlat Code Coverage" `
  --results-directory .\TestResults

python eng\coverage_gate.py `
  --reports ".\TestResults\**\coverage.cobertura.xml" `
  --include-package "QualityGateLab.Api" `
  --threshold 70
```

## Planned deployment gates

When continuous delivery is introduced, the following controls will be added:

* Bicep linting, validation and what-if review.
* Deployment only from a successful, immutable pipeline artifact.
* Development-environment smoke tests.
* Manual approval before production deployment.
* Application Insights health verification after deployment.
