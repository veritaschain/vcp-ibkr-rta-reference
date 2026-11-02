#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local consistency checks for a legacy VCP evidence pack.

This verifier does NOT implement signature verification, trusted signer/key
binding, or external TSA/blockchain receipt validation. It cannot return VALID.
Matching local hashes are not proof of provenance, production use or conformity.

License: Apache 2.0
Copyright (c) 2025 VeritasChain Standards Organization
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


VALID = "VALID"
INVALID = "INVALID"
INDETERMINATE = "INDETERMINATE"
HEX_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")


@dataclass
class VerificationResult:
    status: str
    local_checks_passed: bool
    messages: List[str]

    def __bool__(self) -> bool:
        return self.status == VALID


def canonicalize_json(obj: Any) -> str:
    """Preserve this pack's legacy JSON encoding; not a general RFC 8785 JCS."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def compute_sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def compute_event_hash(event: dict) -> str:
    header = {k: v for k, v in event['Header'].items() if k != 'EventHash'}
    payload = {k: v for k, v in event.items() if k != 'Header'}
    return compute_sha256(canonicalize_json(header) + canonicalize_json(payload))


def _hash(value: Any) -> str:
    if not isinstance(value, str) or not HEX_HASH.fullmatch(value):
        raise ValueError('expected a 32-byte hexadecimal hash')
    return value


def rfc6962_leaf_hash(data: str) -> str:
    return hashlib.sha256(b'\x00' + bytes.fromhex(_hash(data))).hexdigest()


def rfc6962_node_hash(left: str, right: str) -> str:
    return hashlib.sha256(b'\x01' + bytes.fromhex(_hash(left)) +
                          bytes.fromhex(_hash(right))).hexdigest()


def build_merkle_tree(hashes: List[str]) -> str:
    if not hashes:
        return compute_sha256('')
    nodes = [rfc6962_leaf_hash(h) for h in hashes]
    while len(nodes) > 1:
        nodes = [rfc6962_node_hash(nodes[i], nodes[i + 1])
                 if i + 1 < len(nodes) else nodes[i]
                 for i in range(0, len(nodes), 2)]
    return nodes[0]


def verify_inclusion_proof(event_hash: str, proof: List[dict], merkle_root: str,
                           leaf_index: Optional[int] = None,
                           tree_size: Optional[int] = None) -> bool:
    """Check a local path. Pack checks also bind ID/hash/index/root to its batch.

    Legacy three-argument calls check only the hash path, not tree geometry or
    authentication. When index/size are supplied, both must be valid integers.
    """
    try:
        current = rfc6962_leaf_hash(event_hash)
        _hash(merkle_root)
        if not isinstance(proof, list):
            return False
        positions = None
        if leaf_index is not None or tree_size is not None:
            if (type(leaf_index) is not int or type(tree_size) is not int or
                    tree_size < 1 or not 0 <= leaf_index < tree_size):
                return False
            positions = []
            index, size = leaf_index, tree_size
            while size > 1:
                if index % 2:
                    positions.append('left')
                elif index + 1 < size:
                    positions.append('right')
                index, size = index // 2, (size + 1) // 2
            if len(positions) != len(proof):
                return False
        for i, step in enumerate(proof):
            position = step['position']
            if position not in ('left', 'right'):
                return False
            if positions is not None and position != positions[i]:
                return False
            current = (rfc6962_node_hash(step['hash'], current) if position == 'left'
                       else rfc6962_node_hash(current, step['hash']))
        return current == merkle_root
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def verify_v1_1_compliance(events_data: dict, events: List[dict]) -> Tuple[bool, List[str]]:
    """Compatibility API: declarations cannot establish VCP conformity."""
    return False, ['VCP conformity: INDETERMINATE; declaration fields are not '
                   'signature, trusted-key or external-anchor verification.']


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON member: ' + key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError('non-finite JSON number: ' + value)


def _inspect(evidence_dir: Path) -> VerificationResult:
    errors, gaps, messages = [], [], ['Legacy VCP evidence pack — local consistency only']
    data: Dict[str, list] = {}
    for name in ('events', 'batches', 'anchors'):
        try:
            with (evidence_dir / (name + '.json')).open(encoding='utf-8') as source:
                doc = json.load(source, object_pairs_hook=_unique_object,
                                parse_constant=_reject_constant)
            if not isinstance(doc, dict):
                raise ValueError('top-level JSON must be an object')
            values = doc.get(name, [])
            if not isinstance(values, list) or any(not isinstance(v, dict) for v in values):
                raise ValueError(name + ' must be an array of objects')
            data[name] = values
            if not values:
                gaps.append('missing or empty ' + name)
        except OSError as exc:
            gaps.append(name + ': evidence unavailable (' + type(exc).__name__ + ')')
            data[name] = []
        except (ValueError, UnicodeError) as exc:
            errors.append(name + ': malformed evidence (' + str(exc) + ')')
            data[name] = []

    events, batches, anchors = (data[name] for name in ('events', 'batches', 'anchors'))
    event_by_id, trading_hashes, control_events = {}, [], []
    previous_hash, previous_time = None, None
    hash_checks = 0
    for i, event in enumerate(events):
        try:
            header = event['Header']
            event_id, event_type = header['EventID'], header['EventType']
            if not isinstance(event_id, str) or not event_id or not isinstance(event_type, str):
                raise ValueError('invalid event ID/type')
            if event_id in event_by_id:
                raise ValueError('duplicate event ID')
            event_by_id[event_id] = event
            stored = _hash(header['EventHash'])
            if header.get('HashAlgo') not in (None, 'SHA256'):
                gaps.append('unsupported event hash algorithm at ' + event_id)
            elif compute_event_hash(event) != stored:
                errors.append('event hash mismatch at ' + event_id)
            else:
                hash_checks += 1
            prev = header.get('PrevHash')
            if i > 0 and prev is not None and _hash(prev) != previous_hash:
                errors.append('hash chain break at ' + event_id)
            previous_hash = stored
            timestamp = header.get('TimestampISO')
            if timestamp is not None:
                instant = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if instant.tzinfo is None:
                    raise ValueError('timestamp lacks timezone')
                if previous_time is not None and instant < previous_time:
                    messages.append('Timeline observation: non-monotonic timestamp at ' + event_id +
                                    '; clock accuracy and chronology requirements are not verified.')
                previous_time = instant
            if event_type in ('VCP_BATCH', 'VCP_ANCHOR'):
                control_events.append(event)
            else:
                trading_hashes.append(stored)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            errors.append('malformed event at index ' + str(i) + ': ' + str(exc))
    messages.append('Event hashes matching the legacy encoding: ' + str(hash_checks) + '/' + str(len(events)))

    batch_by_id, declared_hashes = {}, []
    complete_membership = True
    for i, batch in enumerate(batches):
        try:
            batch_id = batch['BatchID']
            if not isinstance(batch_id, str) or not batch_id or batch_id in batch_by_id:
                raise ValueError('invalid or duplicate batch ID')
            batch_by_id[batch_id] = batch
            hashes = batch.get('EventHashes')
            if not isinstance(hashes, list) or not hashes:
                gaps.append('missing batch event hashes at ' + batch_id)
                complete_membership = False
                continue
            for h in hashes:
                _hash(h)
            declared_hashes.extend(hashes)
            if type(batch.get('EventCount')) is not int or batch['EventCount'] != len(hashes):
                raise ValueError('batch event count mismatch')
            root = _hash(batch['MerkleRoot'])
            if batch.get('MerkleConstruction') not in (None, 'RFC6962'):
                gaps.append('unsupported Merkle construction at ' + batch_id)
                continue
            if build_merkle_tree(hashes) != root:
                errors.append('Merkle root mismatch at ' + batch_id)
            proofs = batch.get('InclusionProofs', [])
            if not isinstance(proofs, list):
                raise ValueError('inclusion proofs must be an array')
            if not proofs:
                gaps.append('no inclusion proofs supplied for ' + batch_id)
            for proof in proofs:
                target = event_by_id.get(proof['EventID'])
                if target is None and not events:
                    gaps.append('proof target cannot be checked without event evidence')
                    continue
                index = proof['LeafIndex']
                if (target is None or type(index) is not int or not 0 <= index < len(hashes) or
                        target['Header']['EventHash'] != proof['EventHash'] or
                        hashes[index] != proof['EventHash'] or proof['MerkleRoot'] != root or
                        type(proof.get('TreeSize', len(hashes))) is not int or
                        proof.get('TreeSize', len(hashes)) != len(hashes) or
                        not verify_inclusion_proof(proof['EventHash'], proof['AuditPath'], root,
                                                   index, len(hashes))):
                    errors.append('inclusion proof is not bound to this event/batch at ' + batch_id)
            messages.append('Local batch checked: ' + batch_id)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            errors.append('malformed batch at index ' + str(i) + ': ' + str(exc))
    if events and batches and complete_membership and declared_hashes != trading_hashes:
        errors.append('batch event hashes do not match the ordered non-control event stream')

    anchor_by_id = {}
    for i, anchor in enumerate(anchors):
        try:
            anchor_id = anchor['AnchorID']
            if not isinstance(anchor_id, str) or not anchor_id or anchor_id in anchor_by_id:
                raise ValueError('invalid or duplicate anchor ID')
            anchor_by_id[anchor_id] = anchor
            root = _hash(anchor['MerkleRoot'])
            batch_ids = anchor.get('BatchIDs', [anchor['BatchID']] if 'BatchID' in anchor else [])
            if not isinstance(batch_ids, list) or not batch_ids:
                gaps.append('anchor has no batch binding: ' + anchor_id)
                continue
            if len(batch_ids) != 1:
                gaps.append('multi-batch anchor interpretation is unsupported: ' + anchor_id)
            for batch_id in batch_ids:
                batch = batch_by_id.get(batch_id)
                if batch is None:
                    (errors if batches else gaps).append('anchor references an unavailable batch: ' + anchor_id)
                elif len(batch_ids) == 1 and root != batch.get('MerkleRoot'):
                    errors.append('anchor Merkle root mismatch: ' + anchor_id)
                elif 'EventCount' in anchor and len(batch_ids) == 1 and (
                        type(anchor['EventCount']) is not int or anchor['EventCount'] != batch.get('EventCount')):
                    errors.append('anchor event count mismatch: ' + anchor_id)
            messages.append('Anchor record inspected locally; external proof NOT VERIFIED: ' + anchor_id)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            errors.append('malformed anchor at index ' + str(i) + ': ' + str(exc))

    for event in control_events:
        try:
            governance = event['Governance']
            is_batch = event['Header']['EventType'] == 'VCP_BATCH'
            record = ((batch_by_id if is_batch else anchor_by_id)
                      .get(governance['BatchID' if is_batch else 'AnchorID']))
            if record is None:
                gaps.append('control event has no corresponding batch/anchor record')
            else:
                for field in ('MerkleRoot', 'EventCount', 'AnchorTarget'):
                    if field in governance and field in record and governance[field] != record[field]:
                        errors.append('control event disagrees with its record: ' + field)
        except (KeyError, TypeError, AttributeError) as exc:
            errors.append('malformed control event: ' + str(exc))

    messages.extend('INVALID: ' + error for error in errors)
    messages.extend('INDETERMINATE: ' + gap for gap in gaps)
    local_passed = bool(events and batches and anchors) and not errors and not gaps
    messages.append('Local consistency: ' + ('PASS (not authenticated)' if local_passed else 'NOT ESTABLISHED'))
    messages.extend([
        'Signature verification: NOT IMPLEMENTED (including signer/key trust and revocation).',
        'External anchor verification: NOT IMPLEMENTED (including TSA signatures, trust chains and message imprints).',
        'No production provenance, clock accuracy, regulatory compliance or VCP conformity is established.',
    ])
    status = INVALID if errors else INDETERMINATE
    messages.append('Overall: ' + status)
    return VerificationResult(status, local_passed, messages)


def verify_evidence_pack_result(evidence_dir: Path) -> VerificationResult:
    """Detailed fail-closed result; authentication is deliberately unavailable."""
    try:
        return _inspect(Path(evidence_dir))
    except Exception as exc:
        # Malformed or unsupported inputs must never fall through to success.
        return VerificationResult(INVALID, False, [
            'Verifier could not safely process evidence: ' + type(exc).__name__,
            'Overall: INVALID',
        ])


def verify_evidence_pack(evidence_dir: Path) -> Tuple[bool, List[str]]:
    """Backward-compatible API. INDETERMINATE and INVALID both return False."""
    result = verify_evidence_pack_result(evidence_dir)
    return bool(result), result.messages


def main(evidence_dir: Optional[Path] = None) -> int:
    result = verify_evidence_pack_result(evidence_dir if evidence_dir is not None else Path(__file__).parent)
    for message in result.messages:
        print(message)
    return {VALID: 0, INVALID: 1, INDETERMINATE: 2}[result.status]


if __name__ == '__main__':
    raise SystemExit(main())
