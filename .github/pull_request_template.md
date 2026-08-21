## Summary

<!-- Explain what changed and why. -->

## Azure Boards

<!-- Use the real work-item ID, for example: AB#123 -->

AB#

## Quality evidence

- [ ] Release build succeeds
- [ ] Unit tests pass
- [ ] Integration/API tests pass
- [ ] EF Core migration validation passes when persistence changes
- [ ] Aggregate line coverage meets the configured threshold
- [ ] Documentation reflects implemented versus planned functionality
- [ ] No secrets, credentials, database files, or generated artifacts are committed

## Validation performed

```text
dotnet build --configuration Release
dotnet test --configuration Release
```

## Screenshots or pipeline links

<!-- Add evidence when the change affects UI, pipelines, deployments, or monitoring. -->
