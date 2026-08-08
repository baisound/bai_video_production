from pathlib import PureWindowsPath
import hashlib

import pytest

from ai_video_production import (
    AssetRecord,
    AssetType,
    AudioRightsStatus,
    CharacterIdentityProfile,
    CharacterIdentityService,
    CharacterReferenceBundle,
    LogicalPathResolver,
    PathMapping,
    PermissionState,
    ProductError,
    ProfileSnapshot,
    RightsStatus,
    SQLiteProductStore,
)


def make(tmp_path):
    store = SQLiteProductStore(tmp_path / 'db.sqlite3')
    job = store.create_job(ProfileSnapshot.create('char', '1.0', {}).profile_snapshot_id)
    resolver = LogicalPathResolver([
        PathMapping('asset://', tmp_path / 'assets', PureWindowsPath('D:/assets')),
        PathMapping('job://', tmp_path / 'jobs', PureWindowsPath('D:/jobs')),
    ])
    return store, job, resolver


def image_asset(store, job, resolver, name, *, rights=True):
    logical = f'asset://{job.job_id}/source/{name}.png'
    path = resolver.resolve(logical)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = b'png-' + name.encode()
    path.write_bytes(content)
    checksum = 'sha256:' + hashlib.sha256(content).hexdigest()
    asset = AssetRecord(
        job.job_id,
        AssetType.IMAGE,
        logical,
        checksum,
        RightsStatus.OWNED if rights else RightsStatus.UNKNOWN,
        'USER',
        original_name=f'{name}.png',
        commercial_use=PermissionState.ALLOWED if rights else PermissionState.UNKNOWN,
        derivative_allowed=PermissionState.ALLOWED if rights else PermissionState.UNKNOWN,
        reuse_allowed=PermissionState.ALLOWED,
        audio_rights_status=AudioRightsStatus.NOT_APPLICABLE,
    )
    store.register_asset(asset)
    return asset


def profile():
    return CharacterIdentityProfile(
        'hero_01',
        '1.0',
        'Hero',
        'Japanese woman, black bob haircut, blue jacket',
        immutable_traits={'hair': 'black bob', 'eyes': 'brown'},
        forbidden_drift=('hair color', 'jacket color'),
    )


def test_profile_builds_deterministic_identity_and_sheet_prompt():
    p = profile()
    prompt = p.identity_prompt()
    assert 'eyes: brown' in prompt and 'hair: black bob' in prompt
    sheet = p.character_sheet_prompt()
    assert 'front, side, and back turnaround' in sheet


def test_bundle_requires_same_job_image_rights(tmp_path):
    store, job, resolver = make(tmp_path)
    face = image_asset(store, job, resolver, 'face')
    bundle = CharacterReferenceBundle(job.job_id, 'hero_01', '1.0', face.asset_id)
    refs = CharacterIdentityService(store, resolver).validate_bundle(profile(), bundle)
    assert refs[0]['asset_id'] == face.asset_id

    denied = image_asset(store, job, resolver, 'denied', rights=False)
    with pytest.raises(ProductError) as exc:
        CharacterIdentityService(store, resolver).validate_bundle(profile(), CharacterReferenceBundle(job.job_id, 'hero_01', '1.0', denied.asset_id))
    assert exc.value.code == 'ERR_POLICY_CHARACTER_REFERENCE_RIGHTS'


def test_locked_bundle_requires_approval_and_no_duplicate_refs(tmp_path):
    store, job, resolver = make(tmp_path)
    face = image_asset(store, job, resolver, 'face')
    with pytest.raises(ValueError):
        CharacterReferenceBundle(job.job_id, 'hero_01', '1.0', face.asset_id, locked_for_production=True)
    with pytest.raises(ValueError):
        CharacterReferenceBundle(job.job_id, 'hero_01', '1.0', face.asset_id, front_asset_id=face.asset_id)


def test_character_bundle_revalidates_canonical_reference_bytes(tmp_path):
    store, job, resolver = make(tmp_path)
    face = image_asset(store, job, resolver, 'face-tamper')
    path = resolver.resolve(face.logical_uri)
    path.write_bytes(b'tampered')
    with pytest.raises(ProductError) as exc:
        CharacterIdentityService(store, resolver).validate_bundle(
            profile(), CharacterReferenceBundle(job.job_id, 'hero_01', '1.0', face.asset_id)
        )
    assert exc.value.code == 'ERR_INTEGRITY_CHARACTER_REFERENCE_CHECKSUM'
