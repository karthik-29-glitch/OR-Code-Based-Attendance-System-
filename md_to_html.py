import sys
import subprocess
try:
    import markdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

with open("d:\\qrat\\Project_Report.md", "r", encoding="utf-8") as f:
    text = f.read()

# Parse using markdown with extra extensions for code blocks and tables
html_body = markdown.markdown(text, extensions=['fenced_code', 'tables'])

# Construct the HTML structure with inline CSS matching the user's explicit formatting request
html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: 'Times New Roman', Times, serif;
        line-height: 1.5;
        padding: 40px;
    }}
    h1 {{
        font-size: 16pt;
        font-weight: bold;
        text-align: left;
    }}
    h2, h3, h4, h5, h6 {{
        font-size: 14pt;
        font-weight: bold;
    }}
    p, li, td, th, div, span, pre, code {{
        font-size: 12pt;
        text-align: justify;
    }}
    pre {{
        background-color: #f4f4f4;
        padding: 10px;
        border: 1px solid #ccc;
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 20px;
    }}
    th, td {{
        border: 1px solid black;
        padding: 8px;
        font-size: 12pt;
    }}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

with open("d:\\qrat\\Project_Report.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("Conversion to HTML complete.")
