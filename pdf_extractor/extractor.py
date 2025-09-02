import logging
import re
import fitz  # PyMuPDF library for PDF processing
from pdf_extractor.config import INPUT_MAPPING  # Configuration mapping labels to their possible aliases

# Configure logging to display informational messages and errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    A class for extracting labeled data from a PDF file using PyMuPDF.
    It maps labels defined in INPUT_MAPPING to their nearest values in the PDF.
    The core idea is to find text spans that match known labels, then locate the nearest 
    visually distinct text span (often a value) next to each label.
    """
    def __init__(self, pdf_path: str) -> None:
        """
        Initialize the PDFExtractor. Opens the PDF and sets up data structures.

        Args:
            pdf_path (str): Path to the PDF file.
        """
        self.doc = None  # Will hold the fitz.Document object
        # Initialize the result dictionary with keys from INPUT_MAPPING and None values
        self.extracted_data = {key: None for key in INPUT_MAPPING}
        # Create a working copy of the mapping to track which labels haven't been found yet
        self.mapping_copy = {k: v[:] for k, v in INPUT_MAPPING.items()}
        self.labels = []  # List to store spans identified as labels
        self.label_fonts = []  # List to store fonts used by labels (for value discrimination)
        self.rest_spans = []  # List to store all spans that are NOT identified as labels

        try:
            # Open the PDF document using PyMuPDF
            self.doc = fitz.open(pdf_path)
        except FileNotFoundError:
            logger.error(f"PDF file '{pdf_path}' does not exist.")
            raise
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            raise

    def extract(self) -> dict:
        """
        Main extraction pipeline. Orchestrates the entire process.
        - Collect all text spans from the document.
        - Detect labels from the collected spans.
        - For each detected label, find the nearest corresponding value.
        - Return extracted data as dictionary.

        Returns:
            dict: Extracted data with labels as keys and matched values.
        """
        try:
            # Step 1: Extract all text spans from the PDF, split into logical blocks and sub-spans
            all_spans = self._collect_spans()
            # Step 2: Identify which spans are labels (based on INPUT_MAPPING). 
            # Populates self.labels and self.rest_spans.
            self._find_labels(all_spans)
            # Step 3: For each found label, find its corresponding value from rest_spans
            for label in self.labels:
                self._find_nearest_value(label)
            logger.info(f"Final extracted data: {self.extracted_data}")
            return self.extracted_data
        except Exception as e:
            logger.error(f"Error extracting data: {e}")
            # Return a dictionary with all keys set to None in case of error
            return {key: None for key in INPUT_MAPPING}

    def _collect_spans(self) -> list:
        """
        Collects and splits text spans into sub-spans for each text block in the entire PDF. 
        This method focuses on granular text extraction, preserving visual and spatial information (bbox, font, size).
        It does NOT classify spans as labels or values at this stage.

        Returns:
            list: A list where each element is a list of sub-spans for one text block.
        """
        if not self.doc:
            logger.error("No PDF document found.")
            return []

        try:
            all_spans = []  # Master list of all blocks and their sub-spans
            # Iterate through each page in the PDF (page_num starts at 1 for readability)
            for page_num, page in enumerate(self.doc, start=1):
                # Get the page text as a dictionary structure containing 'blocks'
                blocks = page.get_text("dict").get("blocks", [])
                for b in blocks:
                    # Skip non-text blocks (images, etc.). Type 0 is text.
                    if b.get("type") != 0:
                        continue

                    block_spans = []  # List to hold all sub-spans for the current text block
                    # Iterate through lines and spans within the block
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            # Skip empty text spans
                            if not span.get("text"):
                                continue
                            # Create a dictionary with crucial span properties
                            span_data = {
                                "text": span["text"],
                                "font": span["font"],
                                "size": span["size"],
                                "bbox": span["bbox"], # Bounding box: (x0, y0, x1, y1)
                                "page": page_num,
                            }
                            # Split the span into smaller sub-spans (e.g., on "...." or "____")
                            # This is critical for handling fillable forms where labels and values might be in the same span.
                            for subspan in self._split_span(span_data):
                                block_spans.append(subspan)

                    # If the block contained any spans, add it to the master list
                    if block_spans:
                        all_spans.append(block_spans)

            return all_spans
        except Exception as e:
            logger.error(f"Error in _collect_spans: {e}")
            return []

    def _find_labels(self, all_spans: list) -> list:
        """
        Identifies label spans based on the predefined INPUT_MAPPING.
        Populates self.labels (found labels) and self.label_fonts.
        All spans that are not labels are added to self.rest_spans (potential values).

        Args:
            all_spans (list): List of spans collected from the PDF.

        Returns:
            list: The list of found labels (self.labels).
        """
        try:
            # Iterate over each block of spans
            for block_spans in all_spans:
                block_has_label = False  # Flag to track if this block contains a label

                # Check every sub-span in the current block
                for subspan in block_spans:
                    # Iterate over a *copy* of the current mapping items
                    # (so we can remove found labels during iteration)
                    for key, aliases in list(self.mapping_copy.items()):
                        # Check each alias (possible text variation) for the current label key
                        for alias in aliases:
                            # Normalize both the alias and span text for comparison: remove non-alphanumeric chars and lowerCase.
                            # This makes matching more robust against minor formatting differences.
                            if alias.lower() == "".join(
                                ch for ch in subspan["text"].lower() if ch.isalnum()
                            ):
                                # Mark this span as a label and specify which key it corresponds to
                                subspan["label_for"] = key
                                self.labels.append(subspan)
                                # Remember the font used for this label (helps find values later)
                                self.label_fonts.append(subspan["font"])
                                block_has_label = True
                                logger.info(
                                    f"Added label: {key} -> '{subspan['text']}'"
                                )
                                # Remove the found label from the working copy so we don't search for it again
                                self.mapping_copy.pop(key, None)
                                break  # Break out of the alias loop
                        else:
                            # Continue to next alias if no break occurred in inner loop
                            continue
                        break  # Break out of the key loop if a label was found and popped

                # If the entire block was processed and no label was found,
                # add all its spans to the rest_spans list (they are candidate values)
                if not block_has_label:
                    self.rest_spans.extend(block_spans)

            return self.labels
        except Exception as e:
            logger.error(f"Error in _find_labels: {e}")
            return self.labels

    def _find_nearest_value(self, label: dict) -> None:
        """
        For a given label, searches the rest_spans list for the nearest candidate value.
        The candidate must be on the same page, in a similar vertical position (same line),
        and ideally have a different font (a common visual cue for values in forms).
        The closest candidate by Euclidean distance is chosen.

        Args:
            label (dict): The label span dictionary to find a value for.

        Returns:
            None
        """
        try:
            # Extract the bounding box coordinates of the label
            lx0, ly0, lx1, ly1 = label["bbox"]
            label_height = ly1 - ly0
            # Calculate the vertical center point of the label
            label_center_y = (ly0 + ly1) / 2
            # Define a vertical search window around the label's center (60% of label height above and below)
            # This targets text on the same line.
            y_min = label_center_y - 0.6 * label_height
            y_max = label_center_y + 0.6 * label_height

            # Filter candidate value spans:
            candidates = [
                s
                for s in self.rest_spans
                if s["font"] != label.get("font")  # Value often has different font
                and s["page"] == label.get("page") # Must be on the same page
                # Check if the vertical center of the candidate span is within the search window
                and y_min <= (s["bbox"][1] + s["bbox"][3]) / 2 <= y_max
            ]

            # Log details about the label being processed
            logger.info(
                f"[LABEL] {label.get('label_for')} | text='{label.get('text')}' | "
                f"font='{label.get('font')}' | page={label.get('page')} | bbox={label.get('bbox')}"
            )

            if not candidates:
                logger.warning(
                    f"No candidates found for label: {label.get('label_for')}"
                )
                return

            # Score each candidate by its distance to the label
            # Lower distance score is better.
            scored = sorted(
                [(self._distance(label, span), span) for span in candidates],
                key=lambda t: t[0]  # Sort by the distance (first element of the tuple)
            )
            # Get the candidate with the smallest distance
            nearest_dist, nearest = scored[0]
            logger.info(
                f"[MATCH] {label.get('label_for')} -> '{nearest['text']}' (dist={nearest_dist:.2f})"
            )
            key = label.get("label_for", "")
            if key:
                # Assign the found text to the corresponding key in the result dictionary
                self.extracted_data[key] = nearest["text"]

        except Exception as e:
            logger.error(
                f"Error in _find_nearest_value for {label.get('label_for')}: {e}"
            )

    def _split_span(self, span: dict) -> list:
        """
        Splits a single span into sub-spans based on sequences of dots or underscores.
        This is necessary because in PDFs, labels and values are sometimes part of the same text span
        separated by filler characters like "..........". Splitting allows us to process them separately.
        It calculates approximate bounding boxes for each new sub-span to preserve spatial information.

        Args:
            span (dict): The original span dictionary.

        Returns:
            list: A list of sub-span dictionaries, each with text, font, size, bbox, and page.
        """
        try:
            text = span["text"]
            font = span["font"]
            size = span["size"]
            x0, y0, x1, y1 = span["bbox"]
            page = span["page"]

            # Split the text on sequences of 3 or more dots or underscores.
            # The parentheses in the regex pattern ensure the separators are also included in the parts list.
            parts = re.split(r"(\.{3,}|_{3,})", text)
            # Remove any empty strings resulting from the split
            clean_parts = [p for p in parts if p]

            # Define a helper function to estimate the visual width of a character.
            # This is a heuristic: some chars (like '.' and 'i') are narrower.
            def char_length(c: str) -> int:
                return 1 if c in {".", " ", "i", "j"} else 2

            # Calculate the width of each part in "units" (based on the heuristic)
            units = [sum(char_length(c) for c in p) for p in clean_parts]
            total_units = sum(units)
            total_width = x1 - x0  # Total actual width of the original span
            # Calculate the width of one unit in actual coordinates
            unit = total_width / total_units if total_units else 0

            spans_out = []
            cursor = x0  # Tracks the current x-position while building new bboxes

            for p, w in zip(clean_parts, units):
                # Calculate the actual width this part should occupy
                width = w * unit
                # Check if the part is NOT a separator (dots/underscores)
                # We typically ignore the separators and only create sub-spans for the meaningful text.
                if not re.fullmatch(r"(\.{3,}|_{3,})", p):
                    # Create a new sub-span for the meaningful text part
                    spans_out.append(
                        {
                            "text": p,
                            "font": font,
                            "size": size,
                            "bbox": (cursor, y0, cursor + width, y1), # New bbox
                            "page": page,
                        }
                    )
                # Move the cursor forward for the next part, regardless of whether it was kept
                cursor += width

            return spans_out
        except Exception as e:
            logger.error(f"Error in _split_span: {e}")
            return []

    @staticmethod
    def _distance(label: dict, span: dict) -> float:
        """
        Calculates the Euclidean distance between the center of the left edge of the label
        and the center of the left edge of the candidate value span.
        This prioritizes horizontal proximity, which is most important for finding values on the same line.

        Args:
            label (dict): The label span.
            span (dict): The candidate value span.

        Returns:
            float: The calculated Euclidean distance.
        """
        lx0, ly0, lx1, ly1 = label["bbox"]
        sx0, sy0, sx1, sy1 = span["bbox"]
        # Calculate points: Middle of the left edge of each span
        label_center = (lx0, (ly0 + ly1) / 2)
        span_center = (sx0, (sy0 + sy1) / 2)
        # Standard Euclidean distance formula in 2D
        return ((label_center[0] - span_center[0]) ** 2 +
                (label_center[1] - span_center[1]) ** 2) ** 0.5