from dataclasses import dataclass
from datetime import date, datetime
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable, List, Optional, TypedDict, Union, cast
import xml.dom.minidom

import requests


OMAHA_URL = "https://tools.google.com/service/update2"
CHROME_PLUS_LATEST_RELEASE_URL = "https://api.github.com/repos/Bush2021/chrome_plus/releases/latest"
CHROMIUM_LAST_CHANGE_URL = (
    "https://storage.googleapis.com/chromium-browser-snapshots/Win_x64/LAST_CHANGE"
)
CHROMIUM_DOWNLOAD_TEMPLATE = "https://storage.googleapis.com/chromium-browser-snapshots/Win_x64/{revision}/chrome-win.zip"
REQUEST_TIMEOUT = 60
PROJECT_CONFIG_OVERRIDES = {
    "data_dir": r"%app%\..\Data",
    "cache_dir": r"%app%\..\Cache",
    "command_line": (
        "--silent-debugger-extension-api --test-type --ignore-certificate-errors "
        "--no-first-run --no-default-browser-check"
    ),
    "double_click_close": "0",
    "keep_last_tab": "0",
    "wheel_tab": "1",
    "wheel_tab_when_press_rbutton": "1",
}

OMAHA_REQUEST = """<?xml version="1.0" encoding="UTF-8"?>
<request protocol="3.0" updater="Omaha" updaterversion="1.3.36.112" shell_version="1.3.36.111"
    installsource="update3web-ondemand" dedup="cr" ismachine="0" domainjoined="0">
    <os platform="win" version="10.0.22000.282" arch="x64"/>
    <app appid="{8A69D345-D564-463C-AFF1-A69D9E530F96}" ap="x64-stable-multi-chrome" lang="en-us">
        <updatecheck />
    </app>
</request>"""


@dataclass(frozen=True)
class BuildTarget:
    key: str
    output_name: str


@dataclass(frozen=True)
class DownloadMetadata:
    version: str
    download_url: str
    archive_name: str


@dataclass(frozen=True)
class ChromePlusAssets:
    version_dll: Path
    config_file: Path
    version: Optional[str] = None


class ChromePlusReleaseAsset(TypedDict):
    name: str
    url: str


class ChromePlusRelease(TypedDict):
    tag_name: str
    assets: List[ChromePlusReleaseAsset]


def get_default_targets() -> List[BuildTarget]:
    return [
        BuildTarget(key="chrome", output_name="Chrome"),
        BuildTarget(key="chromium", output_name="Chromium"),
    ]


def parse_chrome_update_response(xml_text: str) -> DownloadMetadata:
    dom = xml.dom.minidom.parseString(xml_text)
    urls = dom.getElementsByTagName("url")
    manifests = dom.getElementsByTagName("manifest")
    actions = dom.getElementsByTagName("action")

    if not urls or not urls[0].getAttribute("codebase"):
        raise ValueError("invalid chrome update response: missing codebase")
    if not manifests or not manifests[0].getAttribute("version"):
        raise ValueError("invalid chrome update response: missing version")
    if not actions or not actions[0].getAttribute("run"):
        raise ValueError("invalid chrome update response: missing archive")

    codebase = urls[0].getAttribute("codebase")
    version = manifests[0].getAttribute("version")
    archive_name = actions[0].getAttribute("run")
    return DownloadMetadata(
        version=version,
        download_url=f"{codebase}{archive_name}",
        archive_name=archive_name,
    )


