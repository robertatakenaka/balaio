#coding: utf-8
import os
import stat
import zipfile
import itertools
import xml.etree.ElementTree as etree
import logging
import sys

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.exc import IntegrityError

import models
import utils
import notifier


__all__ = ['PackageAnalyzer', 'get_attempt']
logger = logging.getLogger('balaio.checkin')
utils.setup_logging()


class SPSMixin(object):

    @property
    def xmls(self):
        fps = self.get_fps('xml')
        for fp in fps:
            yield etree.parse(fp)

    @property
    def xml(self):
        xmls = list(itertools.islice(self.xmls, 2))
        if len(xmls) == 1:
            return xmls[0]
        else:
            raise AttributeError('there is not a single xml file')

    @property
    def meta(self):
        dct_mta = {}

        xml_nodes = {"journal_title": ".//journal-meta/journal-title-group/journal-title",
                     "journal_eissn": ".//journal-meta/issn[@pub-type='epub']",
                     "journal_pissn": ".//journal-meta/issn[@pub-type='ppub']",
                     "article_title": ".//article-meta/title-group/article-title",
                     "issue_year": ".//article-meta/pub-date/year",
                     "issue_volume": ".//article-meta/volume",
                     "issue_number": ".//article-meta/issue",
                     "supplement": ".//article-meta/supplement",
                     }

        for node_k, node_v in xml_nodes.items():
            node = self.xml.find(node_v)
            dct_mta[node_k] = getattr(node, 'text', None)

        ign, dct_mta['issue_suppl_volume'], dct_mta['issue_number'], dct_mta['issue_suppl_number'] = utils.issue_identification(dct_mta['issue_volume'], dct_mta['issue_number'], dct_mta['supplement'])
        del dct_mta['supplement']
        return dct_mta


class Xray(object):

    def __init__(self, filename):
        """
        ``filename`` is the full path to a zip file.
        """
        if not zipfile.is_zipfile(filename):
            raise ValueError('%s is not a valid zipfile.' % filename)

        self._filename = filename
        self._zip_pkg = zipfile.ZipFile(filename, 'r')
        self._pkg_names = {}

        self._classify()

    def __del__(self):
        self._cleanup_package_fp()

    def _cleanup_package_fp(self):
        # raises AttributeError if the object have not
        # been initialized properly.
        try:
            self._zip_pkg.close()
        except AttributeError:
            pass

    def _classify(self):
        for fileinfo, filename in zip(self._zip_pkg.infolist(), self._zip_pkg.namelist()):
            # ignore directories and empty files
            if fileinfo.file_size:
                _, ext = filename.rsplit('.', 1)
                ext_node = self._pkg_names.setdefault(ext, [])
                ext_node.append(filename)

    def get_ext(self, ext):
        """
        Get a list os members having ``ext`` as extension. Raises
        ValueError if the archive does not have any members matching
        the extension.
        """
        try:
            return self._pkg_names[ext]
        except KeyError:
            raise ValueError("the package does not contain a '%s' file" % ext)

    def get_fps(self, ext):
        """
        Get file objects for all members having ``ext`` as extension.
        If ``ext`` is not found in the archive, the iterator is empty.
        """
        try:
            filenames = self.get_ext(ext)
        except ValueError:
            raise StopIteration()

        for filename in filenames:
            yield self._zip_pkg.open(filename, 'r')


class PackageAnalyzer(SPSMixin, Xray):

    def __init__(self, *args):
        super(PackageAnalyzer, self).__init__(*args)
        self._errors = set()
        self._default_perms = stat.S_IMODE(os.stat(self._filename).st_mode)
        self._is_locked = False

    def __enter__(self):
        self.lock_package()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.restore_perms()
        except OSError, exc:
            logger.info('The package had been deleted before the permissions restore procedure: %s' % exc)
        self._cleanup_package_fp()

    @property
    def errors(self):
        """
        Returns a tuple of errors
        """
        return tuple(self._errors)

    def is_valid_package(self):
        """
        Validate if exist at least one xml file and one pdf file
        """
        is_valid = True
        for ext in ['xml', 'pdf']:
            try:
                _ = self.get_ext(ext)
            except ValueError, e:
                self._errors.add(e.message)
                is_valid = False

        return is_valid

    def lock_package(self):
        """
         - Removes the write permission for Owners and Others
           http://docs.python.org/2/library/stat.html#stat.S_IWOTH
         - Change the group of package to the application group
           http://docs.python.org/2/library/os.html#os.chown
        """

        if not self._is_locked:
            perm = self._default_perms ^ stat.S_IWOTH ^ stat.S_IWUSR

            try:
                os.chmod(self._filename, perm)
            except OSError, e:
                self._errors.add(e.message)
                raise ValueError("Cant change the package permission")
            else:
                try:
                    os.chown(self._filename, -1, os.getgid())
                except OSError, e:
                    self.restore_perms()
                    self._errors.add(e.message)
                    raise ValueError("Cant change the group")

            self._is_locked = True

    def restore_perms(self):
        os.chmod(self._filename, self._default_perms)
        self._is_locked = False

    @property
    def checksum(self):
        """
        Encapsulate the digest generation in order to avoid
        things like secret key changes that could crash the
        package identification.
        """
        return utils.make_digest_file(self._filename)


def get_attempt(package):
    """
    Always returns a brand new models.Attempt instance, bound to
    the expected models.ArticlePkg instance.
    - Verify if exist at least one ISSN.

    :param package: filesystem path to a package
    """
    config = utils.Configuration.from_env()
    #CheckinNotifier = notifier.checkin_notifier_factory(config)
    logger.info('Analyzing package: %s' % package)

    with PackageAnalyzer(package) as pkg:
        try:
            Session = models.Session
            logging.debug('Binding a new sqlalchemy.engine')

            Session.configure(bind=models.create_engine_from_config(config))
            logging.debug('Creating a transactional session scope')

            session = Session()

            attempt = models.Attempt.get_from_package(pkg)
            session.add(attempt)
            logging.debug('passou session.add(attempt)')
            #attempt_notifier = CheckinNotifier(attempt)
            #attempt_notifier.start()
            import pdb; pdb.set_trace()

            try:
                
                article_pkg = models.ArticlePkg.get_or_create_from_package(pkg, session, logging)
                logging.debug('passou article_pkg = models.ArticlePkg.get_or_create_from_package(pkg, session)')
                if article_pkg not in session:
                    session.add(article_pkg)
                logging.debug('passou session.add(article_pkg)')
            except:
                attempt.is_valid = False
                #attempt_notifier.tell('Failed to load an ArticlePkg. The Attempt was invalidated.', models.Status.error, 'Checkin')
                logging.error('Failed to load an ArticlePkg. The Attempt was invalidated.')
            else:
                attempt.articlepkg = article_pkg
                logging.debug('passou attempt.articlepkg = article_pkg')
            session.commit()

            #attempt_notifier.end()
            logging.debug('passou session.commit()')
        except IOError:
            session.rollback()
            logger.error('The package %s had been deleted during analysis' % package)
            raise ValueError('The package %s had been deleted during analysis' % package)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            import traceback

            session.rollback()
            logger.error('Unexpected error! The package analysis for %s was aborted. Traceback: %s' % (
                package, traceback.print_tb(exc_traceback)))
            raise ValueError('Unexpected error! The package analysis for %s was aborted.' % package)
        finally:
            logging.debug('Closing the transactional session scope')
            session.close()

    return attempt
