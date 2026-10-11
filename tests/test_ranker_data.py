import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ranker_data import load_projects, session_path
from ranker_model import fit_preferences
from ranker_session import load_session

ROOT = Path(__file__).resolve().parents[1]


class DataTests(unittest.TestCase):
    def load(self, content, columns, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'projects.csv'
            path.write_text(content, encoding='utf-8')
            return load_projects(path, columns, **kwargs)

    def test_reordered_headers_and_optional_metadata(self):
        projects, ratings = self.load(
            'tags,name,level,brief\nNovel; Space;Novel,A,3.5,First\n,B,,Second\n',
            {'title': 'name', 'tags': 'tags', 'difficulty': 'level', 'description': 'brief'})
        self.assertEqual(projects, [['', 'A', 'First'], ['', 'B', 'Second']])
        self.assertEqual(ratings[0]['tags'], ['Novel', 'Space'])
        self.assertEqual(ratings[0]['difficulty'], 3.5)
        self.assertIsNone(ratings[1]['difficulty'])
        ranker = SimpleNamespace(projects=projects, reference_ratings=ratings,
                                 scores=[0, 0], comparisons=[(1, 2)], history=[], position=0)
        np.testing.assert_allclose(fit_preferences(ranker)['score'], [50, 50])

    def test_headerless_and_custom_delimiter(self):
        projects, _ = self.load('S|A|Brief\nT|B|Other\n',
                                {'supervisor': 0, 'title': 1, 'description': 2},
                                has_header=False, delimiter='|')
        self.assertEqual(projects[1], ['T', 'B', 'Other'])

    def test_invalid_inputs(self):
        cases = [
            ('name\nA\nB\n', {}, {}, 'title column'),
            ('name\nA\nB\n', {'title': 'absent'}, {}, 'header'),
            ('name\nA\nB\n', {'title': 2}, {}, 'outside'),
            ('name\nA\nB\n', {'title': -1}, {}, 'nonnegative'),
            ('A\nB\n', {'title': 'name'}, {'has_header': False}, 'requires a header'),
            ('name\nA\nB\n', {'title': 'name', 'unknown': 0}, {}, 'Unknown'),
            ('name,s\n,S\nB,T\n', {'title': 'name'}, {}, 'title is required'),
            ('name\nA\na.\n', {'title': 'name'}, {}, 'duplicate'),
            ('name\nA\n', {'title': 'name'}, {}, 'at least two'),
            ('name,s\nA\nB,T\n', {'title': 'name', 'supervisor': 's'}, {}, 'missing column'),
        ]
        for text, columns, kwargs, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.load(text, columns, **kwargs)
        for field in ('difficulty', 'ai_assistance'):
            for value in ('0', '11', 'nan', 'inf', 'wrong'):
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, '1 to 10'):
                    self.load(f'name,rating\nA,{value}\nB,\n', {'title': 'name', field: 'rating'})

    def test_session_paths_are_per_csv(self):
        self.assertNotEqual(session_path('data/a.csv'), session_path('data/b.csv'))
        self.assertEqual(session_path('data/a.csv').name, 'a.csv.ranker-session.json')


class NotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        notebook = json.loads((ROOT / 'Ranker.ipynb').read_text())
        source = ''.join(notebook['cells'][7]['source'])
        cls.namespace = {'Path': Path}
        exec(source.split('# Rerunning setup/display cells preserves')[0], cls.namespace)

    def test_choices_skip_undo_save_and_restore(self):
        projects, ratings = load_projects(ROOT / 'examples/projects.csv', {
            field: field for field in ('title', 'supervisor', 'description', 'tags', 'summary', 'tools',
                                      'difficulty', 'ai_assistance')})
        pairs = [(a, b) for a in range(1, len(projects)+1) for b in range(a+1, len(projects)+1)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.json'
            ranker = self.namespace['ProjectRanker'](projects, pairs, [0]*len(projects), ratings, save_path=path)
            ranker.choose(0)
            scores = list(ranker.scores)
            ranker.skip()
            self.assertEqual(ranker.scores, scores)
            ranker.back()
            self.assertEqual(ranker.position, 1)
            ranker.back()
            self.assertEqual(ranker.scores, [0]*len(projects))
            ranker.choose(2)
            ranker.show_ranking()
            self.assertIn('Current top 20', ranker.ranking.value)
            state = load_session(path, projects)
            restored = self.namespace['ProjectRanker'](
                projects, [tuple(pair) for pair in state['comparisons']], state['scores'], ratings,
                position=state['position'], history=state['history'], save_path=path)
            self.assertEqual(restored.position, ranker.position)
            self.assertEqual(restored.scores, ranker.scores)
            # Corrupt primary checkpoint: load the preceding valid backup.
            path.write_text('broken')
            self.assertIsNotNone(load_session(path, projects))
            with self.assertRaisesRegex(ValueError, 'Cannot restore'):
                load_session(path, list(reversed(projects)))
            ranker.view.close()
            restored.view.close()

    def test_missing_metadata_is_hidden(self):
        ranker = self.namespace['ProjectRanker'](
            [['', 'First', 'Brief'], ['', 'Second', 'Other']], [(1, 2)], [0, 0],
            [{'ranks': [], 'sections': [], 'tags': [], 'summary': '', 'potential_stack': '',
              'difficulty': None, 'ai_assistance': None} for _ in range(2)])
        for label in ('Difficulty', 'AI assistance', 'Draft ranking', 'Supervisor:', 'At a glance', 'Potential tools'):
            self.assertNotIn(label, ranker.options.value)
        ranker.view.close()

    def test_notebooks_are_output_free_and_compile(self):
        for path in (ROOT/'Ranker.ipynb',):
            notebook = json.loads(path.read_text())
            for cell in notebook['cells']:
                if cell['cell_type'] == 'code':
                    self.assertEqual(cell['outputs'], [])
                    self.assertIsNone(cell['execution_count'])
                    compile(''.join(cell['source']), str(path), 'exec')


if __name__ == '__main__':
    unittest.main()
