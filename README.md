# VeritasChain Protocol (VCP) — IBKR-labelled legacy evidence reference

## Current status: authentication and production provenance unverified

This repository preserves an older VCP v1.1-shaped FIX 4.2 evidence pack labelled as an Interactive Brokers integration. The current verifier can inspect local hash/proof relationships. **It cannot authenticate signatures or external anchors and therefore does not establish VCP Gold Tier conformity, production readiness or regulatory compliance.**

Current distribution metadata marks this pack for **demonstration use** and treats production provenance, synthetic origin, conformity and HSM custody as unverified. `synthetic_data: null` means unknown; a placeholder account and contradictory demo-key notes do not prove the origin of every record. The original metadata and key manifest are preserved byte-for-byte under `archive/`; the current annotations do not establish that real IBKR trading occurred or that the pack was wholly generated synthetically.

Previous README claims of an actual HSM/CloudHSM deployment, certified key custody, live capture, SEC/FINRA compliance and independently verified Ed25519 signatures are not substantiated by the checks in this repository and must not be used as current assurances. Naming Interactive Brokers does not imply its endorsement, participation or approval.

The bundled files contain 26 events, with 24 non-control event hashes in one batch. All 26 event hashes and the supplied local Merkle paths match under the legacy encoding. The event timestamps move backwards at three positions; the verifier reports these observations without inventing a new conformance rule or claiming clock accuracy.

## Run the local checks

```bash
python verify.py
```

For the unchanged bundled pack, the current result is:

```text
Local consistency: PASS (not authenticated)
Signature verification: NOT IMPLEMENTED (including signer/key trust and revocation).
External anchor verification: NOT IMPLEMENTED (including TSA signatures, trust chains and message imprints).
Overall: INDETERMINATE
```

| Result | Exit code | Meaning |
|---|---:|---|
| `INVALID` | 1 | An observed hash, chain, membership, proof or record mismatch, or malformed input, was found. |
| `INDETERMINATE` | 2 | No supported mismatch was found, but authenticity remains unverified; required verification is unavailable or evidence is missing. |
| `VALID` | 0 | Reserved for authenticated verification. **This implementation has no path that returns it.** |

Both nonzero results require attention. Do not treat exit code 2 as success.
The compatibility `verify_evidence_pack(path)` API returns `(False, messages)` for both results. `verify_v1_1_compliance(...)` also returns `False`: declaration fields do not prove conformity.

The detailed API exposes the distinction between local checks and authentication:

```python
from pathlib import Path
from verify import verify_evidence_pack_result

result = verify_evidence_pack_result(Path('.'))
print(result.status)               # INDETERMINATE for the bundled pack
print(result.local_checks_passed)  # True only for supported local consistency checks
assert not result                 # Never authenticated by this implementation
```

## What is checked

Only `events.json`, `batches.json` and `anchors.json` are read by the verifier.

- Recompute each supported SHA-256 event hash using the **legacy pack encoding**. This preserves existing evidence bytes and is not a general RFC 8785/JCS implementation.
- Check supplied `PrevHash` links and propagate a chain break to `INVALID`.
- Bind ordered batch membership and declared counts to the non-control event stream, and rebuild each supported Merkle root.
- Bind each supplied inclusion proof to the event ID/hash, batch root, leaf index and batch size; reject wrong directions, wrong paths, and unrelated proofs. A missing proof-level `TreeSize` is derived from the checked batch membership.
- Compare local anchor references, roots and counts with the corresponding batch. Matching an anchor JSON field does **not** validate a timestamp or an external receipt.
- Reject malformed JSON, duplicate JSON members, non-finite JSON numbers, malformed hashes and invalid proof structure. Missing evidence cannot yield success.

These checks describe this legacy file layout. They do not amend a VCP specification, implement all VCP requirements, or prove that the supplied event population includes every real-world event. Multi-batch anchor interpretation and unsupported algorithms remain indeterminate.

## What remains unverified

**No event/signature authentication, trusted signer identity, key revocation, TSA token signature/trust-chain/message-imprint verification, blockchain receipt verification, or external witness check is implemented.** A public key file, `SignAlgo`, `VerificationStatus`, or an anchor target name does not satisfy those checks. Fabricated signature/receipt strings cannot upgrade the overall result to `VALID`.

The verifier does not establish clock accuracy, live-trading origin, broker participation, completeness of original FIX capture, regulatory compliance, certification, production readiness, or suitability for live trading. It does not authenticate `events.jsonl`, source FIX messages, dataset metadata, certificate files, historical or current file manifests, or precomputed reports. See [mapping.md](mapping.md) for the legacy mapping examples; mapping correctness requires separate validation.

## Historical outputs and fixed evidence

`verifier_outputs/`, certificate files and historical assessment documents remain historical artifacts. Their previous success/compliance statements are **not current verifier results**. The original manifest is preserved byte-for-byte at `archive/hash_manifest.pre-2026-11-02.json`; its old README/verifier hashes do not describe the current source. The regenerated `hash_manifest.json` records the current listed file bytes, including the archived original. It is an unsigned local checksum inventory, not provenance or conformity evidence.

No event, batch, anchor, public key, certificate, source message or historical verifier output is regenerated. Current dataset/key metadata is a publication correction with byte-preserved originals in `archive/`; neither is a trusted signer registry. Current file digests describe bytes only. This preserves the evidence under review while withdrawing unsupported distribution assurances. Run the current verifier to obtain its current result; independent authentication still requires a separately reviewed implementation and trust policy.

## Current checksum inventory

After committing source changes, regenerate the listed file checksums with `python tools/update_hash_manifest.py`. Use `--include <path>` for a newly created file before it is tracked. The regression suite checks current hashes/sizes and verifies that the archived original manifest and original evidence bytes remain intact. This does not authenticate any source.

## Regression tests

```bash
python -m unittest discover -s tests -v
```

The tests generate synthetic packs in temporary directories. They cover unsigned/fabricated evidence, real local mismatches, proof substitution and geometry, missing/malformed inputs, distinct nonzero exit codes, and an independent recursive Merkle oracle. No live account, external AI, broker connection or TSA is used.

## License and contact

- Verification script: Apache 2.0, as stated in its source header.
- Existing repository licensing and attribution remain in [LICENSE](LICENSE).
- Technical questions: technical@veritaschain.org
- Standards questions: standards@veritaschain.org

Maintained by **VeritasChain Standards Organization (VSO)**. The organization name does not establish independent certification or formal standards-body adoption. This reference is supplied for investigation and education, with no warranty of compliance or suitability for production.
