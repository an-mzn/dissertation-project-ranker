import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from ranker_session import load_session
from ranker_window import PAGE, RankerWindow
import test_ranker_data

ROOT = test_ranker_data.ROOT


class ReleaseChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_ranker_data.NotebookTests.setUpClass()
        cls.ranker_class = test_ranker_data.NotebookTests.namespace['ProjectRanker']

    def ranker(self, path=None):
        return self.ranker_class(
            [['', 'First', 'Brief'], ['', 'Second', 'Other']], [(1, 2)], [0, 0],
            [{'ranks': [], 'sections': [], 'tags': [], 'summary': '', 'potential_stack': '',
              'difficulty': None, 'ai_assistance': None} for _ in range(2)], save_path=path)

    def test_corrupt_session_shapes_recover_from_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'session.json'
            ranker = self.ranker(path)
            ranker.save_progress()
            state = json.loads(path.read_text())
            path.with_suffix('.json.bak').write_text(json.dumps(state))
            bad_states = [[], None, 3, dict(state, comparisons=[3]), dict(state, history=[3], position=1),
                          dict(state, scores={}), dict(state, answer_budget='wrong'),
                          dict(state, adaptive_schedule='false'), dict(state, stability_review_after=-1)]
            for bad in bad_states:
                with self.subTest(bad=bad):
                    path.write_text(json.dumps(bad))
                    self.assertEqual(load_session(path, ranker.projects)['scores'], [0, 0])
            path.with_suffix('.json.bak').write_text('[]')
            with self.assertRaisesRegex(ValueError, 'Cannot restore'):
                load_session(path, ranker.projects)
            ranker.view.close()

    def test_completion_clears_cards_and_undo_restores_them(self):
        ranker = self.ranker()
        ranker.choose(0)
        self.assertEqual(ranker.options.value, '')
        self.assertTrue(ranker.choose_a.disabled)
        ranker.back()
        self.assertIn('First', ranker.options.value)
        self.assertFalse(ranker.choose_a.disabled)
        ranker.view.close()

    def test_browser_actions_and_invalid_payloads(self):
        ranker = self.ranker()
        window = RankerWindow(ranker)
        try:
            self.assertEqual(window.server.server_address[0], '127.0.0.1')
            for data in (b'null', b'[]', b'{"action":"unknown"}', b'broken'):
                with self.subTest(data=data), self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(window.url+'action', data=data))
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
            request = urllib.request.Request(window.url+'action', data=b'{"action":"a"}')
            state = json.load(urllib.request.urlopen(request))
            self.assertTrue(state['complete'])
            self.assertEqual(state['options'], '')
        finally:
            window.close()
            ranker.view.close()

    def test_summary_clicks_are_excluded_from_card_selection(self):
        # A summary is interactive: opening original text must not submit a choice.
        self.assertIn("event.target.closest('a,button,input,textarea,select,summary')", PAGE)

    def test_public_notebook_has_no_saved_outputs(self):
        notebook = json.loads((ROOT/'Ranker.ipynb').read_text())
        self.assertNotIn('widgets', notebook['metadata'])
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                self.assertEqual(cell['outputs'], [])
                self.assertIsNone(cell['execution_count'])


if __name__ == '__main__':
    unittest.main()
