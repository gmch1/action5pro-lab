#!/usr/bin/env python3
"""Read-only DJI Osmo Action 5 Pro EDL inspection and backup tool."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Sequence


VERSION = "0.1.0"
READ_ONLY_EDL_COMMANDS = frozenset({"printgpt", "gpt", "rl", "rs"})
DEFAULT_SKIP = (
    "system_a",
    "system_b",
    "emulated",
    "userdata",
    "blackbox",
    "blackbox_upgrade",
    "rawdump",
)
REQUIRED_PARTITIONS = ("devinfo", "abl_a", "abl_b")
KNOWN_LOADER_SHA256 = (
    "b85fb0e651f88f12e3c9b7b56c0f7229449c410f87fc20c6bc35698516383297"
)


class Action5Error(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True)
class Partition:
    label: str
    lun: int
    start_sector: int
    num_sectors: int
    sector_size: int
    filename: str = ""

    @property
    def size_bytes(self) -> int:
        return self.num_sectors * self.sector_size

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "lun": self.lun,
            "start_sector": self.start_sector,
            "num_sectors": self.num_sectors,
            "sector_size": self.sector_size,
            "size_bytes": self.size_bytes,
            "filename": self.filename,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_rawprogram_files(paths: Iterable[Path]) -> list[Partition]:
    partitions: list[Partition] = []
    for path in sorted(paths):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            raise Action5Error(f"无法解析 GPT XML {path}: {exc}") from exc
        for node in root.iter("program"):
            attrs = node.attrib
            label = attrs.get("label", "").strip()
            if not label:
                continue
            # bkerler emits synthetic GPT entries alongside real partitions.
            # BackupGPT uses an expression such as NUM_DISK_SECTORS-5 rather
            # than a concrete sector, and both images are already exported.
            if label in {"PrimaryGPT", "BackupGPT"}:
                continue
            try:
                lun = parse_int(attrs["physical_partition_number"])
                start = parse_int(attrs["start_sector"])
                sectors = parse_int(attrs["num_partition_sectors"])
                sector_size = parse_int(attrs["SECTOR_SIZE_IN_BYTES"])
            except (KeyError, ValueError) as exc:
                raise Action5Error(f"{path} 中 {label!r} 的分区字段不完整") from exc
            partitions.append(
                Partition(
                    label=label,
                    lun=lun,
                    start_sector=start,
                    num_sectors=sectors,
                    sector_size=sector_size,
                    filename=attrs.get("filename", ""),
                )
            )
    unique: dict[tuple[int, str], Partition] = {}
    for partition in partitions:
        unique[(partition.lun, partition.label)] = partition
    return sorted(unique.values(), key=lambda item: (item.lun, item.start_sector))


def parse_active_slots(text: str) -> dict[str, bool]:
    """Best-effort parser; GPT XML itself does not carry Android slot state."""
    found: dict[str, bool] = {}
    patterns = (
        r"(?im)^\s*(?P<name>[A-Za-z0-9_.-]+).*?Active\s*[:=]?\s*(?P<active>True|False)\b",
        r"(?im)^\s*(?P<name>[A-Za-z0-9_.-]+).*?active\s*[:=]\s*(?P<active>yes|no)\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            found[match.group("name")] = match.group("active").lower() in {"true", "yes"}
    return found


def ensure_file(path: Path, description: str) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise Action5Error(f"找不到{description}: {path}")
    return path


def python_for_edl(explicit: str | None, edl_script: Path) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.exists():
            # Keep a virtualenv launcher path intact. Resolving its symlink to the
            # Homebrew/system interpreter discards the virtualenv's site-packages.
            return str(candidate.absolute())
        resolved = shutil.which(explicit)
        if resolved:
            return resolved
        raise Action5Error(f"找不到 Python: {explicit}")
    venv_python = edl_script.parent.parent / ".edl-venv" / "bin" / "python"
    if venv_python.is_file():
        return str(venv_python)
    return sys.executable


def assert_read_only_edl_args(args: Sequence[str]) -> None:
    if not args or args[0] not in READ_ONLY_EDL_COMMANDS:
        command = args[0] if args else "<empty>"
        raise Action5Error(f"内部安全检查拒绝非只读 EDL 命令: {command}")


def run_edl(
    python: str,
    edl_script: Path,
    loader: Path,
    args: Sequence[str],
    log_path: Path,
) -> str:
    assert_read_only_edl_args(args)
    command = [
        python,
        str(edl_script),
        *args,
        "--memory=ufs",
        f"--loader={loader}",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    display = " ".join(subprocess.list2cmdline([part]) for part in command)
    print(f"\n[只读] {display}", flush=True)
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log_path.write_text(result.stdout, encoding="utf-8")
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode != 0:
        raise Action5Error(f"EDL 命令失败（退出码 {result.returncode}），日志：{log_path}")
    return result.stdout


def usb_9008_status() -> tuple[bool | None, str]:
    if platform.system() == "Darwin":
        if not shutil.which("ioreg"):
            return None, "系统没有 ioreg，未检测 USB"
        result = subprocess.run(
            ["ioreg", "-p", "IOUSB", "-l", "-w", "0"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        text = result.stdout.lower()
        present = (
            "qusb_bulk" in text
            or ("\"idvendor\" = 1478" in text and "\"idproduct\" = 36872" in text)
        )
        return present, "检测到 05c6:9008/QUSB_BULK" if present else "未检测到 05c6:9008/QUSB_BULK"
    if platform.system() == "Linux" and shutil.which("lsusb"):
        result = subprocess.run(
            ["lsusb", "-d", "05c6:9008"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        present = result.returncode == 0 and bool(result.stdout.strip())
        return present, "检测到 05c6:9008" if present else "未检测到 05c6:9008"
    return None, "当前系统不支持自动检测 9008"


def doctor(args: argparse.Namespace) -> int:
    edl_script = ensure_file(Path(args.edl_script), "edl.py")
    loader = ensure_file(Path(args.loader), "Firehose loader")
    python = python_for_edl(args.python, edl_script)
    loader_hash = sha256_file(loader)
    usb_present, usb_message = usb_9008_status()
    print(f"action5-edl {VERSION}")
    print(f"Python: {python}")
    print(f"EDL: {edl_script}")
    print(f"Loader: {loader}")
    print(f"Loader SHA-256: {loader_hash}")
    print(f"USB: {usb_message}")
    if loader_hash != KNOWN_LOADER_SHA256:
        print("警告：loader 哈希与 Action 5 Pro 实机教程中的已知值不一致。", file=sys.stderr)
        return 2
    if usb_present is False:
        return 3
    print("预检通过：工具只包含 printgpt/gpt/rl/rs 四种读取操作。")
    return 0


def make_session_dir(base: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    session = base.expanduser().resolve() / f"action5-{stamp}"
    session.mkdir(parents=True, exist_ok=False)
    return session


def scan_device(
    args: argparse.Namespace, session: Path
) -> tuple[list[Partition], dict[str, bool], dict[str, object]]:
    edl_script = ensure_file(Path(args.edl_script), "edl.py")
    loader = ensure_file(Path(args.loader), "Firehose loader")
    loader_hash = sha256_file(loader)
    if loader_hash != KNOWN_LOADER_SHA256 and not args.allow_unknown_loader:
        raise Action5Error(
            "loader 哈希未知，已停止。确认来源后可用 --allow-unknown-loader 仅执行读取。"
        )
    python = python_for_edl(args.python, edl_script)
    logs = session / "logs"
    gpt_dir = session / "gpt"
    gpt_dir.mkdir(parents=True)
    printgpt_output = run_edl(
        python, edl_script, loader, ["printgpt"], logs / "printgpt.log"
    )
    run_edl(
        python,
        edl_script,
        loader,
        ["gpt", str(gpt_dir), "--genxml"],
        logs / "gpt-export.log",
    )
    xml_paths = list(gpt_dir.glob("rawprogram*.xml"))
    if not xml_paths:
        raise Action5Error(f"EDL 未生成 rawprogram XML：{gpt_dir}")
    partitions = parse_rawprogram_files(xml_paths)
    by_name: dict[str, list[Partition]] = {}
    for partition in partitions:
        by_name.setdefault(partition.label, []).append(partition)
    missing = [name for name in REQUIRED_PARTITIONS if name not in by_name]
    if missing:
        raise Action5Error(f"GPT 缺少关键分区：{', '.join(missing)}")
    if len(by_name["devinfo"]) != 1:
        raise Action5Error("GPT 中 devinfo 不唯一，拒绝继续")
    devinfo = by_name["devinfo"][0]
    if devinfo.size_bytes != 4096:
        raise Action5Error(f"devinfo 大小不是 4096 B，而是 {devinfo.size_bytes} B")
    active = parse_active_slots(printgpt_output)
    metadata: dict[str, object] = {
        "schema": 1,
        "created_at": utc_timestamp(),
        "tool_version": VERSION,
        "read_only": True,
        "host": {"system": platform.system(), "release": platform.release()},
        "loader": {"path": str(loader), "sha256": loader_hash},
        "edl": {"script": str(edl_script), "sha256": sha256_file(edl_script)},
        "active_from_printgpt": active,
        "partitions": [partition.as_dict() for partition in partitions],
    }
    (session / "scan.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\n关键分区：")
    for name in (*REQUIRED_PARTITIONS, "userdata"):
        for partition in by_name.get(name, []):
            print(
                f"  {partition.label}: LUN {partition.lun}, start {partition.start_sector}, "
                f"sectors {partition.num_sectors}, bytes {partition.size_bytes}"
            )
    if not active:
        print("警告：未能从文本输出可靠识别活动槽；备份可继续，未来写入不可继续。")
    return partitions, active, metadata


def hash_tree(root: Path, excluded: set[Path] | None = None) -> list[dict[str, object]]:
    excluded = {path.resolve() for path in (excluded or set())}
    records: list[dict[str, object]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.resolve() in excluded:
            continue
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def write_checksums(session: Path, metadata: dict[str, object]) -> None:
    checksum_path = session / "SHA256SUMS"
    manifest_path = session / "manifest.json"
    files = hash_tree(session, {checksum_path, manifest_path})
    checksum_path.write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in files), encoding="utf-8"
    )
    manifest = dict(metadata)
    manifest["completed_at"] = utc_timestamp()
    manifest["files"] = files
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def scan_command(args: argparse.Namespace) -> int:
    session = make_session_dir(Path(args.output))
    print(f"会话目录：{session}")
    partitions, _active, metadata = scan_device(args, session)
    metadata["partition_count"] = len(partitions)
    write_checksums(session, metadata)
    print(f"\n扫描完成：{session}")
    return 0


def backup_command(args: argparse.Namespace) -> int:
    session = make_session_dir(Path(args.output))
    print(f"会话目录：{session}")
    partitions, _active, metadata = scan_device(args, session)
    edl_script = ensure_file(Path(args.edl_script), "edl.py")
    loader = ensure_file(Path(args.loader), "Firehose loader")
    python = python_for_edl(args.python, edl_script)
    backup_dir = session / "partitions"
    backup_dir.mkdir()
    skip = list(DEFAULT_SKIP)
    if args.include_userdata:
        skip.remove("userdata")
    run_edl(
        python,
        edl_script,
        loader,
        ["rl", str(backup_dir), f"--skip={','.join(skip)}"],
        session / "logs" / "backup.log",
    )
    expected = {"devinfo.bin": 4096, "abl_a.bin": 1048576, "abl_b.bin": 1048576}
    all_files = list(backup_dir.rglob("*"))
    for filename, expected_size in expected.items():
        matches = [path for path in all_files if path.is_file() and path.name == filename]
        if len(matches) != 1:
            raise Action5Error(f"备份中 {filename} 数量不是 1：{len(matches)}")
        actual = matches[0].stat().st_size
        if actual != expected_size:
            raise Action5Error(f"{filename} 大小异常：{actual}，预期 {expected_size}")
    devinfo_path = next(path for path in all_files if path.is_file() and path.name == "devinfo.bin")
    devinfo = devinfo_path.read_bytes()
    if not devinfo.startswith(b"ANDROID-BOOT!"):
        raise Action5Error("devinfo 备份缺少 ANDROID-BOOT! 魔数")
    metadata["backup"] = {
        "profile": "critical",
        "skipped": skip,
        "include_userdata": args.include_userdata,
        "partition_count_seen": len(partitions),
    }
    write_checksums(session, metadata)
    print(f"\n备份与哈希清单已完成：{session}")
    print("请把整个目录复制到第二块存储介质，再校验 SHA256SUMS。")
    return 0


def add_common_device_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--edl-script", required=True, help="bkerler/edl 的 edl.py 路径")
    parser.add_argument("--loader", required=True, help="Firehose loader 路径")
    parser.add_argument("--python", help="运行 edl.py 的 Python；默认使用当前解释器")
    parser.add_argument(
        "--allow-unknown-loader",
        action="store_true",
        help="允许未知 loader 哈希；仍然只执行读取命令",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="action5-edl",
        description="DJI Action 5 Pro 的只读 9008 GPT 探测与分区备份工具",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="检查工具、loader 哈希和 9008 USB")
    doctor_parser.add_argument("--edl-script", required=True)
    doctor_parser.add_argument("--loader", required=True)
    doctor_parser.add_argument("--python")
    doctor_parser.set_defaults(func=doctor)

    scan_parser = subparsers.add_parser("scan", help="读取并导出 GPT，不备份分区")
    add_common_device_args(scan_parser)
    scan_parser.add_argument("--output", default="backups", help="会话目录的父目录")
    scan_parser.set_defaults(func=scan_command)

    backup_parser = subparsers.add_parser("backup", help="读取 GPT 并备份关键分区")
    add_common_device_args(backup_parser)
    backup_parser.add_argument("--output", default="backups", help="会话目录的父目录")
    backup_parser.add_argument(
        "--include-userdata", action="store_true", help="同时备份 userdata（可能较大且含隐私）"
    )
    backup_parser.set_defaults(func=backup_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (Action5Error, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消；本工具没有执行设备写入。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
