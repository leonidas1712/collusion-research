"""Register fresh alarm counts at original and development-episode thresholds."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN = 'runs/20261027-0049-e05-arxiv-episode-calibration-descriptive'


def main():
    registry = json.loads((HERE / 'numbers.yaml').read_text())
    data = json.loads((ROOT / RUN / 'metrics.json').read_text())
    def add(macro, path, fmt='integer', decimals=0):
        value = data
        for part in path:
            value = value[part]
        registry['numbers'][macro] = dict(value=value, macro=macro, dataset='Fresh episodes',
            evaluation='Original threshold or descriptive fresh-refusing episode cutoff; no refits',
            status='post_hoc', run=RUN, format=fmt, decimals=decimals,
            source=dict(file=RUN+'/metrics.json', value_path=path))
        return macro
    rows=[]
    for model, prefix, label in [('qwen_probe','qwen','Qwen probe'), ('qwen_jev','qwenJev','Qwen Jev'), ('gptoss_reasoning','gptoss','GPT reasoning')]:
        for mode, suffix, cut in [('original','Original','Original'), ('episode_calibrated','Episode','Fresh desc.')]:
            cells=[label,cut]
            for field, short in [('precision','Precision'), ('leaking_calls','LeakCalls'), ('leaking_episodes','LeakEpisodes'),
                                 ('refusing_calls','RefusingCalls'), ('refusing_episodes','RefusingEpisodes'), ('control_calls','ControlCalls'), ('control_episodes','ControlEpisodes')]:
                if data[model][mode][field]['rate'] is None:
                    cells.append('---');continue
                stem=prefix+'Calibration'+suffix+short
                n=add(stem+'Numerator',[model,mode,field,'numerator'])
                d=add(stem+'Denominator',[model,mode,field,'denominator'])
                add(stem+'Rate',[model,mode,field,'rate'],'percent',1)
                cells.append('\\'+n+'{}/\\'+d+'{}')
            rows.append(cells)
    rows.append([r'\multicolumn{9}{l}{Training-episode cutoff (in-sample): \qwenEpisodeCalTrainRefusingEpisodes{} of refusing fresh Qwen episodes alarm.}'])
    registry['tables']['episode_calibration']=dict(columns='@{}llrrrrrrr@{}',header=['Detector','Cutoff','Precision',r'Leak calls',r'Leak eps.',r'Ref. calls',r'Ref. eps.',r'Ctrl. calls',r'Ctrl. eps.'],rows=rows)
    add('qwenFreshProbePrecision',['qwen_probe','original','precision','rate'],'percent')
    add('qwenEpisodeCalCaught',['qwen_probe','episode_calibrated','leaking_episodes','rate'],'percent')
    add('qwenEpisodeCalRefusingAlarm',['qwen_probe','episode_calibrated','refusing_episodes','rate'],'percent')
    for model,prefix in [('qwen_jev','qwenJev'),('gptoss_reasoning','gptoss')]:
        add(prefix+'EpisodeCalCaught',[model,'episode_calibrated','leaking_episodes','rate'],'percent')
        add(prefix+'EpisodeCalRefusingAlarm',[model,'episode_calibrated','refusing_episodes','rate'],'percent')
    train_run='runs/20261027-0047-e05-arxiv-episode-calibration'
    train=json.loads((ROOT/train_run/'metrics.json').read_text())
    registry['numbers']['qwenEpisodeCalTrainRefusingEpisodes']=dict(value=train['qwen_probe']['episode_calibrated']['refusing_episodes']['rate'],macro='qwenEpisodeCalTrainRefusingEpisodes',dataset='Qwen fresh episodes',evaluation='Cutoff calibrated on in-sample development predictions; training-calibration transfer audit',status='post_hoc',run=train_run,format='percent',decimals=0,source=dict(file=train_run+'/metrics.json',value_path=['qwen_probe','episode_calibrated','refusing_episodes','rate']))
    original=registry['numbers']['qwen_fresh_input_refusing_rate']
    registry['numbers']['qwenFreshProbeAlarmRounded']=dict(original,macro='qwenFreshProbeAlarmRounded',decimals=0)
    (HERE/'numbers.yaml').write_text(json.dumps(registry,indent=2)+'\n')


if __name__=='__main__':
    main()
