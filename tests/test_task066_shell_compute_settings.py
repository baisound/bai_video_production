from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import inspect
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from ai_video_production.desktop_compute_policy import (
    CompatibilityStatus,
    ComputePreference,
    DesktopComputeProfileStore,
    EffectiveWorkloadRoute,
    WorkloadClass,
)
from ai_video_production.desktop_install_layout import (
    DesktopInstallLayout,
    DesktopInstallLayoutError,
)
from ai_video_production.desktop_shell import ShellApplicationService
from ai_video_production.errors import ProductError
from ai_video_production.task036_shell_ui import Task036ShellBridge
from ai_video_production.task036_shell_v611 import HTML
import ai_video_production.task036_trusted_launcher as trusted_launcher


NODE_TIMEOUT_SECONDS = 5


def _profile_store(tmp_path: Path) -> DesktopComputeProfileStore:
    binary_root = tmp_path / "bin"
    data_root = tmp_path / "data"
    binary_root.mkdir()
    (data_root / "settings").mkdir(parents=True)
    layout = DesktopInstallLayout(
        install_instance_id="bvp-install-0123456789abcdef0123456789abcdef",
        install_scope="PER_USER",
        binary_root=binary_root,
        data_root=data_root,
        task063_descriptor_sha256="sha256:" + "1" * 64,
        layout_sha256="sha256:" + "2" * 64,
        acl_principal_sids=("S-1-5-21-1-2-3-1001",),
    )
    return DesktopComputeProfileStore(layout)


def _planning_cpu_route() -> EffectiveWorkloadRoute:
    return EffectiveWorkloadRoute(
        workload_id="planning.local.ollama",
        workload_class=WorkloadClass.GPU_PREFERRED_CPU_ALLOWED,
        effective_backend="CPU",
        adapter_identity=None,
        reason_code="AUTO_GPU_UNAVAILABLE_CPU_FALLBACK",
        compatibility_status=CompatibilityStatus.PASS,
        cpu_fallback_visible_before_execution=True,
    )


def test_compute_settings_are_fail_closed_when_installed_profile_is_unbound() -> None:
    bridge = Task036ShellBridge(ShellApplicationService(product_version="0.21.0"))
    snapshot = bridge.desktop_compute_settings_snapshot({})
    assert snapshot == {
        "available": False,
        "reason_code": "DESKTOP_COMPUTE_SETTINGS_NOT_BOUND",
        "message_ja": "インストール済み実行環境の情報を確認できないため、実行方法を変更できません。",
        "preference_options": [
            {"value": "AUTO_GPU_FIRST", "label_ja": "自動（GPU優先）"},
            {"value": "GPU_REQUIRED", "label_ja": "GPUのみ"},
            {"value": "CPU_EXPLICIT", "label_ja": "CPUのみ"},
        ],
        "workloads": [],
        "renderer": None,
        "restart_required": False,
        "provider_execution_started": False,
        "workload_execution_started": False,
        "webview_gpu_disable_flag_applied": False,
    }
    with pytest.raises(ProductError) as exc:
        bridge.desktop_compute_settings_update(
            {"revision": 0, "selected_preference": "AUTO_GPU_FIRST"}
        )
    assert exc.value.code == "ERR_TASK066_DESKTOP_COMPUTE_SETTINGS_NOT_BOUND"
    with pytest.raises(ProductError) as broad:
        bridge.desktop_compute_settings_snapshot({"probe": True})
    assert broad.value.code == "ERR_SHELL_BRIDGE_REQUEST_INVALID"


