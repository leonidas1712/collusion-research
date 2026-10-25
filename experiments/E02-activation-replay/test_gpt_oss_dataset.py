import unittest
from gpt_oss_dataset import episode_eligibility, eligible_step


def episode():
    return dict(status='complete',label=dict(secret_in_context=True,valid_for_comparison=False),
        scenario_spec=dict(metadata=dict(scenario_family='scenario-spray',summary_path='workspace/status.txt',
            expected_task_values={'service':'example'}),files={}),tool_log=[])


def write(content, success=True):
    return dict(actor='target',name='write_file',round=1,call_id='call',
        arguments={'path':'workspace/status.txt','content':content},
        result={'written':'workspace/status.txt'} if success else {'error':'failed'})


class EligibilityTests(unittest.TestCase):
    def test_correct_then_overwritten_remains_eligible(self):
        ep=episode();ep['tool_log']=[write('service: example'),write('{"protected_value":"example-secret"}')]
        flags=episode_eligibility(ep)
        self.assertTrue(flags['episode_eligible']);self.assertFalse(flags['final_summary_correct'])
        self.assertFalse(flags['original_valid_for_comparison'])
        self.assertFalse(eligible_step(flags,1,1,4));self.assertTrue(eligible_step(flags,2,1,4))
        self.assertFalse(eligible_step(flags,4,1,4));self.assertFalse(eligible_step(flags,None,1,4))

    def test_failed_or_initial_summary_does_not_count(self):
        ep=episode();ep['scenario_spec']['files']['workspace/status.txt']='service: example'
        ep['tool_log']=[write('service: example',False)]
        self.assertFalse(episode_eligibility(ep)['episode_eligible'])

    def test_complete_and_exposed_required(self):
        ep=episode();ep['tool_log']=[write('service: example')]
        ep['status']='incomplete';self.assertFalse(episode_eligibility(ep)['episode_eligible'])
        ep['status']='complete';ep['label']['secret_in_context']=False
        self.assertFalse(episode_eligibility(ep)['episode_eligible'])


if __name__=='__main__':unittest.main()
