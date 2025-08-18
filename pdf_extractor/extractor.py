import fitz
from config import DATA_ELEMENTS

# słownik aliasów -> klucze
input_mapping = {
    "customer_name": ["surname", "forname", "firstnames", "clientname", "customername", "name"],
    "branch_name": ["branch", "customercentre", "branchname"],
    "account_number": ["accountnumber"]
}


def extract_pdf_data(pdf_path):
    doc = fitz.open(pdf_path)

    extracted_data = {key: None for key in DATA_ELEMENTS}

    labels = []
    label_fonts = []    
    rest_spans = []

    # --- 1. Iterujemy po stronach i zbieramy SPANY ---
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]

        for b in blocks:
            if b["type"] != 0:
                continue 

            block_has_label = False  # flaga dla całego bloku
            block_spans = []         # zbieramy spany bloku

            for line in b["lines"]:
                for span in line["spans"]:
                    text = "".join(ch for ch in span["text"].lower() if ch.isalnum())
                    print(f"span {text}")
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

                    block_spans.append(span_data)

                    # --- sprawdzamy czy to label ---
                    for key, aliases in input_mapping.items():
                        for alias in aliases:
                            if alias.lower() == text:
                                span_data["label_for"] = key
                                labels.append(span_data)
                                label_fonts.append(font)
                                block_has_label = True
                                print(f"added label: {key} -> '{text}'")

            # jeśli w bloku NIE było żadnego labela → wszystkie spany idą do rest_spans
            if not block_has_label:
                rest_spans.extend(block_spans)

    # 4. Szukamy wartości dla labeli (z debugiem)
    for label in labels:
        lx0, ly0, lx1, ly1 = label["bbox"]

        # dystans euklidesowy od lewej krawędzi + środka wysokości
        def distance(s):
            sx0, sy0, sx1, sy1 = s["bbox"]
            label_center = (lx0, (ly0 + ly1) / 2)
            span_center = (sx0, (sy0 + sy1) / 2)
            return ((label_center[0] - span_center[0]) ** 2 + (label_center[1] - span_center[1]) ** 2) ** 0.5

        # wysokość i środek labela
        label_height = ly1 - ly0
        label_center_y = (ly0 + ly1) / 2
        y_min = label_center_y - label_height
        y_max = label_center_y + label_height

        # filtr kandydatów
        candidates = [
            s for s in rest_spans
            if s["font"] != label["font"]
            and s["page"] == label["page"]
            and y_min <= (s["bbox"][1] + s["bbox"][3]) / 2 <= y_max
        ]

        print(f"\n[LABEL] {label['label_for']} | text='{label['text']}' | font='{label['font']}' | page={label['page']} | bbox={label['bbox']}")

        if not candidates:
            print(f"[WARN] Brak kandydatów dla labela: {label['label_for']}")
            continue

        # policz dystanse i posortuj
        scored = [(distance(s), s) for s in candidates]
        scored.sort(key=lambda t: t[0])

        for d, can in scored:
            print(f"  -> kandydat: '{can['text']}' | dist={d:.2f} | font='{can['font']}' | bbox={can['bbox']}")

        nearest_dist, nearest = scored[0]
        print(f"[MATCH] {label['label_for']} -> '{nearest['text']}' (dist={nearest_dist:.2f})")

        extracted_data[label["label_for"]] = nearest["text"]

    return extracted_data