def test_compute_settings_save_preference_and_read_back_without_execution(tmp_path: Path) -> None:
    store = _profile_store(tmp_path)
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=store,
    )
    initial = bridge.desktop_compute_settings_snapshot({})
    assert initial["available"] is True
    assert initial["revision"] == 0
    assert initial["selected_preference"] == "AUTO_GPU_FIRST"
    assert initial["profile_status"] == "DEFAULT_MISSING"
    assert initial["provider_execution_started"] is False
    assert initial["workload_execution_started"] is False
    assert initial["webview_gpu_disable_flag_applied"] is False

    rows = {row["workload_id"]: row for row in initial["workloads"]}
    assert set(rows) == {
        "planning.local.ollama",
        "image.local.comfyui",
        "video.local.generation",
    }
    assert rows["planning.local.ollama"]["enabled"] is False
    assert rows["planning.local.ollama"]["reason_code"] == "CURRENT_BIND_REQUIRED"
    assert rows["image.local.comfyui"]["reason_code"] == "CURRENT_BIND_REQUIRED"
    assert rows["video.local.generation"]["reason_code"] == "DISABLED_UNTIL_IMPLEMENTED"
    renderer = initial["renderer"]
    assert renderer["renderer_id"] == "shell.webview2.renderer"
    assert renderer["preference_applies"] is False
    assert renderer["hardware_acceleration_policy"] == "ENABLED_WHEN_SUPPORTED"

    updated = bridge.desktop_compute_settings_update(
        {"revision": 0, "selected_preference": "CPU_EXPLICIT"}
    )
    assert updated["revision"] == 1
    assert updated["selected_preference"] == "CPU_EXPLICIT"
    assert updated["restart_required"] is True
    assert updated["provider_execution_started"] is False
    assert updated["workload_execution_started"] is False
    assert updated["webview_gpu_disable_flag_applied"] is False

    restarted = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=DesktopComputeProfileStore(store.layout),
    ).desktop_compute_settings_snapshot({})
    assert restarted["profile_status"] == "LOADED"
    assert restarted["revision"] == 1
    assert restarted["selected_preference"] == "CPU_EXPLICIT"
    assert restarted["restart_required"] is False


def test_compute_settings_preserve_or_explicitly_invalidate_seeded_routes(tmp_path: Path) -> None:
    store = _profile_store(tmp_path)
    admitted_route = _planning_cpu_route()
    seeded = store.save(
        selected_preference=ComputePreference.AUTO_GPU_FIRST,
        workload_routes=(admitted_route,),
        expected_revision=0,
    )
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=store,
    )

    same = bridge.desktop_compute_settings_update(
        {
            "revision": seeded.profile.revision,
            "selected_preference": "AUTO_GPU_FIRST",
        }
    )
    assert same["revision"] == 2
    assert store.load().profile.workload_routes == (admitted_route,)

    changed = bridge.desktop_compute_settings_update(
        {"revision": 2, "selected_preference": "GPU_REQUIRED"}
    )
    changed_route = store.load().profile.workload_routes
    assert len(changed_route) == 1
    assert changed_route[0].workload_id == admitted_route.workload_id
    assert changed_route[0].compatibility_status is CompatibilityStatus.BLOCKED
    assert changed_route[0].effective_backend == "DISABLED"
    assert changed_route[0].adapter_identity is None
    assert changed_route[0].reason_code == "PREFERENCE_CHANGED_REBIND_REQUIRED"
    assert changed_route[0].restart_required is True
    changed_row = next(
        row
        for row in changed["workloads"]
        if row["workload_id"] == admitted_route.workload_id
    )
    assert changed_row["enabled"] is False
    assert changed_row["reason_code"] == "PREFERENCE_CHANGED_REBIND_REQUIRED"

    restarted = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=DesktopComputeProfileStore(store.layout),
    ).desktop_compute_settings_snapshot({})
    restarted_row = next(
        row
        for row in restarted["workloads"]
        if row["workload_id"] == admitted_route.workload_id
    )
    assert restarted_row["reason_code"] == "PREFERENCE_CHANGED_REBIND_REQUIRED"


def test_compute_settings_reject_unknown_mode_stale_revision_and_extra_fields(tmp_path: Path) -> None:
    store = _profile_store(tmp_path)
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=store,
    )
    for request in (
        {"revision": 0, "selected_preference": "SILENT_CPU_FALLBACK"},
        {"revision": True, "selected_preference": "AUTO_GPU_FIRST"},
        {"revision": 0, "selected_preference": "AUTO_GPU_FIRST", "execute": True},
    ):
        with pytest.raises(ProductError):
            bridge.desktop_compute_settings_update(request)
    assert not store.path.exists()

    bridge.desktop_compute_settings_update(
        {"revision": 0, "selected_preference": "GPU_REQUIRED"}
    )
    before = store.path.read_bytes()
    with pytest.raises(ProductError) as stale:
        bridge.desktop_compute_settings_update(
            {"revision": 0, "selected_preference": "CPU_EXPLICIT"}
        )
    assert stale.value.code == "ERR_TASK066_DESKTOP_COMPUTE_SETTINGS_STALE"
    assert store.path.read_bytes() == before


