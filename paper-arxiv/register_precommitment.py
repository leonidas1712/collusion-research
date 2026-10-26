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
    for prefix, label in [('qwen', 'Qwen fresh (last-prompt)'), ('gptoss', 'gpt-oss fresh (reasoning)')]:
        rows.append([label,
                     macro(prefix, 'JevLeakingFlagged')+' / '+macro(prefix, 'JevLeakingTotal'),
                     macro(prefix, 'JevNonleakingFlagged')+' / '+macro(prefix, 'JevNonleakingTotal'),
                     macro(prefix, 'AllAUROC')+' '+macro(prefix, 'AllAUROCCI'),
                     macro(prefix, 'NoJevAUROC')+' '+macro(prefix, 'NoJevAUROCCI')])
    rows.append([r'\multicolumn{5}{l}{Blind review, counting earlier reasoning: \precommitJevReviewAgreements{}/\precommitJevReviewSample{} agreement; $\kappa$ = \precommitJevReviewKappa{}.}'])
    reg['tables']['precommitment'] = dict(
        columns=r'@{}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.14\linewidth}>{\raggedright\arraybackslash}p{0.15\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.20\linewidth}@{}',
        header=['Fresh cohort', 'Leaking calls flagged / total', 'Non-leaking calls flagged / total', 'AUROC: all calls', 'AUROC: unflagged calls'], rows=rows)
    (HERE/'numbers.yaml').write_text(json.dumps(reg, indent=2)+'\n')


if __name__ == '__main__': main()
