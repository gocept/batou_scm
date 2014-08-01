from batou.component import Component
from batou.lib.file import File, Content
import ast
import batou.lib.git
import batou.lib.mercurial
import collections
import os.path
import pkg_resources
import urlparse


class Source(Component):

    dist_sources = '[]'
    sources = '[]'

    hg_hostfingerprints = {
        'bitbucket.org':
        '45:ad:ae:1a:cf:0e:73:47:06:07:e0:88:f5:cc:10:e5:fa:1c:f7:99',
        'code.gocept.com':
        '5e:ec:16:18:7a:4a:c1:33:9d:7d:35:42:ff:f4:39:69:3f:8c:66:d6',
    }
    additional_hgrc_content = ''

    vcs_update = 'True'

    def _eval_attr(self, *names):
        for name in names:
            if isinstance(getattr(self, name), basestring):
                setattr(self, name, ast.literal_eval(getattr(self, name)))

    def configure(self):
        self._eval_attr('dist_sources', 'sources', 'vcs_update',
                        'hg_hostfingerprints')

        self.hg_hostfingerprints = collections.OrderedDict(
            x for x in sorted(self.hg_hostfingerprints.items()))

        self.provide('source', self)

        additional_hgrc = os.path.join(self.defdir, 'hgrc')
        if not self.additional_hgrc_content and os.path.exists(
                additional_hgrc):
            self |= Content('additional_hgrc', source=additional_hgrc)
            self.additional_hgrc_content = self._.content

        self.hgrc = File('~/.hgrc', source=pkg_resources.resource_filename(
            'batou_scm', 'resources/hgrc'))
        self += self.hgrc

        self.distributions = dict(
            self.add_clone(url) for url in self.dist_sources)
        self.clones = self.distributions.copy()
        self.clones.update(self.add_clone(url) for url in self.sources)

    VCS = {
        'hg': {
            'component': batou.lib.mercurial.Clone,
            'default-branch': 'default',
        },
        'git': {
            'component': batou.lib.git.Clone,
            'default-branch': 'master',
        },
    }

    def add_clone(self, url):
        parts = urlparse.urlsplit(url)
        vcs, _, scheme = parts.scheme.partition('+')
        if not vcs:
            raise ValueError(
                'Malformed VCS URL %r, need <vcs>+<protocol>://<url>, '
                'e.g. hg+ssh://hg@bitbucket.org/gocept/batou' % url)
        url = urlparse.urlunsplit((scheme,) + parts[1:])

        url, _, parameter_list = url.partition(' ')
        parameters = dict(
            target=filter(bool, url.split('/'))[-1],
            branch=self.VCS[vcs]['default-branch']
        )
        parameters.update(x.split('=') for x in parameter_list.split())

        clone = self.VCS[vcs]['component']
        self += clone(url, vcs_update=self.vcs_update, **parameters)
        return parameters['target'], self._
