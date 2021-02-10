import os
import sys
import logging
import argparse
from tabtool.utils import *
from tabtool.config import Config

__all__  = ['deploy']

commands = ['html', 'pdf', 'pkg', 'colab', 'all']

def deploy():
    parser = argparse.ArgumentParser(description='Deploy documents')
    parser.add_argument('commands', nargs='+', choices=commands)
    args = parser.parse_args(sys.argv[2:])
    config = Config()
    deployer = Deployer(config)
    for cmd in args.commands:
        getattr(deployer, cmd)()

class Deployer(object):
    def __init__(self, config):
        self.config = config

    def _check(self):
        assert self.config.deploy['s3_bucket'] is not '', 'empty target URL'

    def html(self):
        self._check()
        bash_fname = os.path.join(os.path.dirname(__file__), 'upload_doc_s3.sh')
        run_cmd(['bash', bash_fname, self.config.html_dir, self.config.deploy['s3_bucket']])
        self.colab()

    def colab(self):
        if self.config.colab['github_repo']:
            bash_fname = os.path.join(os.path.dirname(__file__), 'upload_github.sh')
            run_cmd(['bash', bash_fname, self.config.colab_dir, self.config.colab['github_repo']])

    def pdf(self):
        self._check()
        url = self.config.deploy['s3_bucket']
        if not url.endswith('/'):
            url += '/'
        logging.info('cp %s to %s', self.config.pdf_fname, url)
        run_cmd(['aws s3 cp', self.config.pdf_fname, url, "--acl 'public-read' --quiet"])

    def _deploy_other_files(self, tgt_url):
        other_urls = self.config.deploy['other_file_s3urls'].split()
        for other_url in other_urls:
            logging.info('cp %s to %s', other_url, tgt_url)
            run_cmd(['aws s3 cp', other_url, tgt_url, "--acl 'public-read' --quiet"])

    def pkg(self):
        self._check()
        url = self.config.deploy['s3_bucket']
        if not url.endswith('/'):
            url += '/'
        logging.info('cp %s to %s', self.config.pkg_fname, url)
        run_cmd(['aws s3 cp', self.config.pkg_fname, url, "--acl 'public-read' --quiet"])
        self._deploy_other_files(url)

    def all(self):
        self.html()
        self.pdf()
        self.pkg()
