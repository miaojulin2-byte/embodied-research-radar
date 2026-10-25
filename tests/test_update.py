import importlib.util
from pathlib import Path
import unittest
from datetime import timedelta

spec = importlib.util.spec_from_file_location('update', Path(__file__).parents[1] / 'scripts/update.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

class PipelineTests(unittest.TestCase):
    def test_version_dedup_and_preserve_review(self):
        old = [{'id':'arxiv:2501.12345', 'url':'https://arxiv.org/abs/2501.12345', 'title':'Reviewed', 'institution':'Verified lab', 'verified':True}]
        incoming = [{'id':'arxiv:2501.12345v3','url':'https://arxiv.org/abs/2501.12345v3','title':'New title','abstract':'new abstract','updated':'2026-01-02','verified':False}]
        out = u.merge_items(old,incoming)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]['id'],'arxiv:2501.12345')
        self.assertEqual(out[0]['institution'],'Verified lab')
        self.assertEqual(out[0]['abstract'],'new abstract')

    def test_explicit_cross_source_alias(self):
        out = u.merge_items([{'id':'blog:test','url':'https://lab.test/post','title':'Demo'}],[{'id':'arxiv:2501.12345','url':'https://arxiv.org/abs/2501.12345','title':'Paper','aliases':['blog:test']}])
        self.assertEqual(len(out),1)
        self.assertIn('https://lab.test/post',out[0]['sources'])

    def test_metadata_refresh_preserves_source_grounded_field(self):
        old=[{'id':'arxiv:2501.12345','url':'https://arxiv.org/abs/2501.12345','institution':'Stanford','field_evidence':{'institution':{'value':'Stanford','status':'supported'}}}]
        out=u.merge_items(old,[{'id':'arxiv:2501.12345','url':'https://arxiv.org/abs/2501.12345','institution':'待核验','verified':False}])
        self.assertEqual(out[0]['institution'],'Stanford')

    def test_partial_arxiv_pages_are_not_discarded_on_later_failure(self):
        class Fake:
            calls=0
            def get(self,*args,**kw):
                self.calls+=1
                if self.calls==2:raise TimeoutError()
                return b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/"><o:totalResults>2</o:totalResults><entry><id>http://arxiv.org/abs/2501.12345v2</id><title>A paper</title></entry></feed>'
        cfg={'categories':['cs.RO'],'keywords':['robot'],'page_size':1,'max_pages':3,'delay_seconds':3.2}
        rows,status=u.fetch_arxiv(Fake(),cfg,u.now())
        self.assertEqual(len(rows),1);self.assertFalse(status['complete']);self.assertEqual(status['error'],'TimeoutError')

    def test_no_fuzzy_title_merge(self):
        out=u.merge_items([], [{'url':'https://a.test','title':'Same'},{'url':'https://b.test','title':'Same'}])
        self.assertEqual(len(out),2)

    def test_baseline_missing_is_not_zero(self):
        self.assertIsNone(u.week_growth([],{'papers':{'a':{'citations':2,'observed_at':u.iso()}}},'papers','a','citations'))

    def test_week_delta_and_stale_failure(self):
        before=(u.now()-timedelta(days=7,hours=1)).isoformat()
        hist=[{'at':before,'papers':{'a':{'citations':10,'observed_at':before}}}]
        current={'papers':{'a':{'citations':13,'observed_at':u.iso()}}}
        self.assertEqual(u.week_growth(hist,current,'papers','a','citations'),3)
        current['papers']['a']['observed_at']=(u.now()-timedelta(days=3)).isoformat()
        self.assertIsNone(u.week_growth(hist,current,'papers','a','citations'))

    def test_atom_error_not_empty_success(self):
        with self.assertRaises(ValueError):
            u.parse_atom(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors</id><title>Error</title></entry></feed>')

    def test_atom_original_date_and_versions(self):
        raw=b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/"><o:totalResults>1</o:totalResults><entry><id>http://arxiv.org/abs/2501.12345v2</id><title>A paper</title><published>2025-01-01T00:00:00Z</published><updated>2026-01-01T00:00:00Z</updated></entry></feed>'
        rows,total=u.parse_atom(raw)
        self.assertEqual(total,1)
        self.assertEqual(rows[0]['published'],'2025-01-01')
        self.assertEqual(rows[0]['id'],'arxiv:2501.12345')

    def test_ambiguous_rule_stays_reviewed(self):
        item={'title':'An approach to robots', 'url':'https://arxiv.org/abs/2601.12345', 'abstract':'We study a dataset.'}
        u.initialize(item,u.load('routes.yaml'))
        self.assertEqual(set(item['routes']),{'R7'})
        self.assertTrue(item['review'])
        self.assertLess(item['confidence'],0.8)

if __name__=='__main__':unittest.main()
