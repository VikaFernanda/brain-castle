import base64
import sqlite3

import pytest

from brain_castle import db
from brain_castle.api import Api
from brain_castle.services import Services

# 1x1 PNG
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def data_url(raw: bytes = PNG, mime="image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


class Clock:
    def __init__(self, today="2026-11-17"):
        self.value = today

    def __call__(self):
        return self.value


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def images_dir(tmp_path):
    d = tmp_path / "images"
    d.mkdir()
    return d


@pytest.fixture
def con(tmp_path):
    c = db.connect(tmp_path / "t.db")
    yield c
    c.close()


@pytest.fixture
def svc(con, images_dir, clock):
    return Services(con, images_dir, image_url=lambda n: "http://x/images/" + n, today=clock)


@pytest.fixture
def api(svc):
    return Api(svc)


def files(images_dir):
    return sorted(p.name for p in images_dir.iterdir())
