"""Download or prepare LogHub raw data for the benchmark datasets."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.io_utils import ensure_dir, raw_dir
from src.schema import DATASETS, validate_dataset


USER_AGENT = "semantic-log-retrieval-benchmark/0.1"


class DatasetSource(NamedTuple):
    loghub_name: str
    filename: str
    urls: tuple[str, ...]


DATASET_SOURCES: dict[str, DatasetSource] = {
    "apache": DatasetSource(
        loghub_name="Apache",
        filename="Apache_2k.log",
        urls=(
            "https://raw.githubusercontent.com/logpai/loghub/refs/heads/master/Apache/Apache_2k.log",
            "https://github.com/logpai/loghub/raw/refs/heads/master/Apache/Apache_2k.log",
        ),
    ),
    "openstack": DatasetSource(
        loghub_name="OpenStack",
        filename="OpenStack_2k.log",
        urls=(
            "https://raw.githubusercontent.com/logpai/loghub/refs/heads/master/OpenStack/OpenStack_2k.log",
            "https://github.com/logpai/loghub/raw/refs/heads/master/OpenStack/OpenStack_2k.log",
        ),
    ),
    "hdfs": DatasetSource(
        loghub_name="HDFS",
        filename="HDFS_2k.log",
        urls=(
            "https://raw.githubusercontent.com/logpai/loghub/refs/heads/master/HDFS/HDFS_2k.log",
            "https://github.com/logpai/loghub/raw/refs/heads/master/HDFS/HDFS_2k.log",
        ),
    ),
}


@dataclass(slots=True)
class RawFileInfo:
    path: Path
    size_bytes: int


@dataclass(slots=True)
class RawDataStatus:
    dataset: str
    destination: Path
    files: list[RawFileInfo]

    @property
    def ready(self) -> bool:
        return any(file.size_bytes > 0 for file in self.files)


def format_size(size_bytes: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size_bytes} B"


def list_raw_files(destination: Path) -> list[RawFileInfo]:
    if not destination.exists():
        return []
    files: list[RawFileInfo] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep" or path.name.startswith("."):
            continue
        files.append(RawFileInfo(path=path, size_bytes=path.stat().st_size))
    return files


def inspect_dataset(dataset: str, root: Path) -> RawDataStatus:
    dataset = validate_dataset(dataset)
    destination = raw_dir(dataset, root)
    ensure_dir(destination)
    return RawDataStatus(
        dataset=dataset,
        destination=destination,
        files=list_raw_files(destination),
    )


def print_manual_instructions(dataset: str, destination: Path) -> None:
    source = DATASET_SOURCES[dataset]
    print("Manual fallback:")
    print(f"- Open https://github.com/logpai/loghub/tree/master/{source.loghub_name}")
    print(f"- Download {source.filename} or another raw {source.loghub_name} log file")
    print(f"- Place it in {destination}")
    print("- Then run: python scripts/check_raw_data.py --dataset " + dataset)


def download_file(url: str, destination: Path) -> int:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        content = response.read()
    if not content:
        raise ValueError(f"Downloaded empty response from {url}")
    destination.write_bytes(content)
    return len(content)


def prepare_dataset(dataset: str, root: Path, *, force: bool = False) -> RawDataStatus:
    dataset = validate_dataset(dataset)
    destination = raw_dir(dataset, root)
    ensure_dir(destination)
    source = DATASET_SOURCES[dataset]
    target_path = destination / source.filename

    if target_path.exists() and not force:
        print(f"Skip download: {target_path} already exists. Use --force to overwrite.")
        return inspect_dataset(dataset, root)

    last_error: Exception | None = None
    for url in source.urls:
        try:
            bytes_written = download_file(url, target_path)
            print(f"Downloaded {source.filename} from {url}")
            print(f"Wrote {format_size(bytes_written)} to {target_path}")
            return inspect_dataset(dataset, root)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            last_error = exc
            print(f"Download failed from {url}: {exc}")

    if target_path.exists() and target_path.stat().st_size == 0:
        target_path.unlink()
    print(f"Could not download {source.loghub_name} automatically.")
    if last_error is not None:
        print(f"Last error: {last_error}")
    print_manual_instructions(dataset, destination)
    return inspect_dataset(dataset, root)


def print_status(status: RawDataStatus) -> None:
    print(f"Dataset: {status.dataset}")
    print(f"Destination: {status.destination}")
    print("Files:")
    if not status.files:
        print("- none")
    for file in status.files:
        print(f"- {file.path.name} ({format_size(file.size_bytes)})")
    print(f"Status: {'ready' if status.ready else 'not ready'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the target sample log file if it already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        status = prepare_dataset(dataset, args.root, force=args.force)
        print_status(status)
        if not status.ready:
            print_manual_instructions(dataset, status.destination)


if __name__ == "__main__":
    main()
