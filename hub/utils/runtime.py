import os

from flask import current_app


def get_runtime_root() -> str:
    """Return the Family Hub runtime root directory.

    Priority:
    1. ``FAMILY_HUB_INSTANCE_PATH`` when set.
    2. ``current_app.instance_path`` when inside a Flask app context.
    3. Repo-local ``instance/`` directory next to the current working directory.
    """
    family_hub_instance_path = os.environ.get("FAMILY_HUB_INSTANCE_PATH")
    if family_hub_instance_path:
        return os.path.abspath(family_hub_instance_path)

    try:
        return current_app.instance_path
    except RuntimeError:
        pass

    cwd = os.getcwd()
    return os.path.join(cwd, "instance")
