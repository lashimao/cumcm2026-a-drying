"""One command reproduces every numerical table and figure from the A inputs."""
import argparse
import json
from pathlib import Path
from experiments import compute
from export_results import export_all
from make_figures import build_figures
from utils.repro_manifest import build_manifest


def write_manifest(input_dir, output_root):
    root = Path(output_root)
    inputs = sorted(Path(input_dir).rglob('*.xlsx'))
    summary = json.loads((root/'results/summary.json').read_text())
    manifest = build_manifest(inputs,2026,
        {'models': {k:v['config'] for k,v in summary['nominal'].items()},
         'threshold': .15, 'initial_temperature_C': 28., 'initial_moisture': 2.55,
         'initial_radius_m': .02, 'heat_exchange': 25., 'mass_exchange': 8e-7,
         'ambient_extension': summary['ambient_extension'],
         'spatial_time_relative_tolerance': .001,
         'analytic_benchmark_normalized_tolerance': 5e-5,
         'jacobian': 'analytic sparse', 'stochastic_solver': False},
        'python reproduce.py --input-dir data/附件',
        ['numpy','scipy','openpyxl','xlsxwriter','matplotlib','Pillow'])
    for item in manifest['input_files']:
        item['path'] = 'data/附件/'+str(Path(item['path']).relative_to(Path(input_dir).resolve()))
    manifest['figures'] = json.loads((root/'figures/figure-registry.json').read_text())
    manifest['excel_outputs'] = json.loads((root/'results/excel-export.json').read_text())
    (root/'results/复现清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir',type=Path,default=Path('data/附件'))
    parser.add_argument('--out',type=Path,default=Path('.'))
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    compute(args.input_dir,args.out)
    export_all(args.input_dir,args.out)
    build_figures(args.input_dir,args.out)
    write_manifest(args.input_dir,args.out)
    print('All four A-question tables and figure sets reproduced.',flush=True)


if __name__ == '__main__':
    main()
