import sys, markdown, asyncio, pathlib
from playwright.async_api import async_playwright

src, out, titulo = sys.argv[1], sys.argv[2], sys.argv[3]
html_body = markdown.markdown(pathlib.Path(src).read_text(encoding="utf-8"),
    extensions=["tables","fenced_code","sane_lists","attr_list"])
CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: Calibri, "Segoe UI", Arial, sans-serif; color:#29334C;
       font-size:10.5pt; line-height:1.5; margin:0; }
h1 { font-family: Cambria, Georgia, serif; color:#141D33; font-size:22pt;
     margin:0 0 4mm; line-height:1.15; }
h2 { font-family: Cambria, Georgia, serif; color:#141D33; font-size:14pt;
     margin:9mm 0 3mm; padding-top:3mm; border-top:1px solid #DAE0EA; }
h3 { font-family: Cambria, Georgia, serif; color:#2B5A8A; font-size:11.5pt; margin:6mm 0 2mm; }
h2:first-of-type { border-top:none; padding-top:0; }
p, li { margin:0 0 2.4mm; }
ul, ol { margin:0 0 3mm; padding-left:6mm; }
li > ul { margin-top:1.6mm; }
strong { color:#141D33; }
code { font-family: Consolas, "Courier New", monospace; font-size:9.3pt;
       background:#EEF1F6; padding:0.4mm 1.2mm; border-radius:2px; color:#1F3A5C; }
pre { background:#F4F6F9; border:1px solid #DAE0EA; border-radius:3px; padding:3mm;
      font-size:9pt; overflow-wrap:anywhere; white-space:pre-wrap; }
pre code { background:none; padding:0; }
table { border-collapse:collapse; width:100%; margin:0 0 4mm; font-size:9.6pt; }
th { background:#E5EDF6; color:#141D33; text-align:left; font-weight:600; }
th, td { border:1px solid #DAE0EA; padding:1.6mm 2.4mm; vertical-align:top; }
hr { border:none; border-top:1px solid #DAE0EA; margin:6mm 0; }
blockquote { margin:0 0 3mm; padding:2mm 0 2mm 4mm; border-left:3px solid #2B5A8A;
             color:#57617A; }
h1,h2,h3 { break-after:avoid; }
table, pre { break-inside:avoid; }
"""
page_html = f"<!doctype html><meta charset='utf-8'><title>{titulo}</title><style>{CSS}</style>{html_body}"

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page()
        await pg.set_content(page_html, wait_until="load")
        await pg.pdf(path=out, format="A4", print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template="<div style='width:100%;font:8pt Calibri,Arial;color:#8A93A6;"
                            "padding:0 16mm;display:flex;justify-content:space-between'>"
                            f"<span>{titulo}</span><span class='pageNumber'></span></div>")
        await b.close()
asyncio.run(main())
print("gerado:", out)
