# FIX → VCP Field Mapping Reference
## Interactive Brokers FIX 4.2 Integration Guide

---

## Overview

This document defines the mapping between FIX Protocol 4.2 tags (as used by Interactive Brokers) and VCP v1.1 event fields. The mapping ensures complete audit trail capture while preserving IBKR-specific extensions.

---

## FIX 4.2 Standard Header Mapping

| FIX Tag | FIX Name | VCP Field | Notes |
|---------|----------|-----------|-------|
| 8 | BeginString | (Protocol metadata) | `FIX.4.2` |
| 9 | BodyLength | - | Validation only |
| 35 | MsgType | Header.EventType (derived) | See event type mapping |
| 34 | MsgSeqNum | Governance.FIXCorrelation.MsgSeqNum | Sequence tracking |
| 49 | SenderCompID | (Session metadata) | `IBKR_ALGO_CLIENT` |
| 56 | TargetCompID | (Session metadata) | `IBKR` |
| 52 | SendingTime | Header.TimestampISO | Primary timestamp |
| 115 | OnBehalfOfCompID | Trade.RoutingDestination | IBKR Smart Routing |
| 116 | OnBehalfOfSubID | - | Account delegation |
| 128 | DeliverToCompID | - | Routing chain |
| 129 | DeliverToSubID | - | Routing chain |

---

## Event Type Mapping (MsgType → VCP EventType)

| FIX MsgType (35) | FIX Name | VCP EventType | Conditions |
|------------------|----------|---------------|------------|
| D | NewOrderSingle | ORD | Always |
| G | OrderCancelReplaceRequest | MOD | Always |
| F | OrderCancelRequest | CXL | Always |
| 8 | ExecutionReport | ACK | ExecType (150) = 0 |
| 8 | ExecutionReport | EXE | ExecType (150) = 2 |
| 8 | ExecutionReport | PRT | ExecType (150) = 1 |
| 8 | ExecutionReport | MOD | ExecType (150) = 5 |
| 8 | ExecutionReport | CXL | ExecType (150) = 4 |
| 8 | ExecutionReport | REJ | ExecType (150) = 8 |

---

## NewOrderSingle (MsgType = D) Mapping

### Standard Fields

| FIX Tag | FIX Name | VCP Field | Required |
|---------|----------|-----------|----------|
| 11 | ClOrdID | Trade.ClOrdID | Yes |
| 55 | Symbol | Trade.Symbol | Yes |
| 54 | Side | Trade.Side | Yes (1=BUY, 2=SELL) |
| 38 | OrderQty | Trade.Volume | Yes |
| 40 | OrdType | Trade.OrderType | Yes |
| 44 | Price | Trade.Price | Conditional |
| 99 | StopPx | Trade.StopPrice | For stop orders |
| 59 | TimeInForce | Trade.TimeInForce | Optional |
| 60 | TransactTime | (Validation) | Yes |
| 207 | SecurityExchange | Trade.RoutingDestination | IBKR specific |

### IBKR-Specific Extensions

| FIX Tag | FIX Name | VCP Field | Notes |
|---------|----------|-----------|-------|
| 9882 | IBAlgo | Governance.IBKRAlgorithm | IBKR native algos |
| 9883 | IBAlgoParams | Governance.AlgoParameters | Algo configuration |
| 5700 | ClearingAccount | Trade.ClearingInfo | For institutional |

### Side Mapping (Tag 54)

| FIX Value | FIX Meaning | VCP Value |
|-----------|-------------|-----------|
| 1 | Buy | BUY |
| 2 | Sell | SELL |
| 3 | Buy Minus | BUY_MINUS |
| 4 | Sell Plus | SELL_PLUS |
| 5 | Sell Short | SELL_SHORT |
| 6 | Sell Short Exempt | SELL_SHORT_EXEMPT |

### OrdType Mapping (Tag 40)

| FIX Value | FIX Meaning | VCP Value |
|-----------|-------------|-----------|
| 1 | Market | MKT |
| 2 | Limit | LMT |
| 3 | Stop | STP |
| 4 | Stop Limit | STP_LMT |
| K | Market If Touched | MIT |
| P | Pegged | PEG |

### TimeInForce Mapping (Tag 59)

| FIX Value | FIX Meaning | VCP Value |
|-----------|-------------|-----------|
| 0 | Day | DAY |
| 1 | Good Till Cancel | GTC |
| 2 | At the Opening | OPG |
| 3 | Immediate or Cancel | IOC |
| 4 | Fill or Kill | FOK |
| 6 | Good Till Date | GTD |

---

## ExecutionReport (MsgType = 8) Mapping

### Standard Fields

