import configparser
import json
import sys
import threading
import subprocess
import webbrowser
from solana_sniper_bot import add_debug_info, add_text_to_pdf, create_table, getRugAPIJsonData, debug_info, start_server, add_image_to_pdf
from utils.send_message import send_message, composedEmbed
from utils.utils_sec import checkPoolSize, checkLiquidityLockPercentage, checkPresentRisks, checkMintAuthority, checkFreezeAuthority, checkTopHolders
from solana.rpc.api import Client
from solders.pubkey import Pubkey  # type: ignore
from reportlab.lib.pagesizes import A4  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore
from reportlab.platypus import Table, TableStyle  # Add this line
from reportlab.lib import colors  # Add this line

# Set up canvas parameters
w, h = A4
c = canvas.Canvas("report.pdf", pagesize=A4)

def create_pdf_report(data):
    global y_position
    y_position = h - 40

    # Set the scale to fit content within the page
    c.scale(0.9, 0.9)

    # Translate to move the origin
    c.translate(30, 30)

    def draw_text(text, x=40, y=None):
        global y_position
        if y is None:
            y = y_position
            y_position -= 20
        c.drawString(x, y, text)
        if y_position < 40:  # Add new page if space is running out
            c.showPage()
            y_position = h - 40
            c.scale(0.9, 0.9)
            c.translate(30, 30)

    token_name = data.get('tokenMeta', {}).get('name', 'Unknown Token')
    title = "Solana Sniper Bot Report for " + token_name
    c.setFont("Helvetica-Bold", 16)
    draw_text(title, y=750)

    draw_text("[*] Debug information saved in debug_info.json")

    # Ensure the table is positioned correctly
    table_y_position = y_position - 50
    create_table(data, c, table_y_position)

    c.save()

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
    table.wrapOn(pdf_canvas, w - 80, h - 80)
    table.drawOn(pdf_canvas, 40, table_y_position)

def get_pool_infos(token_address, pool_number):
    add_debug_info("ENGAGING WITH SECURITY CHECKS", "")
    
    # Check Pool Size
    add_debug_info("CHECKING POOL SIZE", "")
    global checkPoolSizeFlag
    checkPoolSizeFlag = checkPoolSize(pool_number, minimum_pool_size, maximum_pool_size)
    if checkPoolSizeFlag:
        add_debug_info("Pool size check", "Passed: Pool Size " + str(pool_number) + " (Minimum " + str(minimum_pool_size) + ", Maximum " + str(maximum_pool_size) + ")")
        
        rugPullAPIJsonData = getRugAPIJsonData(token_address)
        
        # Add token image to PDF
        token_image_url = rugPullAPIJsonData.get('tokenMeta', {}).get('image', '')
        if token_image_url:
            add_debug_info("Adding token image to PDF", "")
            add_image_to_pdf(token_image_url, c)
        
        # Check Locked Liquidity Percentage
        add_debug_info("CHECKING LOCKED LIQUIDITY PERCENTAGE", "")
        lockedPercentage = checkLiquidityLockPercentage(rugPullAPIJsonData)
        if int(lockedPercentage) >= int(minimum_locked_percentage):
            add_debug_info("Locked liquidity percentage check", "Passed: " + str(lockedPercentage) + "% (Minimum required: " + str(minimum_locked_percentage) + "%)")
            
            # Check Mint Authority
            add_debug_info("CHECKING MINT AUTHORITY", "")
            mintAuthority = checkMintAuthority(rugPullAPIJsonData)
            if not mintAuthority:
                add_debug_info("Mint authority check", "Passed: No mint authority detected")
                
                # Check Freeze Authority
                add_debug_info("CHECKING FREEZE AUTHORITY", "")
                freezeAuthority = checkFreezeAuthority(rugPullAPIJsonData)
                if not freezeAuthority:
                    add_debug_info("Freeze authority check", "Passed: No freeze authority detected")
                    
                    # Check Top Holders Percentage
                    add_debug_info("CHECKING TOP HOLDERS PERCENTAGE", "")
                    topHoldersPercentage = checkTopHolders(rugPullAPIJsonData, max_holder_percentage)
                    if topHoldersPercentage:
                        add_debug_info("Top holders percentage check", "Passed: Top holders percentage is within acceptable range")
                        
                        # Risk Analysis
                        add_debug_info("RISK ANALYSIS", "")
                        if not checkPresentRisks(rugPullAPIJsonData, max_risk_count):
                            add_debug_info("Risk analysis", "Passed: No significant risks detected")
                            embed = composedEmbed(rugPullAPIJsonData, token_address, pool_number, mintAuthority, freezeAuthority, topHoldersPercentage, True)
                            send_message(embed)
                            subprocess.Popen(['python3', 'utils/trade.py', token_address])
                        else:
                            add_debug_info("Risk analysis", "Failed: Significant risks detected")
                    else:
                        add_debug_info("Top holders percentage check", "Failed: Top holders exceed acceptable limit")
                else:
                    add_debug_info("Freeze authority check", "Failed: Freeze authority detected")
            else:
                add_debug_info("Mint authority check", "Failed: Mint authority detected")
        else:
            add_debug_info("Locked liquidity percentage check", "Failed: " + str(lockedPercentage) + "% (Minimum required: " + str(minimum_locked_percentage) + "%)")
    else:
        add_debug_info("Pool size check", "Failed: Pool Size " + str(pool_number) + " (Minimum " + str(minimum_pool_size) + ", Maximum " + str(maximum_pool_size) + ")")
        sys.exit(1)
    
    return rugPullAPIJsonData

