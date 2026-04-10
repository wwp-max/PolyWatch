# language: en
Feature: Benford's Law anomaly detection for potential volume fabrication
  As a Market Integrity Analyst
  I want to test whether leading-digit distributions follow Benford's Law
  So that I can identify markets with potentially fabricated transaction patterns

  # This is a specification artifact used for requirement traceability.

  Background:
    Given the Benford analyzer is initialized with chi2_threshold = 15.507
    And a minimum sample size of 100 observations is required

  Rule: Organic market activity should approximately conform to Benford distribution

  Scenario: Healthy market passes Benford test
    Given a market with 350 historical trade observations
    When the leading digits of trade-size values are extracted
    And a chi-square goodness-of-fit test is executed against Benford expected distribution
    Then the resulting chi2 statistic should be less than or equal to 15.507
    And the market should be labeled "BENFORD_PASS"
    And no alert should be raised

  Scenario: Fabricated round-number pattern fails Benford test
    Given a market with 352 observations concentrated around round numbers
    When the chi-square statistic is computed as sum((O - E)^2 / E) over digits 1..9
    Then the resulting chi2 statistic should be greater than 15.507
    And the market should be labeled "BENFORD_FAIL"
    And the system should emit alert level "High"

  Scenario: Insufficient sample size should skip test
    Given a market with only 45 observations
    When the Benford analyzer runs
    Then the test should be skipped
    And the result should be labeled "BENFORD_SKIP"
    And no alert should be raised

  Rule: Chi-square threshold must be configurable for sensitivity tuning

  Scenario Outline: Threshold boundary conditions
    Given a market with chi2 statistic of <chi2_value>
    And the configured threshold is 15.507
    Then the detection result should be <expected_result>

    Examples:
      | chi2_value | expected_result |
      | 15.506     | BENFORD_PASS    |
      | 15.507     | BENFORD_PASS    |
      | 15.508     | BENFORD_FAIL    |
      | 40.0       | BENFORD_FAIL    |
