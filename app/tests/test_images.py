import re
import urllib.error
import urllib.request

import pytest

from brain_castle import images as imgs
from brain_castle.services import ServiceError
from conftest import PNG, data_url, files

TOKEN = re.compile(r"img:(\w+)")


def task_with_image(svc, alt="pic", raw=PNG, mime="image/png"):
    return svc.create_task({"title": "t", "notes": f"hello\n\n![{alt}](img:i900)", "images": {"i900": data_url(raw, mime)}})


def test_sniff_real_type():
    assert imgs.sniff(PNG) == "png"
    assert imgs.sniff(b"\xff\xd8\xff\xe0abc") == "jpg"
    assert imgs.sniff(b"GIF89a....") == "gif"
    assert imgs.sniff(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "webp"
    assert imgs.sniff(b"<svg></svg>") is None and imgs.sniff(b"MZ\x90\x00") is None


def test_save_checks_type_and_size(images_dir):
    name = imgs.save_image(images_dir, PNG)
    assert name.endswith(".png") and (images_dir / name).read_bytes() == PNG
    with pytest.raises(imgs.ImageError):
        imgs.save_image(images_dir, b"not an image at all")
    with pytest.raises(imgs.ImageError):
        imgs.save_image(images_dir, b"")
    with pytest.raises(imgs.ImageError):
        imgs.save_image(images_dir, PNG + b"0" * 100, max_bytes=50)
    assert len(files(images_dir)) == 1


def test_decode_data_url_errors():
    assert imgs.decode_data_url(data_url()) == PNG
    for bad in ("data:image/png,rawtext", "data:image/png;base64,@@@", "data:image/png;base64"):
        with pytest.raises(imgs.ImageError):
            imgs.decode_data_url(bad)
    with pytest.raises(imgs.ImageError):
        imgs.decode_data_url(data_url(PNG * 10), max_bytes=100)


def test_the_file_name_does_not_come_from_the_user(images_dir):
    assert re.fullmatch(r"[0-9a-f]{32}\.png", imgs.save_image(images_dir, PNG))


def test_saving_text_with_a_new_image_stores_the_file(svc, images_dir):
    t = task_with_image(svc)
    (new_id,) = t["images"]
    assert new_id.startswith("i") and f"(img:{new_id})" in t["notes"] and "img:i900)" not in t["notes"]
    assert t["images"][new_id].startswith("http://x/images/")
    assert len(files(images_dir)) == 1


def test_a_fake_image_is_refused_and_nothing_is_saved(svc, images_dir):
    with pytest.raises(ServiceError if False else imgs.ImageError):
        task_with_image(svc, raw=b"MZ this is an exe", mime="image/png")
    assert svc.load_all()["tasks"] == [] and files(images_dir) == []


def test_a_failed_save_removes_the_files_it_wrote(svc, images_dir):
    with pytest.raises(ServiceError):
        svc.create_task({"title": "t", "notes": "![a](img:i1)", "images": {"i1": data_url()}, "tags": ["g99"]})
    assert files(images_dir) == []


def test_update_keeps_existing_images_and_adds_new_ones(svc, images_dir):
    t = task_with_image(svc)
    (old,) = t["images"]
    notes = t["notes"] + "\n\n![two](img:i7)"
    u = svc.update_task(t["id"], {"notes": notes, "images": {**t["images"], "i7": data_url()}})
    assert len(u["images"]) == 2 and old in u["images"]
    assert len(files(images_dir)) == 2
    # an old id is not mistaken for another image even if JS invents the same id as another item's
    assert set(TOKEN.findall(u["notes"])) == set(u["images"])


def test_images_not_in_the_text_are_deleted(svc, images_dir):
    t = task_with_image(svc)
    u = svc.update_task(t["id"], {"notes": "no pictures now", "images": {}})
    assert u["images"] == {} and files(images_dir) == []


def test_text_edit_without_an_images_map_keeps_images_that_are_still_used(svc, images_dir):
    t = task_with_image(svc)
    u = svc.update_task(t["id"], {"notes": t["notes"] + " more words"})
    assert u["images"] == t["images"] and len(files(images_dir)) == 1


def test_delete_task_deletes_its_files(svc, images_dir):
    t = task_with_image(svc)
    svc.delete_task(t["id"])
    assert files(images_dir) == []


def test_delete_book_deletes_note_files(svc, images_dir):
    b = svc.create_book({"name": "b"})
    svc.create_note({"title": "n", "bookId": b["id"], "body": "![a](img:i1)", "images": {"i1": data_url()}})
    keep = svc.create_note({"title": "k", "bookId": svc.create_book({"name": "c"})["id"], "body": "![a](img:i1)", "images": {"i1": data_url()}})
    assert len(files(images_dir)) == 2
    svc.delete_book(b["id"])
    assert len(files(images_dir)) == 1 and len(keep["images"]) == 1


def test_same_image_twice_in_the_text_is_one_file(svc, images_dir):
    t = svc.create_task({"title": "t", "notes": "![a](img:i1)\n\n![b](img:i1)", "images": {"i1": data_url()}})
    assert len(t["images"]) == 1 and len(files(images_dir)) == 1
    assert len(set(TOKEN.findall(t["notes"]))) == 1


def test_unknown_id_without_data_is_left_alone(svc, images_dir):
    t = svc.create_task({"title": "t", "notes": "![a](img:i55)", "images": {}})
    assert t["images"] == {} and t["notes"] == "![a](img:i55)" and files(images_dir) == []


def test_ids_from_another_item_are_not_taken_over(svc, images_dir):
    a = task_with_image(svc)
    (aid,) = a["images"]
    b = svc.create_task({"title": "b", "notes": f"![x](img:{aid})", "images": {aid: a["images"][aid]}})
    assert b["images"] == {}  # the id belongs to task a, so b does not get it
    assert len(files(images_dir)) == 1


def test_image_server_serves_only_the_images_folder(images_dir, tmp_path):
    (tmp_path / "secret.txt").write_text("secret")
    name = imgs.save_image(images_dir, PNG)
    srv = imgs.LocalServer(images_dir).start()
    try:
        url = srv.url_for(name)
        assert url.startswith("http://127.0.0.1:")
        with urllib.request.urlopen(url) as r:
            assert r.read() == PNG and r.headers["Content-Type"] == "image/png"
        for path in ("/images/../secret.txt", "/images/secret.txt", "/etc/passwd", "/images/" + "0" * 32 + ".png"):
            with pytest.raises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(url.split("/images/")[0] + path)
            assert e.value.code == 404
    finally:
        srv.stop()


def test_local_server_serves_the_web_folder_with_js_mime(images_dir, tmp_path):
    web = tmp_path / "web"
    (web / "js").mkdir(parents=True)
    (web / "index.html").write_text("<p>hi</p>")
    (web / "js" / "a.js").write_text("export default 1")
    (tmp_path / "outside.txt").write_text("secret")
    srv = imgs.LocalServer(images_dir, web).start()
    try:
        with urllib.request.urlopen(srv.base + "/index.html?host=py") as r:
            assert r.read() == b"<p>hi</p>"
        with urllib.request.urlopen(srv.base + "/js/a.js") as r:
            assert r.headers["Content-Type"].startswith("text/javascript")
        for path in ("/../outside.txt", "/%2e%2e/outside.txt", "/js/missing.js", "/js"):
            with pytest.raises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(srv.base + path)
            assert e.value.code == 404
    finally:
        srv.stop()
