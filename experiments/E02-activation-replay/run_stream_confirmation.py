"""Finish the approved confirmation after collection, stopping on failed gates."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from collusion.runs import start_run, write_json_atomic


def run_logged(command, log):
    with log.open('w') as out:
        subprocess.run(command, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, check=True)


def say(message):
    subprocess.run(['aboard', 'say', '--to', '@claude', '--reply', '1833', message], cwd=ROOT, check=True)


def main(freeze):
    freeze = freeze.resolve()
    run = start_run('e05-stream-confirm-completion', experiment='E05', parents=[freeze.name],
                    settings={'approval': 'Aboard1833/1838/1861/1867', 'hard_cap_usd': 10,
                              'API_cap_usd': 5, 'Modal_cap_usd': 4, 'reserve_usd': 1,
                              'new_data_refits': False})
    root_python = str(ROOT / '.venv/bin/python')
    replay_python = str(ROOT / 'experiments/E02-activation-replay/.venv/bin/python')
    score_python = str(ROOT / 'experiments/E05-probes/.venv/bin/python')
    try:
        while True:
            bulk = json.loads((freeze / 'bulk_run.json').read_text())
            if bulk['status'] == 'finished':
                break
            meta = json.loads((Path(bulk['run_dir']) / 'meta.json').read_text())
            assert meta['status'] == 'running', 'Collection stopped before completion'
            time.sleep(20)
        assert bulk['incomplete'] == 0, 'Incomplete API attempts: preserve and review replacement plan before replay'
        run_logged([root_python, 'experiments/E03-target-screen/stream_confirm_manifest.py',
                    '--freeze', str(freeze)], run.dir / 'manifest.log')
        manifest = json.loads((freeze / 'confirmation_manifest.json').read_text())
        assert manifest['selected'] == 84 and not manifest['deficits']
        ledger = [{'charged_or_reserved_usd': bulk['charged_or_reserved_total_including_benchmark'],
                   'billed_usd': bulk['billed_total_including_benchmark'],
                   'source': str(Path(bulk['run_dir']) / 'budget.json'),
                   'benchmark_included_once': True}]
        write_json_atomic(freeze / 'replay_api_ledger.json', ledger)
        assert float(ledger[0]['charged_or_reserved_usd']) <= 5
        run_logged([replay_python, 'experiments/E02-activation-replay/plan_gpt_oss_confirmation.py',
                    '--manifest', manifest['path'], '--shard-size', '100',
                    '--provider-modes', '{"AkashML":"current_turn","DekaLLM":"drop_all"}',
                    '--approval-ref', 'Aboard1833/1838/1861; same frozen provider-specific renderer',
                    '--budget-root', str(freeze / 'gpu-budget')], run.dir / 'plan.log')
        lines = (run.dir / 'plan.log').read_text().splitlines()
        paths = [s.removeprefix('FULL_PLAN ') for s in lines if s.startswith('FULL_PLAN ')]
        assert len(paths) == 1
        plan_path = Path(paths[0]).resolve()
        plan = json.loads(plan_path.read_text())
        projection = plan['counts']['prior_projection_usd_with_2x_margin']
        assert projection <= 4, 'Prior replay projection exceeds USD4 phase cap'
        write_json_atomic(freeze / 'replay_plan_pointer.json', {'path': str(plan_path), 'counts': plan['counts']})
        say(f"Confirmation collection fixed84 complete; API billed USD{ledger[0]['billed_usd']}, "
            f"charged/reserved USD{ledger[0]['charged_or_reserved_usd']}. Replay plan {plan_path.parent.name}: "
            f"{plan['counts']['requests']} requests, prior2x-margin GPU projection USD{projection:.3f}. "
            "Launching cached-weight replay under USD4 cap; measured first-shard projection abort remains enabled. Frozen weights unchanged.")
        gpu_log = (run.dir / 'gpu.log').open('w')
        gpu = subprocess.Popen([root_python, 'experiments/E02-activation-replay/gpt_oss_confirmation_budget.py',
                                '--plan', str(plan_path), '--api-ledger', str(freeze / 'replay_api_ledger.json'),
                                '--cap', '4'], cwd=ROOT, stdout=gpu_log, stderr=subprocess.STDOUT)
        client_list = freeze / 'gpu-budget/clients.json'
        while not client_list.exists():
            assert gpu.poll() is None, 'GPU wrapper failed before client creation'
            time.sleep(1)
        client = json.loads(client_list.read_text())[-1]
        write_json_atomic(freeze / 'replay_client_pointer.json', {'path': client})
        download_log = (run.dir / 'download.log').open('w')
        download = subprocess.Popen([root_python, 'experiments/E02-activation-replay/download_gpt_oss_stream.py',
                                     '--plan', str(plan_path), '--client', client, '--workers', '8'],
                                    cwd=ROOT, stdout=download_log, stderr=subprocess.STDOUT)
        gpu_code = gpu.wait(); gpu_log.close()
        download_code = download.wait(); download_log.close()
        assert gpu_code == 0 and download_code == 0, 'Replay/download failed; outputs preserved, no scoring'
        summary = json.loads((Path(client) / 'summary.json').read_text())
        assert summary['app_stopped'] and summary['total_upper_usd'] <= 4
        total = float(ledger[0]['charged_or_reserved_usd']) + summary['total_upper_usd']
        assert total + 1 <= 10
        costs = {'API': ledger[0], 'GPU': summary, 'total_conservative_usd': total,
                 'unspent_reserve_usd': 1, 'shared_cap_usd': 10}
        write_json_atomic(freeze / 'final_costs.json', costs)
        run_logged([score_python, 'experiments/E05-probes/score_stream_confirmation.py',
                    '--freeze', str(freeze), '--plan', str(plan_path)], run.dir / 'score.log')
        result = json.loads((freeze / 'confirmation_result.json').read_text())
        write_json_atomic(Path(result['run']) / 'costs.json', costs)
        primary = result['primary']
        say(f"Frozen confirmation complete: {result['run']}/report.md. "
            f"Primary MAX within scenario×round AUROC {primary['within_round_auc']:.4f} "
            f"CI{primary['within_round_ci95']}; predeclared success={primary['predeclared_success']}. "
            f"Counts{result['counts']}. Conservative shared cost USD{total:.4f}<10; Modal app stopped. "
            "No new-data fit, threshold change or label selection. Integrity checks passed; independent review next.")
        run.result(primary=primary, costs=costs); run.finish()
    except BaseException as exc:
        run.finish('failed', str(exc))
        say(f"Confirmation completion stopped at a gate: {type(exc).__name__}: {exc}. "
            f"Logs preserved in {run.dir}; no automatic scope/model/threshold change.")
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--freeze', type=Path, required=True)
    main(p.parse_args().freeze)
