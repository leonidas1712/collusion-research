"""Register E15: forbidden, early-permitted and late-permitted sharing calls on the five Qwen test scenarios, split by calls since the last read."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = 'runs/20261028-1039-e15-giving-in-scaleup'
ARMS = [('FORBID', 'Forbid', 'Forbidding rule'),
        ('EARLY', 'Early', 'Permitting rule, peer asks at once'),
        ('LATE', 'Late', 'Permitting rule, peer asks in its fifth message')]
BINS = [('0', 'Zero'), ('1', 'One'), ('2', 'Two'), ('3+', 'Three')]


def main():
    reg = json.loads((HERE/'numbers.yaml').read_text())
    data = json.loads((ROOT/RUN/'results.json').read_text())

    def get(path):
        value = data
        for key in path: value = value[key]
        return value

    def add(macro, path, ci=None, fmt='integer', decimals=0):
        source = dict(file=RUN+'/results.json', value_path=path)
        entry = dict(value=get(path), macro=macro,
                     dataset='E15: new Qwen3-32B episodes on the five test scenarios (forbidding rule; permitting rule with the request at once or in the peer\'s fifth message), plus the existing forbidden test leaks and the E14 permitted dispatch episodes',
                     evaluation='Frozen last-prompt probe, frozen threshold; exact-emission label; a call follows a read when its prompt ends with a tool result containing the value; no refits',
                     status='verified', run=RUN, format=fmt, decimals=decimals, source=source)
        if ci:
            entry['ci'] = get(ci)
            source['ci_path'] = ci
        reg['numbers'][macro] = entry

    def rate(m, path):
        add(m+'Over', path+['over'])
        add(m+'Calls', path+['n'])
        if get(path)['n']:
            add(m+'Rate', path+['share'], path+['wilson95'], fmt='percent')

    rows = []
    for arm, name, label in ARMS:
        m = 'eFifteen' + name
        add(m+'Episodes', ['episodes', arm, 'complete'])
        add(m+'SharingEpisodes', ['episodes', arm, 'sharing'])
        rate(m+'Nonread', ['primary_nonread', arm])
        add(m+'NonreadMedian', ['primary_nonread', arm, 'median_score'], fmt='decimal', decimals=2)
        rate(m+'Read', ['follows_read', arm])
        rate(m+'All', ['all_sharing', arm])
        add(m+'Hedged', ['hedge_before_share', arm, 'hedged'])
        add(m+'HedgeCalls', ['hedge_before_share', arm, 'n'])
        add(m+'Delta', ['within_episode_delta', arm, 'value'], ['within_episode_delta', arm, 'ci95'], fmt='signed', decimals=2)
        cells = []
        for b, word in BINS:
            rate(m+'Bin'+word, ['recency', arm, b])
            cells.append('\\'+m+'Bin'+word+'Over{}/\\'+m+'Bin'+word+'Calls{}' if get(['recency', arm, b])['n'] else '--')
        rows.append([label] + cells + ['\\'+m+'NonreadOver{}/\\'+m+'NonreadCalls{} (\\'+m+'NonreadRate{})'])
    for key, name in [('FORBID_old', 'Old'), ('FORBID_new', 'New'), ('FORBID_round3plus', 'RoundThree')]:
        rate('eFifteenForbid'+name+'Nonread', ['primary_nonread', key])
    add('eFifteenEarlyMinusForbid', ['diff_EARLY_minus_FORBID_nonread', 'points'],
        ['diff_EARLY_minus_FORBID_nonread', 'points_ci95'], fmt='signed')
    add('eFifteenLateMinusForbid', ['diff_LATE_minus_FORBID_nonread_round3plus', 'points'],
        ['diff_LATE_minus_FORBID_nonread_round3plus', 'points_ci95'], fmt='signed')
    add('eFifteenLateAskFifth', ['late_compliance', 'ask_in_round_5'])
    add('eFifteenLatePreAskShares', ['late_pre_ask_shares', 'n'])
    reg['tables']['e15_recency'] = dict(
        columns=r'@{}>{\raggedright\arraybackslash}p{0.30\linewidth}*{4}{>{\centering\arraybackslash}p{0.09\linewidth}}>{\centering\arraybackslash}p{0.20\linewidth}@{}',
        header=['Rule and request', '0', '1', '2', '3+', 'Not after a read'],
        rows=rows)
    (HERE/'numbers.yaml').write_text(json.dumps(reg, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__': main()
