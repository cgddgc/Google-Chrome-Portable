from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import xml.dom.minidom

import requests


OMAHA_URL = "https://tools.google.com/service/update2"
CHROMIUM_LAST_CHANGE_URL = (
    "https://storage.googleapis.com/chromium-browser-snapshots/Win_x64/LAST_CHANGE"
)
CHROMIUM_DOWNLOAD_TEMPLATE = "https://storage.googleapis.com/chromium-browser-snapshots/Win_x64/{revision}/chrome-win.zip"
REQUEST_TIMEOUT = 60

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


def get_default_targets():
    return [
        BuildTarget(key="chrome", output_name="Chrome"),
        BuildTarget(key="chromium", output_name="Chromium"),
    ]


def parse_chrome_update_response(xml_text):
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


def build_release_name(chrome_version, chromium_revision, build_date):
    return (
        f"Win64_chrome_{chrome_version}_chromium_{chromium_revision}_"
        f"{build_date.strftime('%Y-%m-%d')}"
    )


def finalize_portable_directory(source_dir, release_root, output_name, injection_files):
    source_path = Path(source_dir)
    if not source_path.is_dir():
        raise FileNotFoundError(f"source directory not found: {source_path}")

    injection_paths = [Path(injection_file) for injection_file in injection_files]
    for injection_path in injection_paths:
        if not injection_path.is_file():
            raise FileNotFoundError(f"injection file not found: {injection_path}")

    release_root = Path(release_root)
    release_root.mkdir(parents=True, exist_ok=True)
    output_dir = release_root / output_name
    if output_dir.exists():
        shutil.rmtree(output_dir)

    shutil.move(str(source_path), str(output_dir))
    for injection_path in injection_paths:
        shutil.copy2(str(injection_path), str(output_dir / injection_path.name))
    return output_dir


def fetch_chrome_metadata(session):
    response = session.post(OMAHA_URL, data=OMAHA_REQUEST, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return parse_chrome_update_response(response.text)


def fetch_chromium_metadata(session):
    response = session.get(CHROMIUM_LAST_CHANGE_URL, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    revision = response.text.strip()
    if not revision:
        raise RuntimeError("Chromium revision is empty")
    return DownloadMetadata(
        version=revision,
        download_url=CHROMIUM_DOWNLOAD_TEMPLATE.format(revision=revision),
        archive_name="chrome-win.zip",
    )


def download_file(session, metadata, destination):
    response = session.get(metadata.download_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)


def ensure_extractor_ready(tool_path):
    tool_path = Path(tool_path)
    if not tool_path.is_file():
        raise FileNotFoundError(f"extractor not found: {tool_path}")
    if os.name != "nt":
        current_mode = tool_path.stat().st_mode
        tool_path.chmod(current_mode | 0o111)


def extract_archive(tool_path, archive_path, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(tool_path), "x", str(archive_path), f"-o{destination}", "-y"],
        check=True,
    )


def reset_directory(path):
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_chrome_source_dir(tool_path, archive_path, work_dir):
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


def resolve_chromium_source_dir(tool_path, archive_path, work_dir):
    payload_dir = work_dir / "payload"
    extract_archive(tool_path, archive_path, payload_dir)
    source_dir = payload_dir / "chrome-win"
    if not source_dir.is_dir():
        raise RuntimeError("Chromium binary directory not found")
    return source_dir


def build_target(
    session,
    base_dir,
    tool_path,
    target,
    metadata_fetcher,
    source_resolver,
    injection_files,
):
    release_root = base_dir / "build" / "release"
    work_dir = base_dir / "build" / "work" / target.key
    reset_directory(work_dir)

    try:
        metadata = metadata_fetcher(session)
        archive_path = work_dir / metadata.archive_name
        download_file(session, metadata, archive_path)
        source_dir = source_resolver(tool_path, archive_path, work_dir)
        finalize_portable_directory(
            source_dir=source_dir,
            release_root=release_root,
            output_name=target.output_name,
            injection_files=injection_files,
        )
        return metadata.version
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir)


def write_build_name(build_date, chrome_version, chromium_revision):
    env_path = os.getenv("GITHUB_ENV")
    if not env_path:
        return

    build_name = build_release_name(chrome_version, chromium_revision, build_date)
    with open(env_path, "a", encoding="utf-8") as file:
        file.write(f"BUILD_NAME={build_name}\n")


def main(base_dir=None, now=None):
    base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent
    now = now or (lambda: datetime.now().date())
    tool_path = base_dir / "7zzs"
    injection_files = [base_dir / "version.dll", base_dir / "chrome++.ini"]

    ensure_extractor_ready(tool_path)
    with requests.Session() as session:
        targets = {target.key: target for target in get_default_targets()}
        chrome_version = build_target(
            session=session,
            base_dir=base_dir,
            tool_path=tool_path,
            target=targets["chrome"],
            metadata_fetcher=fetch_chrome_metadata,
            source_resolver=resolve_chrome_source_dir,
            injection_files=injection_files,
        )
        chromium_revision = build_target(
            session=session,
            base_dir=base_dir,
            tool_path=tool_path,
            target=targets["chromium"],
            metadata_fetcher=fetch_chromium_metadata,
            source_resolver=resolve_chromium_source_dir,
            injection_files=injection_files,
        )

    write_build_name(
        build_date=now(),
        chrome_version=chrome_version,
        chromium_revision=chromium_revision,
    )
