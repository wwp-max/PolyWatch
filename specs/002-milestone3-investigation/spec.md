# Feature Specification: Milestone 3 Investigation (Case Studies)

**Feature Branch**: `002-milestone3-investigation`  
**Created**: 2026-03-27  
**Status**: Draft  
**Input**: User description: "Complete deep investigation report and case studies for manipulative events"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Etherscan / Polygonscan Transaction Flow Tracking (Priority: P1)

As a security researcher (Member D), I want to trace the funding source and transaction flow for highly suspicious accounts flagged by Member C's clustering/Sybil algorithms.

**Why this priority**: Required for the deep forensics (+5% bonus). Proves manipulation empirically.

**Independent Test**: Can be tested by manually verifying a flagged wallet address on Polygonscan and identifying its initial funding source (e.g., Centralized Exchange or Mixer).

**Acceptance Scenarios**:

1. **Given** a set of suspicious wallets, **When** I query their transaction history, **Then** I can trace the initial funding source.
2. **Given** the funding source, **When** it links to Tornado Cash or identical CEX withdrawals across multiple wallets, **Then** it serves as evidence of a Sybil cluster.

---

### User Story 2 - GraphViz Wallet Association Visualization (Priority: P2)

As a security researcher, I want to map out the financial interactions between suspicious wallets to provide a clear, undeniable visual representation of the attack.

**Why this priority**: "A picture is worth a thousand words". Highly requested for the final presentation.

**Independent Test**: Can be tested by generating a GraphViz `.dot` file and rendering it to a PNG showing wallet edges.

**Acceptance Scenarios**:

1. **Given** a list of transactions between clustered wallets, **When** I run the graph generation script, **Then** a visual chart linking the wallets and the target Polymarket contract is produced.

---

### User Story 3 - Final Case Study Report Generation (Priority: P1)

As a security researcher, I want to consolidate the transaction trace, funding analysis, external event validation, and algorithm alerts into a final, comprehensive Markdown Case Study report.

**Why this priority**: This is the primary deliverable for Milestone 3 (Final Integration).

**Independent Test**: Can be tested by reviewing the final `case_study_00X.md` file against the project rubric.

**Acceptance Scenarios**:

1. **Given** all collected forensic evidence, **When** I compile the report, **Then** it clearly argues whether an event was an organic market shift or a malicious Sybil/Whale manipulation.

---

### User Story 4 - Individual Evidence Pack Submission (Priority: P1)

As a security researcher (Member D), I want to compile all Milestone 2 and Milestone 3 deliverables into `forensics/Individual-Evidence-Pack-Milestone3.md` as a submission index so that I can submit one complete, auditable package to the instructor without duplicating report content.

**Why this priority**: This is the final grading-facing artifact that proves completion quality and traceability.

**Independent Test**: Can be tested by reviewing `forensics/Individual-Evidence-Pack-Milestone3.md` and confirming all required artifacts are linked with status mapping, and that detailed analysis remains in the original case-study/report artifacts.

**Acceptance Scenarios**:

1. **Given** Milestone 2/3 outputs are generated, **When** I build the Evidence Pack, **Then** it includes references to FP report, case studies, and fund-flow diagrams.
2. **Given** evidence details already exist in case-study/report artifacts, **When** I finalize the Evidence Pack, **Then** it links those artifacts and does not duplicate the full analysis tables/content.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST output flagged suspicious addresses from Member C's Sybil detection.
- **FR-002**: Researcher MUST query block explorers (Polygonscan/Etherscan) or the Graph API to pull historical wallet balances and transfers.
- **FR-003**: System MUST provide visualization of the malicious money flow.
- **FR-004**: Final report MUST include at least 3 distinct Case Studies demonstrating varying levels of manipulation.
- **FR-005**: Researcher MUST produce `forensics/Individual-Evidence-Pack-Milestone3.md` as an index-style submission package that references (not duplicates) Milestone 2 and 3 evidence artifacts.

### Key Entities

- **Sybil Cluster**: A group of dynamically generated wallets funded by the same source, behaving uniformly.
- **Fund Flow Graph**: A DAG (Directed Acyclic Graph) showing the path of USDC from source to Polymarket CLOB.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 3 to 5 comprehensive Case Study Markdown reports are generated in the `forensics` folder.
- **SC-002**: At least 1 Case Study identifies a previously unverified or highly suspicious manipulation attempt.
- **SC-003**: Reports include concrete evidence such as Transaction Hashes, timestamp synchronization analysis, and funding source diagrams.
- **SC-004**: `forensics/Individual-Evidence-Pack-Milestone3.md` includes artifact links, per-artifact status mapping, and a final submission checklist, while detailed evidence remains in referenced source reports.

## Assumptions

- Etherscan / Polygonscan API or web interface is available and not rate-limiting the required queries.
- Member C's clustering algorithm has identified at least some candidate wallets to investigate.