| FIX Tag | FIX Name | VCP Field | Required |
|---------|----------|-----------|----------|
| 37 | OrderID | Trade.BrokerOrderID | Yes |
| 17 | ExecID | Trade.ExecID | Yes |
| 11 | ClOrdID | Trade.ClOrdID | Yes |
| 55 | Symbol | Trade.Symbol | Yes |
| 54 | Side | Trade.Side | Yes |
| 150 | ExecType | (Event type derivation) | Yes |
| 39 | OrdStatus | Trade.OrderStatus | Yes |
| 32 | LastQty | Trade.FillQty | For fills |
| 31 | LastPx | Trade.FillPrice | For fills |
| 151 | LeavesQty | Trade.RemainingQty | Yes |
| 14 | CumQty | Trade.CumulativeQty | Yes |
| 6 | AvgPx | Trade.AvgPrice | Yes |
| 60 | TransactTime | Header.TimestampISO | Yes |

### Commission Fields

| FIX Tag | FIX Name | VCP Field | Notes |
|---------|----------|-----------|-------|
| 12 | Commission | Trade.Commission | Per-share |
| 13 | CommType | Trade.CommissionType | 3 = per share |

### Execution Venue Fields

| FIX Tag | FIX Name | VCP Field | Notes |
|---------|----------|-----------|-------|
| 30 | LastMkt | Trade.ExecutionVenue | Exchange code |
| 207 | SecurityExchange | Trade.RoutingDestination | Original routing |

### ExecType Mapping (Tag 150)

| FIX Value | FIX Meaning | VCP EventType |
|-----------|-------------|---------------|
| 0 | New | ACK |
| 1 | Partial Fill | PRT |
| 2 | Fill | EXE |
| 3 | Done for Day | DFD |
| 4 | Canceled | CXL |
| 5 | Replaced | MOD |
| 6 | Pending Cancel | PCX |
| 7 | Stopped | STP |
| 8 | Rejected | REJ |
| 9 | Suspended | SUS |
| A | Pending New | PND |
| B | Calculated | CAL |
| C | Expired | EXP |
| D | Restated | RST |
| E | Pending Replace | PMD |

### OrdStatus Mapping (Tag 39)

| FIX Value | FIX Meaning | VCP OrderStatus |
|-----------|-------------|-----------------|
| 0 | New | NEW |
| 1 | Partially Filled | PARTIAL |
| 2 | Filled | FILLED |
| 3 | Done for Day | DFD |
| 4 | Canceled | CANCELED |
| 5 | Replaced | REPLACED |
| 6 | Pending Cancel | PENDING_CXL |
| 7 | Stopped | STOPPED |
| 8 | Rejected | REJECTED |
| 9 | Suspended | SUSPENDED |
| A | Pending New | PENDING_NEW |

### Rejection Reason Mapping (Tag 103)

| FIX Value | FIX Meaning | VCP RejectionCode |
|-----------|-------------|-------------------|
| 0 | Broker option | BROKER_OPTION |
| 1 | Unknown symbol | UNKNOWN_SYMBOL |
| 2 | Exchange closed | EXCHANGE_CLOSED |
| 3 | Order exceeds limit | EXCEEDS_LIMIT |
| 4 | Too late to enter | TOO_LATE |
| 5 | Unknown order | UNKNOWN_ORDER |
| 6 | Duplicate order | DUPLICATE |
| 99 | Other | OTHER |

---

## OrderCancelReplaceRequest (MsgType = G) Mapping

| FIX Tag | FIX Name | VCP Field | Notes |
|---------|----------|-----------|-------|
| 41 | OrigClOrdID | Trade.OriginalClOrdID | Original order |
| 11 | ClOrdID | Trade.ClOrdID | New order ID |
| 55 | Symbol | Trade.Symbol | Must match |
| 54 | Side | Trade.Side | Must match |
| 38 | OrderQty | Trade.NewVolume | Modified qty |
| 44 | Price | Trade.NewPrice | Modified price |
| 40 | OrdType | Trade.OrderType | May change |

---

## OrderCancelRequest (MsgType = F) Mapping

| FIX Tag | FIX Name | VCP Field | Notes |
|---------|----------|-----------|-------|
| 41 | OrigClOrdID | Trade.OriginalClOrdID | Order to cancel |
| 11 | ClOrdID | Trade.ClOrdID | Cancel request ID |
| 55 | Symbol | Trade.Symbol | Verification |
| 54 | Side | Trade.Side | Verification |

---

## IBKR Exchange Codes (Tag 207 / Tag 30)

| Code | Exchange | Description |
|------|----------|-------------|
| SMART | IB Smart Routing | Best execution routing |
| NYSE | New York Stock Exchange | Primary listing |
| NASDAQ | NASDAQ | Electronic exchange |
| ARCA | NYSE Arca | Electronic exchange |
| BATS | Cboe BZX | High-frequency venue |
| IEX | IEX Exchange | Anti-HFT exchange |
| ISLAND | NASDAQ | Legacy code |
| DRCTEDGE | Direct Edge | Alternative venue |
| EDGEA | Cboe EDGA | Low-fee venue |
| BYX | Cboe BYX | Maker-taker inverted |

---

## VCP Event Structure Example

### NewOrderSingle → ORD Event

**FIX Message (Raw)**:
```
8=FIX.4.2|35=D|49=IBKR_ALGO_CLIENT|56=IBKR|115=U12345678|
34=1|52=20250106-09:30:00.123|11=IBKR20250106.000001|
55=AAPL|207=SMART|54=1|38=100|44=185.50|40=2|59=0|
60=20250106-09:30:00.123|9882=IBKR_ADAPTIVE|10=001|
```

