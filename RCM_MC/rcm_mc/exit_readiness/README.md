# exit_readiness/

Year-prior-to-exit readiness check. Inverse of diligence — instead of "what's wrong here?", asks "what would a buyer's diligence find?".

| File | Purpose |
|------|---------|
| `readiness.py` | Top-level scorer — multi-dimensional readiness (financial / operational / data / regulatory) |
| `equity_story.py` | Auto-generated equity story for the CIM (confidential information memorandum) |
| `packet.py` | Sell-side IC packet — what a strategic / sponsor buyer would build their case on |
| `roadmap.py` | 12-month pre-sale roadmap — what to fix before going to market |
| `target.py` | Target-buyer-set identification + valuation by buyer type |
| `valuators.py` | Multiple-valuator ensemble — DCF, comps, precedent transactions, LBO-back-into |

## When this fires

- **Y-1 of plan**: monthly readiness scoring → roadmap items
- **Q-2 of exit**: equity story drafted, target buyer-set finalized
- **Bake-off**: buyer-side diligence questions auto-anticipated and pre-answered
