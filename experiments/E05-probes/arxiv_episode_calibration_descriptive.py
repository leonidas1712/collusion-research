"""Describe a common fresh-refusing episode calibration for all three detectors."""
import copy
import hashlib
import json
from arxiv_episode_calibration import ROOT, read, evaluate, calibrate
from collusion.runs import start_run, write_json_atomic

SOURCE = ROOT / 'runs/20261027-0047-e05-arxiv-episode-calibration'


def main():
    data = json.loads((SOURCE / 'metrics.json').read_text())
    scores = read(SOURCE / 'scores.csv.gz')
    results = copy.deepcopy(data)
    for detector in results:
        fresh = [{k: r[k] for k in ['row_id', 'episode', 'condition']} | dict(
            label=int(r['label']), ever=r['ever']=='True', score=float(r['score']) if r['score'] else None)
            for r in scores if r['detector']==detector and r['split']=='fresh']
        cutoff, detail = calibrate(fresh)
        results[detector].update(episode_threshold=cutoff, calibration=detail,
            calibration_status='descriptive_fresh_refusing_calibration', episode_calibrated=evaluate(fresh, cutoff))
    run = start_run('e05-arxiv-episode-calibration-descriptive', experiment='E05', parents=[SOURCE.name],
        settings=dict(saved_scores_only=True, no_fit=True, no_rescoring=True, no_api=True, no_gpu=True,
            source_scores=str((SOURCE/'scores.csv.gz').relative_to(ROOT)),
            source_scores_sha256=hashlib.sha256((SOURCE/'scores.csv.gz').read_bytes()).hexdigest(),
            calibration='Same rule for all three: strict >; threshold chosen on fresh refusing-episode maxima; at most floor(0.05*n) episode alarms',
            status='DESCRIPTIVE; no prospective operating-point claim',
            original_points='Original unchanged threshold metrics copied from source; precision includes earlier nonleaking calls in eventual-leak episodes',
            unavailable='Jev fresh control scores unavailable; zero denominators mean unavailable, not zero false alarms'))
    write_json_atomic(run.dir/'metrics.json',results)
    run.result(no_api=True,no_gpu=True);run.finish();print(run.dir)
    for detector, m in results.items():
        print(detector, m['episode_threshold'], json.dumps(m['episode_calibrated']))


if __name__=='__main__':main()
