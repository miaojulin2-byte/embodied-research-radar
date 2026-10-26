import json
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import evidence as e

ORGS=[{'name':'Stanford','aliases':['Stanford University'],'region':'海外'}, {'name':'清华','aliases':['Tsinghua University'],'region':'国内'}]
ROUTES=[{'id':'R2','keywords':['flow matching']},{'id':'R9','keywords':['dexterous']}]

class EvidenceTests(unittest.TestCase):
    def item(self):
        x={'id':'arxiv:2601.12345','url':'https://arxiv.org/abs/2601.12345','title':'Flow matching for robot action','abstract':'We introduce a flow matching policy for robot control.', 'verified':False}
        e.initialize(x,ROUTES)
        return x

    def test_source_excerpt_without_llm_and_route_strength(self):
        x=self.item()
        self.assertEqual(x['contribution'],x['abstract'])
        self.assertFalse(x['review'])
        self.assertFalse(x['verified'])
        self.assertEqual(x['classification_method'],'rules')
        self.assertEqual(x['field_evidence']['contribution']['source_url'],x['url'])
        self.assertIn('institution',x['missing_fields'])

    def test_affiliation_not_reference_or_robot_brand(self):
        raw='<article><div class="ltx_role_affiliation">Stanford University</div><p>We use a Unitree G1 robot.</p><div class="ltx_bibliography">Tsinghua University</div></article>'
        doc=e.parse_html(raw,'https://arxiv.org/html/2601.12345')
        x=self.item();e.extract_document(x,doc,ORGS)
        self.assertEqual(x['institution'],'Stanford')
        self.assertEqual(x['region'],'海外')
        self.assertIn('Unitree G1',x['hardware'])
        self.assertNotIn('Tsinghua',doc['text'])

    def test_unmapped_affiliation_is_retained_and_country_not_overclaimed(self):
        doc=e.parse_html('<div class="ltx_role_affiliation">Affiliation: Stanford University Affiliation: Example University</div>','https://arxiv.org/html/2601.12345')
        x=self.item();e.extract_document(x,doc,ORGS)
        self.assertIn('Example University',x['institution'])
        self.assertEqual(x['region'],'待核验')

    def test_email_contact_is_not_an_affiliation(self):
        doc=e.parse_html('<span class="ltx_contact ltx_role_email">Stanford University</span>','https://arxiv.org/html/2601.12345')
        x=self.item();e.extract_document(x,doc,ORGS)
        self.assertNotIn('institution',x)

    def test_anonymous_placeholder_is_not_an_institution(self):
        doc=e.parse_html('<div class="ltx_role_affiliation">Affiliations withheld for double-blind review</div>','https://arxiv.org/html/2601.12345')
        x=self.item();e.extract_document(x,doc,ORGS)
        self.assertNotIn('institution',x)

    def test_cross_country_affiliations(self):
        doc=e.parse_html('<div class="ltx_role_affiliation">Stanford University and Tsinghua University</div>','https://arxiv.org/html/2601.12345')
        x=self.item();e.extract_document(x,doc,ORGS)
        self.assertEqual(x['region'],'国际合作')

    def test_author_name_and_body_mentions_do_not_establish_institution(self):
        doc=e.parse_html('<p>Stanford University provides a baseline. Unitree G1 is popular.</p>','https://arxiv.org/html/2601.12345')
        x=self.item();e.extract_document(x,doc,ORGS)
        self.assertNotIn('institution',x)
        self.assertNotIn('hardware',x)

    def test_unknown_affiliation_keeps_original_without_country_guess(self):
        doc=e.parse_html('<div class="ltx_role_affiliation">Example University</div>','https://arxiv.org/html/2601.12345')
        x=self.item();e.extract_document(x,doc,ORGS)
        self.assertEqual(x['institution'],'Example University')
        self.assertNotIn('region',x)

    def test_author_link_and_baseline_link_are_distinct(self):
        doc=e.parse_html('<div class="ltx_authors"><a href="https://github.com/lab/ours">Code</a></div><p>We compare <a href="https://github.com/lab/baseline">Baseline</a>.</p>','https://arxiv.org/html/2601.12345')
        self.assertEqual(e.linked_sources(doc),['https://github.com/lab/ours'])

    def test_invented_quote_is_rejected(self):
        x=self.item();doc={'url':x['url'],'text':x['abstract'],'affiliations':''}
        class Fake:
            def json(self,*a,**kw):return {'choices':[{'message':{'content':json.dumps({'summary_zh':'一种动作策略。','claims':[{'field':'institution','value':'Stanford University','source_url':x['url'],'quote':'This nonexistent source proves Stanford University'}]})}}]}
        with patch.dict('os.environ',{'LLM_API_KEY':'test'},clear=False):
            e.grounded_llm(x,[doc],Fake(),{})
        self.assertNotIn('institution',x)
        self.assertEqual(x['rejected_claims'],['institution'])
        self.assertFalse(x['verified'])

    def test_claim_value_must_be_supported_by_its_quote(self):
        x=self.item();text='We use a Unitree G1 humanoid robot for all experiments.'
        class Fake:
            def json(self,*a,**kw):return {'choices':[{'message':{'content':json.dumps({'claims':[{'field':'hardware','value':'Franka Panda','source_url':x['url'],'quote':text}]})}}]}
        with patch.dict('os.environ',{'LLM_API_KEY':'test'},clear=False):e.grounded_llm(x,[{'url':x['url'],'text':text}],Fake(),{})
        self.assertNotIn('hardware',x)
        self.assertIn('hardware',x['rejected_claims'])

    def test_body_quote_cannot_become_author_affiliation(self):
        x=self.item();text='Stanford University developed a baseline which we compare against.'
        class Fake:
            def json(self,*a,**kw):return {'choices':[{'message':{'content':json.dumps({'claims':[{'field':'institution','value':'Stanford University','source_url':x['url'],'quote':text}]})}}]}
        with patch.dict('os.environ',{'LLM_API_KEY':'test'},clear=False):
            e.grounded_llm(x,[{'url':x['url'],'text':text,'affiliations':''}],Fake(),{})
        self.assertNotIn('institution',x)

    def test_no_unlinked_model_weights_or_deployment_from_llm(self):
        x=self.item();text='We introduce a flow matching policy for robot control.'
        class Fake:
            def json(self,*a,**kw):return {'choices':[{'message':{'content':json.dumps({'claims':[{'field':'weights','value':True,'source_url':x['url'],'quote':text},{'field':'deployment','value':True,'source_url':x['url'],'quote':text}]})}}]}
        with patch.dict('os.environ',{'LLM_API_KEY':'test'},clear=False):e.grounded_llm(x,[{'url':x['url'],'text':text}],Fake(),{})
        self.assertNotIn('weights',x)
        self.assertNotIn('deployment',x)

    def test_weight_model_card_alone_is_insufficient(self):
        class Fake:
            def json(self,*a,**kw):return {'siblings':[{'rfilename':'README.md'}],'gated':False}
        result=e.verify_resource(Fake(),'https://huggingface.co/lab/model')
        self.assertEqual(result['status'],'not_found')

    def test_weight_public_file_requires_access_probe(self):
        class Fake:
            called=False
            def json(self,*a,**kw):return {'siblings':[{'rfilename':'model.safetensors'}],'gated':False}
            def head(self,*a,**kw):self.called=True
        f=Fake();r=e.verify_resource(f,'https://huggingface.co/lab/model')
        self.assertTrue(f.called);self.assertEqual(r['status'],'supported')

    def test_checkpoint_and_time_budget_preserve_completed_item(self):
        import copy
        items=[copy.deepcopy(self.item()) for _ in range(3)]
        for n,item in enumerate(items):item['id']='arxiv:2601.'+str(12345+n)
        doc={'url':'https://arxiv.org/html/2601.12345','text':'A paper body','affiliations':'Stanford University','format':'html','links':[],'fetched_at':e.stamp()}
        checkpoints=[]
        with tempfile.TemporaryDirectory() as tmp, patch.object(e.EvidenceReader,'paper',return_value=(doc,[])), patch.object(e.time,'monotonic',side_effect=[0,0,6]):
            reports=e.enrich_documents(items,None,{'max_per_run':3,'max_seconds':5,'checkpoint_every':1,'use_llm':False},ORGS,tmp,checkpoint=lambda reports:checkpoints.append(len(reports)))
        self.assertEqual(len(reports),1)
        self.assertEqual(checkpoints,[1])
        self.assertEqual(items[0]['extraction']['status'],'complete')
        self.assertNotIn('extraction',items[1])

    def test_increased_size_budget_retries_failed_paper_same_day(self):
        x=self.item()
        x['extraction']={'version':e.VERSION,'paper_updated':x.get('updated'),'attempted_at':e.stamp(),'status':'failed','max_bytes':20000000}
        doc={'url':x['url'],'text':'Robot policy study.','format':'html','fetched_at':e.stamp(),'affiliations':'','links':[]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(e.EvidenceReader,'paper',return_value=(doc,[])):
            reports=e.enrich_documents([x],None,{'max_bytes':100000000,'use_llm':False},ORGS,tmp)
        self.assertEqual(len(reports),1)
        self.assertTrue(reports[0]['ok'])
        self.assertEqual(x['extraction']['max_bytes'],100000000)

    def test_paper_failure_preserves_underlying_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(e.EvidenceReader,'read',side_effect=ValueError('Source exceeds configured size limit')):
            with self.assertRaisesRegex(ValueError,'Source exceeds configured size limit'):
                e.EvidenceReader(None,tmp,{}).paper(self.item())

    def test_revision_invalidates_document_cache(self):
        class Fake:
            calls=0
            def get(self,*a,**kw):self.calls+=1;return b'<p>'+b'a'*250+b'</p>'
        f=Fake()
        with tempfile.TemporaryDirectory() as tmp:
            reader=e.EvidenceReader(f,tmp,{})
            reader.read('https://arxiv.org/html/2601.12345',revision='v1')
            reader.read('https://arxiv.org/html/2601.12345',revision='v1')
            reader.read('https://arxiv.org/html/2601.12345',revision='v2')
        self.assertEqual(f.calls,2)

if __name__=='__main__':unittest.main()
