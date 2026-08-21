# QualityGateLab — Continuous Testing

QualityGateLab is an in-progress continuous quality engineering project combining .NET test automation with AZ-400 DevOps practices.

The project currently demonstrates .NET 10, xUnit, API integration testing, EF Core, SQLite, GitHub pull requests, Azure Boards traceability and Azure DevOps continuous integration.

## Current implementation

* ASP.NET Core customer-order REST API
* Test-first order domain model
* Required-field and email validation
* Quantity boundary validation from 1 to 100
* Unique order identifiers
* Initial `Pending` order status
* EF Core persistence using SQLite
* EF Core database migrations
* Swagger/OpenAPI documentation
* xUnit unit and integration tests
* GitHub feature-branch and pull-request workflow
* Azure Boards work-item traceability using `AB#` references
* Azure DevOps YAML continuous integration pipeline
* Automated test-result and code-coverage publishing
* Aggregate line-coverage quality gate
* Deployable API pipeline artifact

## Architecture

```mermaid
flowchart TD
    Client["API client / Swagger"] --> API["ASP.NET Core API"]
    API --> Validation["Request validation"]
    Validation --> Domain["Order domain model"]
    Domain --> EF["Entity Framework Core"]
    EF --> DB["SQLite database"]

    GitHub["GitHub pull request"] --> Pipeline["Azure DevOps pipeline"]
    Pipeline --> Build["Restore and build"]
    Build --> Tests["Unit and integration tests"]
    Tests --> Gate["Coverage threshold"]
    Gate --> Results["Results and API artifact"]
```

The diagram above shows the currently implemented CI workflow. Azure deployment is intentionally identified as planned work until the infrastructure and deployment stages are implemented and verified.

## Database strategy

### Current development and testing

SQLite is used for local development and automated integration testing. This keeps the repository easy to clone and run without provisioning an external database. Integration tests use isolated SQLite databases so persistence behaviour can be verified without sharing state between test runs.

### Planned production environment

The planned Azure deployment will use Azure SQL Database as the production data store while retaining SQLite for local development and tests. The production implementation will include:

* The EF Core SQL Server provider selected through environment-specific configuration
* A separate SQL Server-compatible migration set
* Azure SQL provisioned through Bicep
* Passwordless App Service access using managed identity
* An EF Core migration bundle produced in CI and applied during deployment
* No database credentials committed to the repository

## API endpoints

| Method | Endpoint           | Purpose                 | Successful response |
| ------ | ------------------ | ----------------------- | ------------------- |
| `POST` | `/api/orders`      | Create a customer order | `201 Created`       |
| `GET`  | `/api/orders/{id}` | Retrieve an order by ID | `200 OK`            |

Example create-order request:

```json
{
  "customerEmail": "customer@example.com",
  "productName": "Mechanical Keyboard",
  "quantity": 2
}
```

Example response:

```json
{
  "id": "generated-order-guid",
  "customerEmail": "customer@example.com",
  "productName": "Mechanical Keyboard",
  "quantity": 2,
  "status": "Pending",
  "createdAtUtc": "2026-08-20T18:00:00Z"
}
```

## Run locally

Requirements:

* .NET 10 SDK
* Git

Clone and restore the repository:

```powershell
git clone https://github.com/kemalyasintha/qualitygatelab-continuous-testing.git
Set-Location qualitygatelab-continuous-testing
dotnet restore
```

Verify the solution before starting the API:

```powershell
dotnet test --configuration Release
```

Create or update the local SQLite database:

```powershell
dotnet tool restore

dotnet ef database update `
  --project src\QualityGateLab.Api `
  --startup-project src\QualityGateLab.Api
```

Start the API:

```powershell
dotnet run --project src\QualityGateLab.Api
```

Use the URL displayed in the terminal and append `/swagger` to open the interactive API documentation. For example:

```text
http://localhost:5034/swagger
```

The local port may be different on another computer.

## Run the automated tests

Run the complete test suite:

```powershell
dotnet test --configuration Release
```

Run the unit tests:

```powershell
dotnet test tests\QualityGateLab.UnitTests --configuration Release
```