def test_compute_settings_bridge_concurrent_same_revision_has_one_winner(tmp_path: Path) -> None:
    store = _profile_store(tmp_path)
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=store,
    )

    def attempt(preference: str) -> str:
        try:
            bridge.desktop_compute_settings_update(
                {"revision": 0, "selected_preference": preference}
            )
            return "PASS"
        except ProductError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["GPU_REQUIRED", "CPU_EXPLICIT"]))

    assert sorted(results) == [
        "ERR_TASK066_DESKTOP_COMPUTE_SETTINGS_STALE",
        "PASS",
    ]
    assert store.load().profile.revision == 1


def test_compute_settings_reject_future_revision_before_route_derivation(
    tmp_path: Path,
) -> None:
    backing = _profile_store(tmp_path)
    winner_route = _planning_cpu_route()

    class InterleavingStore:
        def __init__(self) -> None:
            self.save_calls = 0

        def load(self):
            return backing.load()

        def save(self, **kwargs):
            self.save_calls += 1
            backing.save(
                selected_preference=ComputePreference.AUTO_GPU_FIRST,
                workload_routes=(winner_route,),
                expected_revision=0,
            )
            return backing.save(**kwargs)

    racing = InterleavingStore()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=racing,  # type: ignore[arg-type]
    )
    with pytest.raises(ProductError) as stale:
        bridge.desktop_compute_settings_update(
            {"revision": 1, "selected_preference": "CPU_EXPLICIT"}
        )
    assert stale.value.code == "ERR_TASK066_DESKTOP_COMPUTE_SETTINGS_STALE"
    assert racing.save_calls == 0
    assert backing.load().profile.revision == 0


def test_compute_settings_interleaving_winner_routes_are_not_overwritten(
    tmp_path: Path,
) -> None:
    backing = _profile_store(tmp_path)
    winner_route = _planning_cpu_route()

    class InterleavingStore:
        def load(self):
            return backing.load()

        def save(self, **kwargs):
            if backing.load().profile.revision == 0:
                backing.save(
                    selected_preference=ComputePreference.AUTO_GPU_FIRST,
                    workload_routes=(winner_route,),
                    expected_revision=0,
                )
            return backing.save(**kwargs)

    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=InterleavingStore(),  # type: ignore[arg-type]
    )
    with pytest.raises(ProductError) as stale:
        bridge.desktop_compute_settings_update(
            {"revision": 0, "selected_preference": "CPU_EXPLICIT"}
        )
    assert stale.value.code == "ERR_TASK066_DESKTOP_COMPUTE_SETTINGS_STALE"
    current = backing.load().profile
    assert current.revision == 1
    assert current.workload_routes == (winner_route,)


def test_compute_settings_preserve_rejected_profile_and_do_not_overwrite(tmp_path: Path) -> None:
    store = _profile_store(tmp_path)
    store.path.write_bytes(b'{"schema_version":"corrupt"}\n')
    original = store.path.read_bytes()
    bridge = Task036ShellBridge(
        ShellApplicationService(product_version="0.21.0"),
        desktop_compute_profile_store=store,
    )
    snapshot = bridge.desktop_compute_settings_snapshot({})
    assert snapshot["profile_status"] == "DEFAULT_REJECTED"
    assert snapshot["rejected_source_preserved"] is True
    with pytest.raises(ProductError):
        bridge.desktop_compute_settings_update(
            {"revision": 0, "selected_preference": "AUTO_GPU_FIRST"}
        )
    assert store.path.read_bytes() == original


def test_installed_profile_resolution_is_read_only_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(trusted_launcher.sys, "frozen", False, raising=False)
    assert trusted_launcher._installed_desktop_compute_profile_store() is None

    executable = tmp_path / "BAI Video Production.exe"
    executable.write_bytes(b"exe")
    layout = object()
    sentinel = object()
    observed: list[object] = []
    monkeypatch.setattr(trusted_launcher.sys, "frozen", True, raising=False)
    monkeypatch.setattr(trusted_launcher.sys, "executable", str(executable))
    monkeypatch.setattr(
        trusted_launcher,
        "derive_binary_root",
        lambda path: observed.append(path) or executable.parent,
    )
    monkeypatch.setattr(
        trusted_launcher,
        "resolve_desktop_install_layout",
        lambda root: observed.append(root) or layout,
    )
    monkeypatch.setattr(
        trusted_launcher,
        "DesktopComputeProfileStore",
        lambda value: observed.append(value) or sentinel,
    )
    assert trusted_launcher._installed_desktop_compute_profile_store() is sentinel
    assert observed == [executable, executable.parent, layout]

    monkeypatch.setattr(
        trusted_launcher,
        "resolve_desktop_install_layout",
        lambda _root: (_ for _ in ()).throw(DesktopInstallLayoutError("invalid")),
    )
    assert trusted_launcher._installed_desktop_compute_profile_store() is None


