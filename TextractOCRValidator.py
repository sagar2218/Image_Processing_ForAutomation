import boto3
import json
import time
import os
from pathlib import Path
from PIL import Image
import pytesseract
from pytesseract import Output
import pandas as pd

# ── AWS Clients ──────────────────────────────────────────────────────
textract_client  = boto3.client('textract',  region_name='us-east-1')
s3_client        = boto3.client('s3',        region_name='us-east-1')

S3_BUCKET = "your-ocr-bucket-name"


class TextractOCRValidator:
    """
    Full Textract pipeline for statements and PDFs.
    Handles: raw text, tables, key-value forms, and confidence scoring.
    """

    def __init__(self, bucket_name, region='us-east-1'):
        self.bucket = bucket_name
        self.textract = boto3.client('textract', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)

    # ── S3 Upload ────────────────────────────────────────────────────
    def upload_to_s3(self, local_path, s3_key=None):
        """Upload file to S3 before sending to Textract (required for PDFs)."""
        if s3_key is None:
            s3_key = f"ocr-input/{Path(local_path).name}"

        self.s3.upload_file(local_path, self.bucket, s3_key)
        print(f"Uploaded → s3://{self.bucket}/{s3_key}")
        return s3_key

    # ── Sync: Images only (< 5MB) ────────────────────────────────────
    def extract_from_image(self, image_path):
        """
        Synchronous extraction — best for single-page images/screenshots.
        Returns raw text blocks with confidence scores.
        """
        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        response = self.textract.analyze_document(
            Document={'Bytes': image_bytes},
            FeatureTypes=['TABLES', 'FORMS']  # extract tables + key-value pairs
        )
        return self._parse_response(response)

    # ── Async: PDFs / Multi-page (recommended for statements) ────────
    def extract_from_pdf(self, local_pdf_path):
        """
        Asynchronous extraction — required for multi-page PDFs.
        Polls until complete, then fetches all pages.
        """
        s3_key = self.upload_to_s3(local_pdf_path)

        # Start async job
        response = self.textract.start_document_analysis(
            DocumentLocation={
                'S3Object': {'Bucket': self.bucket, 'Name': s3_key}
            },
            FeatureTypes=['TABLES', 'FORMS']
        )
        job_id = response['JobId']
        print(f"Textract Job Started → {job_id}")

        # Poll for completion
        return self._poll_and_fetch(job_id)

    def _poll_and_fetch(self, job_id, interval=5):
        """Poll Textract job until complete, then collect all pages."""
        all_blocks = []

        while True:
            response = self.textract.get_document_analysis(JobId=job_id)
            status = response['DocumentMetadata'] if 'DocumentMetadata' in response else {}
            job_status = response['JobStatus']

            print(f"Job status: {job_status}")

            if job_status == 'SUCCEEDED':
                all_blocks.extend(response['Blocks'])

                # Paginate if results span multiple API pages
                while 'NextToken' in response:
                    response = self.textract.get_document_analysis(
                        JobId=job_id,
                        NextToken=response['NextToken']
                    )
                    all_blocks.extend(response['Blocks'])
                break

            elif job_status == 'FAILED':
                raise RuntimeError(f"Textract job failed: {response.get('StatusMessage')}")

            time.sleep(interval)

        return self._parse_blocks(all_blocks)

    # ── Response Parsers ─────────────────────────────────────────────
    def _parse_response(self, response):
        """Parse synchronous Textract response."""
        return self._parse_blocks(response['Blocks'])

    def _parse_blocks(self, blocks):
        """
        Separates blocks into:
          - lines     → raw readable text with confidence
          - tables    → structured rows/columns (for statements)
          - forms     → key-value pairs (for invoices, forms)
          - words     → individual word confidences
        """
        lines = []
        tables = []
        forms = {}
        word_conf = []

        block_map = {b['Id']: b for b in blocks}

        for block in blocks:
            btype = block['BlockType']
            conf = block.get('Confidence', 0)

            # ── Raw lines ────────────────────────────────────────
            if btype == 'LINE':
                lines.append({
                    'text': block['Text'],
                    'confidence': round(conf, 2),
                    'page': block.get('Page', 1),
                    'geometry': block.get('Geometry', {})
                })

            # ── Word-level confidence ────────────────────────────
            elif btype == 'WORD':
                word_conf.append({
                    'word': block['Text'],
                    'confidence': round(conf, 2)
                })

            # ── Tables ───────────────────────────────────────────
            elif btype == 'TABLE':
                table = self._extract_table(block, block_map)
                tables.append(table)

            # ── Key-Value Forms ──────────────────────────────────
            elif btype == 'KEY_VALUE_SET' and 'KEY' in block.get('EntityTypes', []):
                key, value, kconf = self._extract_kv(block, block_map)
                if key:
                    forms[key] = {'value': value, 'confidence': round(kconf, 2)}

        return {
            'lines': lines,
            'tables': tables,
            'forms': forms,
            'word_confidences': word_conf,
            'raw_text': "\n".join([l['text'] for l in lines])
        }

    def _extract_table(self, table_block, block_map):
        """Reconstruct table rows and columns from Textract cell blocks."""
        rows = {}
        for rel in table_block.get('Relationships', []):
            if rel['Type'] == 'CHILD':
                for cell_id in rel['Ids']:
                    cell = block_map.get(cell_id, {})
                    if cell.get('BlockType') == 'CELL':
                        r = cell['RowIndex']
                        c = cell['ColumnIndex']
                        text = self._get_cell_text(cell, block_map)
                        rows.setdefault(r, {})[c] = text

        # Convert to list of lists
        table = []
        for r in sorted(rows):
            row = [rows[r].get(c, '') for c in sorted(rows[r])]
            table.append(row)
        return table

    def _get_cell_text(self, cell, block_map):
        """Get text content of a table cell."""
        words = []
        for rel in cell.get('Relationships', []):
            if rel['Type'] == 'CHILD':
                for wid in rel['Ids']:
                    w = block_map.get(wid, {})
                    if w.get('BlockType') == 'WORD':
                        words.append(w.get('Text', ''))
        return " ".join(words)

    def _extract_kv(self, key_block, block_map):
        """Extract key-value pair and return with confidence."""
        key_text = self._get_cell_text(key_block, block_map)
        confidence = key_block.get('Confidence', 0)
        value_text = ""

        for rel in key_block.get('Relationships', []):
            if rel['Type'] == 'VALUE':
                for vid in rel['Ids']:
                    val_block = block_map.get(vid, {})
                    value_text = self._get_cell_text(val_block, block_map)

        return key_text, value_text, confidence
# must exist in your AWS account