# coding: utf-8
import unittest
import mocker

from balaio import models
from balaio import validator
from balaio import utils
from balaio.tests.doubles import *


#
# Pipes
#
class SetupPipeTests(mocker.MockerTestCase):

    def _makeOne(self, data, **kwargs):
        from balaio import utils
        _scieloapi = kwargs.get('_scieloapi', ScieloAPIClientStub())
        _notifier = kwargs.get('_notifier', lambda args: NotifierStub)
        _sapi_tools = kwargs.get('_sapi_tools', get_ScieloAPIToolbeltStubModule())
        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _issn_validator = kwargs.get('_issn_validator', utils.is_valid_issn)

        vpipe = validator.SetupPipe(scieloapi=_scieloapi,
                                    notifier=_notifier,
                                    sapi_tools=_sapi_tools,
                                    pkg_analyzer=_pkg_analyzer,
                                    issn_validator=_issn_validator)
        vpipe.feed(data)
        return vpipe

    def test_transform_returns_right_datastructure(self):
        """
        The right datastructure is a tuple in the form:
        (<models.Attempt>, <checkin.PackageAnalyzer>, <dict>)
        """
        data = "<root><issn pub-type='epub'>0102-6720</issn></root>"

        scieloapi = ScieloAPIClientStub()
        scieloapi.issues.filter = lambda print_issn=None, eletronic_issn=None, volume=None, number=None, suppl_volume=None, suppl_number=None, limit=None: [{}]

        vpipe = self._makeOne(data, _scieloapi=scieloapi)
        vpipe._notifier = lambda args: NotifierStub()
        result = vpipe.transform(AttemptStub())

        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], AttemptStub)
        self.assertIsInstance(result[1], PackageAnalyzerStub)
        # index 2 is the return data from scieloapi.journals.filter
        # so, testing its type actualy means nothing.
        self.assertEqual(len(result), 3)

    def test_fetch_journal_data_with_valid_criteria(self):
        """
        Valid criteria means a valid querystring param.
        See a list at http://ref.scielo.org/nssk38

        The behaviour defined by the Restful API is to
        ignore the query for invalid criteria, and so
        do we.
        """
        data = "<root><issn pub-type='epub'>0102-6720</issn></root>"
        scieloapi = ScieloAPIClientStub()
        scieloapi.journals.filter = lambda **kwargs: [{'foo': 'bar'}]

        vpipe = self._makeOne(data, _scieloapi=scieloapi)
        self.assertEqual(vpipe._fetch_journal_data({'print_issn': '1234-1234'}),
                         {'foo': 'bar'})

    def test_fetch_journal_data_with_unknown_issn_raises_ValueError(self):
        data = "<root><issn pub-type='epub'>0102-6720</issn></root>"
        scieloapi = ScieloAPIClientStub()
        scieloapi.journals.filter = lambda **kwargs: []

        sapi_tools = get_ScieloAPIToolbeltStubModule()

        def _get_one(dataset):
            raise ValueError()
        sapi_tools.get_one = _get_one

        vpipe = self._makeOne(data, _scieloapi=scieloapi, _sapi_tools=sapi_tools)
        self.assertRaises(ValueError,
                          lambda: vpipe._fetch_journal_data({'print_issn': '1234-1234'}))

    def test_fetch_journal_issue_data_with_valid_criteria(self):
        """
        Valid criteria means a valid querystring param.
        See a list at http://ref.scielo.org/nssk38

        The behaviour defined by the Restful API is to
        ignore the query for invalid criteria, and so
        do we.
        """
        data = "<root><issn pub-type='epub'>0102-6720</issn></root>"
        scieloapi = ScieloAPIClientStub()
        scieloapi.issues.filter = lambda **kwargs: [{'foo': 'bar'}]

        vpipe = self._makeOne(data, _scieloapi=scieloapi)
        self.assertEqual(vpipe._fetch_journal_and_issue_data(print_issn='0100-879X', **{'volume': '30', 'number': '4'}),
                         {'foo': 'bar'})

    def test_fetch_journal_issue_data_with_unknown_issn_raises_ValueError(self):
        #FIXME
        data = "<root><issn pub-type='epub'>0102-6720</issn></root>"
        scieloapi = ScieloAPIClientStub()
        scieloapi.journals.filter = lambda **kwargs: []

        sapi_tools = get_ScieloAPIToolbeltStubModule()

        def _get_one(dataset):
            raise ValueError()
        sapi_tools.get_one = _get_one

        vpipe = self._makeOne(data, _scieloapi=scieloapi, _sapi_tools=sapi_tools)
        self.assertRaises(ValueError,
                          lambda: vpipe._fetch_journal_and_issue_data(print_issn='0100-879X', **{'volume': '30', 'number': '4'}))

    def test_fetch_journal_issue_data_with_unknown_criteria_raises_ValueError(self):
        #FIXME
        data = "<root><issn pub-type='epub'>0102-6720</issn></root>"
        scieloapi = ScieloAPIClientStub()
        scieloapi.journals.filter = lambda **kwargs: []

        sapi_tools = get_ScieloAPIToolbeltStubModule()

        def _get_one(dataset):
            raise ValueError()
        sapi_tools.get_one = _get_one

        vpipe = self._makeOne(data, _scieloapi=scieloapi, _sapi_tools=sapi_tools)
        self.assertRaises(ValueError,
                          lambda: vpipe._fetch_journal_and_issue_data(**{'print_issn': '1234-1234', 'volume': '30', 'number': '4'}))

    def test_transform_grants_valid_issn_before_fetching(self):
        #FIXME verificar
        stub_attempt = AttemptStub()
        stub_attempt.articlepkg.journal_pissn = '0100-879X'
        stub_attempt.articlepkg.journal_eissn = None
        stub_attempt.articlepkg.issue_volume = '30'
        stub_attempt.articlepkg.issue_number = '4'

        mock_issn_validator = self.mocker.mock()
        #mock_fetch_journal_data = self.mocker.mock()
        mock_fetch_journal_and_issue_data = self.mocker.mock()

        with self.mocker.order():
            mock_issn_validator('0100-879X')
            self.mocker.result(True)

            #mock_fetch_journal_data({'print_issn': '0100-879X'})
            #self.mocker.result({'foo': 'bar', 'resource_uri': '/api/...'})

            mock_fetch_journal_and_issue_data(print_issn='0100-879X', **{'volume': '30', 'number': '4'})
            self.mocker.result({'foo': 'bar'})

            self.mocker.replay()

        data = "<root><issn pub-type='epub'>0102-6720</issn></root>"

        vpipe = self._makeOne(data)
        vpipe._issn_validator = mock_issn_validator
        #vpipe._fetch_journal_data = mock_fetch_journal_data
        vpipe._fetch_journal_and_issue_data = mock_fetch_journal_and_issue_data
        vpipe._notifier = lambda args: NotifierStub()

        result = vpipe.transform(stub_attempt)


