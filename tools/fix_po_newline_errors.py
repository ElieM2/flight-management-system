from pathlib import Path
import polib


BASE_DIR = Path(__file__).resolve().parent.parent

PO_FILES = [
    BASE_DIR / "locale" / "fr" / "LC_MESSAGES" / "django.po",
    BASE_DIR / "locale" / "ru" / "LC_MESSAGES" / "django.po",
]


def align_newlines(source, translation):
    if translation is None:
        return translation

    if not translation:
        return translation

    fixed = translation

    source_starts_with_newline = source.startswith("\n")
    translation_starts_with_newline = fixed.startswith("\n")

    if source_starts_with_newline and not translation_starts_with_newline:
        fixed = "\n" + fixed

    if not source_starts_with_newline and translation_starts_with_newline:
        fixed = fixed.lstrip("\n")

    source_ends_with_newline = source.endswith("\n")
    translation_ends_with_newline = fixed.endswith("\n")

    if source_ends_with_newline and not translation_ends_with_newline:
        fixed = fixed + "\n"

    if not source_ends_with_newline and translation_ends_with_newline:
        fixed = fixed.rstrip("\n")

    return fixed


def fix_file(path):
    if not path.exists():
        print(f"Missing file: {path}")
        return

    po = polib.pofile(str(path))
    fixed = 0

    for entry in po:
        if entry.obsolete or entry.msgid == "":
            continue

        if entry.msgid_plural:
            for index, value in list(entry.msgstr_plural.items()):
                new_value = align_newlines(entry.msgid, value)

                if new_value != value:
                    entry.msgstr_plural[index] = new_value
                    fixed += 1

            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")

            continue

        new_msgstr = align_newlines(entry.msgid, entry.msgstr)

        if new_msgstr != entry.msgstr:
            entry.msgstr = new_msgstr
            fixed += 1

        if "fuzzy" in entry.flags:
            entry.flags.remove("fuzzy")

    po.save(str(path))
    print(f"{path}: fixed {fixed} newline issue(s)")


def main():
    for path in PO_FILES:
        fix_file(path)


if __name__ == "__main__":
    main()