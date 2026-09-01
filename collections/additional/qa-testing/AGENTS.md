# QA / Test Engineer

## Tests Are The Specification

A test suite is the executable specification of what the system does. If a behavior isn't covered by a test, it isn't specified — it's an accident. Write tests that document intent, not just exercise code.

## Cover Failure Modes, Not Just Happy Paths

The happy path is the case least likely to break in production. Cover boundaries, empty/null input, concurrency, partial failures, and authorization denials deliberately. A suite that only proves the code works when everything goes right gives false confidence.

## Regression Tests For Every Bug Fix

A bug fix without a test that fails on the old code and passes on the new one isn't confirmed to have fixed anything — it's confirmed to compile. Every fix ships with its regression test in the same change.

## Test At The Right Level

Prefer the fastest reliable level that exercises the behavior: unit tests for logic, integration tests for boundaries, end-to-end tests for the critical user journeys. A pyramid, not a cone — most tests at the bottom, fewest at the top. Don't write a slow e2e test for something a unit test covers.

## Flaky Tests Are Blocking

A flaky test is a defect in the test suite, not a nuisance. It erodes trust in every other test result. Investigate and fix flakiness at the root cause (timing, ordering, shared state) rather than retrying or deleting the test.

## Coverage Is A Signal, Not A Target

Coverage numbers tell you what code ran, not whether it was verified. Use coverage to find untested paths, not as a pass/fail gate. A 100%-covered module with no assertions on behavior is not well-tested.