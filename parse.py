import re
import json
import sys
import os


def clean_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    def ordinal(m):
        n = m.group(1)
        if n.endswith(('11', '12', '13')):
            return n + 'th'
        suffix = {'1': 'st', '2': 'nd', '3': 'rd'}.get(n[-1], 'th')
        return n + suffix

    text = re.sub(r'(\d+)\?\?', ordinal, text)
    return text


# 🔍 NEW: extract ALL course IDs from raw text
def extract_all_course_ids(text: str) -> set:
    ids = re.findall(r'\b[A-Z]{2,3}\d{3,4}[A-Z]?\b', text)
    return set(ids)


def parse_file(content: str) -> list:
    # improved header detection
    course_header = re.compile(
        r'([A-Z]{2,3}\d{3,4}[A-Z]?)\s+([A-Z][A-Z0-9 ,\-&/()\'.]+?)\s+L\s*T\s*P',
        re.MULTILINE
    )

    matches = list(course_header.finditer(content))
    courses = []

    for idx, match in enumerate(matches):
        course_id = match.group(1).strip()
        course_title = match.group(2).strip()

        block_start = match.end()
        block_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        block = content[block_start:block_end]

        ref_section = re.search(
            r'References?\s*:(.*)',
            block,
            re.DOTALL | re.IGNORECASE
        )

        raw_references = []

        if ref_section:
            ref_text = ref_section.group(1).strip()

            # 🚧 STOP references if next course appears inline
            ref_text = re.split(
                r'(?=[A-Z]{2,3}\d{3,4}[A-Z]?\s+[A-Z])',
                ref_text
            )[0]

            ref_entries = re.split(r'\n(?=\[\d+\]|\d+\.)', ref_text)

            for entry in ref_entries:
                entry = re.sub(r'\n+', ' ', entry).strip()
                entry = re.sub(r'^\[(\d+)\]\s*', r'\1. ', entry)
                if entry:
                    raw_references.append(entry)

        courses.append({
            "course_id": course_id,
            "course_title": course_title,
            "raw_references": raw_references
        })

    return courses


def generate_audit(courses: list) -> dict:
    total_courses = len(courses)
    total_references = sum(len(c["raw_references"]) for c in courses)

    courses_with_refs = [c for c in courses if len(c["raw_references"]) > 0]
    courses_without_refs = [c for c in courses if len(c["raw_references"]) == 0]

    coverage = (len(courses_with_refs) / total_courses * 100) if total_courses else 0

    return {
        "summary": {
            "total_courses": total_courses,
            "total_references": total_references,
            "courses_with_references": len(courses_with_refs),
            "courses_without_references": len(courses_without_refs),
            "coverage_percent": round(coverage, 2)
        },
        "courses_without_references": [
            {
                "course_id": c["course_id"],
                "course_title": c["course_title"]
            } for c in courses_without_refs
        ]
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python parse_courses.py <input.txt> <output.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.exists(input_path):
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    print(f"Parsing {input_path} ...")

    # 📥 Read raw file
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        raw_text = f.read()

    raw_text = clean_text(raw_text)

    # 🔍 ALL course IDs in TXT
    all_ids = extract_all_course_ids(raw_text)

    # 📊 Parsed courses
    courses = parse_file(raw_text)
    parsed_ids = set(c["course_id"] for c in courses)

    # 👻 Missing (not parsed at all)
    missing_ids = sorted(all_ids - parsed_ids)

    # 📊 Audit (missing references only)
    audit = generate_audit(courses)

    # 💾 Save JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    # ===== TERMINAL OUTPUT =====
    print("\n=== AUDIT REPORT ===")

    summary = audit["summary"]
    print(f"Total courses              : {summary['total_courses']}")
    print(f"Total references           : {summary['total_references']}")
    print(f"Courses with references    : {summary['courses_with_references']}")
    print(f"Courses WITHOUT references : {summary['courses_without_references']}")
    print(f"Coverage                  : {summary['coverage_percent']}%")

    print("\n--- Courses with NO references ---")
    missing_refs = audit["courses_without_references"]

    if not missing_refs:
        print("None 🎉")
    else:
        for c in missing_refs:
            print(f"{c['course_id']}  -  {c['course_title']}")

    print("\n=== COURSES NOT PARSED (CRITICAL) ===")

    if not missing_ids:
        print("None 🎉")
    else:
        for cid in missing_ids:
            print(cid)

    print(f"\nOutput written to {output_path}")


if __name__ == '__main__':
    main()