if len(sys.argv) != 3:
    add_debug_info("Usage", "python main.py <token_address> <pool_size>")
    sys.exit(1)

token_address = sys.argv[1]
pool_size_str = sys.argv[2]

# Validate token address
if not token_address:
    add_debug_info("Error", "Token address is not provided.")
    sys.exit(1)

# Validate pool size
try:
    pool_size_float = float(pool_size_str)
    pool_size = int(pool_size_float)
except ValueError:
    add_debug_info("Error", "Invalid pool size. Please provide a valid number.")
    sys.exit(1)

config = configparser.ConfigParser()
config.read('config.ini')
minimum_pool_size = int(config['config']['minimum_pool_size'])
maximum_pool_size = int(config['config']['maximum_pool_size'])
minimum_locked_percentage = int(config['config']['locked_percentage'])
max_holder_percentage = int(config['config']['max_holder_percentage'])
max_risk_count = int(config['config']['max_risk_count'])
main_url = config['solanaConfig']['main_url']
wss_url = config['solanaConfig']['wss_url']
raydium_lp_v4 = config['solanaConfig']['raydium_lp_v4']
log_instruction = config['solanaConfig']['log_instruction']

solana_client = Client(main_url)
raydium_lp_v4 = Pubkey.from_string(raydium_lp_v4)

add_debug_info("Started the Solana Sniper Bot", "")
add_debug_info("Token Address: " + token_address, "")
add_debug_info("Token Pool Size: " + str(pool_size), "")
add_debug_info("Minimum pool size: " + str(minimum_pool_size), "")
add_debug_info("Maximum pool size: " + str(maximum_pool_size), "")
add_debug_info("Maximum holder percentage: " + str(max_holder_percentage), "")

rugPullAPIJsonData = get_pool_infos(token_address, pool_size)

# Save debug info to JSON file
with open('debug_info.json', 'w') as json_file:
    json.dump(debug_info, json_file, indent=4)

# Create and save PDF
create_pdf_report(rugPullAPIJsonData)

# Start the server and open the browser
server_thread = threading.Thread(target=start_server)
server_thread.start()

# Open the default web browser to view the report
webbrowser.open("http://localhost:8000/report.pdf")
