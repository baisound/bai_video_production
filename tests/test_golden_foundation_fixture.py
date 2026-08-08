import json
from pathlib import Path
from ai_video_production import AssetRecord, AssetType, JobStateService, LogicalPathResolver, PathMapping, ProfileSnapshot, RightsStatus, SQLiteProductStore
from ai_video_production.atomic import AtomicJsonWriter
from ai_video_production.manifest import ManifestEnvelope, Producer
from ai_video_production.schema_contracts import validate_instance

ROOT=Path(__file__).parents[1]

def test_foundation_consumer_fixture(tmp_path):
    ps=ProfileSnapshot.create("dbd-youtube","1.0.0",{"output":"youtube-long"})
    store=SQLiteProductStore(tmp_path/"runtime.db")
    job=store.create_job(ps.profile_snapshot_id)
    state=JobStateService(store).transition(job.job_id,"INGESTING",expected_version=1)
    assert state.state.value=="INGESTING"

    assets_root=tmp_path/"assets"; assets_root.mkdir()
    resolver=LogicalPathResolver([PathMapping("asset://",assets_root),PathMapping("job://",tmp_path/"jobs")])
    logical=f"asset://{job.job_id}/source/gameplay.mp4"
    assert str(resolver.resolve(logical)).startswith(str(assets_root))
    asset=AssetRecord(job.job_id,AssetType.VIDEO,logical,"sha256:"+"1"*64,RightsStatus.OWNED,"USER")
    store.register_asset(asset)

    envelope=ManifestEnvelope.create(schema_id="ai-video.source-manifest",schema_version="1.0.0",production_job_id=job.job_id,
        revision=1,producer=Producer("asset-service","0.1.0"),profile_snapshot_id=ps.profile_snapshot_id,
        payload={"assets":[asset.to_dict()]})
    schema=ROOT/"schemas/canonical-manifest-envelope.schema.json"
    validate_instance(envelope.to_dict(),schema)
    out=tmp_path/"jobs"/job.job_id/"manifests"/"source-manifest.json"
    AtomicJsonWriter.write(out,envelope.to_dict(),validator=lambda v: validate_instance(v,schema))
    loaded=json.loads(out.read_text())
    assert loaded["production_job_id"]==job.job_id
