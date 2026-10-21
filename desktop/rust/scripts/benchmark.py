#!/usr/bin/env python3
"""Compare both editions at the same offscreen, fully rendered window stage."""
import argparse
import json
import os
import platform
from pathlib import Path
import statistics
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
PYTHON_CASE = r'''
import time
started = time.perf_counter()
import json
import os
from pathlib import Path
import sys
from PySide6.QtCore import qVersion
from PySide6.QtWidgets import QApplication
sys.path.insert(0, os.environ['BANKAI_PYTHON_SOURCE'])
import control_center as center
app = QApplication([])
app.setStyle('Fusion')
app.setStyleSheet(center.STYLE)
window = center.ControlCenter()
window.show()
app.processEvents()
result = {'edition': 'python-pyside6', 'startup_ms': (time.perf_counter()-started)*1000}
result['thumbnail_ready_ms'] = result['startup_ms']
result['qt_version'] = qVersion()
result['python_version'] = sys.version.split()[0]
for line in Path('/proc/self/status').read_text().splitlines():
    if line.startswith(('VmRSS:', 'VmHWM:')):
        key, value = line.split(':', 1)
        result[key + '_kib'] = int(value.split()[0])
result['preset_count'] = len(center.PRESETS)
print(json.dumps(result))
window.close()
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=7)
    parser.add_argument('--output', type=Path, default=PROJECT / 'artifacts/benchmark.json',
                        help='write raw measurements here (default: desktop/rust/artifacts/benchmark.json)')
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('Choose at least one run')
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen',
                       BANKAI_PYTHON_SOURCE=str(PROJECT.parent / 'python'))
    cases = {'rust': [str(PROJECT / 'target/release/bankai-rust'), '--benchmark'],
             'python': [sys.executable, '-c', PYTHON_CASE]}
    measurements = {'rust': [], 'python': []}
    for iteration in range(args.runs + 1):
        # Alternate order. The first pair warms caches and is discarded.
        order = ['rust', 'python'] if iteration % 2 == 0 else ['python', 'rust']
        for edition in order:
            start = time.perf_counter()
            result = subprocess.run(cases[edition], text=True, capture_output=True, env=environment,
                                    check=True, timeout=30)
            value = json.loads(result.stdout)
            value['process_wall_ms'] = (time.perf_counter()-start)*1000
            value['preset_count'] = int(value['preset_count'])
            if iteration:
                measurements[edition].append(value)
    summary = {}
    rust_presets = {value['preset_count'] for value in measurements['rust']}
    python_presets = {value['preset_count'] for value in measurements['python']}
    if len(rust_presets) != 1 or rust_presets != python_presets:
        raise RuntimeError(
            f'Cannot compare editions with different preset catalogs: Rust={rust_presets}, Python={python_presets}')
    qt_versions = {
        edition: {value['qt_version'] for value in values}
        for edition, values in measurements.items()
    }
    if any(len(versions) != 1 for versions in qt_versions.values()):
        raise RuntimeError(f'Qt versions changed during measurement: {qt_versions}')
    for edition, values in measurements.items():
        summary[edition] = {key: round(statistics.median(v[key] for v in values), 2)
                            for key in ['startup_ms', 'thumbnail_ready_ms',
                                        'process_wall_ms', 'VmRSS_kib', 'VmHWM_kib']}
    preset_count = next(iter(rust_presets))
    cpu_model = platform.processor()
    cpu_info = Path('/proc/cpuinfo')
    if cpu_info.is_file():
        for line in cpu_info.read_text(errors='replace').splitlines():
            key, separator, value = line.partition(':')
            if separator and key.strip() in {'model name', 'Hardware', 'Processor'}:
                cpu_model = value.strip()
                break
    report = {'runs_per_edition': args.runs, 'preset_count': preset_count,
              'environment': {
                  'platform': platform.platform(),
                  'architecture': platform.machine(),
                  'cpu_model': cpu_model or 'unknown',
                  'python_version': platform.python_version(),
                  'qt_versions': {edition: next(iter(versions))
                                  for edition, versions in qt_versions.items()},
              },
              'summary': summary, 'runs': measurements,
              'method': f'Offscreen Qt Fusion; both source editions load all {preset_count} presets and the initial wallpaper. Startup is measured at first paint; thumbnail readiness is measured after every preset card has artwork. The Python case imports desktop/python from this checkout. Warm-up pair discarded; interleaved process launches.',
              'limits': 'Native code also downsizes thumbnails earlier. Gains reflect implementation and language/runtime changes. This does not measure live Wayland startup, idle CPU, actual tray hosting, or proportional physical memory.'}
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['summary'], indent=2))
    print('Full results:', output)


if __name__ == '__main__':
    main()