def fetch_chromium_metadata(session: requests.Session) -> DownloadMetadata:
    response = session.get(CHROMIUM_LAST_CHANGE_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    revision = response.text.strip()
    if not revision:
        raise RuntimeError("Chromium revision is empty")
    if not revision.isdigit():
        raise RuntimeError("Chromium revision is invalid")
    return DownloadMetadata(
        version=revision,
        download_url=CHROMIUM_DOWNLOAD_TEMPLATE.format(revision=revision),
        archive_name="chrome-win.zip",
    )


def build_release_name(chrome_version: str, chromium_revision: str, build_date: date) -> str:
    return (
        f"Win64_chrome_{chrome_version}_chromium_{chromium_revision}_"
        f"{build_date.strftime('%Y-%m-%d')}"
    )


def finalize_portable_directory(
    source_dir: Union[str, Path],
    release_root: Union[str, Path],
    output_name: str,
    chrome_plus_assets: ChromePlusAssets,
) -> Path:
    source_path = Path(source_dir)
    if not source_path.is_dir():
        raise FileNotFoundError(f"source directory not found: {source_path}")

    injection_paths = [chrome_plus_assets.version_dll, chrome_plus_assets.config_file]
    for injection_path in injection_paths:
        if not injection_path.is_file():
            raise FileNotFoundError(f"injection file not found: {injection_path}")

    release_root = Path(release_root)
    release_root.mkdir(parents=True, exist_ok=True)
    output_dir = release_root / output_name
    app_dir = output_dir / "App"
    if output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_path), str(app_dir))
    for injection_path in injection_paths:
        shutil.copy2(str(injection_path), str(app_dir / injection_path.name))
    apply_chrome_plus_config_overrides(app_dir / "chrome++.ini")
    (output_dir / "Data").mkdir(exist_ok=True)
    (output_dir / "Cache").mkdir(exist_ok=True)
    return output_dir


def apply_chrome_plus_config_overrides(config_file: Path) -> None:
    lines = config_file.read_text(encoding="utf-16").splitlines()
    updated_lines = []
    for line in lines:
        key = line.split("=", 1)[0].strip().lower() if "=" in line else ""
        if key in PROJECT_CONFIG_OVERRIDES and not line.lstrip().startswith(";"):
            updated_lines.append(f"{key}={PROJECT_CONFIG_OVERRIDES[key]}")
        else:
            updated_lines.append(line)
    config_file.write_text("\r\n".join(updated_lines) + "\r\n", encoding="utf-16")


def fetch_chrome_metadata(session: requests.Session) -> DownloadMetadata:
    response = session.post(OMAHA_URL, data=OMAHA_REQUEST, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return parse_chrome_update_response(response.text)


def download_file(session: requests.Session, metadata: DownloadMetadata, destination: Path) -> None:
    response = session.get(metadata.download_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)


def ensure_extractor_ready(tool_path: Path) -> None:
    tool_path = Path(tool_path)
    if not tool_path.is_file():
        raise FileNotFoundError(f"extractor not found: {tool_path}")
    if os.name != "nt":
        current_mode = tool_path.stat().st_mode
        tool_path.chmod(current_mode | 0o111)


def extract_archive(tool_path: Path, archive_path: Path, destination: Path) -> None:
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(tool_path), "x", str(archive_path), f"-o{destination}", "-y"],
        check=True,
    )


def reset_directory(path: Path) -> Path:
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_chrome_source_dir(tool_path: Path, archive_path: Path, work_dir: Path) -> Path:
    installer_dir = work_dir / "installer"
    extract_archive(tool_path, archive_path, installer_dir)

    nested_archive = installer_dir / "chrome.7z"
    if nested_archive.is_file():
        payload_dir = work_dir / "payload"
        extract_archive(tool_path, nested_archive, payload_dir)
        source_dir = payload_dir / "Chrome-bin"
    else:
        source_dir = installer_dir / "Chrome-bin"

    if not source_dir.is_dir():
        raise RuntimeError("Chrome binary directory not found")
    return source_dir


def resolve_chromium_source_dir(tool_path: Path, archive_path: Path, work_dir: Path) -> Path:
    payload_dir = work_dir / "payload"
    extract_archive(tool_path, archive_path, payload_dir)
    source_dir = payload_dir / "chrome-win"
    if not source_dir.is_dir() and (payload_dir / "chrome.exe").is_file():
        source_dir = payload_dir
    if not source_dir.is_dir() or not (source_dir / "chrome.exe").is_file():
        raise RuntimeError("Chromium binary directory not found")
    return source_dir


def resolve_local_chrome_plus_assets(base_dir: Path) -> ChromePlusAssets:
    return ChromePlusAssets(
        version_dll=base_dir / "version.dll",
        config_file=base_dir / "chrome++.ini",
    )


def find_chrome_plus_asset(release: ChromePlusRelease) -> ChromePlusReleaseAsset:
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if name.startswith("Chrome++_") and name.endswith("_x86_x64_arm64.7z"):
            return asset
    raise RuntimeError("Chrome++ release asset not found")


