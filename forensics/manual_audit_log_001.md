# PolyWatch Manual Forensic Log

**Case ID**: POLYWATCH-2026-001  
**Auditor**: CHEN Sijie (ID: 59872908)
**Date**: 2026-02-11  
**Status**: 🔴 Confirmed Manipulation  
**Severity**: HIGH  

> ⚠️ **SYNTHETIC CASE NOTICE**: This is a synthetic case constructed for algorithm validation and demonstration purposes. Transaction hashes and wallet addresses are illustrative and do not represent actual on-chain data. The patterns and methodology demonstrated are based on real-world manipulation techniques.

---

## 1. Case Summary

| Field | Value |
|-------|-------|
| Trigger Source | VAS Detection System Alert (VAS = 4.7) |
| Target Market | 2026 NBA Championship - Lakers Win |
| Time Window | 2026-02-10 22:00 UTC ~ 2026-02-11 02:00 UTC |
| Funds Involved | ~$2.3M USDC |
| Related Wallets | 5 (suspected single entity control) |

---

## 2. Transaction Trace

### 2.1 Entry Point Transaction

| Field | Details |
|-------|---------|
| **Transaction Hash** | `0x7a2f8c9d1e3b5a7c4d6e8f0a2b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f6a8b0` |
| **Block Number** | 21,847,291 |
| **Timestamp** | 2026-02-10 22:15:32 UTC |
| **From** | `0xTornadoCash_Withdrawal_Proxy` |
| **To** | `0xSuspect_Wallet_A (0x1a2b...3c4d)` |
| **Value** | 500,000 USDC |

