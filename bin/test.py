import os
import subprocess

import pytest
import testinfra
import yaml

ASTRO_IMAGE_NAME = os.environ["ASTRO_IMAGE_NAME"]
ASTRO_IMAGE_TEST_CONFIG_PATH = os.environ["ASTRO_IMAGE_TEST_CONFIG_PATH"]

os.environ["ASTRO_IMAGE_TAG"] = os.environ.get("CIRCLE_SHA1", "latest")
test_config = {}

# Read the test config
if os.path.exists(ASTRO_IMAGE_TEST_CONFIG_PATH):
    with open(ASTRO_IMAGE_TEST_CONFIG_PATH) as file:
        config = yaml.safe_load(file)

        # Reading test config
        if config is not None and "tests" in config:
            test_config = config["tests"]


@pytest.fixture(scope="session")
def docker_host(request):
    run_command = ["docker-compose", "run", "-d", ASTRO_IMAGE_NAME]

    # run a container
    docker_id = subprocess.check_output(run_command).decode().strip()

    # return a testinfra connection to the container
    yield testinfra.get_host("docker://" + docker_id)
    # cleanup container after test completion
    subprocess.check_call(["docker", "rm", "-f", docker_id])


@pytest.mark.skipif(
    "root_user_test" not in test_config or test_config["root_user_test"] == False,
    reason="Config `root_user_test` is not set in `test.yaml`.",
)
def test_no_root_user(docker_host):
    user_info = docker_host.user()
    assert user_info.name != "root"
    assert user_info.group != "root"
    assert user_info.gid != 0
    assert user_info.uid != 0


@pytest.mark.skipif(
    "default_user" not in test_config,
    reason="Config `default_user` is not set in `test.yaml`.",
)
def test_default_user(docker_host):
    if "default_user" in test_config:
        """Ensure default user"""
        user = docker_host.check_output("whoami")
        assert (
            user == test_config["default_user"]
        ), f"Expected container to be running as 'nobody', not '{user}'"


@pytest.mark.skipif(
    "users_config" not in test_config,
    reason="Config `users_config` is not set in `test.yaml`.",
)
def test_user_config(docker_host):
    if "users_config" in test_config:

        for user_config in test_config["users_config"]:

            user_info = docker_host.user(user_config["name"])

            if "group" in user_config:
                assert user_info.group == user_config["group"]

            if "gid" in user_config:
                assert user_info.gid == user_config["gid"]

            if "uid" in user_config:
                assert user_info.uid == user_config["uid"]


@pytest.mark.skipif(
    "http_services_running" not in test_config,
    reason="Config `http_services_running` is not set in `test.yaml`.",
)
def test_http_service_running(docker_host):
    if "http_services_running" in test_config:

        for service_config in test_config["http_services_running"]:
            """Ensure user is 'nobody'"""
            output = docker_host.check_output(
                "wget --spider -S http://0.0.0.0:"
                + str(service_config["port"])
                + " 2>&1 | grep 'HTTP/' | awk '{print $2}'"
            )
            assert output == str(service_config["response_code"])