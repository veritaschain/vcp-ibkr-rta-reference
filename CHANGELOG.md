# Changelog

All notable changes to this VCP Evidence Pack will be documented in this file.

## Publication correction — 2026-11-02

- The current verifier reports local consistency only; unauthenticated packs remain `INDETERMINATE`, and observed mismatches are `INVALID`. Earlier compliance and production claims below are historical, not current findings.
- Preserve the original file manifest under `archive/` and regenerate the current checksum inventory after the verifier/README repair. Neither manifest authenticates origin or establishes conformity.
- Mark current dataset/key distribution metadata as demonstration use with unverified origin and custody; retain exact original metadata in `archive/`. Unknown synthetic origin is `null`, not a new assertion of synthetic generation.

## [1.1.0] - 2025-01-06

### Added
- Full VCP v1.1 specification compliance
- Interactive Brokers FIX 4.2 integration
- Gold Tier conformance level with enhanced requirements
- SEC Rule 17a-4 / FINRA Rule 4511 regulatory alignment
- Microsecond timestamp precision (Gold Tier)
- NTP_SYNC clock synchronization requirement
- Signature verification requirement flag
- IBKR-specific FIX extensions support
  - Smart Routing (IBKR SMART)
  - Native algorithms (IBKR_ADAPTIVE, IBKR_VWAP)
  - Per-share commission model
- Five trading scenarios demonstrating complete order lifecycle
- Event certificates for ORD, ACK, EXE, REJ events
- Complete FIX Tag → VCP Field mapping documentation
- GDPR/Crypto-Shredding readiness notes

### Changed
- Upgraded from Silver to Gold conformance tier
- Enhanced PolicyIdentification with SignatureVerificationRequired
- Improved Governance.FIXCorrelation structure
- More detailed regulatory context in metadata

### Technical
- 26 VCP events including SIG events
- 18 FIX 4.2 messages
- RFC 6962 Merkle tree with full inclusion proofs
- TSA external anchor (production-grade)
- SHA-256 hash algorithm
- Ed25519 signature algorithm (demo keys)

## [1.0.0] - 2025-01-01

### Initial Release
- VCP v1.0 specification compliance
- Basic FIX 4.4 support
- Silver Tier conformance

---

*VeritasChain Standards Organization (VSO)*
