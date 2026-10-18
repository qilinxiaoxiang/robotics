"""Two pinned source metadata migrations; never a motion acceptance waiver.

Only head geometry consumers may use validated_equivalent_geometry_source().
It returns a proof dictionary on success and raises SourceCompatibilityError on
any unknown source, missing patch, or additional change. It never edits inputs.
"""
from pathlib import Path
import argparse
import copy
import gzip
import hashlib
import json

D = Path(__file__).resolve().parent
G = D.parent
OLD_SHA256 = "f3e39000857868fe9037f979307c7e891cf34810265deb17f0888d2c8a8e51f0"
OLD_VECTOR_FIELD = {"imu_board": [-28, 0, 0]}
NEW_VECTOR_FIELD = {"imu_board": [-28, 0, 0], "imu_clamp": [-28, 0, 0]}
FASTENERS_KEY = "build-pack-20260913/redesign-20260913/assembly-fasteners.json"
OLD_FASTENERS_SHA256 = "89449c084aa7835b4dc9a9012c790444a5a7b07061a25a391325b233b78b1cdc"
NEW_FASTENERS_SHA256 = "1993ce1fb28549e95001ab29c93c258dd8c65f61cf6dee86f225ae9bf3a767da"


class SourceCompatibilityError(ValueError):
    pass


