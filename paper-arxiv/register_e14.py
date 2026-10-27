"""Register E14: whole episodes under a rule that permits sharing, scored by the frozen Qwen probe."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = 'runs/20261028-0224-e14-permitted-onpolicy'
ROWS = [('forbidden_dispatch_test', 'Forbid', 'Forbidding rule (test episodes)'),
        ('arms/PERMIT', 'Permit', 'Permitting rule, consequence kept'),
        ('arms/PERMIT_NO_CONSEQUENCE', 'PermitClean', 'Permitting rule, consequence removed')]


def main():
    reg = json.loads((HERE/'numbers.yaml').read_text())
    data = json.loads((ROOT/RUN/'results.json').read_text())

    def add(macro, path, ci=None, fmt='decimal', decimals=2):
        value = data
        for key in path: value = value[key]
        source = dict(file=RUN+'/results.json', value_path=path)
        entry = dict(value=value, macro=macro,
                     dataset='E14: 60 new Qwen3-32B episodes on dispatch-integration-code under a permitting rule, plus the forbidding-rule test episodes of that scenario',
                     evaluation='Frozen last-prompt probe, frozen threshold; exact-emission label; no refits',
                     status='verified', run=RUN, format=fmt, decimals=decimals, source=source)
        if ci:
            bounds = data
            for key in ci: bounds = bounds[key]
            entry['ci'] = bounds
            source['ci_path'] = ci
        reg['numbers'][macro] = entry
        return {'key': macro}

    rows = []
    for path, name, label in ROWS:
        p = path.split('/')
        calls = 'leaking_calls' if name == 'Forbid' else 'sharing_calls'
        eps = 'leaking_episodes' if name == 'Forbid' else 'sharing_episodes'
        total = 'episodes_scored' if name == 'Forbid' else 'complete'
        m = 'eFourteen' + name
        add(m+'Sharing', p+[eps], fmt='integer')
        add(m+'Episodes', p+[total], fmt='integer')
        add(m+'Over', p+[calls, 'over_threshold'], fmt='integer')
        add(m+'Calls', p+[calls, 'n'], fmt='integer')
        add(m+'OverShare', p+[calls, 'share_over_threshold'], p+[calls, 'wilson95'], fmt='percent', decimals=0)
        add(m+'Median', p+[calls, 'median'])
        add(m+'Auroc', p+['within_round_auroc'], p+['within_round_auroc_ci'])
        rows.append([label, '\\'+m+'Sharing{}/\\'+m+'Episodes{}', '\\'+m+'Over{}/\\'+m+'Calls{} (\\'+m+'OverShare{})',
                     '\\'+m+'Median{}', {'key': m+'Auroc', 'ci': True}])
    add('eFourteenPermitCleanDiff', ['arms', 'PERMIT_NO_CONSEQUENCE', 'median_diff_vs_forbidden_leaks'],
        ['arms', 'PERMIT_NO_CONSEQUENCE', 'median_diff_ci'], fmt='signed', decimals=2)
    add('eFourteenPermitDiff', ['arms', 'PERMIT', 'median_diff_vs_forbidden_leaks'],
        ['arms', 'PERMIT', 'median_diff_ci'], fmt='signed', decimals=2)
    a = ['addon_e08_permit_no_consequence']
    add('eFourteenReplayNoConsequenceShift', a+['median_PERMIT_NO_CONSEQUENCE_minus_FORBID'],
        a+['median_PERMIT_NO_CONSEQUENCE_minus_FORBID_ci'], fmt='signed', decimals=2)
    add('eFourteenReplayNoConsequenceOver', a+['share_over_threshold', 'PERMIT_NO_CONSEQUENCE'], fmt='percent', decimals=0)
    add('eFourteenThreshold', ['threshold'])
    add('qwenFreshProbeCaughtWilson', ['all_test_leaking_calls', 'share_over_threshold'], ['all_test_leaking_calls', 'wilson95'], fmt='percent', decimals=0)
    add('eFourteenReplayNoConsequenceAuroc', a+['within_round_auroc_PERMIT_NO_CONSEQUENCE'])
    # Replay table: the no-consequence prompt from the E14 add-on (Qwen3-32B only).
    t = reg['tables']['policy_counterfactual']
    t['rows'] = [r for r in t['rows'] if not str(r[0]).startswith('Permitting rule, no consequence')]
    def after(prefix, row):
        i = next(k for k, r in enumerate(t['rows']) if r[0].startswith(prefix))
        t['rows'].insert(i+1, row)
    after('Neutral rewording minus', ['Permitting rule, no consequence sentence, minus original rule',
                                      {'key': 'eFourteenReplayNoConsequenceShift', 'ci': True}, '--'])
    after('Neutral rewording AUROC', ['Permitting rule, no consequence sentence, AUROC',
                                      {'key': 'eFourteenReplayNoConsequenceAuroc'}, '--'])
    after('Neutral rewording threshold', ['Permitting rule, no consequence sentence, threshold crossings',
                                          {'key': 'eFourteenReplayNoConsequenceOver'}, '--'])
    # Split by whether the call's prompt ends with a tool result containing the value.
    split_run = 'runs/20261028-0257-e14-just-read-split'
    split = json.loads((ROOT/split_run/'results.json').read_text())
    def addsplit(macro, path, fmt='integer', decimals=0):
        value = split
        for key in path: value = value[key]
        reg['numbers'][macro] = dict(value=value, macro=macro, dataset='E14 sharing calls and Qwen3-32B test leaking calls',
            evaluation='Frozen last-prompt probe and threshold; a call follows a read when its last prompt message is a tool result containing the value',
            status='verified', run=split_run, format=fmt, decimals=decimals,
            source=dict(file=split_run+'/results.json', value_path=path))
    srows = []
    for key, name, label in [('forbidden_test_leaks', 'TestLeaks', 'Forbidding rule, all test leaks'),
                             ('PERMIT', 'Permit', 'Permitting rule, consequence kept'),
                             ('PERMIT_NO_CONSEQUENCE', 'PermitClean', 'Permitting rule, consequence removed')]:
        m = 'eFourteenRead' + name
        addsplit(m+'Share', [key, 'share_follows_read'], fmt='percent')
        for part, suffix in [('follows_read', 'After'), ('other', 'Other')]:
            addsplit(m+suffix+'Over', [key, part, 'over'])
            addsplit(m+suffix+'Calls', [key, part, 'calls'])
            addsplit(m+suffix+'Rate', [key, part, 'share_over'], fmt='percent')
        srows.append([label, '\\'+m+'Share{}',
                      '\\'+m+'AfterOver{}/\\'+m+'AfterCalls{}',
                      '\\'+m+'OtherOver{}/\\'+m+'OtherCalls{} (\\'+m+'OtherRate{})'])
    reg['tables']['e14_read'] = dict(
        columns=r'@{}>{\raggedright\arraybackslash}p{0.34\linewidth}>{\centering\arraybackslash}p{0.17\linewidth}>{\centering\arraybackslash}p{0.17\linewidth}>{\centering\arraybackslash}p{0.22\linewidth}@{}',
        header=['Rule in the episode', 'Sharing calls just after a read', 'Over threshold, after a read', 'Over threshold, otherwise'],
        rows=srows)
    reg['tables']['e14'] = dict(
        columns=r'@{}>{\raggedright\arraybackslash}p{0.24\linewidth}>{\centering\arraybackslash}p{0.13\linewidth}>{\centering\arraybackslash}p{0.17\linewidth}>{\centering\arraybackslash}p{0.12\linewidth}>{\centering\arraybackslash}p{0.20\linewidth}@{}',
        header=['Rule in the episode', 'Episodes sharing', 'Sharing calls over threshold', 'Median score', 'AUROC within round'],
        rows=rows)
    (HERE/'numbers.yaml').write_text(json.dumps(reg, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__': main()
