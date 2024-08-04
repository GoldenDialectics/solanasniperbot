import requests
import json
import io
from time import sleep
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from PIL import Image
import logging
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger()

# Create a PDF canvas
pdf_canvas = canvas.Canvas("report.pdf", pagesize=letter)
width, height = letter
y_position = height - 40

# Debug information storage
debug_info = {
    "steps": []
}

def add_debug_info(step, info):
    debug_info["steps"].append({step: info})
    logger.info("%s, %s", step, info)

def add_text_to_pdf(text_str):
    global y_position
    pdf_canvas.drawString(40, y_position, text_str)
    y_position -= 20
    logger.info(text_str)

def add_image_to_pdf(image_url, pdf_canvas, x=40, y=height - 200, width=200):
    try:
        response = requests.get(image_url)
        image = Image.open(io.BytesIO(response.content))
        image_reader = ImageReader(image)
        pdf_canvas.drawImage(image_reader, x, y, width, height=width * image.size[1] / image.size[0])
    except Exception as e:
        logger.error("Failed to add image to PDF: " + str(e))

def getRugAPIJsonData(token_address):
    while True:
        try:
            add_debug_info("Getting token metadata", "Fetching metadata for token address " + token_address)
            r = requests.get('https://api.rugcheck.xyz/v1/tokens/' + token_address + '/report')
            if r.text is not None:
                add_debug_info("Metadata obtained", r.json())
                return r.json()
        except Exception as e:
            add_debug_info("Failed to parse JSON", "Error: " + str(e) + ", retrying in 5 seconds")
            sleep(5)

def create_table(data, pdf_canvas, table_y_position):
    table_data = [["Test", "Result", "Details"]]
    for item in debug_info["steps"]:
        for key, value in item.items():
            result = "💯" if "Passed" in value else "😡"
            table_data.append([key, result, json.dumps(value, indent=4)])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    table.wrapOn(pdf_canvas, width - 80, height - 80)
    table.drawOn(pdf_canvas, 40, table_y_position)

def start_server():
    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(("localhost", 8000), handler)
    logger.info("Serving at port 8000")
    httpd.serve_forever()