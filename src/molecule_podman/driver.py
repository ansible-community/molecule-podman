#  Copyright (c) 2015-2018 Cisco Systems, Inc.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
"""Podman Driver Module."""

from __future__ import absolute_import

import distutils.spawn
import os
from typing import Dict

from ansible_compat.ports import cache
from ansible_compat.runtime import Runtime
from molecule import logger, util
from molecule.api import Driver
from molecule.constants import RC_SETUP_ERROR
from molecule.util import sysexit_with_message
from packaging.version import Version

log = logger.get_logger(__name__)


class Podman(Driver):
    """
    The class responsible for managing `Podman`_ containers.

    `Podman`_ is not default driver used in Molecule.

    Molecule uses Podman ansible connector and podman CLI while mapping
    variables from ``molecule.yml`` into ``create.yml`` and ``destroy.yml``.

    .. _`podman connection`: https://docs.ansible.com/ansible/latest/plugins/connection/podman.html

    .. code-block:: yaml

        driver:
          name: podman
        platforms:
          - name: instance
            hostname: instance
            image: image_name:tag
            dockerfile: Dockerfile.j2
            pull: True|False
            pre_build_image: True|False
            registry:
              url: registry.example.com
              credentials:
                username: $USERNAME
                password: $PASSWORD
            override_command: True|False
            command: sleep infinity
            tty: True|False
            pid_mode: host
            privileged: True|False
            security_opts:
              - seccomp=unconfined
            volumes:
              - /sys/fs/cgroup:/sys/fs/cgroup:ro
            tmpfs:
              - /tmp
              - /run
            capabilities:
              - SYS_ADMIN
            exposed_ports:
              - 53/udp
              - 53/tcp
            published_ports:
              - 0.0.0.0:8053:53/udp
              - 0.0.0.0:8053:53/tcp
            ulimits:
              - nofile=1024:1028
            dns_servers:
              - 8.8.8.8
            network: host
            etc_hosts: {'host1.example.com': '10.3.1.5'}
            cert_path: /foo/bar/cert.pem
            tls_verify: true
            env:
              FOO: bar
            restart_policy: on-failure
            restart_retries: 1
            buildargs:
              http_proxy: http://proxy.example.com:8080/
            cgroup_manager: cgroupfs
            storage_opt: overlay.mount_program=/usr/bin/fuse-overlayfs
            storage_driver: overlay
            systemd: true|false|always

    If specifying the `CMD`_ directive in your ``Dockerfile.j2`` or consuming a
    built image which declares a ``CMD`` directive, then you must set
    ``override_command: False``. Otherwise, Molecule takes care to honour the
    value of the ``command`` key or uses the default of ``bash -c "while true;
    do sleep 10000; done"`` to run the container until it is provisioned.

    When attempting to utilize a container image with `systemd`_ as your init
    system inside the container to simulate a real machine, make sure to set
    the ``privileged``, ``command``, and ``environment`` values. An example
    using the ``centos:8`` image is below:

    .. note:: Do note that running containers in privileged mode is considerably
              less secure.

    .. code-block:: yaml

        platforms:
        - name: instance
          image: centos:8
          privileged: true
          command: "/usr/sbin/init"
          tty: True

    .. code-block:: bash

        $ python3 -m pip install molecule[podman]

    When pulling from a private registry, it is the user's discretion to decide
    whether to use hard-code strings or environment variables for passing
    credentials to molecule.

    .. important::

        Hard-coded credentials in ``molecule.yml`` should be avoided, instead use
        `variable substitution`_.

    Provide a list of files Molecule will preserve, relative to the scenario
    ephemeral directory, after any ``destroy`` subcommand execution.

    .. code-block:: yaml

        driver:
          name: podman
          safe_files:
            - foo

    .. _`Podman`: https://podman.io/
    .. _`systemd`: https://www.freedesktop.org/wiki/Software/systemd/
    .. _`CMD`: https://docs.docker.com/engine/reference/builder/#cmd
    """  # noqa

    def __init__(self, config=None):
        """Construct Podman."""
        super().__init__(config)
        self._name = "podman"
        # To change the podman executable, set environment variable
        # MOLECULE_PODMAN_EXECUTABLE
        # An example could be MOLECULE_PODMAN_EXECUTABLE=podman-remote
        self.podman_exec = os.environ.get("MOLECULE_PODMAN_EXECUTABLE", "podman")
        self.podman_cmd = distutils.spawn.find_executable(self.podman_exec)
        if not self.podman_cmd:
            msg = f"command not found in PATH {self.podman_exec}"
            util.sysexit_with_message(msg)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def login_cmd_template(self):
        return (
            f"{self.podman_cmd} exec "
            "-e COLUMNS={columns} "
            "-e LINES={lines} "
            "-e TERM=bash "
            "-e TERM=xterm "
            "-ti {instance} bash"
        )

    @property
    def default_safe_files(self):
        return [os.path.join(self._config.scenario.ephemeral_directory, "Dockerfile")]

    @property
    def default_ssh_connection_options(self):
        return []

    def login_options(self, instance_name):
        return {"instance": instance_name}

    def ansible_connection_options(self, instance_name):
        return {
            "ansible_connection": "podman",
            "ansible_podman_executable": f"{self.podman_exec}",
        }

    @cache
    def sanity_checks(self):
        """Implement Podman driver sanity checks."""
        log.info("Sanity checks: '%s'", self._name)
        # TODO(ssbarnea): reuse ansible runtime instance from molecule once it
        # fully adopts ansible-compat
        runtime = Runtime()
        if runtime.version < Version("2.10.0") and runtime.config.ansible_pipelining:
            sysexit_with_message(
                f"Podman connections do not work with Ansible {runtime.version} when pipelining is enabled. "
                "Disable pipelining or "
                "upgrade Ansible to 2.11 or newer.",
                code=RC_SETUP_ERROR,
            )

    @property
    def required_collections(self) -> Dict[str, str]:
        """Return collections dict containing names and versions required."""
        return {"containers.podman": "1.7.0", "ansible.posix": "1.3.0"}
