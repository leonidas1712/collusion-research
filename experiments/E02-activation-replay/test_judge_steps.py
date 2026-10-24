import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from judge_steps import own_text, prepare, step_key

class PrefixJudgeTests(unittest.TestCase):
    def test_only_prior_target_authored_text(self):
        messages=[{'role':'system','content':'share'}, {'role':'user','content':'agree'},
          {'role':'assistant','content':'I refuse'}, {'role':'tool','content':'secret'},
          {'role':'assistant','tool_calls':[{'function':{'name':'send_message','arguments':json.dumps({'content':'I defer'})}}]}]
        self.assertEqual(own_text(messages),[{'source':'assistant_text','text':'I refuse'}, {'source':'send_message_content','text':'I defer'}])

    def test_no_current_response_or_future_outcome_in_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ep=root/'episode.json';plan=root/'steps.jsonl';out=root/'out'
            ep.write_text(json.dumps({'label':{'future':'MUST_NOT_APPEAR'},'requests':[
                {'actor':'target','request':{'messages':[{'role':'assistant','content':'I refuse'}]},
                 'response':{'content':'MUST_NOT_APPEAR'}}]}))
            row={'episode_key':'run/episode.json','episode_file':'episode.json','request_idx':0,'run_id':'run','round':1,'step_in_turn':1,'request_sha256':'existing','label_will_violate':'MUST_NOT_APPEAR'}
            plan.write_text(json.dumps(row)+'\n')
            with patch('judge_steps.ROOT',root):prepare(plan,out)
            self.assertNotIn('MUST_NOT_APPEAR',(out/'inputs.json').read_text())
            self.assertEqual(json.loads((out/'step-joins.json').read_text())[0]['step_id'],step_key(row))

    def test_tool_ids_do_not_change_semantic_projection(self):
        def message(callid):return [{'role':'assistant','tool_calls':[{'id':callid,'function':{'name':'write_file','arguments':'{"content":"status ready"}'}}]}]
        self.assertEqual(own_text(message('a')),own_text(message('b')))

if __name__=='__main__':unittest.main()
