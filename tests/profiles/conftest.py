# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import logging
from pathlib import Path

import pytest
import select_ai

LOG_FORMAT = "%(levelname)s: [%(name)s] %(message)s"


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


@pytest.fixture(autouse=True)
def log_test_case(request, configure_module_logging):
    logger = logging.getLogger(request.module.__name__)
    logger.info("Starting test %s", request.node.name)
    yield
    logger.info("Finished test %s", request.node.name)


@pytest.fixture(scope="module")
def provider():
    return select_ai.OCIGenAIProvider(
        region="us-phoenix-1", oci_apiformat="GENERIC"
    )


@pytest.fixture(scope="module")
def profile_attributes(provider, oci_credential):
    return select_ai.ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        object_list=[{"owner": "SH"}],
        provider=provider,
    )


@pytest.fixture(scope="module")
def min_profile_attributes(provider, oci_credential):
    return select_ai.ProfileAttributes(
        credential_name=oci_credential["credential_name"],
        provider=select_ai.OCIGenAIProvider(),
    )
