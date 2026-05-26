
class OCRConfidenceValidator:
    """
    Flags low-confidence words and lines after Textract extraction.
    Helps identify where OCR may have mis-read characters.
    """

    THRESHOLD = 85.0  # anything below this is flagged

    def validate(self, parsed_result):
        low_confidence_words  = []
        low_confidence_lines  = []

        for w in parsed_result['word_confidences']:
            if w['confidence'] < self.THRESHOLD:
                low_confidence_words.append(w)

        for line in parsed_result['lines']:
            if line['confidence'] < self.THRESHOLD:
                low_confidence_lines.append(line)

        avg_confidence = (
            sum(w['confidence'] for w in parsed_result['word_confidences'])
            / max(len(parsed_result['word_confidences']), 1)
        )

        return {
            'average_confidence':     round(avg_confidence, 2),
            'low_confidence_words':   low_confidence_words,
            'low_confidence_lines':   low_confidence_lines,
            'total_words':            len(parsed_result['word_confidences']),
            'flagged_word_count':     len(low_confidence_words),
            'is_reliable':            avg_confidence >= self.THRESHOLD
        }

    def print_report(self, validation_result):
        print("\n" + "="*50)
        print("       OCR CONFIDENCE REPORT")
        print("="*50)
        print(f"  Average Confidence : {validation_result['average_confidence']}%")
        print(f"  Total Words        : {validation_result['total_words']}")
        print(f"  Flagged Words      : {validation_result['flagged_word_count']}")
        print(f"  Reliable           : {validation_result['is_reliable']}")

        if validation_result['low_confidence_words']:
            print("\n  Low Confidence Words:")
            for w in validation_result['low_confidence_words']:
                print(f"    → '{w['word']}' ({w['confidence']}%)")
        print("="*50 + "\n")