class ReferenceSourceValidationTests(unittest.TestCase):

    def _makeOne(self, data, **kwargs):

        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)

        vpipe = validator.ReferenceSourceValidationPipe(_notifier, _pkg_analyzer)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_reference_list_with_valid_tag_source(self):
        expected = [models.Status.ok, '']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <source><![CDATA[Palaeontology]]></source>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_missing_tag_source(self):
        expected = [models.Status.error, ' B23: missing tag source']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <year>2013</year>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_with_two_missing_tag_source(self):
        expected = [models.Status.error, ' B23: missing tag source B24: missing tag source']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <year>2013</year>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
                <ref id="B24">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <year>2013</year>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_with_tag_source_missing_content(self):
        expected = [models.Status.error, ' B23: missing content in tag source']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <source></source>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)


class ReferenceValidationPipeTests(unittest.TestCase):

    def _makeOne(self, data, **kwargs):

        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)

        vpipe = validator.ReferenceValidationPipe(_notifier, _pkg_analyzer)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_reference_with_valid_tag_ref(self):
        expected = [models.Status.ok, '']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <source><![CDATA[Palaeontology]]></source>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_with_missing_tag_ref(self):
        expected = [models.Status.warning, 'tag reference missing']
        data = '''
            <root>
              <ref-list>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)


class ReferenceJournalTypeArticleTitleValidationTests(unittest.TestCase):

    def _makeOne(self, data, **kwargs):

        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)

        vpipe = validator.ReferenceJournalTypeArticleTitleValidationPipe(_notifier,
            _pkg_analyzer)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_reference_list_with_valid_tag_article_title(self):
        expected = [models.Status.ok, '']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <source><![CDATA[Palaeontology]]></source>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_missing_tag_article_title(self):
        expected = [models.Status.error, ' B23: missing tag article-title']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <year>2013</year>
                    <volume>49</volume>
                    <source><![CDATA[Palaeontology]]></source>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_with_two_missing_tag_article_title(self):
        expected = [models.Status.error, ' B23: missing tag article-title B24: missing tag article-title']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <year>2013</year>
                    <volume>49</volume>
                    <source><![CDATA[Palaeontology]]></source>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
                <ref id="B24">
                  <element-citation publication-type="journal">
                    <year>2013</year>
                    <volume>49</volume>
                    <source><![CDATA[Palaeontology]]></source>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_with_tag_source_missing_content(self):
        expected = [models.Status.error, ' B23: missing content in tag article-title']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"></article-title>
                    <source><![CDATA[Palaeontology]]></source>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)


class ReferenceDateValidationTests(unittest.TestCase):

    def _makeOne(self, data, **kwargs):

        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)

        vpipe = validator.ReferenceYearValidationPipe(_notifier, _pkg_analyzer)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_reference_list_with_valid_tag_year(self):
        expected = [models.Status.ok, '']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <source><![CDATA[Palaeontology]]></source>
                    <volume>49</volume>
                    <year>2013</year>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_with_valid_and_well_format_tag_year(self):
        expected = [models.Status.ok, '']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <source><![CDATA[Palaeontology]]></source>
                    <volume>49</volume>
                    <year>2013</year>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_with_valid_and_not_well_format_tag_year(self):
        expected = [models.Status.error, ' B23: date format is not good']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"><![CDATA[Title]]></article-title>
                    <source><![CDATA[Palaeontology]]></source>
                    <volume>49</volume>
                    <year>13</year>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_missing_tag_year(self):
        expected = [models.Status.error, ' B23: missing tag year']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <volume>49</volume>
                    <source><![CDATA[Palaeontology]]></source>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_with_two_missing_tag_year(self):
        expected = [models.Status.error, ' B23: missing tag year B24: missing tag year']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <volume>49</volume>
                    <source><![CDATA[Palaeontology]]></source>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
                <ref id="B24">
                  <element-citation publication-type="journal">
                    <volume>49</volume>
                    <source><![CDATA[Palaeontology]]></source>
                    <page-range>641-46</page-range>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)

    def test_reference_list_with_tag_year_missing_content(self):
        expected = [models.Status.error, ' B23: missing content in tag year']
        data = '''
            <root>
              <ref-list>
                <ref id="B23">
                  <element-citation publication-type="journal">
                    <article-title xml:lang="en"></article-title>
                    <source><![CDATA[Palaeontology]]></source>
                    <volume>49</volume>
                    <page-range>641-46</page-range>
                    <year></year>
                  </element-citation>
                </ref>
              </ref-list>
            </root>'''

        vpipe = self._makeOne(data)
        pkg_analyzer_stub = self._makePkgAnalyzerWithData(data)

        self.assertEquals(
            vpipe.validate([None, pkg_analyzer_stub, None]), expected)


class JournalAbbreviatedTitleValidationTests(mocker.MockerTestCase):

    def _makeOne(self, data, **kwargs):

        _scieloapi = kwargs.get('_scieloapi', ScieloAPIClientStub())
        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)
        _normalize_data = kwargs.get('_normalize_data', utils.normalize_data)

        vpipe = validator.JournalAbbreviatedTitleValidationPipe(_notifier,
            _pkg_analyzer, _scieloapi, _normalize_data)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_valid_abbreviated_title(self):
        expected = [models.Status.ok, '']
        xml = '''
            <front><journal-meta><abbrev-journal-title abbrev-type="publisher"><![CDATA[An. Acad. Bras. Ciênc.]]></abbrev-journal-title></journal-meta></front>'''

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_normalize_data = self.mocker.mock()
        mock_normalize_data(u'An. Acad. Bras. Ciênc.')
        self.mocker.result(u'AN. ACAD. BRAS. CIÊNC.')

        self.mocker.count(2)

        self.mocker.replay()

        journal_and_issue_data = {'journal': {'short_title': u'An. Acad. Bras. Ciênc.'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._normalize_data = mock_normalize_data

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_invalid_abbreviated_title(self):
        expected = [models.Status.error, 'the abbreviated title in xml is defferent from the abbreviated title in the source']
        xml = '''
            <front><journal-meta><abbrev-journal-title abbrev-type="publisher"><![CDATA[An. Academia Bras. Ciênc.]]></abbrev-journal-title></journal-meta></front>'''

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_normalize_data = self.mocker.mock()
        mock_normalize_data(u'An. Academia Bras. Ciênc.')
        self.mocker.result(u'AN. ACADEMIA. BRAS. CIÊNC.')

        mock_normalize_data(u'An. Acad. Bras. Ciênc.')
        self.mocker.result(u'AN. ACAD. BRAS. CIÊNC.')

        self.mocker.replay()

        journal_and_issue_data = {'journal': {'short_title': u'An. Acad. Bras. Ciênc.'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._normalize_data = mock_normalize_data

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_if_exists_abbreviated_title_tag_on_source(self):
        expected = [models.Status.error, 'missing abbreviated title in source']
        xml = '''
            <front><journal-meta><abbrev-journal-title abbrev-type="publisher"><![CDATA[An. Academia Bras. Ciênc.]]></abbrev-journal-title></journal-meta></front>'''

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        journal_and_issue_data = {'journal': {}}


        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_if_exists_abbreviated_title_tag_on_xml(self):
        expected = [models.Status.error, 'missing abbreviated title in xml']
        xml = '''
            <front><journal-meta></journal-meta></front>'''

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        journal_and_issue_data = {'journal': {'short_title': u'An. Acad. Bras. Ciênc.'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))


class PublisherNameValidationPipeTests(mocker.MockerTestCase):
    """
    docstring for PublisherNameValidationPipeTests
    """
    def _makeOne(self, data, **kwargs):
        from balaio import utils
        _scieloapi = kwargs.get('_scieloapi', ScieloAPIClientStub())
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)
        _sapi_tools = kwargs.get('_sapi_tools', get_ScieloAPIToolbeltStubModule())
        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _normalize_data = kwargs.get('_normalize_data', utils.normalize_data)

        vpipe = validator.PublisherNameValidationPipe(_notifier,
            _scieloapi, _sapi_tools, _pkg_analyzer, _normalize_data)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_publisher_name_matched(self):
        expected = [models.Status.ok, '']
        xml = '<root><journal-meta><publisher><publisher-name>publicador                  da revista brasileira de ....</publisher-name></publisher></journal-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_normalize_data = self.mocker.mock()
        mock_normalize_data(u'publicador                  da revista brasileira de ....')
        self.mocker.result(u'PUBLICADOR DA REVISTA BRASILEIRA DE ....')

        mock_normalize_data(u'publicador da revista brasileira de ....')
        self.mocker.result(u'PUBLICADOR DA REVISTA BRASILEIRA DE ....')

        self.mocker.replay()

        journal_and_issue_data = {'journal': {'publisher_name': 'publicador da revista brasileira de ....'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._normalize_data = mock_normalize_data
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_publisher_name_unmatched(self):
        expected = [models.Status.error, 'publicador da revista brasileira de .... [journal]\npublicador abcdefgh [article]']
        xml = '<root><journal-meta><publisher><publisher-name>publicador abcdefgh</publisher-name></publisher></journal-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_normalize_data = self.mocker.mock()
        mock_normalize_data(u'publicador abcdefgh')
        self.mocker.result(u'PUBLICADOR ABCDEFGH')

        mock_normalize_data(u'publicador da revista brasileira de ....')
        self.mocker.result(u'PUBLICADOR DA REVISTA BRASILEIRA DE ....')

        self.mocker.replay()

        journal_and_issue_data = {'journal': {'publisher_name': 'publicador da revista brasileira de ....'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._normalize_data = mock_normalize_data
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_publisher_name_is_missing_in_journal(self):
        expected = [models.Status.error, 'Missing publisher_name in journal']
        xml = '<root><journal-meta><publisher><publisher-name>publicador abcdefgh</publisher-name></publisher></journal-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        journal_and_issue_data = {'journal': {}}


        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_publisher_name_is_missing_in_article(self):
        expected = [models.Status.error, 'Missing publisher-name in article']
        xml = '<root></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        journal_and_issue_data = {'journal': {'publisher_name': 'publicador da revista brasileira de ....'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))


class FundingGroupValidationPipeTests(mocker.MockerTestCase):

    def _makeOne(self, data, **kwargs):
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)
        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)

        vpipe = validator.FundingGroupValidationPipe(_notifier, _pkg_analyzer)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_no_funding_group_and_no_ack(self):
        expected = [models.Status.warning, 'no funding-group and no ack']
        xml = '<root></root>'

        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)
        data = (AttemptStub(), stub_package_analyzer, {})

        vpipe = self._makeOne(xml)

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_no_funding_group_and_ack_has_no_number(self):
        expected = [models.Status.ok, '<ack>acknowle<sub />dgements</ack>']
        xml = '<root><ack>acknowle<sub/>dgements</ack></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)
        data = (stub_attempt, stub_package_analyzer, {})

        vpipe = self._makeOne(xml)

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_no_funding_group_and_ack_has_number(self):
        expected = [models.Status.warning, '<ack>acknowledgements<p>1234</p></ack> looks to have contract number. If so, it must be identified using funding-group']
        xml = '<root><ack>acknowledgements<p>1234</p></ack></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)
        data = (stub_attempt, stub_package_analyzer, {})

        vpipe = self._makeOne(xml)

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_funding_group(self):
        expected = [models.Status.ok, '<funding-group>funding data</funding-group>']
        xml = '<root><ack>acknowledgements<funding-group>funding data</funding-group></ack></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)
        data = (stub_attempt, stub_package_analyzer, {})

        vpipe = self._makeOne(xml)

        self.assertEqual(expected,
                         vpipe.validate(data))


class NLMJournalTitleValidationPipeTests(mocker.MockerTestCase):
    """
    Tests of NLMJournalTitleValidationPipe
    """
    def _makeOne(self, data, **kwargs):
        from balaio import utils
        _scieloapi = kwargs.get('_scieloapi', ScieloAPIClientStub())
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)
        _sapi_tools = kwargs.get('_sapi_tools', get_ScieloAPIToolbeltStubModule())
        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _normalize_data = kwargs.get('_normalize_data', utils.normalize_data)

        vpipe = validator.NLMJournalTitleValidationPipe(_notifier,
            _pkg_analyzer, _scieloapi, _sapi_tools, _normalize_data)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_nlm_journal_title_matched(self):
        expected = [models.Status.ok, 'NLM Journal title']
        xml = '<root><journal-meta><journal-id journal-id-type="nlm-ta">NLM Journal title</journal-id></journal-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_normalize_data = self.mocker.mock()
        mock_normalize_data(u'NLM Journal title')
        self.mocker.result(u'NLM JOURNAL TITLE')

        self.mocker.count(2)

        self.mocker.replay()

        journal_and_issue_data = {'journal': {'medline_title': 'NLM Journal title'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._normalize_data = mock_normalize_data

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_nlm_journal_title_unmatched(self):
        expected = [models.Status.error, 'NLM Journal Title .... [journal]\nANY Journal Title [article]']
        xml = '<root><journal-meta><journal-id journal-id-type="nlm-ta">ANY Journal Title</journal-id></journal-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_normalize_data = self.mocker.mock()
        mock_normalize_data(u'ANY Journal Title')
        self.mocker.result(u'ANY JOURNAL TITLE')

        mock_normalize_data(u'NLM Journal Title ....')
        self.mocker.result(u'NLM JOURNAL TITLE ....')

        self.mocker.replay()

        journal_and_issue_data = {'journal': {'medline_title': 'NLM Journal Title ....'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._normalize_data = mock_normalize_data

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_nlm_journal_title_is_missing_in_journal(self):
        expected = [models.Status.ok, 'journal has no NLM journal title']
        xml = '<root><journal-meta><journal-id journal-id-type="nlm-ta">ANY Journal Title</journal-id></journal-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        journal_and_issue_data = {'journal': {}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_nlm_journal_title_is_missing_in_article(self):
        expected = [models.Status.error, 'Missing .//journal-meta/journal-id[@journal-id-type="nlm-ta"] in article']
        xml = '<root></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        journal_and_issue_data = {'journal': {'medline_title': 'NLM Journal Title ....'}}

        data = (stub_attempt, stub_package_analyzer, journal_and_issue_data)

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))


class DOIVAlidationPipeTests(mocker.MockerTestCase):

    def _makeOne(self, data, **kwargs):
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)
        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _normalize_data = kwargs.get('_normalize_data', utils.normalize_data)

        vpipe = validator.DOIVAlidationPipe(_notifier, _pkg_analyzer, _normalize_data)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def test_valid_and_matched_DOI(self):
        expected = [models.Status.ok, '']
        xml = '<root><article-id pub-id-type="doi">10.1590/S0001-37652013000100008</article-id></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_doi_validator = self.mocker.mock()
        mock_doi_validator('10.1590/S0001-37652013000100008')
        self.mocker.result(True)

        self.mocker.replay()

        #journal_and_issue_data = {'journal': {'doi': u'10.1590/S0001-37652013000100008'}}

        data = (stub_attempt, stub_package_analyzer, {})

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._doi_validator = mock_doi_validator

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_invalid_but_matched_DOI(self):
        expected = [models.Status.warning, 'DOI is not valid']
        xml = '<root><article-id pub-id-type="doi">10.1590/S0001-37652013000100002</article-id></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_doi_validator = self.mocker.mock()
        mock_doi_validator('10.1590/S0001-37652013000100002')
        self.mocker.result(False)

        self.mocker.replay()

        #journal_and_issue_data = {'journal': {'doi': u'10.1590/S0001-37652013000100002'}}

        data = (stub_attempt, stub_package_analyzer, {})

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._doi_validator = mock_doi_validator

        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_missing_DOI(self):
        expected = [models.Status.warning, 'missing DOI in xml']
        xml = '<root></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        #journal_and_issue_data = {'journal': {'doi': u'10.1590/S0001-37652013000100002'}}

        data = (stub_attempt, stub_package_analyzer, {})

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)

        self.assertEqual(expected,
                         vpipe.validate(data))


class ArticleSectionValidationPipeTests(mocker.MockerTestCase):
    """
    Tests of ArticleSectionValidationPipe
    """
    def _makeOne(self, data, **kwargs):
        from balaio import utils
        _scieloapi = kwargs.get('_scieloapi', ScieloAPIClientStub())
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)
        _sapi_tools = kwargs.get('_sapi_tools', get_ScieloAPIToolbeltStubModule())
        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _normalize_data = kwargs.get('_normalize_data', utils.normalize_data)

        vpipe = validator.ArticleSectionValidationPipe(_notifier, _scieloapi, _sapi_tools, _pkg_analyzer, _normalize_data)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def _issue_data(self):
        # isso deveria ser um dict no lugar de uma lista, mas a api retorna assim
        return {u'section titles': [u'Artículos Originales', u'Original Articles', u'Editorial'], u'label': '1(1)'}

    def test_article_section_matched(self):
        expected = [models.Status.ok, 'Original Articles']
        #article-categories/subj-group[@subj-group-type=”heading”]
        xml = '<root><article-meta><article-categories><subj-group subj-group-type="heading"><subject>Original Articles</subject></subj-group></article-categories></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_is_a_registered_section_title = self.mocker.mock()
        mock_is_a_registered_section_title(self._issue_data()['section titles'], 'Original Articles')
        self.mocker.result(True)

        self.mocker.replay()

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        vpipe._is_a_registered_section_title = mock_is_a_registered_section_title
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_section_is_not_registered(self):
        expected = [models.Status.error, 'Mismatched data: Articles. Expected one of %s' % ' | '.join(self._issue_data()['section titles'])]
        xml = '<root><article-meta><article-categories><subj-group subj-group-type="heading"><subject>Articles</subject></subj-group></article-categories></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        mock_is_a_registered_section_title = self.mocker.mock()
        mock_is_a_registered_section_title(self._issue_data()['section titles'], 'Articles')
        self.mocker.result(False)

        self.mocker.replay()

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        #vpipe._normalize_data = mock_normalize_data
        vpipe._is_a_registered_section_title = mock_is_a_registered_section_title
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_section_is_missing_in_article(self):
        expected = [models.Status.warning, 'Missing .//article-categories/subj-group[@subj-group-type="heading"]/subject']
        xml = '<root></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))


class ArticleMetaPubDateValidationPipeTests(mocker.MockerTestCase):
    """
    Tests of ArticleSectionValidationPipe
    """
    def _makeOne(self, data, **kwargs):
        from balaio import utils
        _scieloapi = kwargs.get('_scieloapi', ScieloAPIClientStub())
        _notifier = kwargs.get('_notifier', lambda: NotifierStub)
        _sapi_tools = kwargs.get('_sapi_tools', get_ScieloAPIToolbeltStubModule())
        _pkg_analyzer = kwargs.get('_pkg_analyzer', PackageAnalyzerStub)
        _normalize_data = kwargs.get('_normalize_data', utils.normalize_data)

        vpipe = validator.ArticleMetaPubDateValidationPipe(_notifier,
            _scieloapi, _sapi_tools, _pkg_analyzer, _normalize_data)
        vpipe.feed(data)
        return vpipe

    def _makePkgAnalyzerWithData(self, data):
        pkg_analyzer_stub = PackageAnalyzerStub()
        pkg_analyzer_stub._xml_string = data
        return pkg_analyzer_stub

    def _issue_data(self, year=1999, start=9, end=0):
        return {'publication_end_month': end,
                'publication_start_month': start,
                'publication_year': year}

    def test_article_pubdate_matched(self):
        expected = [models.Status.ok, 'year: 1999\nstart: 9\nend: 0']
        #article-categories/subj-group[@subj-group-type=”heading”]
        xml = '<root><article-meta><pub-date pub-type="pub" iso-8601-date="1999-03-27"><day>27</day><month>09</month><year>1999</year></pub-date></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_pubdate_matched_month_is_name(self):
        expected = [models.Status.ok, 'year: 1999\nstart: 9\nend: 0']
        #article-categories/subj-group[@subj-group-type=”heading”]
        xml = '<root><article-meta><pub-date pub-type="pub" iso-8601-date="1999-03-27"><day>27</day><month>Sep</month><year>1999</year></pub-date></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_pubdate_matched_month_range(self):
        expected = [models.Status.ok, 'year: 1999\nstart: 1\nend: 3']
        #article-categories/subj-group[@subj-group-type=”heading”]
        xml = '<root><article-meta><pub-date pub-type="pub" iso-8601-date="1999-03-27"><day>27</day><season>Jan-Mar</season><year>1999</year></pub-date></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data(1999, 1, 3))

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_multiple_pubdate_matched(self):
        expected = [models.Status.ok, 'year: 1999\nstart: 9\nend: 0']
        #article-categories/subj-group[@subj-group-type=”heading”]
        xml = '<root><article-meta><pub-date pub-type="pub" iso-8601-date="1999-03-27"><month>11</month><year>1999</year></pub-date>        <pub-date pub-type="pub" iso-8601-date="1999-03-27"><day>27</day><month>09</month><year>1999</year></pub-date></article-meta></root>'
        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_multiple_pubdate_matched_month_is_name(self):
        expected = [models.Status.ok, 'year: 1999\nstart: 9\nend: 0']
        #article-categories/subj-group[@subj-group-type=”heading”]
        xml = '<root><article-meta><pub-date pub-type="pub" iso-8601-date="1999-03-27"><month>11</month><year>1999</year></pub-date><pub-date pub-type="pub" iso-8601-date="1999-03-27"><day>27</day><month>Sep</month><year>1999</year></pub-date></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_multiple_pubdate_matched_month_range(self):
        expected = [models.Status.ok, 'year: 1999\nstart: 9\nend: 0']
        xml = '<root><article-meta><pub-date pub-type="pub" iso-8601-date="1999-03-27"><day>27</day><month>Sep</month><year>1999</year></pub-date><pub-date pub-type="pub" iso-8601-date="1999-03-27"><month>Oct</month><year>1999</year></pub-date></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_pubdate_unmatched(self):
        expected = [models.Status.error, 'Unmatched publication date.\nIn article:\nyear: 1999\nstart: 8\nend: 0\nIn   issue: \n' + 'year: 1999\nstart: 9\nend: 0\n']
        xml = '<root><article-meta><pub-date pub-type="pub" iso-8601-date="1999-03-27"><day>27</day><month>08</month><year>1999</year></pub-date></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))

    def test_article_multiple_pubdate_unmatched_month_range(self):
        expected = [models.Status.error, 'Unmatched publication date.\nIn article:\nyear: 2000\nstart: 9\nend: 0\nyear: 1999\nstart: 11\nend: 0\nIn   issue: \n' + 'year: 1999\nstart: 9\nend: 0\n']
        xml = '<root><article-meta><pub-date pub-type="pub" iso-8601-date="1999-03-27"><day>27</day><month>Sep</month><year>2000</year></pub-date><pub-date pub-type="pub" iso-8601-date="1999-03-27"><month>Nov</month><year>1999</year></pub-date></article-meta></root>'

        stub_attempt = AttemptStub()
        stub_package_analyzer = self._makePkgAnalyzerWithData(xml)

        data = (stub_attempt, stub_package_analyzer, self._issue_data())

        vpipe = self._makeOne(data, _pkg_analyzer=stub_package_analyzer)
        self.assertEqual(expected,
                         vpipe.validate(data))
