"""Install checksum-verified official Prometheus binaries and seed reproducible lab data."""

import hashlib
import io
import platform
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from signalstory.course import ROOT
from signalstory.prom.data import export_csv, openmetrics

VERSION = "3.15.0"


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "signalstory/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def install():
    target = ROOT / ".tools"
    target.mkdir(exist_ok=True)
    system = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64", "AMD64": "amd64"}.get(
        platform.machine()
    )
    if not system or not machine:
        raise SystemExit("Use Docker Compose or install Prometheus manually on this platform.")
    if all((target / name).exists() for name in ("prometheus", "promtool")):
        return
    archive = f"prometheus-{VERSION}.{system}-{machine}.tar.gz"
    base = f"https://github.com/prometheus/prometheus/releases/download/v{VERSION}/"
    checksums = download(base + "sha256sums.txt").decode()
    expected = next(line.split()[0] for line in checksums.splitlines() if line.split()[-1] == archive)
    payload = download(base + archive)
    if hashlib.sha256(payload).hexdigest() != expected:
        raise SystemExit("Prometheus archive checksum does not match the official release.")
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as package:
        for name in ("prometheus", "promtool"):
            member = package.getmember(archive[:-7] + "/" + name)
            if not member.isfile():
                raise SystemExit("Unexpected archive entry")
            (target / name).write_bytes(package.extractfile(member).read())
            (target / name).chmod(0o755)
    (target / "version.txt").write_text(VERSION)


def seed(export=True):
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    data = runtime / "prometheus"
    data.mkdir(exist_ok=True)
    if export:
        export_csv(ROOT / "data/samples.csv")
    if not (data / ".seeded").exists():
        source = runtime / "fixtures.openmetrics"
        openmetrics(source)
        subprocess.run(
            [
                str(ROOT / ".tools/promtool"),
                "tsdb",
                "create-blocks-from",
                "openmetrics",
                str(source),
                str(data),
            ],
            check=True,
        )
        (data / ".seeded").write_text("fixtures-v1\n")


if __name__ == "__main__":
    install()
    seed()
    from signalstory.prom.engine import start_local_engine

    if not start_local_engine():
        raise SystemExit("Could not start Prometheus; inspect .runtime/prometheus.log")
    print("Real PromQL lab is ready at http://127.0.0.1:9108")
