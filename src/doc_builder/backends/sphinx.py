import re
import os
import sys
import codecs
from glob import glob
import logging
import zipfile
from importlib import import_module

from doc_builder.base import BaseBuilder
from doc_builder.utils import run, safe_write, obj_to_json, Capturing
from doc_builder.render import render_to_string
from doc_builder.constants import BuildException, TEMPLATE_DIR


log = logging.getLogger(__name__)

PDF_RE = re.compile('Output written on (.*?)')

sphinx_application = import_module('sphinx.application')


# Monkeypatch this so we don't emit builder-inited signal twice.
def monkeypatch(self, buildername):
    builderclass = self.builderclasses[buildername]
    if isinstance(builderclass, tuple):
        # builtin builder
        mod, cls = builderclass
        builderclass = getattr(
            __import__('sphinx.builders.' + mod, None, None, [cls]), cls)
    self.builder = builderclass(self)

sphinx_application.Sphinx._init_builder = monkeypatch


class BaseSphinx(BaseBuilder):

    """
    The parent for most sphinx builders.
    """

    # def __init__(self, *args, **kwargs):
    #     super(BaseSphinx, self).__init__(*args, **kwargs)
    #     try:
    #         self.old_artifact_path = os.path.join(self.state.fs.conf_dir, self.sphinx_build_dir)
    #     except BuildException:
    #         docs_dir = self.docs_dir()
    #         self.old_artifact_path = os.path.join(docs_dir, self.sphinx_build_dir)

    def build(self, **kwargs):
        app = sphinx_application.Sphinx(
            srcdir=self.state.conf_dir,
            confdir=self.state.conf_dir,
            outdir=self.state.output_path,
            doctreedir=os.path.join(self.state.output_path, '.doctrees'),
            buildername='html',
        )
        app.setup_extension('readthedocs_ext.readthedocs')
        app._init_builder(self.sphinx_builder)
        app.emit('builder-inited')
        app.build(force_all=True)
        return True

    def _write_config(self):
        """
        Create ``conf.py`` if it doesn't exist.
        """
        docs_dir = self.docs_dir()
        conf_template = render_to_string('doc_builder/conf.py.conf',
                                         {'project': self.state.project,
                                          'version': self.state.version,
                                          'template_dir': TEMPLATE_DIR,
                                          })
        conf_file = os.path.join(docs_dir, 'conf.py')
        safe_write(conf_file, conf_template)

    def append_conf(self, **kwargs):
        """Modify the given ``conf.py`` file from a whitelisted user's project.
        """

        # Pull config data
        try:
            self.state.conf_file
        except BuildException:
            self._write_config()
            self.create_index(extension='rst')

        # Open file for appending.
        try:
            outfile = codecs.open(self.state.conf_file, encoding='utf-8', mode='a')
            outfile.write("\n")
        except IOError:
            trace = sys.exc_info()[2]
            raise BuildException('Conf file not found'), None, trace

        rtd_ctx = Context({
            'state': self.state,
            'json_state': obj_to_json(self.state),
            # 'versions': project.api_versions(),
            # 'downloads': self.version.get_downloads(pretty=True),
            # 'current_version': self.version.slug,
            # 'project': project,
            # 'settings': settings,
            # 'static_path': STATIC_DIR,
            # 'template_path': TEMPLATE_DIR,
            # 'conf_py_path': conf_py_path,
            # 'downloads': apiv2.version(self.version.pk).downloads.get()['downloads'],
            # 'api_host': getattr(settings, 'SLUMBER_API_HOST', 'https://readthedocs.org'),
            # GitHub
            # 'github_user': github_info[0],
            # 'github_repo': github_info[1],
            # 'github_version':  remote_version,
            # 'display_github': display_github,
            # BitBucket
            # 'bitbucket_user': bitbucket_info[0],
            # 'bitbucket_repo': bitbucket_info[1],
            # 'bitbucket_version':  remote_version,
            # 'display_bitbucket': display_bitbucket,
        })

        # Avoid hitting database and API if using Docker build environment
        # if getattr(settings, 'DONT_HIT_API', False):
        #     rtd_ctx['versions'] = project.active_versions()
        #     rtd_ctx['downloads'] = self.version.get_downloads(pretty=True)
        # else:
        #     rtd_ctx['versions'] = project.api_versions()
        #     rtd_ctx['downloads'] = (apiv2.version(self.version.pk)
        #                             .downloads.get()['downloads'])
        rtd_string = template_loader.get_template('doc_builder/conf.py.tmpl').render(rtd_ctx)
        outfile.write(rtd_string)


class HtmlBuilder(BaseSphinx):
    type = 'sphinx'
    sphinx_build_dir = '_readthedocs_build/html'

    def __init__(self, *args, **kwargs):
        super(HtmlBuilder, self).__init__(*args, **kwargs)
        if self.state.allow_comments:
            self.sphinx_builder = 'readthedocs-comments'
        else:
            self.sphinx_builder = 'readthedocs'


