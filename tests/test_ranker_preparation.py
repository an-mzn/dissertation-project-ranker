import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ranker_data import load_projects
from ranker_formatting import render_readable_description
from ranker_model import fit_preferences
from ranker_schedule import prioritise_next
from ranker_session import load_session

ROOT = Path(__file__).resolve().parents[1]


def fresh(projects, ratings):
    count = len(projects)
    return SimpleNamespace(projects=projects, reference_ratings=ratings, scores=[0]*count,
                           comparisons=[(a, b) for a in range(1, count+1) for b in range(a+1, count+1)],
                           history=[], position=0)


class PreparationTests(unittest.TestCase):
    def load(self, csv, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'projects.csv'
            path.write_text(csv)
            return load_projects(path, {'title': 'title', 'draft_rank': 'draft_rank',
                                        'topics': 'topics', 'readable_description': 'readable_description'}, **kwargs)

    def test_metadata_and_neutral_defaults(self):
        projects, ratings = self.load('title,draft_rank,topics,readable_description\nA,3,New;Other;New,## Overview\nB,1,,\nC,,,\n')
        self.assertEqual(ratings[0]['sections'], ['New', 'Other'])
        self.assertEqual(ratings[0]['draft_rank'], 3)
        self.assertEqual(ratings[1]['readable_description'], '')
        np.testing.assert_allclose(fit_preferences(fresh(projects, ratings))['score'], [50, 50, 50])

    def test_optional_priors_missing_and_single_ranks(self):
        projects, ratings = self.load('title,draft_rank,topics,readable_description\nA,30,,\nB,2,,\nC,,,\nD,10,,\n', use_draft_prior=True)
        ranker = fresh(projects, ratings)
        np.testing.assert_allclose(fit_preferences(ranker)['score'], [35, 65, 50, 50])
        original = set(ranker.comparisons)
        prioritise_next(ranker)
        self.assertEqual(set(ranker.comparisons), original)
        self.assertTrue(all(r['ranks'] == [] for r in ratings))
        projects, ratings = self.load('title,draft_rank,topics,readable_description\nA,1,,\nB,,,\n', use_draft_prior=True)
        np.testing.assert_allclose(fit_preferences(fresh(projects, ratings))['score'], [50, 50])

    def test_invalid_and_duplicate_ranks(self):
        for value in ('0', '-1', '1.5', 'nan', '1.0', 'wrong'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'positive integer'):
                self.load(f'title,draft_rank,topics,readable_description\nA,{value},,\nB,,,\n')
        with self.assertRaisesRegex(ValueError, 'duplicate draft_rank'):
            self.load('title,draft_rank,topics,readable_description\nA,1,,\nB,01,,\n')

    def test_prior_changes_invalidate_model_without_losing_evidence(self):
        projects, ratings = self.load('title,draft_rank,topics,readable_description\nA,1,,\nB,2,,\n', use_draft_prior=True)
        ranker = fresh(projects, ratings)
        ranker.history = [(0, 0)]
        ranker.position = 1
        ranker.scores = [10, -10]
        first = fit_preferences(ranker)
        for rating in ratings:
            rating['draft_prior'] = .5
        second = fit_preferences(ranker)
        self.assertIsNot(first, second)
        self.assertEqual(second['answer_count'], 1)
        self.assertGreater(second['score'][0], 50)
        ranker.history.clear()
        ranker.position = 0
        ranker.scores = [0, 0]
        np.testing.assert_allclose(fit_preferences(ranker)['score'], [50, 50])

    def test_safe_markdown_blocks(self):
        result = render_readable_description('## Overview\n\nFirst paragraph\ncontinued\n\n- A\n- B\n\n3. C\n4. D\n\n<script>alert(1)</script>\n![image](https://example.org/x)')
        self.assertIn('<h5>Overview</h5>', result)
        self.assertIn('<ul><li>A</li><li>B</li></ul>', result)
        self.assertIn('<ol start="3"><li>C</li><li>D</li></ol>', result)
        self.assertIn('First paragraph\ncontinued', result)
        self.assertNotIn('<script>', result)
        self.assertNotIn('<img', result)
        self.assertIn('&lt;script&gt;', result)

    def test_notebook_reruns_and_restore_with_enriched_metadata(self):
        notebook = json.loads((ROOT/'Ranker.ipynb').read_text())
        ns = {'Path': Path}
        projects, ratings = load_projects(ROOT/'examples/projects.csv', {
            key: key for key in ('title', 'supervisor', 'description', 'tags', 'summary', 'tools',
                                'difficulty', 'ai_assistance', 'readable_description', 'draft_rank', 'topics')})
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            ns.update(data=projects, project_ratings=ratings, save_path=Path(directory)/'session.json')
            for i in range(2, 8):
                exec(''.join(notebook['cells'][i]['source']), ns)
            ranker = ns['ranker']
            self.assertIn('<details><summary>Original university description</summary>', ranker.options.value)
            self.assertIn('Draft rank', ranker.options.value)
            ranker.choose(0)
            scores = list(ranker.scores)
            state = load_session(ns['save_path'], projects)
            self.assertEqual(state['scores'], scores)
            ranker.back()
            self.assertEqual(ranker.scores, [0]*len(projects))
            ranker.choose(0)
            # Change metadata and priors, then rerun setup without resetting choices.
            for rating in ratings:
                rating['draft_prior'] = .6
                rating['sections'] = ['Fresh topic']
            for i in range(2, 8):
                exec(''.join(notebook['cells'][i]['source']), ns)
            self.assertEqual(ns['ranker'].scores, scores)
            self.assertEqual(ns['ranker'].position, 1)
            self.assertIn('Fresh topic', ns['ranker'].options.value)
            self.assertEqual(fit_preferences(ns['ranker'])['answer_count'], 1)
            self.assertEqual(load_session(ns['save_path'], projects)['scores'], scores)
            # Simulate a new kernel: restore the same choices from disk.
            del ns['ranker']
            for i in range(2, 8):
                exec(''.join(notebook['cells'][i]['source']), ns)
            self.assertEqual(ns['ranker'].scores, scores)
            self.assertEqual(ns['ranker'].position, 1)
            ns['ranker'].view.close()


if __name__ == '__main__':
    unittest.main()
