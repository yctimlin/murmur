import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TREE = Path(sys.argv.pop(1))
sys.path.insert(0, str(TREE))

class CatalogueCases(unittest.TestCase):
    def setUp(self):
        self.api = importlib.import_module('catalogue')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, name='a.json', **values):
        data = dict(id='Alpha', title='Routing Guide')
        data.update(values)
        file = self.root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(data), encoding='utf-8')
        return file

    def build(self):
        return self.api.build_catalog(self.root)

    def search(self, docs, query='', **options):
        return self.api.search_catalog({'documents': docs, 'errors': []}, query, **options)

    def doc(self, identity, **values):
        result = dict(id=identity,title='',body='',revision=1,tags=[],links=[],status='published',updated='2025-01-01',path=identity+'.json',broken_links=[])
        result.update(values)
        return result

    def test_01_defaults(self):
        self.put()
        self.assertEqual(self.build(), {'documents':[self.doc('alpha',title='Routing Guide',updated='1970-01-01',path='a.json')], 'errors':[]})

    def test_02_recursive_and_id_order(self):
        self.put('deep/z.json',id='z')
        self.put('x/a.json',id='a')
        self.assertEqual([x['id'] for x in self.build()['documents']], ['a','z'])

    def test_03_ignore_directories(self):
        self.put('.private/a.json'); self.put('_cache/a.json'); self.put('ok/a.json')
        self.assertEqual([x['path'] for x in self.build()['documents']], ['ok/a.json'])

    def test_04_ignore_symlinks(self):
        source = self.put('real/a.json')
        (self.root/'alias.json').symlink_to(source)
        (self.root/'aliasdir').symlink_to(source.parent, target_is_directory=True)
        self.assertEqual([x['path'] for x in self.build()['documents']], ['real/a.json'])

    def test_05_extension(self):
        self.put('x.JSON',id='upper'); self.put('x.txt',id='text'); self.put('x.json',id='ok')
        self.assertEqual([x['id'] for x in self.build()['documents']], ['ok'])

    def test_06_bom(self):
        self.put().write_bytes(b'\xef\xbb\xbf'+b'{"id":"a","title":"BOM"}')
        self.assertEqual(self.build()['documents'][0]['title'],'BOM')

    def test_07_invalid_json(self):
        self.put('z.json').write_text('{')
        self.assertEqual(self.build()['errors'],[{'path':'z.json','code':'json'}])

    def test_08_invalid_encoding(self):
        self.put().write_bytes(b'\xff')
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'json'}])

    def test_09_non_object(self):
        self.put().write_text('[1,2]')
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_10_missing_required(self):
        self.put().write_text('{"id":"alpha"}')
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_11_empty_identity(self):
        self.put(id='   ')
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_12_non_string_title(self):
        self.put(title=12)
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_13_boolean_revision(self):
        self.put(revision=True)
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_14_zero_revision(self):
        self.put(revision=0)
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_15_wrong_body_type(self):
        self.put(body=None)
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_16_wrong_tags_type(self):
        self.put(tags='network')
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_17_blank_link(self):
        self.put(links=[' '])
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_18_invalid_status(self):
        self.put(status='Published')
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_19_invalid_date(self):
        self.put(updated='2025-02-29')
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_20_exact_date_format(self):
        self.put(updated='2024-2-9')
        self.assertEqual(self.build()['errors'],[{'path':'a.json','code':'schema'}])

    def test_21_normalization(self):
        self.put(id=' Straße ',title='  T  ',body=' x\n ',tags=[' B ','a','A'],links=[' Z ','z'],updated='2024-02-29')
        doc=self.build()['documents'][0]
        self.assertEqual((doc['id'],doc['title'],doc['body'],doc['tags'],doc['links']),('strasse','T',' x\n ',['a','b'],['z']))

    def test_22_unknown_fields_ignored(self):
        self.put(extra='ignore')
        self.assertEqual(set(self.build()['documents'][0]),set(self.doc('x')))

    def test_23_revision_wins(self):
        self.put('a.json',revision=1,updated='2026-01-01')
        self.put('b.json',revision=2,updated='2020-01-01')
        self.assertEqual(self.build()['documents'][0]['path'],'b.json')

    def test_24_updated_breaks_tie(self):
        self.put('a.json',updated='2024-01-01'); self.put('b.json',updated='2025-01-01')
        self.assertEqual(self.build()['documents'][0]['path'],'b.json')

    def test_25_path_breaks_tie(self):
        self.put('z.json'); self.put('a.json')
        self.assertEqual(self.build()['documents'][0]['path'],'a.json')

    def test_26_draft_can_replace(self):
        self.put('a.json'); self.put('b.json',revision=2,status='draft')
        data=self.build()
        self.assertEqual((len(data['documents']),self.api.search_catalog(data)),(1,[]))

    def test_27_broken_links_after_winners(self):
        self.put(links=['ALPHA','draft','gone','gone'])
        self.put('b.json',id='draft',status='draft')
        self.assertEqual(self.build()['documents'][0]['broken_links'],['gone'])

    def test_28_sorted_errors_valid_survives(self):
        self.put('z.json',body=1); self.put('a.json',revision=-1); self.put('valid.json')
        data=self.build()
        self.assertEqual((data['errors'],len(data['documents'])),([{'path':'a.json','code':'schema'},{'path':'z.json','code':'schema'}],1))

    def test_29_missing_root(self):
        with self.assertRaises(ValueError): self.api.build_catalog(self.root/'missing')

    def test_30_file_root(self):
        path=self.put()
        with self.assertRaises(ValueError): self.api.build_catalog(path)

    def test_31_default_status(self):
        docs=[self.doc('a'),self.doc('b',status='draft'),self.doc('c',status='archived')]
        self.assertEqual(self.search(docs),['a'])

    def test_32_status_any_and_draft(self):
        docs=[self.doc('a'),self.doc('b',status='draft')]
        self.assertEqual((self.search(docs,status='any'),self.search(docs,status='draft')),(['a','b'],['b']))

    def test_33_all_query_tokens(self):
        docs=[self.doc('a',title='red',body='fox'),self.doc('b',title='red')]
        self.assertEqual(self.search(docs,'RED fox'),['a'])

    def test_34_no_substring_match(self):
        self.assertEqual(self.search([self.doc('a',title='router'),self.doc('b',title='route')],'route'),['b'])

    def test_35_unicode_and_underscore(self):
        self.assertEqual(self.search([self.doc('a',title='Straße_café')],'STRASSE CAFÉ'),['a'])

    def test_36_score_weights(self):
        docs=[self.doc('body',body='cat'),self.doc('tag',tags=['cat']),self.doc('title',title='cat')]
        self.assertEqual(self.search(docs,'cat'),['title','tag','body'])

    def test_37_occurrences_and_unique_query(self):
        docs=[self.doc('a',body='cat cat dog'),self.doc('b',body='cat dog dog')]
        self.assertEqual(self.search(docs,'cat cat dog'),['a','b'])

    def test_38_date_then_id_sort(self):
        docs=[self.doc('z',updated='2026-01-01'),self.doc('b'),self.doc('a')]
        self.assertEqual(self.search(docs),['z','a','b'])

    def test_39_tags_and_normalization(self):
        docs=[self.doc('a',tags=['x','y']),self.doc('b',tags=['x'])]
        self.assertEqual(self.search(docs,tags=[' X ','Y','x']),['a'])

    def test_40_limit(self):
        docs=[self.doc('a'),self.doc('b')]
        self.assertEqual((self.search(docs,limit=0),self.search(docs,limit=1)),([],['a']))

    def test_41_invalid_arguments(self):
        for kw in [{'limit':True},{'limit':-1},{'limit':1.5},{'status':'bad'},{'tags':'x'},{'tags':[' ']},{'query':None}]:
            with self.subTest(kw=kw), self.assertRaises(ValueError): self.search([],**kw)

    def test_42_no_mutation(self):
        docs=[self.doc('b',title='x'),self.doc('a',title='x')]
        original=copy.deepcopy(docs)
        self.assertEqual(self.search(docs,'x'),['a','b'])
        self.assertEqual(docs,original)

    def test_43_punctuation_query(self):
        self.assertEqual(self.search([self.doc('a')],' -- ! '),['a'])

    def cli(self,*args):
        return subprocess.run([sys.executable,'-m','catalogue',*map(str,args)],cwd=TREE,text=True,capture_output=True,timeout=10)

    def test_44_cli_build(self):
        self.put(); out=self.root.parent/(self.root.name+'-index.json'); self.addCleanup(out.unlink,missing_ok=True)
        run=self.cli('build',self.root,'--output',out)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(out.read_text())['documents'][0]['id'],'alpha')

    def test_45_cli_search(self):
        idx=self.root/'index.json'; idx.write_text(json.dumps({'documents':[self.doc('a',title='Cat',tags=['x'])],'errors':[]}))
        run=self.cli('search',idx,'cat','--tag','X','--limit','1')
        self.assertEqual((run.returncode,json.loads(run.stdout)),(0,['a']))

    def test_46_cli_fatal(self):
        run=self.cli('search',self.root/'absent.json','x')
        self.assertEqual(run.returncode,2)
        self.assertTrue(run.stderr.strip()); self.assertNotIn('Traceback',run.stderr)

    def test_47_cli_build_record_error(self):
        self.put().write_text('{'); out=self.root.parent/(self.root.name+'-index.json'); self.addCleanup(out.unlink,missing_ok=True)
        run=self.cli('build',self.root,'--output',out)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(out.read_text())['errors'],[{'path':'a.json','code':'json'}])

    def test_48_corpus(self):
        result=self.api.build_catalog(TREE/'archive')
        self.assertEqual((len(result['documents']),len(result['errors'])),(310,0))
        self.assertEqual(sum(x['revision']==2 for x in result['documents']),26)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CatalogueCases)
    result=unittest.TextTestRunner(stream=sys.stderr,verbosity=1).run(suite)
    total=result.testsRun
    failed = {getattr(test, 'test_case', test).id() for test, _ in result.failures + result.errors + result.skipped}
    passed=total-len(failed)
    print(json.dumps({'passed':passed,'total':total,'rate':passed/total}))