**VCP Event (JSON)**:
```json
{
  "Header": {
    "Version": "1.1",
    "EventID": "019b91a8-9d69-7a90-6fa7-07fd3f4f967d",
    "EventType": "ORD",
    "TimestampISO": "2025-01-06T09:30:00.123Z",
    "TimestampInt": 1736157000123000,
    "HashAlgo": "SHA256",
    "SignAlgo": "ED25519",
    "ClockSyncStatus": "NTP_SYNC",
    "TimestampPrecision": "MICROSECOND",
    "PrevHash": "...",
    "EventHash": "..."
  },
  "Trade": {
    "Symbol": "AAPL",
    "ClOrdID": "IBKR20250106.000001",
    "Side": "BUY",
    "Volume": 100.0,
    "Price": 185.50,
    "RoutingDestination": "SMART"
  },
  "Governance": {
    "AlgorithmName": "IBKR_ALGO_SUITE",
    "AlgorithmVersion": "2.1.0",
    "DecisionReason": "FIX NewOrderSingle processed",
    "FIXCorrelation": {
      "MsgType": "D",
      "MsgSeqNum": "1",
      "Direction": "OUTBOUND"
    },
    "IBKRAlgorithm": "IBKR_ADAPTIVE"
  },
  "PolicyIdentification": {
    "Version": "1.1",
    "PolicyID": "org.veritaschain:vcp-ibkr-production-v1",
    "ConformanceTier": "GOLD",
    "RegistrationPolicy": {
      "Issuer": "VeritasChain IBKR Production Issuer",
      "PolicyURI": "https://veritaschain.org/policies/ibkr-production-v1"
    },
    "VerificationDepth": {
      "HashChainValidation": true,
      "MerkleProofRequired": true,
      "ExternalAnchorRequired": true,
      "SignatureVerificationRequired": true
    }
  }
}
```

---

## Regulatory Field Requirements

### SEC Rule 17a-4 Compliance Fields

| Requirement | FIX Source | VCP Field |
|-------------|------------|-----------|
| Order ID | Tag 11 | Trade.ClOrdID |
| Symbol | Tag 55 | Trade.Symbol |
| Side | Tag 54 | Trade.Side |
| Quantity | Tag 38 | Trade.Volume |
| Price | Tag 44 | Trade.Price |
| Timestamp | Tag 52/60 | Header.TimestampISO |
| Execution Venue | Tag 30 | Trade.ExecutionVenue |
| Fill Details | Tags 31/32 | Trade.FillPrice/FillQty |

### FINRA Rule 4511 Additional Fields

| Requirement | VCP Field | Source |
|-------------|-----------|--------|
| Account | Trade.AccountID | Session metadata |
| Order Receipt Time | Header.TimestampISO | Tag 52 |
| Execution Time | Trade.ExecutionTimestamp | Tag 60 |
| Routing Decision | Governance.DecisionReason | Algorithm |

---

## Implementation Notes

### Timestamp Handling

1. **Primary Timestamp**: Use Tag 52 (SendingTime) for event timestamp
2. **Transaction Time**: Tag 60 (TransactTime) as secondary reference
3. **Precision**: Convert to microseconds for Gold Tier
4. **Format**: ISO 8601 with 'Z' suffix for UTC

### Price Precision

- IBKR uses up to 6 decimal places for prices
- VCP stores as float64 with full precision
- Commission typically 3 decimal places

### Order ID Correlation

```
IBKR ClOrdID Pattern: IBKR{YYYYMMDD}.{NNNNNN}
Example: IBKR20250106.000001

VCP stores:
- Trade.ClOrdID: Original client order ID
- Trade.BrokerOrderID: IBKR assigned OrderID (Tag 37)
- Trade.ExecID: Execution ID for fills (Tag 17)
```

---

## Transformation Rules

### Rule 1: Side Normalization
```python
def normalize_side(fix_side: str) -> str:
    return "BUY" if fix_side in ["1", "3"] else "SELL"
```

### Rule 2: Timestamp Conversion
```python
def fix_to_iso(fix_ts: str) -> str:
    # Input: "20250106-09:30:00.123"
    # Output: "2025-01-06T09:30:00.123Z"
    return datetime.strptime(fix_ts, "%Y%m%d-%H:%M:%S.%f").isoformat() + "Z"
```

### Rule 3: Event Type Derivation
```python
def derive_event_type(msg_type: str, exec_type: str = None) -> str:
    if msg_type == "D":
        return "ORD"
    elif msg_type == "F":
        return "CXL"
    elif msg_type == "G":
        return "MOD"
    elif msg_type == "8":
        exec_map = {
            "0": "ACK", "1": "PRT", "2": "EXE",
            "4": "CXL", "5": "MOD", "8": "REJ"
        }
        return exec_map.get(exec_type, "UNK")
```

---

*Document Version: 1.0 | VCP v1.1 | Interactive Brokers FIX 4.2*
*Generated by VeritasChain Standards Organization*
