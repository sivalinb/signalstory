"""Build a credential-free, static visual playground from the Python studio's course."""

import shutil

from signalstory.course import ROOT


def main():
    destination = ROOT / "docs/playground"
    for component in ("concept", "scene", "hero"):
        shutil.copytree(
            ROOT / "signalstory/components" / component, destination / component, dirs_exist_ok=True
        )
    shutil.copy2(ROOT / "content/course.json", destination / "course.json")
    (ROOT / "docs/.nojekyll").touch()
    print("Built all 70 visual lessons. The preview contains no backend, credentials, or learner records.")


if __name__ == "__main__":
    main()
