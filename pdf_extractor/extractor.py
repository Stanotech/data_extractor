import fitz
import re
from config import DATA_ELEMENTS

input_mapping = {
    "customer_name": ["surname", "forname", "firstnames", "clientname", "customername", "name", "accountname", "firstnamess"],
    "branch_name": ["branch", "customercentre", "branchname", "tocustomercentre"],
    "account_number": ["accountnumber", "mainaccountnumber", "idnumbers"] 
}

def split_span(span):
    """
    If a span contains '........' or '____', it is split into smaller spans.
    Returns a list of artificial spans with correct bounding boxes (bboxes).
    Separators (dots or underscores) are not included in the final result.
    """

    text = span["text"]
    font = span["font"]
    size = span["size"]
    x0, y0, x1, y1 = span["bbox"]
    page = span["page"]

    # split by separators (3 or more)
    parts = re.split(r'(\.{3,}|_{3,})', text)

    clean_parts = [p for p in parts if p]

    def char_length(c):
        if c in {".", " ", "i", "j"}:
            return 1
        else:
            return 2

    units = [sum(char_length(c) for c in p) for p in clean_parts]

    total_units = sum(units)
    total_width = x1 - x0
    unit = total_width / total_units

    spans_out = []
    cursor = x0

    for p, w in zip(clean_parts, units):
        width = w * unit
        # if not separator- then add
        if not re.fullmatch(r'(\.{3,}|_{3,})', p):
            spans_out.append({
                "text": p,
                "font": font,
                "size": size,
                "bbox": (cursor, y0, cursor + width, y1),
                "page": page,
            }) 
        cursor += width

    return spans_out


def extract_pdf_data(pdf_path):
    doc = fitz.open(pdf_path)

    extracted_data = {key: None for key in DATA_ELEMENTS}
    active_mapping = {k: v[:] for k, v in input_mapping.items()}

    labels = []
    label_fonts = []    
    rest_spans = []

    # --- 1. Collecting blocks ---
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]

        for b in blocks:
            if b["type"] != 0:
                continue 

            block_has_label = False
            block_spans = []

            for line in b["lines"]:
                for span in line["spans"]:
                    text = span["text"]
                    font = span["font"]
                    size = span["size"]
                    x0, y0, x1, y1 = span["bbox"]

                    if not text:
                        continue 

                    span_data = {
                        "text": text,
                        "font": font,
                        "size": size, 
                        "bbox": (x0, y0, x1, y1),
                        "page": page_num,
                    } 
 
                    for subspan in split_span(span_data):
                        block_spans.append(subspan)

                        for key, aliases in list(active_mapping.items()):
                            for alias in aliases:
                                if alias.lower() == "".join(ch for ch in subspan["text"].lower() if ch.isalnum()):
                                    subspan["label_for"] = key
                                    labels.append(subspan)
                                    label_fonts.append(font) 
                                    block_has_label = True
                                    print(f"added label: {key} -> '{subspan['text']}'") 
 
                                    active_mapping.pop(key, None)
                                    break
                            else:
                                continue
                            break

            if not block_has_label:
                rest_spans.extend(block_spans)

    # --- 2. searching values for labels ---
    for label in labels:
        lx0, ly0, lx1, ly1 = label["bbox"]

        # nearest euclides distance
        def distance(s):
            sx0, sy0, sx1, sy1 = s["bbox"]
            label_center = (lx0, (ly0 + ly1) / 2)
            span_center = (sx0, (sy0 + sy1) / 2)
            return ((label_center[0] - span_center[0]) ** 2 + (label_center[1] - span_center[1]) ** 2) ** 0.5

        label_height = ly1 - ly0
        label_center_y = (ly0 + ly1) / 2
        y_min = label_center_y - 0.6*label_height
        y_max = label_center_y + 0.6*label_height

        candidates = [
            s for s in rest_spans
            if s["font"] != label["font"]
            and s["page"] == label["page"]
            and y_min <= (s["bbox"][1] + s["bbox"][3]) / 2 <= y_max
        ]

        print(f"\n[LABEL] {label['label_for']} | text='{label['text']}' | font='{label['font']}' | page={label['page']} | bbox={label['bbox']}")

        if not candidates:
            print(f"[WARN] No candidates for label: {label['label_for']}")
            continue

        scored = [(distance(s), s) for s in candidates]
        scored.sort(key=lambda t: t[0])

        for d, can in scored:
            print(f"  -> candidate: '{can['text']}' | dist={d:.2f} | font='{can['font']}' | bbox={can['bbox']}")

        nearest_dist, nearest = scored[0]
        print(f"[MATCH] {label['label_for']} -> '{nearest['text']}' (dist={nearest_dist:.2f})")

        extracted_data[label["label_for"]] = nearest["text"]

    return extracted_data
