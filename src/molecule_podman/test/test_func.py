"""Functional tests."""
import os
import subprocess

from molecule import logger
from molecule.test.conftest import change_dir_to, molecule_directory
from molecule.util import run_command

import molecule_podman

LOG = logger.get_logger(__name__)


def format_result(result: subprocess.CompletedProcess):
    """Return friendly representation of completed process run."""
    return (
        f"RC: {result.returncode}\n"
        + f"STDOUT: {result.stdout}\n"
        + f"STDERR: {result.stderr}"
    )


def test_command_init_scenario(temp_dir, DRIVER):
    """Verify that init scenario works."""
    role_directory = os.path.join(temp_dir.strpath, "test-init")
    cmd = ["molecule", "init", "role", "test-init"]
    scenario_name = "test-scenario-podman"
    result = run_command(cmd)
    assert result.returncode == 0

    with change_dir_to(role_directory):
        scenario_directory = os.path.join(molecule_directory(), scenario_name)
        cmd = [
            "molecule",
            "init",
            "scenario",
            scenario_name,
            "--role-name",
            "test-init",
            "--driver-name",
            DRIVER,
        ]
        result = run_command(cmd)
        assert result.returncode == 0

        assert os.path.isdir(scenario_directory)

        # run molecule reset as this may clean some leftovers from other
        # test runs and also ensure that reset works.
        result = run_command(["molecule", "reset"])  # default sceanario
        assert result.returncode == 0

        result = run_command(["molecule", "reset", "-s", scenario_name])
        assert result.returncode == 0

        cmd = ["molecule", "--debug", "test", "-s", scenario_name]
        result = run_command(cmd)
        assert result.returncode == 0


def test_dockerfile():
    """Verify that our embedded dockerfile can be build."""
    result = subprocess.run(
        ["ansible-playbook", "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        shell=False,
        universal_newlines=True,
    )
    assert result.returncode == 0, result
    assert "ansible-playbook" in result.stdout

    module_path = os.path.dirname(molecule_podman.__file__)
    assert os.path.isdir(module_path)
    env = os.environ.copy()
    env["ANSIBLE_FORCE_COLOR"] = "0"
    result = subprocess.run(
        ["ansible-playbook", "-i", "localhost,", "playbooks/validate-dockerfile.yml"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        shell=False,
        cwd=module_path,
        universal_newlines=True,
        env=env,
    )
    assert result.returncode == 0, format_result(result)
    # , result
