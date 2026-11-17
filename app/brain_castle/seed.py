"""Dev only: fill an EMPTY database with sample data (same as the front-end's mock-data.js).

Used by `python -m brain_castle --seed` so the real UI can be checked by hand or with Playwright.
The real app never calls this: a first run starts empty.
"""
from datetime import date, timedelta

from .services import Services

PAL = ["#FFC9D9", "#FFE9A0", "#C3D4FF", "#E0CCFF", "#BFEBDD", "#FFD3B8"]


def seed(svc: Services) -> None:
    if svc.load_all()["tasks"] or svc.load_all()["books"] or svc.load_all()["tags"]:
        return
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    def wd(i: int) -> str:
        return (monday + timedelta(days=i)).isoformat()

    tag = {name: svc.create_tag({"name": name, "color": color})["id"]
           for name, color in [("self-care", PAL[0]), ("work", PAL[2]), ("home", PAL[4]), ("ideas", PAL[1]), ("dreams", PAL[3])]}
    for f in [
        {"title": "Water the plants", "date": wd(0), "tags": [tag["home"]], "done": True},
        {"title": "Reply to Mia", "notes": "Ask about Saturday brunch", "date": wd(0), "time": "10:00", "tags": [tag["work"]]},
        {"title": "Grocery run", "notes": "Oat milk, berries, bread", "date": wd(1), "time": "17:30", "tags": [tag["home"]]},
        {"title": "30 minute stretch", "date": wd(1), "tags": [tag["self-care"]]},
        {"title": "Plan next week", "date": wd(2), "time": "09:00", "tags": [tag["work"]]},
        {"title": "Book the dentist", "date": wd(3)},
        {"title": "Learn a new recipe", "tags": [tag["ideas"]]},
        {"title": "Renew bus pass", "date": (today - timedelta(days=125)).isoformat()},
    ]:
        svc.create_task(f)
    books = {name: svc.create_book({"name": name, "color": color})["id"]
             for name, color in [("Daily Diary", PAL[1]), ("Dream Journal", PAL[3]), ("Idea Garden", PAL[4])]}
    svc.create_note({"bookId": books["Daily Diary"], "title": "A slow Sunday", "date": wd(-1), "tags": [tag["self-care"]],
                     "body": "Made pancakes, read by the window and finally cleaned the bookshelf."})
    svc.create_note({"bookId": books["Dream Journal"], "title": "The floating library", "tags": [tag["dreams"]],
                     "body": "I was in a library with no roof. Books drifted up like balloons."})
    svc.create_note({"bookId": books["Idea Garden"], "title": "Tiny desk garden", "tags": [tag["ideas"], tag["home"]],
                     "body": "Try a row of herbs on the windowsill."})
    svc.run_maintenance()
