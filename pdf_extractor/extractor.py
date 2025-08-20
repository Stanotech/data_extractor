import logging
import re
import fitz
from pdf_extractor.config import INPUT_MAPPING

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    A class for extracting labeled data from a PDF file using PyMuPDF.
    It maps labels defined in INPUT_MAPPING to their nearest values in the PDF.
    """
    def __init__(self, pdf_path: str) -> None:
        """
        Initialize the PDFExtractor.

        Args:
            pdf_path (str): Path to the PDF file.
        """
        self.doc = None
        self.extracted_data = {key: None for key in INPUT_MAPPING}
        self.mapping_copy = {k: v[:] for k, v in INPUT_MAPPING.items()}
        self.labels = []
        self.label_fonts = []
        self.rest_spans = []

        try:
            self.doc = fitz.open(pdf_path)
        except FileNotFoundError:
            logger.error(f"PDF file '{pdf_path}' does not exist.")
            raise
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            raise

    def extract(self) -> dict:
        """
        Main extraction pipeline.
        - Collect all spans from the document.
        - Detect labels from collected spans.
        - For each detected label, find the nearest corresponding value.
        - Return extracted data as dictionary.

        Returns:
            dict: Extracted data with labels as keys and matched values.
        """
        try:
            all_spans = self._collect_spans()
            self._find_labels(all_spans)
            for label in self.labels:
                self._find_nearest_value(label)
            logger.info(f"Final extracted data: {self.extracted_data}")
            return self.extracted_data
        except Exception as e:
            logger.error(f"Error extracting data: {e}")
            return {key: None for key in INPUT_MAPPING}

    def _collect_spans(self) -> list:
        """
        Collects and splits text spans into sub-spans for each text block
        in the entire PDF. Does NOT classify them as labels or values.
        
        Returns:
            list: A list where each element is a list of sub-spans for one block.
        """
        if not self.doc:
            logger.error("No PDF document found.")
            return []

        try:
            all_spans = []
            for page_num, page in enumerate(self.doc, start=1):
                blocks = page.get_text("dict").get("blocks", [])
                for b in blocks:
                    if b.get("type") != 0:
                        continue

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

                    if block_spans:
                        all_spans.append(block_spans)

            return all_spans
        except Exception as e:
            logger.error(f"Error in _collect_spans: {e}")
            return []

    def _find_labels(self, all_spans: list) -> list:
        """
        Based on all_spans, identifies labels according to INPUT_MAPPING.
        Populates self.labels and self.label_fonts.
        For blocks without labels, fills self.rest_spans with their sub-spans.
        
        Returns:
            list: The list of found labels (self.labels).
        """
        try:
            for block_spans in all_spans:
                block_has_label = False

                for subspan in block_spans:
                    for key, aliases in list(self.mapping_copy.items()):
                        for alias in aliases:
                            if alias.lower() == "".join(
                                ch for ch in subspan["text"].lower() if ch.isalnum()
                            ):
                                subspan["label_for"] = key
                                self.labels.append(subspan)
                                self.label_fonts.append(subspan["font"])
                                block_has_label = True
                                logger.info(
                                    f"Added label: {key} -> '{subspan['text']}'"
                                )
                                self.mapping_copy.pop(key, None)
                                break
                        else:
                            continue
                        break

                if not block_has_label:
                    self.rest_spans.extend(block_spans)

            return self.labels
        except Exception as e:
            logger.error(f"Error in _find_labels: {e}")
            return self.labels

    def _find_nearest_value(self, label: dict) -> None:
        """
        For the given label (label), searches in self.rest_spans for the nearest candidate
        in the same line (vertical window) and writes the found text to
        self.extracted_data under the key label['label_for'].
        
        Returns:
            None
        """
        try:
            lx0, ly0, lx1, ly1 = label["bbox"]
            label_height = ly1 - ly0
            label_center_y = (ly0 + ly1) / 2
            y_min = label_center_y - 0.6 * label_height
            y_max = label_center_y + 0.6 * label_height

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

            scored = sorted(
                [(self._distance(label, span), span) for span in candidates],
                key=lambda t: t[0]
            )
            nearest_dist, nearest = scored[0]
            logger.info(
                f"[MATCH] {label.get('label_for')} -> '{nearest['text']}' (dist={nearest_dist:.2f})"
            )
            key = label.get("label_for", "")
            if key:
                self.extracted_data[key] = nearest["text"]

        except Exception as e:
            logger.error(
                f"Error in _find_nearest_value for {label.get('label_for')}: {e}"
            )

    def _split_span(self, span: dict) -> list:
        """
        Splits a single span into sub-spans based on sequences of dots/underscores,
        calculating approximate segment widths to preserve bbox rectangles.
        
        Returns:
            list: A list of sub-spans in the same format as the input span (text, font, size, bbox, page).
        """
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
            total_units = sum(units)
            total_width = x1 - x0
            unit = total_width / total_units if total_units else 0

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
            logger.error(f"Error in _split_span: {e}")
            return []

    @staticmethod
    def _distance(label: dict, span: dict) -> float:
        """
        Helper: Euclidean distance between the center of the left edge of the label
        and the center of the left side of the candidate (according to previous implementation).
        
        Returns:
            float: The calculated Euclidean distance.
        """
        lx0, ly0, lx1, ly1 = label["bbox"]
        sx0, sy0, sx1, sy1 = span["bbox"]
        label_center = (lx0, (ly0 + ly1) / 2)
        span_center = (sx0, (sy0 + sy1) / 2)
        return ((label_center[0] - span_center[0]) ** 2 +
                (label_center[1] - span_center[1]) ** 2) ** 0.5
