"""Synthetic regressions. No network, real trades, signing keys or TSA calls."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify


def event_digest(event):
    header = {key: value for key, value in event['Header'].items() if key != 'EventHash'}
    payload = {key: value for key, value in event.items() if key != 'Header'}
    encode = lambda data: json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256((encode(header) + encode(payload)).encode()).hexdigest()


def oracle_root(hashes):
    if not hashes:
        return hashlib.sha256(b'').digest()
    if len(hashes) == 1:
        return hashlib.sha256(b'\x00' + bytes.fromhex(hashes[0])).digest()
    split = 1 << ((len(hashes) - 1).bit_length() - 1)
    return hashlib.sha256(b'\x01' + oracle_root(hashes[:split]) + oracle_root(hashes[split:])).digest()


def oracle_path(hashes, index):
    if len(hashes) == 1:
        return []
    split = 1 << ((len(hashes) - 1).bit_length() - 1)
    if index < split:
        return oracle_path(hashes[:split], index) + [{'position': 'right', 'hash': oracle_root(hashes[split:]).hex()}]
    return oracle_path(hashes[split:], index - split) + [{'position': 'left', 'hash': oracle_root(hashes[:split]).hex()}]


def synthetic_pack(broken_chain=False, fake_signatures=False):
    policy = {'PolicyID': 'synthetic-policy', 'ConformanceTier': 'SILVER',
              'RegistrationPolicy': {'Issuer': 'synthetic-issuer'},
              'VerificationDepth': {'HashChainValidation': True, 'MerkleProofRequired': True, 'ExternalAnchorRequired': True}}
    events = []
    for i in range(3):
        event = {'Header': {'EventID': 'synthetic-' + str(i), 'EventType': 'ORD',
                           'TimestampISO': '2026-01-01T00:00:0' + str(i) + 'Z',
                           'HashAlgo': 'SHA256', 'SignAlgo': 'ED25519'},
                 'Payload': {'value': i}, 'PolicyIdentification': copy.deepcopy(policy)}
        if i:
            event['Header']['PrevHash'] = '00' * 32 if broken_chain and i == 1 else events[-1]['Header']['EventHash']
        if fake_signatures:
            event['Signature'] = 'not-a-signature'
        event['Header']['EventHash'] = event_digest(event)
        events.append(event)
    hashes = [e['Header']['EventHash'] for e in events]
    root = oracle_root(hashes).hex()
    batch = {'BatchID': 'synthetic-batch', 'MerkleRoot': root, 'EventCount': len(hashes),
             'MerkleConstruction': 'RFC6962', 'EventHashes': hashes,
             'InclusionProofs': [{'EventID': event['Header']['EventID'], 'EventHash': hashes[i],
                                 'LeafIndex': i, 'TreeSize': len(hashes), 'MerkleRoot': root,
                                 'AuditPath': oracle_path(hashes, i)} for i, event in enumerate(events)]}
    anchor = {'AnchorID': 'synthetic-anchor', 'BatchID': batch['BatchID'], 'MerkleRoot': root,
              'EventCount': len(hashes), 'AnchorTarget': 'TIMESTAMPING_AUTHORITY'}
    anchor_event = {'Header': {'EventID': 'synthetic-anchor-event', 'EventType': 'VCP_ANCHOR',
                               'TimestampISO': '2026-01-01T00:00:04Z', 'HashAlgo': 'SHA256',
                               'SignAlgo': 'ED25519', 'PrevHash': hashes[-1]},
                    'Governance': {'AnchorID': anchor['AnchorID'], 'MerkleRoot': root,
                                   'AnchorTarget': anchor['AnchorTarget']},
                    'PolicyIdentification': copy.deepcopy(policy)}
    anchor_event['Header']['EventHash'] = event_digest(anchor_event)
    events.append(anchor_event)
    return {'events': {'events': events, 'metadata': {'specification': 'VCP v1.1'}, 'policy_identification': policy},
            'batches': {'batches': [batch]}, 'anchors': {'anchors': [anchor]}}


class FailClosedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, pack):
        for name, data in pack.items():
            (self.root / (name + '.json')).write_text(json.dumps(data), encoding='utf-8')

    def result(self, pack):
        self.write(pack)
        return verify.verify_evidence_pack_result(self.root)

    def assert_invalid(self, pack):
        result = self.result(pack)
        self.assertEqual(result.status, verify.INVALID)
        self.assertFalse(result)
        self.assertFalse(result.local_checks_passed)

    def test_locally_consistent_unsigned_pack_is_not_authenticated(self):
        result = self.result(synthetic_pack())
        self.assertEqual(result.status, verify.INDETERMINATE)
        self.assertTrue(result.local_checks_passed)
        self.assertFalse(result)
        accepted, messages = verify.verify_evidence_pack(self.root)
        self.assertFalse(accepted)
        self.assertNotIn('FULLY COMPLIANT', '\n'.join(messages))
        self.assertNotIn('CRYPTOGRAPHICALLY VERIFIED', '\n'.join(messages))

    def test_declarations_never_establish_conformity(self):
        pack = synthetic_pack()
        accepted, _ = verify.verify_v1_1_compliance(pack['events'], pack['events']['events'])
        self.assertFalse(accepted)

    def test_meaningless_signatures_do_not_upgrade_result(self):
        result = self.result(synthetic_pack(fake_signatures=True))
        self.assertEqual(result.status, verify.INDETERMINATE)
        self.assertFalse(result)

    def test_fabricated_tsa_and_success_label_do_not_upgrade_result(self):
        pack = synthetic_pack()
        pack['anchors']['anchors'][0].update({'AnchorProof': 'not-a-timestamp', 'VerificationStatus': 'PASSED'})
        self.assertEqual(self.result(pack).status, verify.INDETERMINATE)

    def test_hash_chain_break_invalidates_otherwise_consistent_hashes(self):
        pack = synthetic_pack(broken_chain=True)
        self.assertTrue(all(event_digest(e) == e['Header']['EventHash'] for e in pack['events']['events']))
        self.assert_invalid(pack)

    def test_event_payload_tampering_is_invalid(self):
        pack = synthetic_pack()
        pack['events']['events'][0]['Payload']['value'] = 'tampered'
        self.assert_invalid(pack)

    def test_inclusion_proof_cannot_select_its_own_event_and_root(self):
        pack = synthetic_pack()
        fake_hash = hashlib.sha256(b'other data').hexdigest()
        pack['batches']['batches'][0]['InclusionProofs'][0].update({
            'EventHash': fake_hash, 'MerkleRoot': oracle_root([fake_hash]).hex(), 'AuditPath': [], 'TreeSize': 1})
        self.assert_invalid(pack)

    def test_wrong_leaf_index_is_invalid(self):
        pack = synthetic_pack()
        pack['batches']['batches'][0]['InclusionProofs'][0]['LeafIndex'] = 1
        self.assert_invalid(pack)

    def test_wrong_tree_size_is_invalid(self):
        pack = synthetic_pack()
        pack['batches']['batches'][0]['InclusionProofs'][0]['TreeSize'] = 4
        self.assert_invalid(pack)

    def test_wrong_proof_direction_is_invalid(self):
        pack = synthetic_pack()
        pack['batches']['batches'][0]['InclusionProofs'][0]['AuditPath'][0]['position'] = 'not-right'
        self.assert_invalid(pack)

    def test_batch_count_mismatch_is_invalid(self):
        pack = synthetic_pack()
        pack['batches']['batches'][0]['EventCount'] = 4
        self.assert_invalid(pack)

    def test_second_batch_is_not_ignored(self):
        pack = synthetic_pack()
        extra = copy.deepcopy(pack['batches']['batches'][0])
        extra.update({'BatchID': 'second-batch', 'MerkleRoot': '00' * 32})
        pack['batches']['batches'].append(extra)
        self.assert_invalid(pack)

    def test_anchor_root_mismatch_is_invalid(self):
        pack = synthetic_pack()
        pack['anchors']['anchors'][0]['MerkleRoot'] = '00' * 32
        self.assert_invalid(pack)

    def test_unknown_anchor_batch_is_invalid(self):
        pack = synthetic_pack()
        pack['anchors']['anchors'][0]['BatchID'] = 'unrelated-batch'
        self.assert_invalid(pack)

    def test_malformed_header_is_invalid_without_escaping(self):
        pack = synthetic_pack()
        pack['events']['events'][0]['Header'] = None
        self.assert_invalid(pack)

    def test_duplicate_event_id_is_invalid(self):
        pack = synthetic_pack()
        pack['events']['events'].append(copy.deepcopy(pack['events']['events'][0]))
        self.assert_invalid(pack)

    def test_malformed_json_is_invalid_without_escaping(self):
        self.write(synthetic_pack())
        (self.root / 'events.json').write_text('{')
        self.assertEqual(verify.verify_evidence_pack_result(self.root).status, verify.INVALID)

    def test_duplicate_json_member_is_invalid(self):
        self.write(synthetic_pack())
        (self.root / 'events.json').write_text('{"events":[],"events":[]}')
        self.assertEqual(verify.verify_evidence_pack_result(self.root).status, verify.INVALID)

    def test_nonfinite_json_number_is_invalid(self):
        self.write(synthetic_pack())
        (self.root / 'events.json').write_text('{"events":[],"unexpected":NaN}')
        self.assertEqual(verify.verify_evidence_pack_result(self.root).status, verify.INVALID)

    def test_missing_evidence_is_indeterminate(self):
        self.assertEqual(verify.verify_evidence_pack_result(self.root).status, verify.INDETERMINATE)

    def test_each_missing_file_is_indeterminate(self):
        for name in ('events', 'batches', 'anchors'):
            with self.subTest(name=name):
                self.write(synthetic_pack())
                (self.root / (name + '.json')).unlink()
                self.assertEqual(verify.verify_evidence_pack_result(self.root).status, verify.INDETERMINATE)

    def test_observed_tampering_remains_invalid_with_missing_anchor(self):
        pack = synthetic_pack()
        pack['events']['events'][0]['Payload']['value'] = 'tampered'
        self.write(pack)
        (self.root / 'anchors.json').unlink()
        self.assertEqual(verify.verify_evidence_pack_result(self.root).status, verify.INVALID)

    def test_empty_evidence_is_indeterminate(self):
        self.assertEqual(self.result({n: {n: []} for n in ('events', 'batches', 'anchors')}).status, verify.INDETERMINATE)

    def test_missing_proofs_is_indeterminate(self):
        pack = synthetic_pack()
        del pack['batches']['batches'][0]['InclusionProofs']
        result = self.result(pack)
        self.assertEqual(result.status, verify.INDETERMINATE)
        self.assertFalse(result.local_checks_passed)

    def test_cli_uses_distinct_nonzero_exit_codes(self):
        self.write(synthetic_pack())
        shutil.copyfile(verify.__file__, self.root / 'verify.py')
        result = subprocess.run([sys.executable, str(self.root / 'verify.py')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Overall: INDETERMINATE', result.stdout)
        pack = synthetic_pack()
        pack['events']['events'][0]['Payload']['value'] = 'tampered'
        self.write(pack)
        result = subprocess.run([sys.executable, str(self.root / 'verify.py')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Overall: INVALID', result.stdout)

    def test_local_merkle_checks_match_independent_recursive_oracle(self):
        for size in range(1, 18):
            hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(size)]
            root = oracle_root(hashes).hex()
            self.assertEqual(verify.build_merkle_tree(hashes), root)
            for i, event_hash in enumerate(hashes):
                self.assertTrue(verify.verify_inclusion_proof(event_hash, oracle_path(hashes, i), root, i, size))
                self.assertFalse(verify.verify_inclusion_proof(event_hash, oracle_path(hashes, i), root, True, size))


if __name__ == '__main__':
    unittest.main()
