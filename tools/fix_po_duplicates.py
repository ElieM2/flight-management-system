from pathlib import Path
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = [
    BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
]


def entry_has_translation(entry):
    if entry.msgid_plural:
        return any(value.strip() for value in entry.msgstr_plural.values())

    return bool(entry.msgstr.strip())


def copy_translation(source, target):
    if source.msgid_plural:
        for key, value in source.msgstr_plural.items():
            if value.strip():
                target.msgstr_plural[key] = value
    else:
        if source.msgstr.strip():
            target.msgstr = source.msgstr


def merge_metadata(source, target):
    for occurrence in source.occurrences:
        if occurrence not in target.occurrences:
            target.occurrences.append(occurrence)

    for comment in source.comment.splitlines():
        if comment and comment not in target.comment:
            if target.comment:
                target.comment += "\n" + comment
            else:
                target.comment = comment

    for tcomment in source.tcomment.splitlines():
        if tcomment and tcomment not in target.tcomment:
            if target.tcomment:
                target.tcomment += "\n" + tcomment
            else:
                target.tcomment = tcomment

    for flag in source.flags:
        if flag not in target.flags:
            target.flags.append(flag)


def fix_duplicates(path):
    if not path.exists():
        print(f"{path}: missing")
        return

    po = polib.pofile(str(path))

    seen = {}
    duplicates = []

    for entry in list(po):
        if entry.obsolete:
            continue

        key = (
            entry.msgctxt or "",
            entry.msgid or "",
            entry.msgid_plural or "",
        )

        if key not in seen:
            seen[key] = entry
            continue

        keeper = seen[key]

        if entry_has_translation(entry) and not entry_has_translation(keeper):
            copy_translation(entry, keeper)

        merge_metadata(entry, keeper)
        duplicates.append(entry)

    for entry in duplicates:
        po.remove(entry)

    po.save(str(path))
    print(f"{path}: removed {len(duplicates)} duplicate entry/entries")


def main():
    for path in PO_FILES:
        fix_duplicates(path)


if __name__ == "__main__":
    main()