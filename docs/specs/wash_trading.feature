# language: en
Feature: Detection of Market Manipulation Patterns
  As a Market Integrity Analyst
  I want to automatically flag suspicious trading activity
  So that I can identify potential wash-trading and spoofing behavior

  # Maintained as spec artifact for traceability and test design.

  Rule: A wash trade involves no meaningful change in beneficial ownership

  Scenario: Basic self-match detection (atomic wash trade)
    Given a set of filled orders on a target market
    When an order is filled where "Maker_Address" equals "Taker_Address"
    Then the transaction should be flagged as "Self-Match"
    And the transaction hash should be logged to a suspicious-activity record

  Scenario: Circular trading pattern (A -> B -> A)
    Given recent transactions within a 5-minute window:
      | TxID | From_User | To_User | Amount | Token_Type |
      | tx_1 | Alice     | Bob     | 1000   | YES_Token  |
      | tx_2 | Bob       | Alice   | 1000   | YES_Token  |
    When a cycle detection algorithm runs
    Then it should identify a closed loop between "Alice" and "Bob"
    And the net inventory change for Alice should be 0
    And the combined volume should be tagged as "Artificial Volume"

  Rule: Spoofing involves intent to cancel before execution

  Scenario: High-frequency cancellation (layering)
    Given a user "Whale_0x1"
    When "Whale_0x1" places 50 limit orders with size > 10000 USD each
    And 90% of these orders are canceled within 10 seconds of placement
    And no orders are filled
    Then the user should be flagged for "Potential Spoofing"
    And the system should trigger alert level "High"
