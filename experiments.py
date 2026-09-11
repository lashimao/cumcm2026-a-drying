"""Numerical convergence, analytic validation and controlled drying experiments."""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from scipy.special import j0, j1
from drying_model import Config, Inputs, RadialModel, integrate


def save_json(filename, obj):
    Path(filename).write_text(json.dumps(obj, ensure_ascii=False, indent=2,
                                        allow_nan=False))


def analytic_validation(data):
    class ConstantEnvironment:
        def radius(self, t, moving):
            return np.full_like(np.asarray(t, dtype=float), .02)
        def boundary(self, t, mode):
            return np.array([28., 0.])
    d, radius, bi = 1e-8, .02, 2.
    x = np.linspace(1e-10, 81*np.pi, 10000)
    f = x*j1(x)-bi*j0(x)
    brackets = np.where(f[:-1]*f[1:] < 0)[0][:80]
    roots = np.array([brentq(lambda z: z*j1(z)-bi*j0(z), x[i], x[i+1])
                      for i in brackets])
    coefficients = 2*j1(roots)/(roots*(j0(roots)**2+j1(roots)**2))
    times = np.array([100., 1000., 10000.])
    rows = []
    for n in (40, 80, 160, 320):
        model = RadialModel(ConstantEnvironment(), Config(law='q1', n=n,
                            hm_scale=bi*d/radius/8e-7, rtol=1e-9,
                            atol_t=1e-9, atol_c=1e-11), constant_d=d)
        result = integrate(model, duration=10000, stop_at_threshold=False)
        exact = j0(model.s[:, None]*roots) @ (
            coefficients[:, None]*np.exp(-roots[:, None]**2*d*times/radius**2))
        error = abs(result.evaluate(times)[model.np:2*model.np]/2.55-exact)
        rows.append({'n': n, 'maximum_normalized_error': float(error.max()),
                     'errors_by_time': error.max(axis=0).tolist()})
    assert all(a['maximum_normalized_error'] > b['maximum_normalized_error']
               for a, b in zip(rows[:-1], rows[1:]))
    assert rows[-1]['maximum_normalized_error'] < 5e-5
    return {'bi': bi, 'diffusivity': d, 'times_seconds': times.tolist(),
            'series_terms': len(roots), 'criterion': 'max normalized error < 5e-5 at N=320',
            'rows': rows, 'passed': True}


def run_case(data, config):
    run = integrate(RadialModel(data, config),
                    duration=1800 if config.law == 'q1' else 14*86400,
                    stop_at_threshold=config.law != 'q1')
    return run, run.diagnostics()


