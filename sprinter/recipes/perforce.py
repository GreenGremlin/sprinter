"""
Creates a git repository and places it at the install location.

[perforce]
recipe = sprinter.recipes.perforce
inputs = p4username
         p4password?
version = r10.1
root_path = ~/p4/
username = %(config:p4username)s
password = %(config:p4password)s
port = perforce.local:1666
client = %(config:node)s
"""
import os
import shutil
import re
import urllib

from sprinter.recipestandard import RecipeStandard
from sprinter import lib

url_template = "http://filehost.perforce.com/perforce/%s/%s/p4"
exec_dict = {"r10.1": {"mac": "bin.macosx104u",
                       "linux": "bin.linux26x86_64"}}

p4settings_template = \
"""
P4USER=%(username)s
P4CLIENT=%(client)s
"""

p4client_template = \
"""
Client:	%(client)s

Update:	2012/12/03 00:16:24

Access:	2012/12/03 00:16:24

Owner:	%(username)s

Host:	%(hostname)s

Description:
        Created by %(username)s

Root:	%(root)s

Options:	noallwrite noclobber nocompress unlocked nomodtime normdir

LineEnd:	local

View:
%(p4view)s
"""


class PerforceRecipe(RecipeStandard):
    """ A sprinter recipe for git"""

    def setup(self, feature_name, config):
        super(PerforceRecipe, self).setup(feature_name, config)
        self.__install_perforce(feature_name, config)
        self.__write_p4settings(config)
        self.__configure_client(config)
        self.__sync_perforce(config)
        self.__add_p4_port(config)

    def update(self, feature_name, config):
        if config['source']['version'] != config['target']['version']:
            os.remove(os.path.join(self.environment.install_directory(feature_name), 'p4'))
            self.__install_perforce(self, feature_name, config['target'])
        self.__write_p4settings(config)
        self.__sync_perforce(config)
        self.__add_p4_port(config)

    def destroy(self, feature_name, config):
        self.__destroy_perforce(config)

    def reload(self, feature_name, config):
        self.__sync_perforce(config)
        self.__add_p4_port(config)

    def __install_perforce(self, feature_name, config):
        """ install perforce binary """
        exec_dir = exec_dict[config['version']]['mac'] if self.environment.isOSX() else \
            exec_dict[config['version']]['linux']
        url = url_template % (config['version'], exec_dir)
        d = self.environment.install_directory(feature_name)
        os.makedirs(d)
        self.logger.info("Downloading p4 executable...")
        urllib.urlretrieve(url, os.path.join(d, "p4"))
        self.environment.symlink_to_bin("p4", os.path.join(d, "p4"))

    def __write_p4settings(self, config):
        """ write perforce settings """
        self.logger.info("Writing p4settings...")
        root_dir = os.path.expanduser(config['root_path'] % self.environment.context())
        p4settings_path = os.path.join(root_dir, ".p4settings")
        out_content = p4settings_template % config
        if os.path.exists(p4settings_path) and out_content != open(p4settings_path, "r+").read():
            overwrite = lib.prompt("p4settings already exists at %s. Overwrite?" % root_dir, default="no")
            if overwrite.lower().startswith('y'):
                self.logger.info("Overwriting existing p4settings...")
                os.remove(p4settings_path)
            else:
                return
        p4settings_file = open(p4settings_path, "w+")
        p4settings_file.write(p4settings_template % config)
        p4settings_file.close()

    def __configure_client(self, config):
        """ write the perforce client """
        pass

    def __sync_perforce(self, config):
        """ prompt and sync perforce """
        sync = lib.prompt("would you like to sync your perforce root?", default="yes")
        if sync.lower.startswith('y'):
            self.logger.info("Syncing perforce root...")
            os.chdir(os.path.expanduser(config['root_path'] % self.environment.context()))
            lib.call("p4 -u %(username)s -p %(password)s sync" % (config['username'],
                                                                  re.escape(config['password'])))

    def __add_p4_port(self, config):
        self.environment.add_to_rc('export P4PORT=%s' % config['port'])

    def __destroy_perforce(self, config):
        """ destroy the perforce root """
        sync = lib.prompt("would you like to completely remove the perforce root?", default="no")
        if sync.lower.startswith('y'):
            self.logger.info("Removing %s..." % config['root_path'])
            shutil.rmtree(os.path.expanduser(config['root_path'] % self.environment.context()))