def test_installed_settings_store_is_private_to_normal_native_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "desktop_compute_profile_store" not in inspect.signature(
        trusted_launcher.build_trusted_launch
    ).parameters
    with pytest.raises(TypeError):
        trusted_launcher.build_trusted_launch(  # type: ignore[call-arg]
            object(), desktop_compute_profile_store=object()
        )

    configuration = SimpleNamespace(display_name="安全なProject")
    sentinel_store = object()
    close_calls: list[str] = []
    window_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    start_calls: list[dict[str, object]] = []
    launch = SimpleNamespace(
        configuration=configuration,
        bridge=object(),
        close=lambda: close_calls.append("closed"),
    )
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        trusted_launcher.Task036LaunchConfiguration,
        "load",
        lambda _path: configuration,
    )
    monkeypatch.setattr(
        trusted_launcher,
        "_installed_desktop_compute_profile_store",
        lambda: sentinel_store,
    )

    def build(actual_configuration: object, **kwargs: object) -> object:
        observed["configuration"] = actual_configuration
        observed["kwargs"] = kwargs
        return launch

    monkeypatch.setattr(trusted_launcher, "_build_trusted_launch_impl", build)
    monkeypatch.setitem(
        sys.modules,
        "webview",
        SimpleNamespace(
            create_window=lambda *args, **kwargs: window_calls.append((args, kwargs)),
            start=lambda **kwargs: start_calls.append(kwargs),
        ),
    )

    trusted_launcher.run_trusted_native_shell("ignored.json")

    assert observed == {
        "configuration": configuration,
        "kwargs": {"desktop_compute_profile_store": sentinel_store},
    }
    assert len(window_calls) == 1
    assert start_calls == [{"gui": "edgechromium", "private_mode": True}]
    assert close_calls == ["closed"]


def test_shell_ui_separates_compute_preference_from_webview_renderer() -> None:
    bridge_source = Path(__import__("ai_video_production.task036_shell_ui", fromlist=["x"]).__file__).read_text(
        encoding="utf-8"
    )
    launcher_source = Path(trusted_launcher.__file__).read_text(encoding="utf-8")
    combined = HTML + bridge_source + launcher_source
    for marker in (
        "desktop_compute_settings_snapshot",
        "desktop_compute_settings_update",
        "AI・動画処理の実行方法",
        "自動（GPU優先）",
        "GPUのみ",
        "CPUのみ",
        "実行方法を保存",
        "設定変更は次回起動から適用されます。処理やAIサービスは開始しません。",
        "実行方法を「CPUのみ」にしても画面描画のGPUを無効化しません。",
        "webview_gpu_disable_flag_applied",
    ):
        assert marker in combined
    assert "--disable-gpu" not in HTML
    assert "desktop_compute_profile_store=_installed_desktop_compute_profile_store()" in launcher_source
    assert "def _build_trusted_launch_impl(" in launcher_source


