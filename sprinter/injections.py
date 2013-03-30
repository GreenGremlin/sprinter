"""
Injections.py handles injections into various configuration files
throughout files on the file system. These operations are batched and
applied together.
"""

import logging
import os
import re

test_injection = """a0.9i0a9deienatd"""

sprinter_override_string = "#_SPRINTER_OVERRIDES"
sprinter_override_match = wrapper_match = re.compile("%s.*%s" % (sprinter_override_string,
                                                                 sprinter_override_string
                                                                ), re.DOTALL)


class Injections(object):
    """
    Injections are staged until they are committed with the commit()
    method. This allow for aggregations until the commiting is ready
    to be performed.
    """

    logger = None  # logging object
    wrapper = None  # the string to wrap around the content.
    inject_dict = {}  # dictionary holding the injection object
    clear_dict = set()  # list holding the filenames to clear injection from

    def __init__(self, wrapper, logger='sprinter'):
        self.logger = logging.getLogger(logger)
        self.wrapper = wrapper

    def inject(self, filename, content):
        """ add the injection content to the dictionary """
        if filename in self.inject_dict:
            self.inject_dict[filename] += ("\n" + content)
        else:
            self.inject_dict[filename] = content

    def clear(self, filename):
        """ add the file to the list of files to clear """
        self.clear_dict.add(filename)

    def commit(self):
        """ commit the injections desired, overwriting any previous injections in the file. """
        wrapper = "#%s" % self.wrapper
        for filename, content in self.inject_dict.items():
            self.logger.info("Injecting values into %s..." % filename)
            self.__inject(filename, wrapper, content)
        for filename in self.clear_dict:
            self.logger.info("Clearing injection from %s..." % filename)
            self.__clear(filename, wrapper)

    def __inject(self, install_filename, wrapper, inject_string):
        """
        Inject inject_string into a file, wrapped with
        #SPRINTER_{{NAMESPACE}} comments if condition lambda is not
        satisfied or is None. Remove old instances of injects if they
        exist.
        """
        install_filename = os.path.expanduser(install_filename)
        if not os.path.exists(os.path.dirname(install_filename)):
            os.makedirs(os.path.dirname(install_filename))
        if not os.path.exists(install_filename):
            open(install_filename, "w+").close()
        install_file = open(install_filename, "r+")
        wrapper_match = re.compile("\n%s.*%s" % (wrapper, wrapper), re.DOTALL)
        content = wrapper_match.sub("", install_file.read())
        sprinter_overrides = sprinter_override_match.search(content)
        if sprinter_overrides:
            content = sprinter_overrides.sub("", content)
            sprinter_overrides = sprinter_overrides.groups()[0]
        else:
            sprinter_overrides = ""
        content += """
%s
%s
%s
%s""" % (wrapper, inject_string, wrapper, sprinter_overrides)
        install_file.close()
        install_file = open(install_filename, "w+")
        install_file.write(content)
        install_file.close()

    def __clear(self, install_filename, wrapper):
        """
        Inject inject_string into a file, wrapped with
        #SPRINTER_{{NAMESPACE}} comments if condition lambda is not
        satisfied or is None. Remove old instances of injects if they
        exist.
        """
        install_filename = os.path.expanduser(install_filename)
        if not os.path.exists(install_filename):
            open(install_filename, "w+").close()
        install_file = open(install_filename, "r+")
        wrapper_match = re.compile("\n%s.*%s" % (wrapper, wrapper), re.DOTALL)
        content = wrapper_match.sub("", install_file.read())
        install_file.close()
        install_file = open(install_filename, "w+")
        install_file.write(content)
        install_file.close()