**Etherscan Link**: [View Transaction](https://etherscan.io/tx/0x7a2f8c9d1e3b5a7c4d6e8f0a2b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4f6a8b0) *(Synthetic - Not a real transaction)*

---

### 2.2 Fund Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FUND FLOW ANALYSIS (On-Chain Tracking)               │
└─────────────────────────────────────────────────────────────────────────┘

     ┌──────────────────┐
     │   Tornado Cash   │  ← Mixer (Unknown fund source)
     │   (Sanctioned)   │
     └────────┬─────────┘
              │
              │ 500,000 USDC
              │ Tx: 0x7a2f...
              │ 2026-02-10 22:15 UTC
              ▼
     ┌──────────────────┐
     │  Suspect Wallet  │  ← Initial receiving wallet
     │  0x1a2b...3c4d   │
     └────────┬─────────┘
              │
              │ Split transfers (5 x 100K USDC)
              │ Interval: 3-5 minutes each
              ▼
    ┌─────────┴─────────┐
    │                   │
    ▼                   ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│Wallet B│  │Wallet C│  │Wallet D│  │Wallet E│  │Wallet F│
│0x2b3c..│  │0x3c4d..│  │0x4d5e..│  │0x5e6f..│  │0x6f7a..│
│100K    │  │100K    │  │100K    │  │100K    │  │100K    │
└───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘
    │           │           │           │           │
    │           │           │           │           │
    └───────────┴───────────┴─────┬─────┴───────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │     POLYMARKET CLOB      │
                    │  (Central Limit Order    │
                    │         Book)            │
                    └────────────┬─────────────┘
                                 │
                                 │ High-frequency Lakers Win Token buys
                                 │ - 352 transactions
                                 │ - Total ~$2.1M purchased
                                 │ - Average $5,966 per trade
                                 │ - Duration: 3.5 hours
                                 ▼
                    ┌──────────────────────────┐
                    │      Price Pump          │
                    │   0.58 → 0.67 (+15.5%)   │
                    └────────────┬─────────────┘
                                 │
                                 │ Profit Taking
                                 │ - Average sell price: $0.65
                                 │ - Estimated profit: ~$180,000
                                 ▼
                    ┌──────────────────────────┐
                    │  Profit consolidated to  │
                    │       Wallet G           │
                    │    0x7a8b...9c0d         │
                    │    ~$2.28M USDC          │
                    └────────────┬─────────────┘
                                 │
                                 │ Tx: 0x9c8d...
                                 │ 2026-02-11 01:45 UTC
                                 ▼
                    ┌──────────────────────────┐
                    │   BINANCE HOT WALLET     │
                    │   0xBinance14...         │
                    │   (Known exchange addr)  │
                    └──────────────────────────┘
                                 │
                                 ▼
                         💰 Funds exited on-chain
                         (Exchange cooperation needed)
```

---

## 3. Key Evidence

### 3.1 Tornado Cash Withdrawal Records

| # | Tx Hash | Amount | Withdrawal Time |
|---|---------|--------|-----------------|
| 1 | `0x7a2f...` | 100,000 USDC | 2026-02-10 22:15 UTC |
| 2 | `0x8b3c...` | 100,000 USDC | 2026-02-10 22:18 UTC |
| 3 | `0x9c4d...` | 100,000 USDC | 2026-02-10 22:22 UTC |
| 4 | `0xa5e6...` | 100,000 USDC | 2026-02-10 22:25 UTC |
| 5 | `0xb6f7...` | 100,000 USDC | 2026-02-10 22:29 UTC |

**Analysis**: 
- 5 withdrawals completed within 14 minutes
- Identical amounts (100K USDC each) → Automated script execution
- Tornado Cash is OFAC-sanctioned protocol → Highly suspicious fund source

### 3.2 Polymarket Trading Behavior Analysis

| Metric | Value | Normal Range | Anomaly Factor |
|--------|-------|--------------|----------------|
| Trade Frequency | 100 trades/hour | 5-15 trades/hour | 🚨 6.7x |
| Average Trade Size | $5,966 | $200-$500 | 🚨 12x |
| Price Impact | +15.5% | <2% | 🚨 7.75x |
| Taker Ratio | 94% taker | ~50% | 🚨 Market Impact |
| Wallets/Volume Ratio | 5 wallets / $2.1M | - | 🚨 Sybil Attack |

### 3.3 Wallet Association Evidence

```
Wallet Clustering Analysis
==========================

  Wallet A ←──┐
  Wallet B ←──┤
  Wallet C ←──┼──── Same Gas Payment Address: 0xGasStation...
  Wallet D ←──┤     (High correlation)
  Wallet E ←──┤
  Wallet F ←──┘

Additional Association Evidence:
- All 5 wallets created: 2026-02-10 21:50-22:00 UTC (within 10 minutes)
- Nonce pattern: Sequential execution, no overlap
- Transaction timestamps: Second-level synchronization → Bot-controlled
```

---

## 4. Violation Assessment

Based on Invariants defined in `specs/threat_model.md`:

| Invariant | Detection Result | Status |
|-----------|------------------|--------|
| **Invariant 1**: Volume-Wallet Consistency | $\frac{\Delta Volume}{\Delta Wallets} = \frac{2.1M}{5} = 420K$ | 🔴 **VIOLATED** (Threshold: 50K) |
| **Invariant 2**: Wallet Activity | 100 trades/hour/wallet >> μ + 3σ | 🔴 **VIOLATED** |
| **Invariant 3**: Fund Loop | Wash_Score = 0.85 >> θ₂ (0.3) | 🔴 **VIOLATED** |
| **VAS Score** | 4.7 > 3.0 | 🔴 **HIGH ALERT** |

---

## 5. Conclusion & Recommendations

### 5.1 Conclusion

This case represents **high-confidence market manipulation** with the following characteristics:

1. **Fund Obfuscation**: Used Tornado Cash to hide fund sources (OFAC-sanctioned protocol)
2. **Sybil Attack**: 5 affiliated wallets operating in coordination to circumvent single-wallet limits
3. **Price Manipulation**: Artificially inflated price through large market orders (+15.5%)
4. **Profit Exit**: Sold at peak, then rapidly transferred funds to CEX

### 5.2 Recommended Actions

| Priority | Action Item | Owner |
|----------|-------------|-------|
| 🔴 P0 | Add 5 involved wallets to monitoring blacklist | Member D |
| 🔴 P0 | Report to Polymarket compliance team | Member A |
| 🟡 P1 | Contact Binance compliance for KYC information | Legal support needed |
| 🟡 P1 | Update Threat Model threshold parameters (based on this case) | Member A + C |
| 🟢 P2 | Add this case as Golden Standard to test dataset | Member C |

---

## 6. Appendix

### 6.1 Involved Wallet List

| Wallet Label | Address | Role |
|--------------|---------|------|
| Wallet A | `0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b` | Primary receiving wallet |
| Wallet B | `0x2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c` | Trading wallet |
| Wallet C | `0x3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d` | Trading wallet |
| Wallet D | `0x4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e` | Trading wallet |
| Wallet E | `0x5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f` | Trading wallet |
| Wallet F | `0x6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a` | Trading wallet |
| Wallet G | `0x7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b` | Profit consolidation wallet |

### 6.2 Reference Transaction Hashes

Full transaction list available at: `data/case_001_transactions.csv`

---

**Auditor Signature**: CHEN Sijie (Member D)
**Audit Date**: 2026-02-13  
**Review Status**: Pending (Awaiting Member A confirmation)