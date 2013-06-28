import zipfile
from tempfile import NamedTemporaryFile
from xml.etree.ElementTree import ElementTree

import mocker

from balaio import checkin


class SPSMixinTests(mocker.MockerTestCase):

    def _make_test_archive(self, arch_data):
        fp = NamedTemporaryFile()
        with zipfile.ZipFile(fp, 'w') as zipfp:
            for archive, data in arch_data:
                zipfp.writestr(archive, data)

        return fp

    def _makeOne(self, fname):
        class Foo(checkin.SPSMixin, checkin.Xray):
            pass

        return Foo(fname)

    def test_xmls_yields_etree_instances(self):
        data = [('bar.xml', b'<root><name>bar</name></root>')]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        xmls = pkg.xmls
        self.assertIsInstance(xmls.next(), ElementTree)

    def test_xml_returns_etree_instance(self):
        data = [('bar.xml', b'<root><name>bar</name></root>')]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertIsInstance(pkg.xml, ElementTree)

    def test_xml_raises_AttributeError_when_multiple_xmls(self):
        data = [
            ('bar.xml', b'<root><name>bar</name></root>'),
            ('baz.xml', b'<root><name>baz</name></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertRaises(AttributeError, lambda: pkg.xml)

    def test_meta_journal_title_data_is_fetched(self):
        data = [
            ('bar.xml', b'<root><journal-title-group><journal-title>foo</journal-title></journal-title-group></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertEqual(pkg.meta['journal_title'], 'foo')

    def test_meta_journal_title_is_None_if_not_present(self):
        data = [
            ('bar.xml', b'<root></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertIsNone(pkg.meta['journal_title'])

    def test_meta_journal_eissn_data_is_fetched(self):
        data = [
            ('bar.xml', b'<root><issn pub-type="epub">1234-1234</issn></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertEqual(pkg.meta['journal_eissn'], '1234-1234')

    def test_meta_journal_eissn_is_None_if_not_present(self):
        data = [
            ('bar.xml', b'<root></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertIsNone(pkg.meta['journal_eissn'])

    def test_meta_journal_pissn_data_is_fetched(self):
        data = [
            ('bar.xml', b'<root><issn pub-type="ppub">1234-1234</issn></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertEqual(pkg.meta['journal_pissn'], '1234-1234')

    def test_meta_journal_pissn_is_None_if_not_present(self):
        data = [
            ('bar.xml', b'<root></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertIsNone(pkg.meta['journal_pissn'])

    def test_meta_article_title_data_is_fetched(self):
        data = [
            ('bar.xml', b'<root><title-group><article-title>bar</article-title></title-group></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertEqual(pkg.meta['article_title'], 'bar')

    def test_meta_article_title_is_None_if_not_present(self):
        data = [
            ('bar.xml', b'<root></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertIsNone(pkg.meta['article_title'])

    def test_meta_issue_year_data_is_fetched(self):
        data = [
            ('bar.xml', b'<root><pub-date><year>2013</year></pub-date></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertEqual(pkg.meta['issue_year'], '2013')

    def test_meta_issue_year_is_None_if_not_present(self):
        data = [
            ('bar.xml', b'<root></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertIsNone(pkg.meta['issue_year'])

    def test_meta_issue_volume_data_is_fetched(self):
        data = [
            ('bar.xml', b'<root><volume>2</volume></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertEqual(pkg.meta['issue_volume'], '2')

    def test_meta_issue_volume_is_None_if_not_present(self):
        data = [
            ('bar.xml', b'<root></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertIsNone(pkg.meta['issue_volume'])

    def test_meta_issue_number_data_is_fetched(self):
        data = [
            ('bar.xml', b'<root><issue>2</issue></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertEqual(pkg.meta['issue_number'], '2')

    def test_meta_issue_number_is_None_if_not_present(self):
        data = [
            ('bar.xml', b'<root></root>'),
        ]
        arch = self._make_test_archive(data)
        pkg = self._makeOne(arch.name)

        self.assertIsNone(pkg.meta['issue_number'])


class XrayTests(mocker.MockerTestCase):

    def _make_test_archive(self, arch_data):
        fp = NamedTemporaryFile()
        with zipfile.ZipFile(fp, 'w') as zipfp:
            for archive, data in arch_data:
                zipfp.writestr(archive, data)

        return fp

    def test_non_zip_archive_raises_ValueError(self):
        fp = NamedTemporaryFile()
        self.assertRaises(ValueError, lambda: checkin.Xray(fp.name))

    def test_get_ext_returns_member_names(self):
        arch = self._make_test_archive(
            [('bar.xml', b'<root><name>bar</name></root>')])

        xray = checkin.Xray(arch.name)

        self.assertEquals(xray.get_ext('xml'), ['bar.xml'])

    def test_get_ext_raises_ValueError_when_ext_doesnot_exist(self):
        arch = self._make_test_archive(
            [('bar.xml', b'<root><name>bar</name></root>')])

        xray = checkin.Xray(arch.name)

        self.assertRaises(ValueError, lambda: xray.get_ext('jpeg'))

    def test_get_fps_returns_an_iterable(self):
        arch = self._make_test_archive(
            [('bar.xml', b'<root><name>bar</name></root>')])

        xray = checkin.Xray(arch.name)

        fps = xray.get_fps('xml')
        self.assertTrue(hasattr(fps, 'next'))

    def test_get_fpd_yields_ZipExtFile_instances(self):
        arch = self._make_test_archive(
            [('bar.xml', b'<root><name>bar</name></root>')])

        xray = checkin.Xray(arch.name)

        fps = xray.get_fps('xml')
        self.assertIsInstance(fps.next(), zipfile.ZipExtFile)

    def test_get_fps_swallow_exceptions_when_ext_doesnot_exist(self):
        arch = self._make_test_archive(
            [('bar.xml', b'<root><name>bar</name></root>')])

        xray = checkin.Xray(arch.name)
        fps = xray.get_fps('jpeg')

        self.assertRaises(StopIteration, lambda: fps.next())


class PackageAnalyserTests(mocker.MockerTestCase):

    def _make_test_archive(self, arch_data):
        fp = NamedTemporaryFile()
        with zipfile.ZipFile(fp, 'w') as zipfp:
            for archive, data in arch_data:
                zipfp.writestr(archive, data)

        return fp

    def _makeOne(self, fname):
        return checkin.PackageAnalyzer(fname)

    def test_package_checksum_is_calculated(self):
        data = [('bar.xml', b'<root><name>bar</name></root>')]
        arch1 = self._make_test_archive(data)
        arch2 = self._make_test_archive(data)

        self.assertEquals(
            self._makeOne(arch1.name).checksum,
            self._makeOne(arch2.name).checksum
        )

    def test_is_subclass_of_spsmixin_and_xray(self):
        self.assertTrue(issubclass(checkin.PackageAnalyzer, checkin.Xray))
        self.assertTrue(issubclass(checkin.PackageAnalyzer, checkin.SPSMixin))

    def test_package_is_locked_during_context(self):
        import os, stat

        data = [('bar.xml', b'<root><name>bar</name></root>')]
        arch = self._make_test_archive(data)

        out_context_perm = stat.S_IMODE(os.stat(arch.name).st_mode)

        with checkin.PackageAnalyzer(arch.name) as pkg:
            in_context_perm = stat.S_IMODE(os.stat(arch.name).st_mode)
            self.assertTrue(out_context_perm != in_context_perm)

        self.assertEqual(out_context_perm, stat.S_IMODE(os.stat(arch.name).st_mode))

    def test_package_remove_user_write_perm_during_context(self):
        import os, stat

        data = [('bar.xml', b'<root><name>bar</name></root>')]
        arch = self._make_test_archive(data)

        with checkin.PackageAnalyzer(arch.name) as pkg:
            in_context_perm = oct(stat.S_IMODE(os.stat(arch.name).st_mode))
            for forbidden_val in ['3', '6', '7']:
                self.assertNotEqual(in_context_perm[1], forbidden_val)