def canonical(value):
    """Retain value types, array order, and every field; ignore JSON whitespace."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def strict_json(value):
    def unique_pairs(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise SourceCompatibilityError(f"Duplicate JSON key: {key}")
            result[key] = item
        return result
    def invalid_constant(value):
        raise SourceCompatibilityError(f"Non-finite JSON number: {value}")
    return json.loads(value, object_pairs_hook=unique_pairs,
                      parse_constant=invalid_constant)


def _operation(data):
    found = [(mi, oi, op) for mi, module in enumerate(data["modules"])
             for oi, op in enumerate(module["operations"])
             if op.get("id") == "imu-01"]
    if len(found) != 1:
        raise SourceCompatibilityError("Expected exactly one imu-01 operation")
    mi, oi, op = found[0]
    if data["modules"][mi]["id"] != "imu":
        raise SourceCompatibilityError("imu-01 moved outside its original module")
    return mi, oi, op


def _validate_documents(old, current):
    mi, oi, op = _operation(old)
    if canonical(op["partApproachVectors"]) != canonical(OLD_VECTOR_FIELD):
        raise SourceCompatibilityError("Pinned old operation does not have declared old vectors")
    ci, co, cop = _operation(current)
    if (mi, oi) != (ci, co):
        raise SourceCompatibilityError("Operation position changed")
    if canonical(cop.get("partApproachVectors")) != canonical(NEW_VECTOR_FIELD):
        raise SourceCompatibilityError("The exact declared IMU patch is absent or altered")
    if old["sourceHashes"].get(FASTENERS_KEY) != OLD_FASTENERS_SHA256:
        raise SourceCompatibilityError("Old fastener source digest is not the pinned value")
    if current["sourceHashes"].get(FASTENERS_KEY) != NEW_FASTENERS_SHA256:
        raise SourceCompatibilityError("Current fastener source digest is not the pinned value")
    expected = copy.deepcopy(old)
    expected["modules"][mi]["operations"][oi]["partApproachVectors"] = NEW_VECTOR_FIELD
    expected["sourceHashes"][FASTENERS_KEY] = NEW_FASTENERS_SHA256
    expected_bytes = canonical(expected)
    current_bytes = canonical(current)
    if expected_bytes != current_bytes:
        raise SourceCompatibilityError("Additional change beyond the two pinned metadata fields")
    # The whole-document comparison above is the actual gate. These independent
    # category digests make the proof readable without weakening that comparison.
    return {
        "allowedFieldPath": f"/modules/{mi}/operations/{oi}/partApproachVectors",
        "operationId": "imu-01",
        "from": OLD_VECTOR_FIELD,
        "to": NEW_VECTOR_FIELD,
        "sourceMetadataMigration": {
            "fieldPath": "/sourceHashes/" + FASTENERS_KEY,
            "from": OLD_FASTENERS_SHA256,
            "to": NEW_FASTENERS_SHA256,
            "purpose": "Canonical rebuild corrects the source digest; all generated parts and screws are unchanged",
        },
        "partsCanonicalSha256": sha(canonical(old["parts"])),
        "screwsCanonicalSha256": sha(canonical(old["screws"])),
        "partsUnchanged": canonical(old["parts"]) == canonical(current["parts"]),
        "screwsUnchanged": canonical(old["screws"]) == canonical(current["screws"]),
        "everyOtherFieldCanonicalBytesUnchanged": True,
        "expectedPatchedDocumentCanonicalSha256": sha(expected_bytes),
        "currentDocumentCanonicalSha256": sha(current_bytes),
    }


def validated_equivalent_geometry_source(expectedOldHash):
    """Return exact lineage proof, or raise; expectedOldHash is not a new allowlist."""
    if expectedOldHash != OLD_SHA256:
        raise SourceCompatibilityError("This helper supports only the pinned original source hash")
    compressed = (D / "source-before.json.gz").read_bytes()
    original = gzip.decompress(compressed)
    if sha(original) != OLD_SHA256:
        raise SourceCompatibilityError("Immutable old snapshot hash mismatch")
    declaration_bytes = (D / "motion-metadata-patch.json").read_bytes()
    declaration = strict_json(declaration_bytes)
    required = {
        "sourceSha256": OLD_SHA256,
        "sourceSnapshot": "non-head-review/source-before.json.gz",
        "canonicalGenerator": "reviewed_motion.py",
        "patches": [{"operationId": "imu-01", "field": "partApproachVectors",
                     "from": OLD_VECTOR_FIELD, "to": NEW_VECTOR_FIELD,
                     "oldEffectiveVectorForImuClamp": [28, 0, 0],
                     "newEffectiveVectorForImuClamp": [-28, 0, 0]}],
        "geometryChanged": False,
        "otherOperationsChanged": False,
    }
    if canonical(declaration) != canonical(required):
        raise SourceCompatibilityError("Patch declaration differs from the pinned migration")
    actual_fasteners = (G.parent / "assembly-fasteners.json").read_bytes()
    if sha(actual_fasteners) != NEW_FASTENERS_SHA256:
        # The whole-design verifier refreshes upstream audit provenance. A fresh
        # canonical generator run must prove its entire output identical except
        # for that one digest before historical geometry evidence can be used.
        import importlib.util
        spec=importlib.util.spec_from_file_location('baseline_refresh_proof',D/'baseline_refresh_proof.py')
        refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)
        refresh.verify(NEW_FASTENERS_SHA256)
    current_bytes = (G / "full-build-data.json").read_bytes()
    proof = _validate_documents(strict_json(original), strict_json(current_bytes))
    proof.update({
        "accepted": True,
        "scope": "Head geometry source lineage only; no motion-path acceptance",
        "originalSha256": sha(original),
        "currentSha256": sha(current_bytes),
        "snapshotGzipSha256": sha(compressed),
        "patchDeclarationSha256": sha(declaration_bytes),
        "actualFastenersSourceSha256": sha(actual_fasteners),
        "validatorSha256": sha(Path(__file__).read_bytes()),
        "motionAcceptanceInherited": False,
    })
    return proof


def self_test():
    """Negative controls use full original content, not a miniature schema."""
    old = strict_json(gzip.decompress((D / "source-before.json.gz").read_bytes()))
    mi, oi, _ = _operation(old)
    current = copy.deepcopy(old)
    current["modules"][mi]["operations"][oi]["partApproachVectors"] = copy.deepcopy(NEW_VECTOR_FIELD)
    current["sourceHashes"][FASTENERS_KEY] = NEW_FASTENERS_SHA256
    _validate_documents(old, current)
    mutations = {
        "unchanged_old_source": lambda d: d["modules"][mi]["operations"][oi].update(partApproachVectors=OLD_VECTOR_FIELD),
        "extra_top_level_field": lambda d: d.update(unapproved=True),
        "part_geometry_or_metadata": lambda d: d["parts"][0].update(unapproved=True),
        "screw_change": lambda d: d["screws"][0].update(unapproved=True),
        "other_operation_change": lambda d: d["modules"][0]["operations"][0].update(unapproved=True),
        "same_imu_other_field": lambda d: d["modules"][mi]["operations"][oi].update(title="Unapproved"),
        "extra_vector": lambda d: d["modules"][mi]["operations"][oi]["partApproachVectors"].update(other=[-28, 0, 0]),
        "wrong_vector_sign": lambda d: d["modules"][mi]["operations"][oi]["partApproachVectors"].update(imu_clamp=[28, 0, 0]),
        "numeric_type_change": lambda d: d["modules"][mi]["operations"][oi]["partApproachVectors"].update(imu_clamp=[-28.0, 0, 0]),
        "source_hash_metadata_change": lambda d: d["sourceHashes"].update(unapproved="0"),
        "old_fasteners_hash": lambda d: d["sourceHashes"].update({FASTENERS_KEY: OLD_FASTENERS_SHA256}),
        "unknown_fasteners_hash": lambda d: d["sourceHashes"].update({FASTENERS_KEY: "0" * 64}),
        "another_existing_source_hash": lambda d: d["sourceHashes"].update({next(k for k in d["sourceHashes"] if k != FASTENERS_KEY): "0" * 64}),
    }
    rejected = []
    for label, mutate in mutations.items():
        candidate = copy.deepcopy(current)
        mutate(candidate)
        try:
            _validate_documents(old, candidate)
        except SourceCompatibilityError:
            rejected.append(label)
        else:
            raise AssertionError(f"Unexpected acceptance: {label}")
    try:
        validated_equivalent_geometry_source("0" * 64)
    except SourceCompatibilityError:
        rejected.append("unknown_expected_source_hash")
    else:
        raise AssertionError("Unknown source hash accepted")
    for label, payload in [("duplicate_json_key", '{"x":1,"x":2}'),
                           ("nonfinite_json_number", '{"x":NaN}')]:
        try:
            strict_json(payload)
        except SourceCompatibilityError:
            rejected.append(label)
        else:
            raise AssertionError(f"Unexpected JSON acceptance: {label}")
    return {"positiveExactPatchPassed": True, "negativeControlsRejected": rejected}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2))
    if args.write_report or not args.self_test:
        proof = validated_equivalent_geometry_source(OLD_SHA256)
        if args.write_report:
            (D / "source-compatibility-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
        print(json.dumps(proof, indent=2))
