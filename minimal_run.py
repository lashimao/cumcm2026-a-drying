"""Actual-input vertical slice and physical regression checks."""
import argparse
import json
from pathlib import Path
import numpy as np
from drying_model import Config, Inputs, RadialModel, integrate, properties


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('results/minimal'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    data = Inputs(args.input_dir)
    report = {'input_hashes': data.hashes, 'runs': {}}
    for law, moving in [('q1', False), ('q23', False), ('q4', True)]:
        run = integrate(RadialModel(data, Config(law=law, moving=moving, n=40)),
                        duration=1800, stop_at_threshold=False)
        report['runs'][law] = run.diagnostics()
        temp, c = run.sample([0, 100, 600, 1800], [0, .5, 1, 1.5, 2])
        np.savetxt(args.out / f'{law}_temperature.csv', temp, delimiter=',')
        np.savetxt(args.out / f'{law}_moisture.csv', c, delimiter=',')
        assert np.allclose(run.evaluate(0)[:41], 28)
        assert np.allclose(run.evaluate(0)[41:82], 2.55)
        assert report['runs'][law]['max_outward_c_increase'] < 1e-7
    closed = integrate(RadialModel(data, Config(law='q4', moving=True, n=40,
                                               h_scale=0, hm_scale=0)),
                       duration=1800, stop_at_threshold=False)
    error = np.max(np.abs(closed.evaluate(1800)-closed.model.initial_state()))
    assert error < 1e-10
    report['closed_shrinkage_max_error'] = float(error)
    initial_d = {law: float(properties(np.array([2.55]), np.array([28.]), law)[3][0])
                 for law in ['q1', 'q23', 'q4']}
    assert all(1e-11 < value < 1e-7 for value in initial_d.values())
    report['initial_diffusivity_m2_s'] = initial_d
    jacobian_checks = {}
    rng = np.random.default_rng(2026)
    for law in ['q1', 'q23', 'q4']:
        model = RadialModel(data, Config(law=law, moving=law=='q4', n=12))
        state = model.initial_state()
        state[:13] = 35 + 4*model.s**2
        state[13:26] = 1.8 - .5*model.s**2
        direction = rng.normal(size=27)
        eps = 1e-5
        numeric = (model.rhs(1800, state+eps*direction)
                   - model.rhs(1800, state-eps*direction))/(2*eps)
        analytic = model.jacobian(1800, state) @ direction
        relative = np.max(abs(numeric-analytic))/np.max(abs(numeric))
        assert relative < 2e-7
        jacobian_checks[law] = float(relative)
    report['analytic_jacobian_relative_errors'] = jacobian_checks
    report['passed'] = True
    (args.out/'minimal-report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
