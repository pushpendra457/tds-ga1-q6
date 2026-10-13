from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from dotenv import dotenv_values
import os
import yaml

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def convert(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return str(value).lower() in (
            "true",
            "1",
            "yes",
            "on",
        )

    return str(value)


def load_yaml():
    with open("config.development.yaml") as f:
        return yaml.safe_load(f) or {}


def load_dotenv():
    env = dotenv_values(".env")

    result = {}

    for key, value in env.items():

        if key == "NUM_WORKERS":
            result["workers"] = value

        elif key.startswith("APP_"):
            result[key[4:].lower()] = value

    return result


def load_os_env():
    result = {}

    for key, value in os.environ.items():

        if key.startswith("APP_"):
            result[key[4:].lower()] = value

    return result



def merge(config, new_values):
    for key, value in new_values.items():
        config[key] = convert(key, value)

    return config




@app.get("/effective-config")
def effective_config(
    set: list[str] | None = Query(default=None)
):
    config = DEFAULTS.copy()

    config = merge(config, load_yaml())

    config = merge(config, load_dotenv())

    config = merge(config, load_os_env())


    if set:

        for item in set:

            if "=" not in item:
                continue

            key, value = item.split("=", 1)

            config[key] = convert(key, value)

    config["api_key"] = "****"

    return config