"""Register E11 saved-score exclusions and the blinded flag validation."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = 'runs/20261027-0259-e11-precommitment'


def main():
    reg = json.loads((HERE/'numbers.yaml').read_text())
    data = json.loads((ROOT/RUN/'metrics.json').read_text())
    def add(macro, path, ci=None, fmt='decimal', decimals=2):
        value = data
        for key in path: value = value[key]
        source = dict(file=RUN+'/metrics.json', value_path=path)
        entry = dict(value=value, macro=macro, dataset='Fresh per-call cohorts: Qwen last-prompt / gpt-oss frozen reasoning MAX',
                     evaluation='E11 pre-commitment exclusion; saved scores, no refits; scenario x round AUROC; 1000 family bootstrap draws seed20261025',
                     status='exploratory', run=RUN, format=fmt, decimals=decimals, source=source)
        if ci:
            bounds = data
            for key in ci: bounds = bounds[key]
            entry['ci'] = bounds
            source['ci_path'] = ci
        reg['numbers'][macro] = entry
    for prefix, model in [('qwen', 'qwen'), ('gptoss', 'gpt-oss')]:
        for part, suffix in [('all', 'All'), ('no_jev', 'NoJev')]:
            stem = prefix+'Precommit'+suffix
            add(stem+'AUROC', [model, part, 'within_round_auc'], [model, part, 'within_round_ci95'])
            for key, ending in [('calls', 'Calls'), ('positives', 'Leaks'), ('episodes', 'Episodes')]:
                add(stem+ending, [model, part, key], fmt='integer')
        for label, suffix in [('1', 'Leaking'), ('0', 'Nonleaking')]:
            for field, ending in [('flagged', 'Flagged'), ('total', 'Total')]:
                add(prefix+'PrecommitJev'+suffix+ending, [model, 'jev', 'prevalence', label, field], fmt='integer')
    review = ['blind_review', 'variants', 'including_reasoning', 'jev']
    for field, suffix, fmt in [('agreement', 'Agreement', 'percent'), ('kappa', 'Kappa', 'decimal'),
                               ('agreements', 'Agreements', 'integer'), ('n', 'Sample', 'integer')]:
        add('precommitJevReview'+suffix, review+[field], fmt=fmt, decimals=0 if fmt=='percent' else 2)
    def macro(prefix, suffix): return '\\'+prefix+'Precommit'+suffix+'{}'
    rows = []
    for label, suffix in [('All calls: AUROC', 'All'), ('After excluding Jev-flagged calls: AUROC', 'NoJev')]:
        rows.append([label]+[macro(p,suffix+'AUROC')+' '+macro(p,suffix+'AUROCCI') for p in ('qwen','gptoss')])
        rows.append(['Leaking / total calls'+(' remaining' if suffix=='NoJev' else '')]+[macro(p,suffix+'Leaks')+' / '+macro(p,suffix+'Calls') for p in ('qwen','gptoss')])
    for label,suffix in [('Jev-flagged leaking calls','Leaking'),('Jev-flagged non-leaking calls','Nonleaking')]:
        rows.append([label]+[macro(p,'Jev'+suffix+'Flagged')+' / '+macro(p,'Jev'+suffix+'Total') for p in ('qwen','gptoss')])
    rows.append(['Blind Jev agreement (both models)', r'\multicolumn{2}{l}{\precommitJevReviewAgreements{}/\precommitJevReviewSample{} = \precommitJevReviewAgreement{}; $\kappa$ = \precommitJevReviewKappa{}}'])
    reg['tables']['precommitment'] = dict(
        columns=r'@{}>{\raggedright\arraybackslash}p{0.39\linewidth}>{\raggedright\arraybackslash}p{0.26\linewidth}>{\raggedright\arraybackslash}p{0.26\linewidth}@{}',
        header=['Pre-commitment check', 'Qwen last-prompt probe', 'gpt-oss reasoning probe'], rows=rows)
    (HERE/'numbers.yaml').write_text(json.dumps(reg, indent=2)+'\n')


if __name__ == '__main__': main()
