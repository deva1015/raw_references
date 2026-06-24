"""
parse_courses.py
----------------
Parses a course syllabus .txt file and extracts course IDs, titles,
and raw reference strings (exactly as they appear in the file).

Usage:
    python parse_courses.py input.txt output.json

Output format:
    [
      {
        "course_id": "MA1003E",
        "course_title": "MATHEMATICS I",
        "raw_references": [
          "[1] H. Anton, I. Bivens, and S. Davis, Calculus, 10th ed. John Wiley & Sons, 2015.",
          "[2] G.B. Thomas, ..."
        ]
      },
      ...
    ]

Requirements: Python 3.6+  (no third-party libraries needed)
"""

import re
import json
import sys
import os


def clean_text(text: str) -> str:
    """Fix garbled characters and normalise line endings."""
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Fix garbled edition markers like 10?? -> 10th
    def ordinal(m):
        n = m.group(1)
        if n.endswith(('11', '12', '13')):
            return n + 'th'
        suffix = {'1': 'st', '2': 'nd', '3': 'rd'}.get(n[-1], 'th')
        return n + suffix
    text = re.sub(r'(\d+)\?\?', ordinal, text)
    return text


def parse_file(path: str) -> list:
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    content = clean_text(content)

    # Match course headers like "MA1003E MATHEMATICS I"
    course_header = re.compile(
        r'\n([A-Z]{2,3}\d{3,4}[A-Z]?)\s+([A-Z][A-Z0-9 ,\-&/()\'.]+?)(?=\n)'
    )
    matches = list(course_header.finditer(content))

    courses = []

    for idx, match in enumerate(matches):
        course_id    = match.group(1).strip()
        course_title = match.group(2).strip()

        block_start = match.end()
        block_end   = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        block       = content[block_start:block_end]

        # Find the References section
        ref_section = re.search(
            r'References?\s*:(.*)',
            block,
            re.DOTALL | re.IGNORECASE
        )

        raw_references = []

        if ref_section:
            ref_text = ref_section.group(1).strip()

            # Split on lines that start a new reference:
            #   [1] style  OR  1. style
            ref_entries = re.split(r'\n(?=\[\d+\]|\d+\.)', ref_text)

            for entry in ref_entries:
                # Clean up the entry: collapse internal newlines into a space
                entry = re.sub(r'\n+', ' ', entry).strip()
                # Convert [1] style to 1. style
                entry = re.sub(r'^\[(\d+)\]\s*', r'\1. ', entry)
                if entry:
                    raw_references.append(entry)

        courses.append({
            "course_id":       course_id,
            "course_title":    course_title,
            "raw_references":  raw_references
        })

    return courses


def main():
    if len(sys.argv) < 3:
        print("Usage: python parse_courses.py <input.txt> <output.json>")
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.exists(input_path):
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    print(f"Parsing {input_path} ...")
    courses = parse_file(input_path)
    print(f"Found {len(courses)} courses.")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    print(f"Output written to {output_path}")


if __name__ == '__main__':
    main()
