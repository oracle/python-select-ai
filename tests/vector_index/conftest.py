# -----------------------------------------------------------------------------
# Copyright (c) 2026, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging
import os
import uuid
from pathlib import Path

import pytest

LOG_FORMAT = "%(levelname)s: [%(name)s] %(message)s"
_VCIDX_ENV_NAMES = {
    "EMBEDDING_LOCATION": "PYTEST_TEST_OBJSTORE_EMBEDDING_LOC",
    "CRED_USERNAME": "PYTEST_TEST_OBJSTORE_USERNAME",
    "CRED_PASSWORD": "PYTEST_TEST_OBJSTORE_PASSWORD",
}


def get_vcidx_env_value(name, default_value=None, required=False):
    """
    Reads vector-index-specific environment variables.
    """
    env_name = _VCIDX_ENV_NAMES[name]
    value = os.environ.get(env_name)
    if value is None:
        if required:
            pytest.exit(
                f"missing value for environment variable {env_name}", 1
            )
        return default_value
    return value


def _configure_logger(logger: logging.Logger, module_file: str) -> None:
    logger.setLevel(logging.DEBUG)
    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"tkex_{Path(module_file).stem}.log"
    formatter = logging.Formatter(fmt=LOG_FORMAT)
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.handlers.clear()
    logger.propagate = False
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.info("Configured logging for module")


@pytest.fixture(scope="module", autouse=True)
def configure_module_logging(request):
    module = request.module
    logger = logging.getLogger(module.__name__)
    _configure_logger(logger, module.__file__)
    yield
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()


@pytest.fixture(scope="session")
def embedding_location():
    value = get_vcidx_env_value("EMBEDDING_LOCATION", required=True)

    # Fail fast with a clear message if the wrong value is being used
    if "inference.generativeai" in value or "/actions/embedText" in value:
        pytest.exit(
            "PYTEST_TEST_OBJSTORE_EMBEDDING_LOC is set to a GenAI inference endpoint. "
            "It must be an Object Storage URI/URL (objectstorage.../n/<ns>/b/<bucket>/o/<prefix>). "
            f"Got: {value}",
            1,
        )

    if "objectstorage." not in value:
        pytest.exit(
            "PYTEST_TEST_OBJSTORE_EMBEDDING_LOC does not look like an Object Storage URL/URI. "
            f"Got: {value}",
            1,
        )

    return value


@pytest.fixture(scope="session")
def vcidx_object_store_credentials():
    return {
        "cred_username": get_vcidx_env_value("CRED_USERNAME"),
        "cred_password": get_vcidx_env_value("CRED_PASSWORD"),
    }


@pytest.fixture(scope="class")
def vcidx_params(
    request,
    test_env,
    oci_credential,
    oci_compartment_id,
    embedding_location,
    vcidx_object_store_credentials,
):
    # Test modules share a schema. Include the module name in every generated
    # resource so credentials, profiles, and indexes never overlap.
    module_suffix = (
        Path(request.module.__file__).stem.removeprefix("test_").upper()
    )
    py_suffix = os.environ.get("PYTHON_VERSION_WITHOUT_DOT")
    run_suffix = os.environ.get("GITHUB_RUN_ID")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    if run_suffix and run_attempt:
        run_suffix = f"{run_suffix}_{run_attempt}"
    elif not run_suffix:
        run_suffix = uuid.uuid4().hex[:12].upper()

    if py_suffix:
        resource_suffix = f"PY{py_suffix}_{run_suffix}_{module_suffix}"
    else:
        resource_suffix = f"PYSAI_{run_suffix}_{module_suffix}"

    return {
        "resource_suffix": resource_suffix,
        "genai_cred": f"GENAI_CRED_{resource_suffix}",
        "objstore_cred": f"OBJSTORE_CRED_{resource_suffix}",
        "profile_name": f"vector_ai_profile_{resource_suffix}",
        "create_index_name": f"test_vector_index_create_{resource_suffix}",
        "drop_index_name": f"test_vector_index_drop_{resource_suffix}",
        "enabledisable_index_name": (
            f"test_vector_index_enable_disable_{resource_suffix}"
        ),
        "attr_index_name": f"test_vector_index_attr_{resource_suffix}",
        "temp_profile_name": f"vector_ai_profile_temp_{resource_suffix}",
        "temp_objstore_cred": f"TEMP_OBJSTORE_CRED_{resource_suffix}",
        "list_index_prefix": f"test_vector_index_{resource_suffix}",
        "list_vecidx_prefix": f"test_vecidx_{resource_suffix}",
        "user": test_env.admin_user,
        "password": test_env.admin_password,
        "dsn": test_env.connect_string,
        "user_ocid": oci_credential["user_ocid"],
        "tenancy_ocid": oci_credential["tenancy_ocid"],
        "private_key": oci_credential["private_key"],
        "fingerprint": oci_credential["fingerprint"],
        "oci_compartment_id": oci_compartment_id,
        "embedding_location": embedding_location,
        "cred_username": vcidx_object_store_credentials["cred_username"],
        "cred_password": vcidx_object_store_credentials["cred_password"],
    }
