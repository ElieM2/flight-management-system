from pathlib import Path
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = [
    BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
]


def entry_key(entry):
    """
    For msgfmt, the real uniqueness key is:
    - msgctxt
    - msgid

    Do NOT include msgid_plural here.
    A same msgid repeated twice can still break compilation.
    """
    return (
        entry.msgctxt or "",
        entry.msgid or "",
    )


def has_translation(entry):
    if entry.msgstr:
        return True

    if entry.msgstr_plural:
        return any(value for value in entry.msgstr_plural.values())

    return False


def copy_translation(source, target):
    if source.msgstr and not target.msgstr:
        target.msgstr = source.msgstr

    if source.msgstr_plural:
        if not target.msgstr_plural:
            target.msgstr_plural = source.msgstr_plural
        else:
            for key, value in source.msgstr_plural.items():
                if value and not target.msgstr_plural.get(key):
                    target.msgstr_plural[key] = value


def merge_occurrences(source, target):
    existing = set(target.occurrences)

    for occurrence in source.occurrences:
        if occurrence not in existing:
            target.occurrences.append(occurrence)
            existing.add(occurrence)


def merge_flags(source, target):
    existing = set(target.flags)

    for flag in source.flags:
        if flag not in existing:
            target.flags.append(flag)
            existing.add(flag)


def merge_comments(source, target):
    if source.comment and source.comment not in target.comment:
        if target.comment:
            target.comment += "\n" + source.comment
        else:
            target.comment = source.comment

    if source.tcomment and source.tcomment not in target.tcomment:
        if target.tcomment:
            target.tcomment += "\n" + source.tcomment
        else:
            target.tcomment = source.tcomment


def clean_file(path):
    po = polib.pofile(str(path))

    seen = {}
    cleaned_entries = []
    duplicate_count = 0
    translated_duplicates_used = 0

    for entry in po:
        key = entry_key(entry)

        if key not in seen:
            seen[key] = entry
            cleaned_entries.append(entry)
            continue

        duplicate_count += 1
        first_entry = seen[key]

        if not has_translation(first_entry) and has_translation(entry):
            copy_translation(entry, first_entry)
            translated_duplicates_used += 1

        merge_occurrences(entry, first_entry)
        merge_flags(entry, first_entry)
        merge_comments(entry, first_entry)

    new_po = polib.POFile()
    new_po.metadata = po.metadata

    for entry in cleaned_entries:
        new_po.append(entry)

    new_po.save(str(path))

    print(f"{path}")
    print(f"  Removed duplicates: {duplicate_count}")
    print(f"  Translations rescued from duplicates: {translated_duplicates_used}")
    print()


def main():
    for path in PO_FILES:
        if not path.exists():
            print(f"Missing file: {path}")
            continue

        clean_file(path)


if __name__ == "__main__":
    main()