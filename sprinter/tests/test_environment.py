from __future__ import unicode_literals
import os
import shutil
import tempfile
from io import StringIO
from mock import Mock, call, patch
from nose import tools
from nose.tools import eq_
from six.moves import configparser
from sprinter.testtools import (MockEnvironment,
                                create_mock_environment,
                                create_mock_formulabase)
from sprinter.lib import SprinterException
from sprinter.environment import Environment
from sprinter.formula.base import FormulaBase
from sprinter.core.templates import source_template
from sprinter.core.globals import create_default_config

source_config = """
[config]
test = hi
"""

target_config = """
[config]
inputs = password?
         main_branch?==comp_main

[noformula]
blank = thishasnoformula
"""


class TestEnvironment(object):
    """ Tests for the environment """

    def test_grab_inputs_existing_source(self):
        """ Grabbing inputs should source from source first, if it exists """

        with MockEnvironment(source_config, target_config) as environment:
            environment.target.grab_inputs = Mock()
            environment.grab_inputs()
            eq_(environment.target.inputs.get_unset_inputs(), set(['password', 'main_branch']))

    @tools.raises(SprinterException)
    def test_running_missing_formula(self):
        """ When a formula is missing, a sprinter exception should be thrown at the end """
        with MockEnvironment(target_config=missing_formula_config) as environment:
            environment.install()

    def test_catch_exception_in_feature(self):
        """
        If an exception occurs in a feature, it should be caught
        and still allow other features to run
        """

    def test_feature_run_order_install(self):
        """ A feature install should have it's methods run in the proper order """
        with MockEnvironment(target_config=test_target) as environment:
            with patch('sprinter.formula.base.FormulaBase', new=create_mock_formulabase()) as formulabase:
                environment.install()
                eq_(formulabase().method_calls, [call.should_run(),
                                                 call.validate(),
                                                 call.resolve(),
                                                 call.prompt(),
                                                 call.sync()])

    def test_feature_run_order_update(self):
        """ A feature update should have it's methods run in the proper order """
        with MockEnvironment(test_source, test_target) as environment:
            with patch('sprinter.formula.base.FormulaBase', new=create_mock_formulabase()) as formulabase:
                environment.directory = Mock(spec=environment.directory)
                environment.directory.new = False
                environment.update()
                eq_(formulabase().method_calls, [call.should_run(),
                                                 call.validate(),
                                                 call.resolve(),
                                                 call.prompt(),
                                                 call.sync()])

    def test_feature_run_order_remove(self):
        """ A feature remove should have it's methods run in the proper order """
        with MockEnvironment(test_source, test_target) as environment:
            with patch('sprinter.formula.base.FormulaBase', new=create_mock_formulabase()) as formulabase:
                environment.directory = Mock(spec=environment.directory)
                environment.directory.new = False
                environment.remove()
                eq_(formulabase().method_calls, [call.should_run(),
                                                 call.validate(),
                                                 call.resolve(),
                                                 call.prompt(),
                                                 call.sync()])

    def test_feature_run_order_deactivate(self):
        """ A feature deactivate should have it's methods run in the proper order """
        with MockEnvironment(test_source, test_target) as environment:
            with patch('sprinter.formula.base.FormulaBase', new=create_mock_formulabase()) as formulabase:
                environment.directory = Mock(spec=environment.directory)
                environment.directory.new = False
                environment.deactivate()
                eq_(formulabase().method_calls, [call.should_run(),
                                                 call.validate(),
                                                 call.resolve(),
                                                 call.prompt(),
                                                 call.deactivate()])

    def test_feature_run_order_activate(self):
        """ A feature should have it's methods run in the proper order """
        with MockEnvironment(test_source, test_target) as environment:
            with patch('sprinter.formula.base.FormulaBase', new=create_mock_formulabase()) as formulabase:
                environment.directory = Mock(spec=environment.directory)
                environment.directory.new = False
                environment.activate()
                eq_(formulabase().method_calls, [call.should_run(),
                                                 call.validate(),
                                                 call.resolve(),
                                                 call.prompt(),
                                                 call.activate()])

    def test_global_shell_configuration_bash(self):
        """ The global shell should dictate what files are injected (bash, gui, no zsh)"""
        # test bash, gui, no zshell
        global_config = create_default_config()
        global_config.set('shell', 'bash', 'true')
        global_config.set('shell', 'zsh', 'false')
        global_config.set('shell', 'gui', 'true')
        with MockEnvironment(test_source, test_target, global_config=global_config) as environment:
            environment.install()
            assert [x for x in environment.injections.inject_dict.keys() if x.endswith('.bashrc')]
            env_injected = False
            for profile in ['.bash_profile', '.bash_login', '.profile']:
                env_injected = env_injected or filter(lambda x: x.endswith(profile), environment.injections.inject_dict.keys())
            assert env_injected
            assert not [x for x in environment.injections.inject_dict.keys() if x.endswith('.zshrc')]
            for profile in ['.zprofile', '.zlogin']:
                assert not [x for x in environment.injections.inject_dict.keys() if x.endswith(profile)]

    def test_env_to_rc_injection(self):
        """ If env_source_rc is set to true, the env environments should source the rc """
        # test bash, gui, no zshell
        global_config = create_default_config()
        global_config.set('shell', 'bash', 'true')
        global_config.set('shell', 'zsh', 'true')
        global_config.set('shell', 'gui', 'false')
        with MockEnvironment(test_source, test_target, global_config=global_config) as environment:
            environment.install()

            # bash
            env_injected = False
            full_rc_path = os.path.expanduser(os.path.join("~", ".bashrc"))
            for profile in ['.bash_profile', '.bash_login', '.profile']:
                full_profile_path = os.path.expanduser(os.path.join("~", profile))
                specific_env_injected = full_profile_path in environment.global_injections.inject_dict
                if specific_env_injected:
                    env_injected = True
                    assert (source_template % (full_rc_path, full_rc_path) in
                            environment.global_injections.inject_dict[full_profile_path])
            assert env_injected

            # zshell
            env_injected = False
            full_rc_path = os.path.expanduser(os.path.join("~", ".zshrc"))
            for profile in ['.zprofile', '.zlogin']:
                full_profile_path = os.path.expanduser(os.path.join("~", profile))
                specific_env_injected = full_profile_path in environment.global_injections.inject_dict
                if specific_env_injected:
                    env_injected = True
                    assert (source_template % (full_rc_path, full_rc_path) in
                            environment.global_injections.inject_dict[full_profile_path])
            assert env_injected

    def test_global_shell_configuration_zshell(self):
        """ The global shell should dictate what files are injected (zsh, no bash, no gui)"""
        # test zshell, no bash, no gui
        global_config = create_default_config()
        global_config.set('shell', 'bash', 'false')
        global_config.set('shell', 'zsh', 'true')
        global_config.set('shell', 'gui', 'false')
        with MockEnvironment(target_config=test_target, global_config=global_config) as environment:
            environment.install()

            assert [x for x in environment.injections.inject_dict.keys() if x.endswith('.zshrc')]

            env_injected = False
            for profile in ['.zprofile', '.zlogin']:
                env_injected = env_injected or filter(lambda x: x.endswith(profile), environment.injections.inject_dict.keys())
            assert env_injected

            assert not [x for x in environment.injections.inject_dict.keys() if x.endswith('.bashrc')]

            for profile in ['.bash_profile', '.bash_login']:
                assert not [x for x in environment.injections.inject_dict.keys() if x.endswith(profile)]

    def test_global_config(self):
        """ Global config should accept a file-like object, or default to ROOT/.sprinter/.global/config.cfg """
        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, ".global"))
        with open(os.path.join(temp_dir, ".global", "config.cfg"), 'w+') as fh:
            fh.write("""[shell]
bash = true

[global]
env_source_rc = False
            """)
        try:
            env = Environment(root=temp_dir)
            assert env.global_config.get('shell', 'bash') == "true"
        finally:
            shutil.rmtree(temp_dir)

    def test_utilssh_file_written(self):
        """ The latest utilssh file should be written at the end of an install """
        with MockEnvironment(target_config=test_target) as environment:
            environment.install()
            assert os.path.exists(os.path.join(environment.global_path, 'utils.sh'))

    def test_message_failure_bad_manifest(self):
        "On an environment with a incorrectly formatted manifest, message_failure should return None"""
        with MockEnvironment(target_config=test_target) as environment:
            environment.target = "gibberish"
            assert environment.message_failure() is None

missing_formula_config = """
[missingformula]

[otherformula]
formula = sprinter.formula.base
"""

test_source = """
[testfeature]
formula = sprinter.formula.base
"""

test_target = """
[config]
namespace = testsprinter

[testfeature]
formula = sprinter.formula.base
"""