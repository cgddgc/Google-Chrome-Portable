from datetime import date
import os
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import portable_build


EXPECTED_COMMAND_LINE = (
    "--silent-debugger-extension-api --test-type --ignore-certificate-errors "
    "--no-first-run --no-default-browser-check"
)


def write_config(path: Path) -> None:
    path.write_text(
        "\r\n".join(
            [
                "[general]",
                "data_dir=",
                "cache_dir=",
                "command_line=",
                "[tabs]",
                "double_click_close=1",
                "keep_last_tab=1",
                "wheel_tab=0",
                "wheel_tab_when_press_rbutton=0",
            ]
        )
        + "\r\n",
        encoding="utf-16",
    )


def pack_fixed_version(version: str) -> tuple[int, int]:
    major, minor, build, patch = (int(part) for part in version.split("."))
    return (major << 16) | minor, (build << 16) | patch


def make_version_info_bytes(product_version: str) -> bytes:
    key = "VS_VERSION_INFO".encode("utf-16le") + b"\x00\x00"
    header = struct.pack("<HHH", 0, 52, 0) + key
    padding = b"\x00" * ((4 - (len(header) % 4)) % 4)
    file_ms, file_ls = pack_fixed_version("1.2.3.4")
    product_ms, product_ls = pack_fixed_version(product_version)
    fixed_info = struct.pack(
        "<13I",
        0xFEEF04BD,
        0x00010000,
        file_ms,
        file_ls,
        product_ms,
        product_ls,
        0x0000003F,
        0,
        0x00040004,
        0x00000001,
        0,
        0,
        0,
    )
    body = header + padding + fixed_info
    return struct.pack("<H", len(body)) + body[2:]


class BuildTargetTests(unittest.TestCase):
    def test_default_targets_include_chrome_and_chromium(self):
        targets = portable_build.get_default_targets()
        self.assertEqual([target.output_name for target in targets], ["Chrome", "Chromium"])


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


class ChromiumMetadataTests(unittest.TestCase):
    def test_fetch_chromium_metadata_uses_latest_win64_snapshot_revision(self):
        response = mock.Mock()
        response.text = "1611271\n"
        response.raise_for_status.return_value = None
        session = mock.Mock()
        session.get.return_value = response

        metadata = portable_build.fetch_chromium_metadata(session)

        self.assertEqual(metadata.version, "1611271")
        self.assertEqual(
            metadata.download_url,
            "https://storage.googleapis.com/chromium-browser-snapshots/Win_x64/1611271/chrome-win.zip",
        )
        self.assertEqual(metadata.archive_name, "chrome-win.zip")

    def test_fetch_chromium_metadata_requires_revision(self):
        response = mock.Mock()
        response.text = "\n"
        response.raise_for_status.return_value = None
        session = mock.Mock()
        session.get.return_value = response

        with self.assertRaisesRegex(RuntimeError, "Chromium revision is empty"):
            portable_build.fetch_chromium_metadata(session)


    def test_fetch_chromium_metadata_requires_numeric_revision(self):
        response = mock.Mock()
        response.text = "not-a-revision\n"
        response.raise_for_status.return_value = None
        session = mock.Mock()
        session.get.return_value = response

        with self.assertRaisesRegex(RuntimeError, "Chromium revision is invalid"):
            portable_build.fetch_chromium_metadata(session)


class WindowsVersionResourceTests(unittest.TestCase):
    def test_read_windows_product_version_from_version_resource(self):
        with TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "chrome.exe"
            executable.write_bytes(
                b"prefix" + make_version_info_bytes("136.0.7103.114") + b"suffix"
            )

            version = portable_build.read_windows_product_version(executable)

        self.assertEqual(version, "136.0.7103.114")

    def test_read_windows_product_version_requires_version_resource(self):
        with TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "chrome.exe"
            executable.write_bytes(b"not a pe version resource")

            with self.assertRaisesRegex(RuntimeError, "version resource"):
                portable_build.read_windows_product_version(executable)


class BuildNameTests(unittest.TestCase):
    def test_build_release_name_contains_chrome_version_and_chromium_revision(self):
        name = portable_build.build_release_name(
            chrome_version="135.0.7049.42",
            chromium_revision="1611271",
            build_date=date(2026, 5, 23),
        )

        self.assertEqual(
            name,
            "Win64_chrome_135.0.7049.42_chromium_1611271_2026-05-23",
        )

    def test_build_artifact_names_contains_chromium_product_version_and_revision(self):
        names = portable_build.build_artifact_names(
            chrome_version="135.0.7049.42",
            chromium_product_version="136.0.7103.114",
            chromium_revision="1611271",
        )

        self.assertEqual(names["chrome"], "Chrome_135.0.7049.42_win64")
        self.assertEqual(
            names["chromium"],
            "Chromium_136.0.7103.114_1611271_win64",
        )


