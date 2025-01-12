"""
Copyright (c) 2015-2022 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""
from __future__ import print_function, absolute_import, unicode_literals

import logging
import os
import os.path

from six.moves import configparser
from six.moves.urllib.parse import urljoin

from osbs.constants import (DEFAULT_CONFIGURATION_FILE, GENERAL_CONFIGURATION_SECTION,
                            DEFAULT_NAMESPACE)
from osbs import utils


logger = logging.getLogger(__name__)


class Configuration(object):
    """
    class for managing configuration; it takes data from

     * ini-style config
     * command line (argparse)
     * dict
    """

    def __init__(self, conf_file=DEFAULT_CONFIGURATION_FILE,
                 conf_section=GENERAL_CONFIGURATION_SECTION,
                 cli_args=None, **kwargs):
        """
        sample initialization:

            Configuration("./osbs.conf", "fedora", openshift_uri="https://localhost:8443/",
                          username="admin", password="something")

        :param conf_file: str, path to configuration file, or None for no configuration file
        :param conf_section: str, name of section with configuration for requested instance
        :param cli_args: instance of argument parser of argparse
        :param kwargs: keyword arguments, which have highest priority: key is cli argument name
        """
        self.scp = configparser.ConfigParser()
        if conf_file and os.path.isfile(conf_file) and os.access(conf_file, os.R_OK):
            self.scp.read(conf_file)
            if not self.scp.has_section(conf_section):
                logger.warning("Specified section '%s' not found in '%s'",
                               conf_section, conf_file)
        self.conf_section = conf_section
        self.args = cli_args
        self.kwargs = kwargs

    def _get_value(self, args_key, conf_section, conf_key, default=None, is_bool_val=False,
                   deprecated=False):
        # and implement it as mixins
        def get_value_from_kwargs():
            return self.kwargs.get(args_key)

        def get_value_from_cli_args():
            return getattr(self.args, args_key, None)

        def get_value_from_conf():
            try:
                return self.scp.get(conf_section, conf_key)
            except configparser.Error:
                return None

        retrieval_order = [
            get_value_from_kwargs,
            get_value_from_cli_args,
            get_value_from_conf,
        ]

        for func in retrieval_order:
            value = func()
            if value is not None:
                # Only print deprecation warnings for cli or file arguments
                if deprecated and func in (get_value_from_cli_args, get_value_from_conf):
                    logger.warning("user configuration key '%s' in section '%s' is ignored, "
                                   "it has been deprecated in favor of the value in the"
                                   " reactor_config_map", args_key, conf_section)
                break
        else:  # we didn't break
            return default

        if is_bool_val:
            try:
                int_val = int(value)
            except ValueError:
                if value.lower() == 'true':
                    return True
                return False
            except TypeError:
                return False
            else:
                return bool(int_val)
        else:
            return value

    def _get_deprecated(self, args_key, conf_section, conf_key, default=None, is_bool_val=False):
        return self._get_value(args_key, conf_section, conf_key, default, is_bool_val,
                               deprecated=True)

    def get_openshift_base_uri(self):
        """
        https://<host>[:<port>]/

        :return: str
        """
        key = "openshift_url"
        val = self._get_value(key, self.conf_section, key)
        return val

    @staticmethod
    def get_k8s_api_version():
        # This is not configurable.
        return "v1"

    def get_k8s_api_uri(self):
        """
        https://<host>[:<port>]/api/<API version>/

        :return: str
        """
        base_uri = self.get_openshift_base_uri()
        version = self.get_k8s_api_version()
        return urljoin(base_uri, "/api/{version}/".format(version=version))

    def get_openshift_api_uri(self):
        """
        Compatible with OCP3.6+
        https://<host>[:<port>]/apis/

        :return: str
        """
        base_uri = self.get_openshift_base_uri()
        return urljoin(base_uri, "/apis/")

    def get_openshift_oauth_api_uri(self):
        """
        https://<host>[:<port>]/oauth/authorize/

        :return: str
        """
        base_uri = self.get_openshift_base_uri()
        return urljoin(base_uri, "/oauth/authorize")  # MUST NOT END WITH SLASH

    def get_verbosity(self):
        return self._get_value("verbose", GENERAL_CONFIGURATION_SECTION, "verbose",
                               is_bool_val=True)

    def get_git_uri(self):
        return self._get_value("git_url", self.conf_section, "git_url")

    def get_git_ref(self):
        return self._get_value("git_commit", self.conf_section, "git_commit")

    def get_git_branch(self):
        return self._get_value("git_branch", self.conf_section, "git_branch")

    def get_user(self):
        """ user namespace when tagging and pushing image """
        return self._get_value("user", self.conf_section, "user")

    def get_tag(self):
        return self._get_value("tag", self.conf_section, "tag")

    def get_yum_repourls(self):
        return self._get_value("yum_repourls", self.conf_section, "yum_repourls")

    def get_dependency_replacements(self):
        return self._get_value("dependency_replacements", self.conf_section,
                               "dependency_replacements")

    def get_namespace(self):
        return self._get_value("namespace", self.conf_section, "namespace",
                               default=DEFAULT_NAMESPACE)

    def get_flatpak(self):
        return self._get_value("flatpak", self.conf_section, "flatpak",
                               is_bool_val=True)

    def get_koji_target(self):
        return self._get_value("target", self.conf_section, "target")

    def get_username(self):
        return self._get_value("username", self.conf_section, "username")

    def get_password(self):
        return self._get_value("password", self.conf_section, "password")

    def get_client_cert(self):
        return self._get_value("client_cert", self.conf_section, "client_cert")

    def get_client_key(self):
        return self._get_value("client_key", self.conf_section, "client_key")

    def get_use_kerberos(self):
        return self._get_value("use_kerberos", self.conf_section, "use_kerberos", is_bool_val=True)

    def get_kerberos_keytab(self):
        return self._get_value("kerberos_keytab", self.conf_section, "kerberos_keytab")

    def get_kerberos_principal(self):
        return self._get_value("kerberos_principal", self.conf_section, "kerberos_principal")

    def get_kerberos_ccache(self):
        return self._get_value("kerberos_ccache", self.conf_section, "kerberos_ccache")

    def get_cleanup_used_resources(self):
        return self._get_value("cleanup_used_resources", self.conf_section,
                               "cleanup_used_resources", default=True, is_bool_val=True)

    def get_verify_ssl(self):
        return self._get_value("verify_ssl", self.conf_section, "verify_ssl",
                               default=True, is_bool_val=True)

    def get_use_auth(self):
        return self._get_value("use_auth", self.conf_section, "use_auth", is_bool_val=True)

    def get_scratch(self, default_value):
        return self._get_value("scratch", self.conf_section, "scratch",
                               default=default_value, is_bool_val=True)

    def get_oauth2_token(self):
        # token overrides token_file
        # either in kwargs overrides cli args
        # either in cli args overrides conf
        key_names = ['token', 'token_file']
        value = None
        found_key = None
        for key in key_names:
            value = self.kwargs.get(key)
            if value is not None:
                found_key = key
                break

        if value is None:
            for key in key_names:
                value = getattr(self.args, key, None)
                if value is not None:
                    found_key = key
                    break

        if value is None:
            for key in key_names:
                try:
                    value = self.scp.get(self.conf_section, key)
                except configparser.Error:
                    pass
                else:
                    found_key = key
                    break

        if value is None:
            instance_token_file = utils.get_instance_token_file_name(self.conf_section)
            if os.path.exists(instance_token_file):
                found_key = 'token_file'
                value = instance_token_file

        # For token_file, read the file
        if found_key == 'token_file':
            token_file = value
            try:
                with open(token_file, 'r') as token_fd:
                    value = token_fd.read().strip()
            except IOError as ex:
                logger.error("exception caught while reading %s: %r",
                             token_file, ex)

        return value

    def get_reactor_config_map(self):
        return self._get_value("reactor_config_map", self.conf_section,
                               "reactor_config_map")

    def get_reactor_config_map_scratch(self):
        return self._get_value("reactor_config_map_scratch", self.conf_section,
                               "reactor_config_map_scratch")

    def get_pipeline_run_path(self):
        return self._get_value("pipeline_run_path", self.conf_section,
                               "pipeline_run_path")

    # dummy function for use with the unit tests
    def get_deprecated_key(self):
        return self._get_deprecated("deprecated_key", self.conf_section, "deprecated_key")
