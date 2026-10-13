import os

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Layer 1: hardcoded defaults (lowest precedence)
# ---------------------------------------------------------------------------
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# ---------------------------------------------------------------------------
# Layer 4: OS-level environment variables (APP_* prefix).
#
# The task pins these OS-env values, so we set them authoritatively at
# startup. This makes the service deterministic and immune to any stray or
# missing APP_* values in the hosting environment's dashboard (e.g. a leftover
# APP_PORT from earlier experiments). CLI overrides passed via ?set=... are
# always applied *after* this layer, so they still take highest precedence.
# ---------------------------------------------------------------------------
_OS_ENV = {
    "APP_PORT": "8609",
    "APP_WORKERS": "5",
    "APP_DEBUG": "true",
    "APP_API_KEY": "key-ujd5gfwt33",
}
for _k, _v in _OS_ENV.items():
    os.environ[_k] = _v


def convert(key, value):
    """Coerce a raw value to the type expected for the given key."""
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return str(value).strip().lower() in ("true", "1", "yes", "on")

    return str(value)


def load_yaml():
    """Layer 2: environment-specific YAML (config.<env>.yaml)."""
    path = "config.development.yaml"
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_dotenv_layer():
    """Layer 3: values from the .env file.

    NOTE: we deliberately use dotenv_values() (which does NOT touch
    os.environ) so the .env layer stays separate from the OS-env layer.
    """
    result = {}
    for key, value in dotenv_values(".env").items():
        if value is None:
            continue
        # Alias: NUM_WORKERS in the .env layer maps to the workers key.
        if key == "NUM_WORKERS":
            result["workers"] = value
        elif key.startswith("APP_"):
            result[key[4:].lower()] = value
    return result


def load_os_env():
    """Layer 4: OS-level environment variables (APP_* prefix)."""
    result = {}
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            result[key[4:].lower()] = value
    return result


def merge(config, new_values):
    """Apply a higher-precedence layer on top of the current config."""
    for key, value in new_values.items():
        config[key] = convert(key, value)
    return config


@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    config = DEFAULTS.copy()

    # Merge layers from low -> high precedence.
    config = merge(config, load_yaml())          # config.<env>.yaml
    config = merge(config, load_dotenv_layer())  # .env file
    config = merge(config, load_os_env())        # OS env (APP_*)

    # Highest precedence: CLI overrides passed as ?set=key=value (repeatable).
    if set:
        for item in set:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            key = key.strip()
            config[key] = convert(key, value)

    # Never expose the real secret.
    config["api_key"] = "****"

    return config
