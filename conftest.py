"""Unit tests do not require a frontend build or a collectstatic manifest.

Production keeps strict WhiteNoise manifest storage. The Docker integration
job separately checks that the compiled bundle is actually served.
"""

import pytest


@pytest.fixture(autouse=True)
def unit_test_static_storage(settings):
    settings.MIDDLEWARE = [
        middleware
        for middleware in settings.MIDDLEWARE
        if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
    ]
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