class FinalizePortableDirectoryTests(unittest.TestCase):
    def test_finalize_portable_directory_moves_payload_to_app_and_copies_assets(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "Chrome-bin"
            source_dir.mkdir()
            (source_dir / "chrome.exe").write_text("binary", encoding="utf-8")

            version_dll = temp_path / "version.dll"
            _ = version_dll.write_text("dll", encoding="utf-8")
            config_file = temp_path / "chrome++.ini"
            write_config(config_file)

            release_root = temp_path / "build" / "release"
            release_root.mkdir(parents=True)

            output_dir = portable_build.finalize_portable_directory(
                source_dir=source_dir,
                release_root=release_root,
                output_name="Chrome",
                chrome_plus_assets=portable_build.ChromePlusAssets(
                    version_dll=version_dll,
                    config_file=config_file,
                ),
            )

            self.assertEqual(output_dir, release_root / "Chrome")
            self.assertTrue((output_dir / "App" / "chrome.exe").exists())
            self.assertTrue((output_dir / "Data").is_dir())
            self.assertTrue((output_dir / "Cache").is_dir())
            self.assertEqual(
                (output_dir / "App" / "version.dll").read_text(encoding="utf-8"),
                "dll",
            )
            config_text = (output_dir / "App" / "chrome++.ini").read_text(
                encoding="utf-16"
            )
            self.assertIn(r"data_dir=%app%\..\Data", config_text)
            self.assertIn(r"cache_dir=%app%\..\Cache", config_text)
            self.assertIn(f"command_line={EXPECTED_COMMAND_LINE}", config_text)
            self.assertNotIn("--disable-infobars", config_text)
            self.assertIn("double_click_close=0", config_text)
            self.assertIn("keep_last_tab=0", config_text)
            self.assertIn("wheel_tab=1", config_text)
            self.assertIn("wheel_tab_when_press_rbutton=1", config_text)
            self.assertFalse(source_dir.exists())
            self.assertTrue(version_dll.exists())
            self.assertTrue(config_file.exists())

    def test_finalize_portable_directory_requires_source_dir(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            release_root = temp_path / "build" / "release"
            release_root.mkdir(parents=True)
            version_dll = temp_path / "version.dll"
            _ = version_dll.write_text("dll", encoding="utf-8")
            config_file = temp_path / "chrome++.ini"
            write_config(config_file)

            with self.assertRaisesRegex(FileNotFoundError, "source directory"):
                portable_build.finalize_portable_directory(
                    source_dir=temp_path / "missing",
                    release_root=release_root,
                    output_name="Chrome",
                    chrome_plus_assets=portable_build.ChromePlusAssets(
                        version_dll=version_dll,
                        config_file=config_file,
                    ),
                )

    def test_finalize_portable_directory_requires_injection_files(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "Chrome-bin"
            source_dir.mkdir()
            release_root = temp_path / "build" / "release"
            release_root.mkdir(parents=True)

            with self.assertRaisesRegex(FileNotFoundError, "injection file"):
                portable_build.finalize_portable_directory(
                    source_dir=source_dir,
                    release_root=release_root,
                    output_name="Chrome",
                    chrome_plus_assets=portable_build.ChromePlusAssets(
                        version_dll=temp_path / "missing.dll",
                        config_file=temp_path / "chrome++.ini",
                    ),
                )


class SourceDirectoryTests(unittest.TestCase):
    def test_resolve_chromium_source_dir_uses_chrome_win_directory(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            def fake_extract(_tool_path, _archive_path, destination):
                chrome_win = destination / "chrome-win"
                chrome_win.mkdir(parents=True)
                (chrome_win / "chrome.exe").write_text("chromium", encoding="utf-8")

            with mock.patch.object(portable_build, "extract_archive", side_effect=fake_extract):
                source_dir = portable_build.resolve_chromium_source_dir(
                    tool_path=temp_path / "7zzs",
                    archive_path=temp_path / "chrome-win.zip",
                    work_dir=temp_path / "work",
                )

            self.assertEqual(source_dir, temp_path / "work" / "payload" / "chrome-win")

    def test_resolve_chromium_source_dir_accepts_flat_payload_directory(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            def fake_extract(_tool_path, _archive_path, destination):
                destination.mkdir(parents=True, exist_ok=True)
                (destination / "chrome.exe").write_text("chromium", encoding="utf-8")

            with mock.patch.object(portable_build, "extract_archive", side_effect=fake_extract):
                source_dir = portable_build.resolve_chromium_source_dir(
                    tool_path=temp_path / "7zzs",
                    archive_path=temp_path / "chrome-win.zip",
                    work_dir=temp_path / "work",
                )

            self.assertEqual(source_dir, temp_path / "work" / "payload")


class ChromePlusAssetTests(unittest.TestCase):
    def test_resolve_chrome_plus_assets_uses_local_files_by_default(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            assets = portable_build.resolve_chrome_plus_assets(
                session=mock.Mock(),
                base_dir=temp_path,
                tool_path=temp_path / "7zzs",
                work_root=temp_path / "work",
            )

            self.assertEqual(assets.version_dll, temp_path / "version.dll")
            self.assertEqual(assets.config_file, temp_path / "chrome++.ini")

    def test_resolve_chrome_plus_assets_uses_latest_when_requested(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            expected = portable_build.ChromePlusAssets(
                version_dll=temp_path / "work" / "extract" / "x64" / "App" / "version.dll",
                config_file=temp_path / "work" / "extract" / "x64" / "App" / "chrome++.ini",
                version="1.16.2",
            )

            with (
                mock.patch.dict(os.environ, {"CHROME_PLUS_SOURCE": "latest"}, clear=False),
                mock.patch.object(
                    portable_build,
                    "download_latest_chrome_plus_assets",
                    return_value=expected,
                ) as download_latest,
            ):
                assets = portable_build.resolve_chrome_plus_assets(
                    session=mock.Mock(),
                    base_dir=temp_path,
                    tool_path=temp_path / "7zzs",
                    work_root=temp_path / "work",
                )

            self.assertEqual(assets, expected)
            download_latest.assert_called_once()

    def test_download_latest_chrome_plus_assets_extracts_x64_files(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            release_response = mock.Mock()
            release_response.json.return_value = {
                "tag_name": "1.16.2",
                "assets": [
                    {
                        "name": "Chrome++_v1.16.2_x86_x64_arm64.7z",
                        "url": "https://api.github.test/assets/1",
                    }
                ],
            }
            release_response.raise_for_status.return_value = None
            asset_response = mock.Mock()
            asset_response.content = b"archive"
            asset_response.raise_for_status.return_value = None
            session = mock.Mock()
            session.get.side_effect = [release_response, asset_response]

            def fake_extract(_tool_path, _archive_path, destination):
                app_dir = destination / "x64" / "App"
                app_dir.mkdir(parents=True)
                (app_dir / "version.dll").write_text("dll", encoding="utf-8")
                write_config(app_dir / "chrome++.ini")

            with mock.patch.object(portable_build, "extract_archive", side_effect=fake_extract):
                assets = portable_build.download_latest_chrome_plus_assets(
                    session=session,
                    tool_path=temp_path / "7zzs",
                    work_root=temp_path / "work",
                )

            self.assertEqual(assets.version, "1.16.2")
            self.assertEqual(assets.version_dll.name, "version.dll")
            self.assertEqual(assets.config_file.name, "chrome++.ini")


class MainFlowTests(unittest.TestCase):
    def test_main_extracts_chrome_and_chromium_and_writes_build_name(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / "github.env"
            version_dll = temp_path / "version.dll"
            _ = version_dll.write_text("dll", encoding="utf-8")
            config_file = temp_path / "chrome++.ini"
            write_config(config_file)

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
                    _ = (destination / "chrome.7z").write_text("nested", encoding="utf-8")
                elif archive_path.name == "chrome.7z":
                    chrome_bin = destination / "Chrome-bin"
                    chrome_bin.mkdir(exist_ok=True)
                    _ = (chrome_bin / "chrome.exe").write_text("chrome", encoding="utf-8")
                elif archive_path.name == "chrome-win.zip":
                    chrome_win = destination / "chrome-win"
                    chrome_win.mkdir(exist_ok=True)
                    _ = (chrome_win / "chrome.exe").write_text("chromium", encoding="utf-8")

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
                mock.patch.object(
                    portable_build,
                    "read_windows_product_version",
                    return_value="136.0.7103.114",
                ),
                mock.patch.dict(os.environ, {"GITHUB_ENV": str(env_file)}, clear=False),
            ):
                portable_build.main(base_dir=temp_path, now=lambda: date(2026, 5, 23))

            self.assertTrue(
                (temp_path / "build" / "release" / "Chrome" / "App" / "chrome.exe").exists()
            )
            self.assertTrue(
                (temp_path / "build" / "release" / "Chromium" / "App" / "chrome.exe").exists()
            )
            self.assertTrue(
                (temp_path / "build" / "release" / "Chromium" / "App" / "version.dll").exists()
            )
            chromium_config = (
                temp_path
                / "build"
                / "release"
                / "Chromium"
                / "App"
                / "chrome++.ini"
            ).read_text(encoding="utf-16")
            self.assertIn(f"command_line={EXPECTED_COMMAND_LINE}", chromium_config)
            self.assertNotIn("--disable-infobars", chromium_config)
            self.assertIn(
                "CHROME_ARTIFACT_NAME=Chrome_135.0.7049.42_win64",
                env_file.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "CHROMIUM_ARTIFACT_NAME=Chromium_136.0.7103.114_1611271_win64",
                env_file.read_text(encoding="utf-8"),
            )

    def test_main_cleans_up_workdirs_when_build_fails(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            _ = (temp_path / "version.dll").write_text("dll", encoding="utf-8")
            write_config(temp_path / "chrome++.ini")

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
                    portable_build, "download_file", side_effect=fake_download
                ),
                mock.patch.object(
                    portable_build, "extract_archive", side_effect=fake_extract
                ),
                mock.patch.object(portable_build, "ensure_extractor_ready"),
            ):
                with self.assertRaisesRegex(RuntimeError, "Chrome binary directory"):
                    portable_build.main(
                        base_dir=temp_path, now=lambda: date(2026, 5, 23)
                    )

            self.assertFalse((temp_path / "build" / "work" / "chrome").exists())
            self.assertFalse((temp_path / "build" / "work" / "chrome_plus").exists())


if __name__ == "__main__":
    unittest.main()