def download_latest_chrome_plus_assets(
    session: requests.Session,
    tool_path: Path,
    work_root: Path,
) -> ChromePlusAssets:
    response = session.get(CHROME_PLUS_LATEST_RELEASE_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    release = cast(ChromePlusRelease, response.json())
    asset = find_chrome_plus_asset(release)

    archive_path = work_root / asset["name"]
    asset_response = session.get(
        asset["url"],
        headers={"Accept": "application/octet-stream"},
        timeout=REQUEST_TIMEOUT,
    )
    asset_response.raise_for_status()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(asset_response.content)

    extract_dir = work_root / "extract"
    extract_archive(tool_path, archive_path, extract_dir)
    app_dir = extract_dir / "x64" / "App"
    assets = ChromePlusAssets(
        version_dll=app_dir / "version.dll",
        config_file=app_dir / "chrome++.ini",
        version=release.get("tag_name"),
    )
    if not assets.version_dll.is_file() or not assets.config_file.is_file():
        raise RuntimeError("Chrome++ x64 assets not found")
    return assets


def resolve_chrome_plus_assets(
    session: requests.Session,
    base_dir: Path,
    tool_path: Path,
    work_root: Path,
) -> ChromePlusAssets:
    if os.getenv("CHROME_PLUS_SOURCE", "local").lower() == "latest":
        return download_latest_chrome_plus_assets(session, tool_path, work_root)
    return resolve_local_chrome_plus_assets(base_dir)


def build_target(
    session: requests.Session,
    base_dir: Path,
    tool_path: Path,
    target: BuildTarget,
    chrome_plus_assets: ChromePlusAssets,
) -> str:
    release_root = base_dir / "build" / "release"
    work_dir = base_dir / "build" / "work" / target.key
    reset_directory(work_dir)

    try:
        if target.key == "chrome":
            metadata_fetcher: Callable[[requests.Session], DownloadMetadata] = fetch_chrome_metadata
            source_resolver = resolve_chrome_source_dir
        elif target.key == "chromium":
            metadata_fetcher = fetch_chromium_metadata
            source_resolver = resolve_chromium_source_dir
        else:
            raise ValueError(f"unsupported build target: {target.key}")

        metadata = metadata_fetcher(session)
        archive_path = work_dir / metadata.archive_name
        download_file(session, metadata, archive_path)
        source_dir = source_resolver(tool_path, archive_path, work_dir)
        finalize_portable_directory(
            source_dir=source_dir,
            release_root=release_root,
            output_name=target.output_name,
            chrome_plus_assets=chrome_plus_assets,
        )
        return metadata.version
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir)


def write_build_name(build_date: date, chrome_version: str, chromium_revision: str) -> None:
    env_path = os.getenv("GITHUB_ENV")
    if not env_path:
        return

    build_name = build_release_name(chrome_version, chromium_revision, build_date)
    with open(env_path, "a", encoding="utf-8") as file:
        file.write(f"BUILD_NAME={build_name}\n")


def main(base_dir: Optional[Union[str, Path]] = None, now: Optional[Callable[[], date]] = None) -> None:
    base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent
    now = now or (lambda: datetime.now().date())
    tool_path = base_dir / "7zzs"
    chrome_plus_work_root = reset_directory(base_dir / "build" / "work" / "chrome_plus")
    versions = {}

    ensure_extractor_ready(tool_path)
    try:
        with requests.Session() as session:
            chrome_plus_assets = resolve_chrome_plus_assets(
                session=session,
                base_dir=base_dir,
                tool_path=tool_path,
                work_root=chrome_plus_work_root,
            )
            for target in get_default_targets():
                versions[target.key] = build_target(
                    session=session,
                    base_dir=base_dir,
                    tool_path=tool_path,
                    target=target,
                    chrome_plus_assets=chrome_plus_assets,
                )
    finally:
        if chrome_plus_work_root.exists():
            shutil.rmtree(chrome_plus_work_root)

    write_build_name(
        build_date=now(),
        chrome_version=versions["chrome"],
        chromium_revision=versions["chromium"],
    )
