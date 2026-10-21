import re
import subprocess
import os
import sys

# Ensure python-docx is available
try:
    import docx
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
except ImportError:
    print("Error: python-docx not found. Please install it with: pip install python-docx")
    sys.exit(1)

def compile_document():
    tex_path = 'survey_paper.tex'
    if not os.path.exists(tex_path):
        print(f"Error: {tex_path} not found.")
        sys.exit(1)

    print(f"[1/4] Reading {tex_path}...")
    with open(tex_path, 'r', encoding='utf-8') as f:
        tex_content = f.read()

    # Extract abstract and keywords
    m_abs = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', tex_content, re.DOTALL)
    abstract_text = m_abs.group(1).strip() if m_abs else ""

    m_kw = re.search(r'\\textbf\{Keywords:\}\s*(.*?)(?=\\end\{center\})', tex_content, re.DOTALL)
    keywords_text = m_kw.group(1).strip() if m_kw else ""

    replacement_hdr = f"""
\\maketitle

\\begin{{center}}
\\textbf{{Abstract}}
\\end{{center}}

{abstract_text}

\\begin{{center}}
\\textbf{{Keywords:}} {keywords_text}
\\end{{center}}
"""

    tex_pandoc = re.sub(r'\\twocolumn\s*\[\s*\\maketitle.*?\\end\{center\}\s*\\vspace\{[^}]+\}\s*\]', 
                        lambda m: replacement_hdr, tex_content, flags=re.DOTALL)

    temp_pandoc = 'temp_pandoc.tex'
    temp_docx = 'temp_build.docx'
    with open(temp_pandoc, 'w', encoding='utf-8') as f:
        f.write(tex_pandoc)

    print("[2/4] Running Pandoc conversion...")
    subprocess.run(['pandoc', '-s', temp_pandoc, '-o', temp_docx], check=True)

    # Extract bibitems
    bib_matches = re.findall(r'\\bibitem\{([^}]+)\}\s*(.*?)(?=\\bibitem|\\end\{thebibliography\})', tex_content, re.DOTALL)
    clean_bibs = []
    for key, raw_text in bib_matches:
        txt = raw_text.replace('\n', ' ').strip()
        txt = re.sub(r'\\emph\{([^}]+)\}', r'\1', txt)
        txt = re.sub(r'\\texttt\{([^}]+)\}', r'\1', txt)
        txt = re.sub(r'\\textbf\{([^}]+)\}', r'\1', txt)
        txt = txt.replace(r'~', ' ').replace(r'--', '–').replace(r'\$', '$').replace(r'\_', '_')
        txt = txt.replace(r'{\`\i}', 'ì').replace(r'\"u', 'ü').replace(r'\&', '&').replace(r'\ ', ' ')
        txt = re.sub(r'\s+', ' ', txt)
        clean_bibs.append(txt)

    print("[3/4] Formatting 2-column layout and typography via python-docx...")
    doc = docx.Document(temp_docx)

    for t in list(doc.tables):
        if len(t.rows) == 0:
            t._tbl.getparent().remove(t._tbl)

    def make_sect_pr(num_cols, space_twips=300):
        sectPr = OxmlElement('w:sectPr')
        pgSz = OxmlElement('w:pgSz')
        pgSz.set(qn('w:w'), '12240')
        pgSz.set(qn('w:h'), '15840')
        sectPr.append(pgSz)
        pgMar = OxmlElement('w:pgMar')
        pgMar.set(qn('w:top'), '864') # 0.60 in
        pgMar.set(qn('w:bottom'), '864')
        pgMar.set(qn('w:left'), '864')
        pgMar.set(qn('w:right'), '864')
        sectPr.append(pgMar)
        t = OxmlElement('w:type')
        t.set(qn('w:val'), 'continuous')
        sectPr.append(t)
        c = OxmlElement('w:cols')
        c.set(qn('w:num'), str(num_cols))
        if num_cols > 1:
            c.set(qn('w:space'), str(space_twips))
        sectPr.append(c)
        return sectPr

    for s in ['Title', 'Author', 'Date', 'Abstract Title', 'Abstract']:
        if s in doc.styles:
            doc.styles[s].paragraph_format.keep_with_next = False

    intro_idx = -1
    for i, p in enumerate(doc.paragraphs):
        txt = p.text.strip().lower()
        if txt in ['1. introduction', '1 introduction', 'introduction']:
            intro_idx = i
            break

    # Title styling
    p0 = doc.paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p0.paragraph_format.space_before = Pt(0)
    p0.paragraph_format.space_after = Pt(3)
    p0.paragraph_format.keep_with_next = True
    for r in p0.runs:
        r.font.size = Pt(15.5)
        r.font.bold = True

    # Author styling
    p1 = doc.paragraphs[1]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_before = Pt(2)
    p1.paragraph_format.space_after = Pt(2)
    p1.paragraph_format.keep_with_next = True
    for r in p1.runs:
        r.font.size = Pt(9.5)

    # Date styling
    p2 = doc.paragraphs[2]
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(4)
    p2.paragraph_format.keep_with_next = True
    for r in p2.runs:
        r.font.size = Pt(8.5)

    # Abstract styling
    for i in range(3, intro_idx):
        p = doc.paragraphs[i]
        p.paragraph_format.keep_with_next = (i < 4)
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.right_indent = Inches(0.35)
        p.paragraph_format.line_spacing = 1.04
        p.paragraph_format.space_before = Pt(1.5)
        p.paragraph_format.space_after = Pt(2.0)
        if 'abstract' in p.text.strip().lower() and len(p.text.strip()) < 15:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.size = Pt(9.0)
                r.font.bold = True
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            for r in p.runs:
                r.font.size = Pt(8.5)

    # Break to 2-column continuous section
    prev_p = doc.paragraphs[intro_idx - 1]
    prev_p._p.get_or_add_pPr().append(make_sect_pr(1))

    bib_p_idx = -1
    for i in range(len(doc.paragraphs)-1, -1, -1):
        if doc.paragraphs[i].text.strip() == '99':
            bib_p_idx = i
            break

    end_body = bib_p_idx if bib_p_idx > 0 else len(doc.paragraphs)
    for i in range(intro_idx, end_body):
        p = doc.paragraphs[i]
        if '[tab:safeguards]' in p.text:
            for r in p.runs:
                if '[tab:safeguards]' in r.text:
                    r.text = r.text.replace('[tab:safeguards]', '1')
        if '[tab:framework_compare]' in p.text:
            for r in p.runs:
                if '[tab:framework_compare]' in r.text:
                    r.text = r.text.replace('[tab:framework_compare]', '2')

        p.paragraph_format.line_spacing = 1.04
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(1.6)
        for r in p.runs:
            if not r.font.size:
                r.font.size = Pt(9.0)

    if bib_p_idx > 0:
        p_bib_title = doc.paragraphs[bib_p_idx]
        p_bib_title.text = "References"
        p_bib_title.style = 'Heading 1'
        p_bib_title.paragraph_format.space_before = Pt(5)
        p_bib_title.paragraph_format.space_after = Pt(2)
        for r in p_bib_title.runs:
            r.font.size = Pt(10)
            r.font.bold = True

        if bib_p_idx + 1 < len(doc.paragraphs):
            p_old_bib = doc.paragraphs[bib_p_idx + 1]
            p_old_bib.text = ""

    # Append cleanly formatted bibliography
    for idx, b_text in enumerate(clean_bibs, 1):
        new_p = doc.add_paragraph()
        new_p.paragraph_format.line_spacing = 1.0
        new_p.paragraph_format.space_before = Pt(0)
        new_p.paragraph_format.space_after = Pt(1.0)
        new_p.paragraph_format.left_indent = Inches(0.2)
        new_p.paragraph_format.first_line_indent = Inches(-0.2)
        run_num = new_p.add_run(f"[{idx}] ")
        run_num.font.size = Pt(7.3)
        run_num.font.bold = True
        run_txt = new_p.add_run(b_text)
        run_txt.font.size = Pt(7.3)

    # Format tables
    for t_idx, t in enumerate(doc.tables):
        t.autofit = True
        for row_idx, row in enumerate(t.rows):
            is_header = (row_idx == 0)
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.0
                    p.paragraph_format.space_before = Pt(0.5)
                    p.paragraph_format.space_after = Pt(0.5)
                    for r in p.runs:
                        r.font.size = Pt(6.8)
                        if is_header:
                            r.font.bold = True

    for t in doc.tables:
        prev_node = t._tbl.getprevious()
        while prev_node is not None and not prev_node.tag.endswith('p'):
            prev_node = prev_node.getprevious()
        if prev_node is not None:
            pPr = prev_node.find(qn('w:pPr'))
            if pPr is None:
                pPr = OxmlElement('w:pPr')
                prev_node.insert(0, pPr)
            pPr.append(make_sect_pr(2, 300))
        
        next_node = t._tbl.getnext()
        while next_node is not None and not next_node.tag.endswith('p'):
            next_node = next_node.getnext()
        if next_node is not None:
            pPr2 = next_node.find(qn('w:pPr'))
            if pPr2 is None:
                pPr2 = OxmlElement('w:pPr')
                next_node.insert(0, pPr2)
            pPr2.append(make_sect_pr(1))

    body_sectPr = doc._body._element.xpath('./w:sectPr')[0]
    t_final = OxmlElement('w:type')
    t_final.set(qn('w:val'), 'continuous')
    body_sectPr.insert(0, t_final)
    cols_body = body_sectPr.xpath('./w:cols')
    if cols_body:
        cols_body[0].set(qn('w:num'), '2')
        cols_body[0].set(qn('w:space'), '300')
    else:
        c2 = OxmlElement('w:cols')
        c2.set(qn('w:num'), '2')
        c2.set(qn('w:space'), '300')
        body_sectPr.append(c2)

    doc.save('survey_paper.docx')
    print("Saved survey_paper.docx successfully.")

    # Cleanup temp files
    if os.path.exists(temp_pandoc):
        os.remove(temp_pandoc)
    if os.path.exists(temp_docx):
        os.remove(temp_docx)

    print("[4/4] Converting survey_paper.docx to survey_paper.pdf via LibreOffice...")
    cmd = [
        'libreoffice',
        '-env:UserInstallation=file:///tmp/lo_profile',
        '--headless',
        '--convert-to', 'pdf',
        'survey_paper.docx'
    ]
    subprocess.run(cmd, check=True)
    print("Done! Generated survey_paper.pdf successfully.")

if __name__ == '__main__':
    compile_document()

