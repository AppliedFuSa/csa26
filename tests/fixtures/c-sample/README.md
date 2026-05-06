# tests/fixtures/c-sample

Mini-Fixture mit absichtlich MISRA-verletzendem C-Code. Wird vom
Self-Smoketest-Workflow benutzt, um zu prüfen, dass die csa26-Action
End-to-End läuft (Container baut, cppcheck startet, Wrapper parst,
Outputs entstehen).

**Nicht** als realistischer embedded-Code gedacht. Die ausführliche
externe Test-Fixture lebt im Repo `AppliedFuSa/csa26-testfixture`
(siehe [`docs/smoketest.md`](../../../docs/smoketest.md)).