class HtmlDirBuilder(HtmlBuilder):
    type = 'sphinx_htmldir'

    def __init__(self, *args, **kwargs):
        super(HtmlDirBuilder, self).__init__(*args, **kwargs)
        if self.version.project.allow_comments:
            self.sphinx_builder = 'readthedocsdirhtml-comments'
        else:
            self.sphinx_builder = 'readthedocsdirhtml'


class SingleHtmlBuilder(HtmlBuilder):
    type = 'sphinx_singlehtml'
    sphinx_builder = 'readthedocssinglehtml'


class SearchBuilder(BaseSphinx):
    type = 'sphinx_search'
    sphinx_builder = 'json'
    sphinx_build_dir = '_build/json'


class LocalMediaBuilder(BaseSphinx):
    type = 'sphinx_localmedia'
    sphinx_builder = 'readthedocssinglehtmllocalmedia'
    sphinx_build_dir = '_readthedocs_build/localmedia'

    def move(self, **kwargs):
        log.info("Creating zip file from %s" % self.old_artifact_path)
        target_file = os.path.join(self.target, '%s.zip' % self.state.project)
        if not os.path.exists(self.target):
            os.makedirs(self.target)
        if os.path.exists(target_file):
            os.remove(target_file)

        # Create a <slug>.zip file
        os.chdir(self.old_artifact_path)
        archive = zipfile.ZipFile(target_file, 'w')
        for root, subfolders, files in os.walk('.'):
            for file in files:
                to_write = os.path.join(root, file)
                archive.write(
                    filename=to_write,
                    arcname=os.path.join("%s-%s" % (self.state.project,
                                                    self.state.version),
                                         to_write)
                )
        archive.close()


class EpubBuilder(BaseSphinx):
    type = 'sphinx_epub'
    sphinx_builder = 'epub'
    sphinx_build_dir = '_readthedocs_build/epub'

    def move(self, **kwargs):
        from_globs = glob(os.path.join(self.old_artifact_path, "*.epub"))
        if not os.path.exists(self.target):
            os.makedirs(self.target)
        if from_globs:
            from_file = from_globs[0]
            to_file = os.path.join(self.target, "%s.epub" % self.state.project)
            run('mv -f %s %s' % (from_file, to_file))


class PdfBuilder(BaseSphinx):
    type = 'sphinx_pdf'
    sphinx_build_dir = '_readthedocs_build/latex'
    pdf_file_name = None

    def build(self, **kwargs):
        self.clean()
        os.chdir(self.state.conf_dir)
        # Default to this so we can return it always.
        results = {}
        latex_results = run('%s -b latex -D language=%s -d _build/doctrees . _build/latex'
                            % ('sphinx-build', self.state.language))

        if latex_results[0] == 0:
            os.chdir(self.sphinx_build_dir)
            tex_files = glob('*.tex')

            if tex_files:
                # Run LaTeX -> PDF conversions
                pdflatex_cmds = [('pdflatex -interaction=nonstopmode %s'
                                  % tex_file) for tex_file in tex_files]
                makeindex_cmds = [('makeindex -s python.ist %s.idx'
                                   % os.path.splitext(tex_file)[0]) for tex_file in tex_files]
                pdf_results = run(*pdflatex_cmds)
                ind_results = run(*makeindex_cmds)
                pdf_results = run(*pdflatex_cmds)
            else:
                pdf_results = (0, "No tex files found", "No tex files found")
                ind_results = (0, "No tex files found", "No tex files found")

            results = [
                latex_results[0] + ind_results[0] + pdf_results[0],
                latex_results[1] + ind_results[1] + pdf_results[1],
                latex_results[2] + ind_results[2] + pdf_results[2],
            ]
            pdf_match = PDF_RE.search(results[1])
            if pdf_match:
                self.pdf_file_name = pdf_match.group(1).strip()
        else:
            results = latex_results
        return results

    def move(self, **kwargs):
        if not os.path.exists(self.target):
            os.makedirs(self.target)

        exact = os.path.join(self.old_artifact_path, "%s.pdf" % self.state.project)
        exact_upper = os.path.join(self.old_artifact_path, "%s.pdf" % self.state.project.capitalize())

        if self.pdf_file_name and os.path.exists(self.pdf_file_name):
            from_file = self.pdf_file_name
        if os.path.exists(exact):
            from_file = exact
        elif os.path.exists(exact_upper):
            from_file = exact_upper
        else:
            from_globs = glob(os.path.join(self.old_artifact_path, "*.pdf"))
            if from_globs:
                from_file = from_globs[0]
            else:
                from_file = None
        if from_file:
            to_file = os.path.join(self.target, "%s.pdf" % self.state.project)
            run('mv -f %s %s' % (from_file, to_file))
