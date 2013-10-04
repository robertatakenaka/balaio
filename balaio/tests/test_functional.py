import zipfile
from tempfile import NamedTemporaryFile
from xml.etree.ElementTree import ElementTree
from sqlalchemy import create_engine
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

import mocker

from balaio import checkin, gateway_server
from balaio import models


class TestFuncionalities(mocker.MockerTestCase):

    def setUp(self):
        Session = models.Session
        engine = create_engine('sqlite+pysqlite:///db.sqlite', echo=True)
        Session.configure(bind=engine)
        self.session = Session()

    def test_pkg(self):
        f = open('samples/0042-9686-bwho-91-08-545.zip', 'r')

        pkg = checkin.PackageAnalyzer(f.name)
        self.assertEqual(pkg.meta.get('article_title', ''), 'In this month\'s ')
        self.assertEqual(pkg.meta.get('journal_pissn', ''), '0042-9686')
        self.assertEqual(pkg.is_valid_package(), True)
        self.assertIsInstance(
            checkin.get_attempt(f.name),
            models.Attempt
            )

    # def test_registering_a_package(self):
    #     f = open('samples/0042-9686-bwho-91-08-545.zip', 'r')

    #     pkg = checkin.PackageAnalyzer(f.name)
    #     article_title = pkg.meta.get('article_title', '')

    #     attempt = checkin.get_attempt(f.name)
    #     article_pkg = self.session.query(models.ArticlePkg).filter_by(article_title=article_title).one()

    #     self.assertEqual(attempt.article_pkg.to_dict(),
    #             article_pkg.to_dict()
    #         )
    #     self.assertEqual(attempt.to_dict(),
    #             self.session.query(models.Attempt).filter_by(package_checksum=attempt.package_checksum, articlepkg_id=attempt.articlepkg_id, filepath=attempt.filepath).one().to_dict()
    #         )

    