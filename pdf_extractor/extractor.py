import logging
import re
import fitz
from pdf_extractor.config import DATA_ELEMENTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

input_mapping = {
    "customer_name": [
        "surname",
        "forname",
        "firstnames",
        "clientname",
        "customername",
        "name",
        "accountname",
        "firstnamess",
    ],
    "branch_name": ["branch", "customercentre", "branchname", "tocustomercentre"],
    "account_number": ["accountnumber", "mainaccountnumber", "idnumbers"],
}


class PDFExtractor:
    def __init__(self, pdf_path: str) -> None:
        self.pdf_path = pdf_path
        self.doc = None
        self.extracted_data = {key: None for key in DATA_ELEMENTS}
        self.active_mapping = {k: v[:] for k, v in input_mapping.items()}
        self.labels = []
        self.label_fonts = []
        self.rest_spans = []

        try:
            self.doc = fitz.open(pdf_path)
        except FileNotFoundError:
            logger.error(f"Plik PDF '{pdf_path}' nie istnieje.")
            raise
        except Exception as e:
            logger.error(f"Nie udało się otworzyć pliku PDF: {e}")
            raise

    def extract(self) -> dict:
        try:
            self._collect_blocks()
            for label in self.labels:
                self._find_nearest_value(label)
            logger.info(f"Final extracted data: {self.extracted_data}")
            return self.extracted_data
        except Exception as e:
            logger.error(f"Błąd podczas ekstrakcji: {e}")
            return {key: None for key in DATA_ELEMENTS}

    def _collect_blocks(self) -> None:
        if not self.doc:
            logger.error("Brak dokumentu do analizy.")
            return

        try:
            for page_num, page in enumerate(self.doc, start=1):
                blocks = page.get_text("dict").get("blocks", [])
                for b in blocks:
                    if b.get("type") != 0:
                        continue
                    block_has_label = False
                    block_spans = []

                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            if not span.get("text"):
                                continue
                            span_data = {
                                "text": span["text"],
                                "font": span["font"],
                                "size": span["size"],
                                "bbox": span["bbox"],
                                "page": page_num,
                            }
                            for subspan in self._split_span(span_data):
                                block_spans.append(subspan)
                                for key, aliases in list(self.active_mapping.items()):
                                    for alias in aliases:
                                        if alias.lower() == "".join(
                                            ch
                                            for ch in subspan["text"].lower()
                                            if ch.isalnum()
                                        ):
                                            subspan["label_for"] = key
                                            self.labels.append(subspan)
                                            self.label_fonts.append(span["font"])
                                            block_has_label = True
                                            logger.info(
                                                f"Added label: {key} -> '{subspan['text']}'"
                                            )
                                            self.active_mapping.pop(key, None)
                                            break
                                    else:
                                        continue
                                    break
                    if not block_has_label:
                        self.rest_spans.extend(block_spans)
        except Exception as e:
            logger.error(f"Błąd w _collect_blocks: {e}")

    def _find_nearest_value(self, label: dict) -> None:
        try:
            lx0, ly0, lx1, ly1 = label["bbox"]
            label_height = ly1 - ly0
            label_center_y = (ly0 + ly1) / 2
            y_min = label_center_y - 0.6 * label_height
            y_max = label_center_y + 0.6 * label_height

            def distance(s: dict) -> float:
                sx0, sy0, sx1, sy1 = s["bbox"]
                label_center = (lx0, (ly0 + ly1) / 2)
                span_center = (sx0, (sy0 + sy1) / 2)
                return (
                    (label_center[0] - span_center[0]) ** 2
                    + (label_center[1] - span_center[1]) ** 2
                ) ** 0.5

            candidates = [
                s
                for s in self.rest_spans
                if s["font"] != label.get("font")
                and s["page"] == label.get("page")
                and y_min <= (s["bbox"][1] + s["bbox"][3]) / 2 <= y_max
            ]

            logger.info(
                f"[LABEL] {label.get('label_for')} | text='{label.get('text')}' | "
                f"font='{label.get('font')}' | page={label.get('page')} | bbox={label.get('bbox')}"
            )

            if not candidates:
                logger.warning(
                    f"No candidates found for label: {label.get('label_for')}"
                )
                return

            scored = sorted([(distance(s), s) for s in candidates], key=lambda t: t[0])
            nearest_dist, nearest = scored[0]
            logger.info(
                f"[MATCH] {label.get('label_for')} -> '{nearest['text']}' (dist={nearest_dist:.2f})"
            )
            key = label.get("label_for", "")
            if key:
                self.extracted_data[key] = nearest["text"]

        except Exception as e:
            logger.error(
                f"Błąd w _find_nearest_value dla {label.get('label_for')}: {e}"
            )

    def _split_span(self, span: dict) -> list:
        try:
            text = span["text"]
            font = span["font"]
            size = span["size"]
            x0, y0, x1, y1 = span["bbox"]
            page = span["page"]

            parts = re.split(r"(\.{3,}|_{3,})", text)
            clean_parts = [p for p in parts if p]

            def char_length(c: str) -> int:
                return 1 if c in {".", " ", "i", "j"} else 2

            units = [sum(char_length(c) for c in p) for p in clean_parts]
            total_units = sum(units) or 1
            total_width = x1 - x0
            unit = total_width / total_units

            spans_out = []
            cursor = x0

            for p, w in zip(clean_parts, units):
                width = w * unit
                if not re.fullmatch(r"(\.{3,}|_{3,})", p):
                    spans_out.append(
                        {
                            "text": p,
                            "font": font,
                            "size": size,
                            "bbox": (cursor, y0, cursor + width, y1),
                            "page": page,
                        }
                    )
                cursor += width

            return spans_out
        except Exception as e:
            logger.error(f"Błąd w _split_span: {e}")
            return []