def test_compute_settings_ui_save_is_single_flight_and_reports_readback() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the GF-B Settings behavior contract")
    reason_function = re.search(r"function desktopComputeReasonMessage\([^\r\n]+", HTML)
    renderer = re.search(r"function renderDesktopComputeSettings\([^\r\n]+", HTML)
    assert reason_function is not None
    assert renderer is not None
    completed = subprocess.run(
        [
            node,
            "-e",
            f"""
const assert=require('node:assert/strict');
let desktopComputeSaveInFlight=false,updateCallCount=0,snapshotCallCount=0,releaseCall=null,nextResult=null,latestSnapshot=null,lastArgs=null;
const currentById=new Map(),host={{children:[],append(...items){{this.children.push(...items)}}}};
currentById.set('settingsContent',host);
function $(id){{return currentById.get(id)||null}}
function clear(node){{node.children=[]}}
function element(tag,className,text){{
  const node={{tag,className,textContent:String(text??''),children:[],attributes:{{}},dataset:{{}},disabled:false,type:null,listener:null,append(...items){{this.children.push(...items)}},setAttribute(name,value){{this.attributes[name]=String(value)}},removeAttribute(name){{delete this.attributes[name]}},addEventListener(name,handler){{assert.equal(name,'click');this.listener=handler}}}};
  Object.defineProperty(node,'id',{{get(){{return this._id}},set(value){{this._id=value;currentById.set(value,this)}}}});
  return node;
}}
const document={{createElement(tag){{return element(tag,'','')}}}};
function card(title,text){{const node=element('div','card','');node.title=title;node.text=text;return node}}
async function call(method,args){{if(method==='desktop_compute_settings_snapshot'){{snapshotCallCount+=1;return latestSnapshot}}assert.equal(method,'desktop_compute_settings_update');updateCallCount+=1;lastArgs=args;await new Promise(resolve=>{{releaseCall=resolve}});return nextResult}}
{reason_function.group(0)}
{renderer.group(0)}
function model(overrides={{}}){{return {{
  available:true,revision:0,selected_preference:'AUTO_GPU_FIRST',message_ja:'未設定のため、自動（GPU優先）を使用します。',rejected_source_preserved:false,
  preference_options:[{{value:'AUTO_GPU_FIRST',label_ja:'自動（GPU優先）'}},{{value:'GPU_REQUIRED',label_ja:'GPUのみ'}},{{value:'CPU_EXPLICIT',label_ja:'CPUのみ'}}],
  workloads:[{{workload_id:'planning.local.ollama',label_ja:'企画（Ollama）',workload_class:'GPU_PREFERRED_CPU_ALLOWED',enabled:false,effective_backend:'DISABLED',compatibility_status:'BLOCKED',reason_code:'CURRENT_BIND_REQUIRED',loaded_runtime_versions:[],cpu_fallback_visible_before_execution:false}}],
  renderer:{{renderer_id:'shell.webview2.renderer',preference_applies:false,hardware_acceleration_policy:'ENABLED_WHEN_SUPPORTED',packaged_renderer_observation:{{status:'NOT_CONFIRMED'}}}},
  ...overrides,
}}}}
(async()=>{{
  renderDesktopComputeSettings(model());
  let select=$('desktopComputePreference'),save=$('desktopComputeSaveButton'),feedback=$('desktopComputeSaveStatus');
  assert.equal(select.disabled,false);assert.equal(select.name,'desktop_compute_preference');assert.equal(select.attributes.autocomplete,'off');assert.equal(save.disabled,false);assert.equal(feedback.attributes['aria-live'],'polite');
  select.value='CPU_EXPLICIT';
  nextResult=model({{revision:1,selected_preference:'CPU_EXPLICIT',message_ja:'保存済みの実行方法を読み込みました。',restart_required:true}});
  const first=save.listener(),second=save.listener();
  assert.equal(updateCallCount,1);assert.deepEqual(lastArgs,{{revision:0,selected_preference:'CPU_EXPLICIT'}});
  assert.equal(save.disabled,true);assert.equal(save.attributes['aria-busy'],'true');assert.equal(feedback.textContent,'保存しています…');
  releaseCall();await Promise.all([first,second]);
  assert.equal($('desktopComputeSaveStatus').textContent,'保存しました。次回起動から適用されます。');
  assert.equal($('desktopComputeSaveButton').disabled,false);assert.equal($('desktopComputeSaveButton').attributes['aria-busy'],undefined);

  renderDesktopComputeSettings(model());nextResult=null;latestSnapshot=model({{revision:2,selected_preference:'GPU_REQUIRED',message_ja:'保存済みの実行方法を読み込みました。'}});
  save=$('desktopComputeSaveButton');feedback=$('desktopComputeSaveStatus');
  const failed=save.listener();releaseCall();await failed;
  assert.equal($('desktopComputeSaveStatus').textContent,'保存できませんでした。最新の設定を再読み込みしました。内容を確認してもう一度操作してください。');
  assert.equal($('desktopComputePreference').children.find(item=>item.selected).value,'GPU_REQUIRED');assert.equal(snapshotCallCount,1);
  assert.equal($('desktopComputeSaveButton').disabled,false);

  const before=updateCallCount;
  renderDesktopComputeSettings(model({{rejected_source_preserved:true,message_ja:'元の設定は保持しました。'}}));
  assert.equal($('desktopComputePreference').disabled,true);assert.equal($('desktopComputeSaveButton').disabled,true);
  await $('desktopComputeSaveButton').listener();assert.equal(updateCallCount,before);
  const workloadCard=host.children.find(item=>item.title?.startsWith('企画（Ollama）'));
  assert.doesNotMatch(workloadCard.text,/CURRENT_BIND_REQUIRED/);
  assert.match(workloadCard.children[0].children[1].textContent,/CURRENT_BIND_REQUIRED/);
  console.log('OK');
}})().catch(error=>{{console.error(error);process.exitCode=1}});
""",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=NODE_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OK"