Run the integration tests:

```powershell
dotnet test tests\QualityGateLab.IntegrationTests --configuration Release
```

Run all tests with code coverage:

```powershell
dotnet test --configuration Release `
  --settings tests\coverage.runsettings `
  --collect:"XPlat Code Coverage" `
  --results-directory .\TestResults
```

Cobertura reports are written below `TestResults\<test-run-id>\coverage.cobertura.xml`. See [the quality gate policy](docs/quality-gates.md) for the local aggregate-coverage check and the required GitHub ruleset.

The test suite covers:

* Required order fields
* Email validation
* Quantity boundaries
* Unique identifiers
* Initial order status
* SQLite persistence
* Successful API order creation
* Invalid API requests
* Retrieving a created order

## Continuous integration

The Azure DevOps YAML pipeline runs for changes to `main`, feature branches and pull requests.

Current CI controls run in this order:

1. Install the .NET 10 SDK
2. Restore NuGet packages
3. Build the solution in Release configuration
4. Restore the repository’s local .NET tools
5. Validate EF Core migrations against a temporary SQLite database
6. Run unit and integration tests
7. Collect code coverage
8. Publish test results and coverage to Azure DevOps
9. Enforce a 70% aggregate line-coverage threshold
10. Produce and publish a deployable API artifact
11. Report the pipeline result as a GitHub pull-request check

The first customer-order pull request passed the Azure Pipeline quality check before being merged into `main`.

## Quality gates

The pipeline fails when the Release build, migration validation, automated tests, coverage publication, coverage threshold or API packaging fails. The repository-level merge policy is documented in [the quality gate policy](docs/quality-gates.md) and requires a one-time GitHub ruleset configuration before it can be marked complete.

SonarQube is not required for the initial gate. Static analysis and security scanning can be added later without replacing the existing build, test, migration and coverage controls.

## Planned Azure delivery architecture

The following architecture is planned and is not yet deployed:

```mermaid
flowchart TD
    Artifact["Verified API artifact"] --> Bicep["Bicep validation and deployment"]
    Bicep --> Dev["App Service development"]
    Dev --> Smoke["API smoke tests"]
    Smoke --> Approval["Environment approval"]
    Approval --> Prod["Production deployment"]
    Prod --> Monitor["Application Insights verification"]
```

## Work-item traceability

Development work is planned in Azure Boards using the Agile process:

```text
Epic → Feature → User Story → Task
```

Git commits include Azure Boards references such as `AB#3`, connecting code changes to the corresponding work item.

## Project roadmap

* [x] Create order domain model
* [x] Add unit and integration tests
* [x] Add request validation
* [x] Configure EF Core and SQLite
* [x] Add database migration testing
* [x] Implement create-order and get-order endpoints
* [x] Add Swagger/OpenAPI
* [x] Add Azure DevOps continuous integration
* [x] Enforce an aggregate line-coverage threshold in CI
* [x] Publish a deployable API pipeline artifact
* [ ] Configure GitHub branch protection and required quality checks
* [ ] Add Playwright end-to-end tests
* [ ] Define Azure infrastructure using Bicep
* [ ] Deploy the API through Azure DevOps
* [ ] Add Application Insights monitoring
* [ ] Add post-deployment smoke tests
* [ ] Add deployment environments and approval gates

## Project evidence

* [Merged customer-order pull request](https://github.com/kemalyasintha/qualitygatelab-continuous-testing/pull/1)
* Azure Pipeline validation displayed as a successful GitHub pull-request check
* Automated test results and code coverage published in Azure DevOps

Additional pipeline, test and deployment screenshots will be added as the project progresses.

## Technologies

* .NET 10
* ASP.NET Core
* C#
* xUnit
* Entity Framework Core
* SQLite
* Swagger/OpenAPI
* Git and GitHub
* Azure Boards
* Azure DevOps Pipelines
* YAML

## Status

This is an actively developed portfolio project. Playwright testing, Bicep infrastructure, Azure deployment and Application Insights monitoring are planned for upcoming milestones.