def compute(input_dir, output_root):
    out = Path(output_root)/'results'
    out.mkdir(parents=True, exist_ok=True)
    data = Inputs(input_dir)
    report = {'input_hashes': data.hashes, 'random_seed': 2026,
              'ambient_extension': {k: v.tolist() for k, v in data.tail.items()}}
    report['analytic_validation'] = analytic_validation(data)
    print('Analytic cylindrical benchmark passed', flush=True)
    convergence, previous, frozen = [], {}, {}
    for n in (40, 80, 160, 320, 640, 1280, 2560):
        level, current, all_pass = {'n': n}, {}, n >= 320
        for law, moving in [('q1', False), ('q23', False), ('q4', True)]:
            run, diag = run_case(data, Config(law=law, moving=moving, n=n))
            current[law] = run
            level[law] = diag
            if law in previous:
                if law == 'q1':
                    t = [100, 300, 600, 900, 1200, 1500, 1800]
                    a = run.sample(t, [0, .5, 1, 1.5, 2])
                    b = previous[law].sample(t, [0, .5, 1, 1.5, 2])
                    diff = [float(np.max(abs(u-v))) for u, v in zip(a, b)]
                    level['q1_table_differences'] = diff
                    all_pass = all_pass and max(diff) < 2e-4
                else:
                    relative = abs(run.event_time-previous[law].event_time)/run.event_time
                    level[f'{law}_relative_time_change'] = float(relative)
                    all_pass = all_pass and relative < .001
        convergence.append(level)
        print(f"Grid N={n}: Q3={level['q23']['threshold_hours']:.6f} h, "
              f"Q4={level['q4']['threshold_hours']:.6f} h", flush=True)
        save_json(out/'convergence-progress.json', convergence)
        if all_pass:
            frozen = current
            break
        previous = current
    if not frozen:
        raise RuntimeError('Spatial convergence target not reached at N=2560')
    n_final = frozen['q23'].model.config.n
    report['spatial_convergence'] = convergence
    report['final_n'] = n_final
    report['nominal'] = {k: v.diagnostics() for k, v in frozen.items()}
    temporal = {}
    for law in ['q23', 'q4']:
        cfg = replace(frozen[law].model.config, rtol=1e-9, atol_t=1e-9,
                      atol_c=1e-11, early_max_step=30, late_max_step=60)
        _, diag = run_case(data, cfg)
        change = abs(diag['threshold_seconds']-frozen[law].event_time)
        assert change / frozen[law].event_time < 2e-5
        temporal[law] = {'refined': diag, 'absolute_time_change_seconds': change}
    report['temporal_convergence'] = temporal
    boundary = []
    for mode in ['mean1h', 'last', 'mean2h', 'fast', 'slow']:
        row = {'scenario': mode, 'ambient_T_C': data.tail[mode].tolist()}
        for law in ['q23', 'q4']:
            if mode == 'mean1h':
                row[law] = frozen[law].event_time/3600
            else:
                _, diag = run_case(data, replace(frozen[law].model.config, boundary=mode))
                row[law] = diag['threshold_hours']
        boundary.append(row)
    report['boundary_scenarios'] = boundary
    parameters = []
    for parameter in ['d_scale', 'hm_scale', 'h_scale']:
        for factor in [.9, 1.1]:
            row = {'parameter': parameter, 'factor': factor}
            for law in ['q23', 'q4']:
                _, diag = run_case(data, replace(frozen[law].model.config,
                                                 **{parameter: factor}))
                row[law] = diag['threshold_hours']
            parameters.append(row)
    report['parameter_scenarios'] = parameters
    crossed = []
    for law in ['q23', 'q4']:
        for moving in [False, True]:
            if moving == frozen[law].model.config.moving:
                diag = frozen[law].diagnostics()
            else:
                _, diag = run_case(data, replace(frozen[law].model.config, moving=moving))
            crossed.append({'law': law, 'moving': moving,
                            'time_hours': diag['threshold_hours'],
                            'radius_extrapolated': diag['radius_extrapolated']})
    report['crossed_ablation'] = crossed
    if any(v['radius_extrapolated'] for v in report['nominal'].values()):
        raise RuntimeError('Nominal radius extrapolation needs a model contract review')
    tables = {}
    for key, law, times in [
            ('q1', 'q1', np.array([100, 300, 600, 900, 1200, 1500, 1800.])),
            ('q2', 'q23', np.arange(1, 7)*1800.),
            ('q3', 'q23', np.r_[np.arange(21600, frozen['q23'].end_time, 21600),
                                 frozen['q23'].event_time, frozen['q23'].end_time]),
            ('q4', 'q4', np.r_[np.arange(21600, frozen['q4'].end_time, 21600),
                                frozen['q4'].event_time, frozen['q4'].end_time])]:
        run = frozen[law]
        tt, cc = run.sample(times, [0, .5, 1, 1.5, 2])
        states = run.evaluate(times)
        rows = []
        for i, seconds in enumerate(times):
            def clean(a):
                return [float(x) if np.isfinite(x) else None for x in a]
            rows.append({'time_seconds': float(seconds), 'time_hours': float(seconds/3600),
                'temperature_C': clean(tt[i]), 'moisture_dry_basis': clean(cc[i]),
                'surface_temperature_C': float(states[run.model.np-1, i]),
                'surface_moisture': float(states[2*run.model.np-1, i]),
                'surface_radius_cm': float(data.radius(seconds, run.model.config.moving))*100})
        tables[key] = rows
    report['requested_tables'] = tables
    for law, run in frozen.items():
        times = np.unique(np.r_[np.linspace(0, min(run.end_time, 14400), 361),
                                 np.arange(0, run.end_time, 60), run.end_time])
        states = run.evaluate(times)
        splot = np.linspace(0, 1, 81)
        temp = np.array([np.interp(splot, run.model.s, states[:run.model.np, i])
                         for i in range(len(times))])
        c = np.array([np.interp(splot, run.model.s,
                                states[run.model.np:2*run.model.np, i])
                      for i in range(len(times))])
        mean = 2*run.model.weights @ states[run.model.np:2*run.model.np]
        np.savez_compressed(out/f'{law}_trajectory.npz', times=times, s=splot,
                            temperature=temp, moisture=c, mean=mean,
                            radius_cm=data.radius(times, run.model.config.moving)*100,
                            loss=states[-1])
    save_json(out/'summary.json', report)
    print(json.dumps({'final_n': n_final, 'Q3_hours': frozen['q23'].event_time/3600,
                      'Q4_hours': frozen['q4'].event_time/3600,
                      'boundary_scenarios': boundary,
                      'crossed_ablation': crossed}, ensure_ascii=False, indent=2), flush=True)
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', type=Path, default=Path('data/附件'))
    parser.add_argument('--out', type=Path, default=Path('.'))
    args = parser.parse_args()
    compute(args.input_dir, args.out)
