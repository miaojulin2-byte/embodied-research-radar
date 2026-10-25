import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from site_data import write_site_data

class SiteDataTests(unittest.TestCase):
    def fixture(self):
        return {'generated_at':'2026-10-25T04:00:00+00:00','history':[{'large':'unused'}],
            'metrics':{'repositories':{},'models':{},'papers':{}},'editorial':{'picks':[{'id':'one'}]},
            'items':[{'id':'one','url':'https://example.org/one','title':'First','published':'2026-08-01','review':False,'field_evidence':{'hardware':{'value':'Franka','quote':'We use Franka.'}}},
                     {'id':'two','url':'https://example.org/two','title':'Second','published':'2024-01-01','review':True,'abstract':'large source abstract'}]}
    def test_home_is_small_and_stats_cover_entire_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_site_data(self.fixture(),tmp)
            home=json.loads((Path(tmp)/'dashboard-home.json').read_text())
            self.assertEqual(len(home['items']),1)
            self.assertEqual(home['dataset_stats'],{'total':2,'recent':1,'review':1})
            self.assertNotIn('history',home)
            self.assertFalse(home['index_loaded'])
    def test_full_evidence_is_lazy_and_keeps_matching_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_site_data(self.fixture(),tmp)
            index=json.loads((Path(tmp)/'dashboard-index.json').read_text())
            self.assertEqual(len(index['items']),2)
            item=index['items'][0]
            self.assertNotIn('field_evidence',item)
            full=json.loads((Path(tmp)/'items'/(item['detail_key']+'.json')).read_text())
            self.assertEqual(full['id'],item['id'])
            self.assertEqual(full['field_evidence']['hardware']['value'],'Franka')

if __name__=='__main__':unittest.main()
