from mock import patch
import os

from .sphinx import SphinxBuilder


def test_setup_installs_sphinx():
    build_config = {}
    builder = SphinxBuilder(build_config=build_config)
    with patch('readthedocs_build.builder.base.VirtualEnv'):
        builder.setup()
        assert any([
            args[0].startswith('Sphinx')
            for args, kwargs in builder.venv.install.call_args_list])


def test_build_html_calls_sphinx_build(tmpdir):
    build_config = {
        'name': 'docs',
        'base': str(tmpdir),
        'output_base': str(tmpdir.join('out')),
    }
    builder = SphinxBuilder(build_config=build_config)
    with patch('readthedocs_build.builder.base.VirtualEnv'):
        builder.build()
        source_dir = str(tmpdir)
        out_dir = str(tmpdir.join('out', 'docs', 'html'))
        builder.venv.python_run.assert_called_with(
            'sphinx-build', [
                '-b',
                'html',
                source_dir,
                out_dir,
            ])
