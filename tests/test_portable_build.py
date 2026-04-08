from datetime import date
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import portable_build


class BuildTargetTests(unittest.TestCase):
    def test_default_targets_include_chrome_and_chromium(self):
        targets = portable_build.get_default_targets()
        self.assertEqual(
            [target.output_name for target in targets], ["Chrome", "Chromium"]
        )


class ChromeResponseParsingTests(unittest.TestCase):
    def test_parse_chrome_update_response_returns_version_and_download_url(self):
        xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <app>
    <updatecheck status="ok">
      <urls>
        <url codebase="https://dl.google.com/dl/chrome/install/" />
      </urls>
      <manifest version="135.0.7049.42">
        <actions>
          <action run="chrome.7z.exe" />
        </actions>
      </manifest>
    </updatecheck>
  </app>
</response>"""

        metadata = portable_build.parse_chrome_update_response(xml_text)

        self.assertEqual(metadata.version, "135.0.7049.42")
        self.assertEqual(
            metadata.download_url,
            "https://dl.google.com/dl/chrome/install/chrome.7z.exe",
        )
        self.assertEqual(metadata.archive_name, "chrome.7z.exe")


class BuildNameTests(unittest.TestCase):
    def test_build_release_name_contains_chrome_and_chromium_versions(self):
        name = portable_build.build_release_name(
            chrome_version="135.0.7049.42",
            chromium_revision="1611271",
            build_date=date(2026, 4, 8),
        )

        self.assertEqual(
            name,
            "Win64_chrome_135.0.7049.42_chromium_1611271_2026-04-08",
        )


class FinalizePortableDirectoryTests(unittest.TestCase):
    def test_finalize_portable_directory_moves_payload_and_copies_injections(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "chrome-win"
            source_dir.mkdir()
            (source_dir / "chrome.exe").write_text("binary", encoding="utf-8")

            version_dll = temp_path / "version.dll"
            version_dll.write_text("dll", encoding="utf-8")
            config_file = temp_path / "chrome++.ini"
            config_file.write_text("ini", encoding="utf-8")

            release_root = temp_path / "build" / "release"
            release_root.mkdir(parents=True)

            output_dir = portable_build.finalize_portable_directory(
                source_dir=source_dir,
                release_root=release_root,
                output_name="Chromium",
                injection_files=[version_dll, config_file],
            )

            self.assertEqual(output_dir, release_root / "Chromium")
            self.assertTrue((output_dir / "chrome.exe").exists())
            self.assertEqual(
                (output_dir / "version.dll").read_text(encoding="utf-8"), "dll"
            )
            self.assertEqual(
                (output_dir / "chrome++.ini").read_text(encoding="utf-8"), "ini"
            )
            self.assertFalse(source_dir.exists())
            self.assertTrue(version_dll.exists())
            self.assertTrue(config_file.exists())

    def test_finalize_portable_directory_requires_source_dir(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            release_root = temp_path / "build" / "release"
            release_root.mkdir(parents=True)
            version_dll = temp_path / "version.dll"
            version_dll.write_text("dll", encoding="utf-8")

            with self.assertRaisesRegex(FileNotFoundError, "source directory"):
                portable_build.finalize_portable_directory(
                    source_dir=temp_path / "missing",
                    release_root=release_root,
                    output_name="Chromium",
                    injection_files=[version_dll],
                )

    def test_finalize_portable_directory_requires_injection_files(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "chrome-win"
            source_dir.mkdir()
            release_root = temp_path / "build" / "release"
            release_root.mkdir(parents=True)

            with self.assertRaisesRegex(FileNotFoundError, "injection file"):
                portable_build.finalize_portable_directory(
                    source_dir=source_dir,
                    release_root=release_root,
                    output_name="Chromium",
                    injection_files=[temp_path / "missing.dll"],
                )


class MainFlowTests(unittest.TestCase):
    def test_main_extracts_nested_chrome_archive_and_writes_build_name(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / "github.env"
            (temp_path / "version.dll").write_text("dll", encoding="utf-8")
            (temp_path / "chrome++.ini").write_text("ini", encoding="utf-8")

            chrome_metadata = portable_build.DownloadMetadata(
                version="135.0.7049.42",
                download_url="https://example.invalid/chrome.7z.exe",
                archive_name="chrome.7z.exe",
            )
            chromium_metadata = portable_build.DownloadMetadata(
                version="1611271",
                download_url="https://example.invalid/chrome-win.zip",
                archive_name="chrome-win.zip",
            )

            def fake_download(_session, metadata, destination):
                destination.write_bytes(metadata.archive_name.encode("utf-8"))

            def fake_extract(_tool_path, archive_path, destination):
                destination.mkdir(parents=True, exist_ok=True)
                if archive_path.name == "chrome.7z.exe":
                    (destination / "chrome.7z").write_text("nested", encoding="utf-8")
                elif archive_path.name == "chrome.7z":
                    chrome_bin = destination / "Chrome-bin"
                    chrome_bin.mkdir(exist_ok=True)
                    (chrome_bin / "chrome.exe").write_text("chrome", encoding="utf-8")
                elif archive_path.name == "chrome-win.zip":
                    chrome_win = destination / "chrome-win"
                    chrome_win.mkdir(exist_ok=True)
                    (chrome_win / "chrome.exe").write_text("chromium", encoding="utf-8")

            with (
                mock.patch.object(
                    portable_build,
                    "fetch_chrome_metadata",
                    return_value=chrome_metadata,
                ),
                mock.patch.object(
                    portable_build,
                    "fetch_chromium_metadata",
                    return_value=chromium_metadata,
                ),
                mock.patch.object(
                    portable_build, "download_file", side_effect=fake_download
                ),
                mock.patch.object(
                    portable_build, "extract_archive", side_effect=fake_extract
                ),
                mock.patch.object(portable_build, "ensure_extractor_ready"),
                mock.patch.dict(os.environ, {"GITHUB_ENV": str(env_file)}, clear=False),
            ):
                portable_build.main(base_dir=temp_path, now=lambda: date(2026, 4, 8))

            self.assertTrue(
                (temp_path / "build" / "release" / "Chrome" / "chrome.exe").exists()
            )
            self.assertTrue(
                (temp_path / "build" / "release" / "Chromium" / "chrome.exe").exists()
            )
            self.assertIn(
                "BUILD_NAME=Win64_chrome_135.0.7049.42_chromium_1611271_2026-04-08",
                env_file.read_text(encoding="utf-8"),
            )

    def test_main_cleans_up_workdirs_when_build_fails(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "version.dll").write_text("dll", encoding="utf-8")
            (temp_path / "chrome++.ini").write_text("ini", encoding="utf-8")

            chrome_metadata = portable_build.DownloadMetadata(
                version="135.0.7049.42",
                download_url="https://example.invalid/chrome.7z.exe",
                archive_name="chrome.7z.exe",
            )

            def fake_download(_session, metadata, destination):
                destination.write_bytes(metadata.archive_name.encode("utf-8"))

            def fake_extract(_tool_path, _archive_path, destination):
                destination.mkdir(parents=True, exist_ok=True)

            with (
                mock.patch.object(
                    portable_build,
                    "fetch_chrome_metadata",
                    return_value=chrome_metadata,
                ),
                mock.patch.object(
                    portable_build,
                    "fetch_chromium_metadata",
                    side_effect=AssertionError("should not continue"),
                ),
                mock.patch.object(
                    portable_build, "download_file", side_effect=fake_download
                ),
                mock.patch.object(
                    portable_build, "extract_archive", side_effect=fake_extract
                ),
                mock.patch.object(portable_build, "ensure_extractor_ready"),
            ):
                with self.assertRaisesRegex(RuntimeError, "Chrome binary directory"):
                    portable_build.main(
                        base_dir=temp_path, now=lambda: date(2026, 4, 8)
                    )

            self.assertFalse((temp_path / "build" / "work" / "chrome").exists())
