from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trivia_editor_windows_packaging_contract_is_present_and_readme_linked():
    batch = (ROOT / 'build-dbd-trivia-editor-exe.bat').read_text(encoding='utf-8')
    spec = (ROOT / 'packaging' / 'task049_trivia_editor.spec').read_text(encoding='utf-8')
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    build_doc = ROOT / 'docs' / 'windows' / 'BUILDING-DBD-TRIVIA-EDITOR-EXE.md'
    usage_doc = ROOT / 'docs' / 'user' / 'DBD-TRIVIA-EDITOR-USAGE.md'

    assert 'packaging\\task049_trivia_editor.spec' in batch
    assert 'BAI DbD Trivia Editor.exe' in batch
    assert 'task049_trivia_editor_windows_entry.py' in spec
    assert build_doc.is_file()
    assert usage_doc.is_file()
    assert 'docs/windows/BUILDING-DBD-TRIVIA-EDITOR-EXE.md' in readme
    assert 'docs/user/DBD-TRIVIA-EDITOR-USAGE.md' in readme
