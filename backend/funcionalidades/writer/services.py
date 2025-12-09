import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from typing import Optional
from PyPDF2 import PdfReader
from pylatex import Document, Command, Package
from pylatex.utils import NoEscape
import subprocess
from pathlib import Path

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def limpar_resposta_ia(texto: str) -> str:
    """
    Remove formatação Markdown, cabeçalhos LaTeX duplicados e blocos desnecessários
    para evitar conflito com o PyLaTeX.
    """
    # 1. Remove blocos de código Markdown (```latex ... ```)
    texto = texto.replace("```latex", "").replace("```", "")
    
    # 2. Remove preâmbulos se a IA tiver gerado (PyLaTeX já faz isso)
    # Remove tudo antes de \begin{document} se existir
    if "\\begin{document}" in texto:
        texto = texto.split("\\begin{document}")[1]
    
    # Remove \documentclass e \usepackage caso a IA tenha colocado no início
    texto = re.sub(r"\\documentclass.*?\n", "", texto)
    texto = re.sub(r"\\usepackage.*?\n", "", texto)
    
    # 3. Remove tags de fechamento (PyLaTeX fecha sozinho)
    texto = texto.replace("\\end{document}", "")
    
    return texto.strip()

def decide_fewshot(style: str) -> str:
    """Gera um exemplo curto para guiar a IA."""
    prompt = f"""
        Descreva o estilo {style}. Forneça um exemplo de SEÇÃO e uma EQUAÇÃO matemática (usando \\begin{{equation}})
        válidos para LaTeX. Não inclua cabeçalhos.
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text
    except:
        return ""

def extract_text_from_file(uploaded_file):
    """Lógica unificada de extração."""
    try:
        uploaded_file.seek(0)
        filename_lower = uploaded_file.name.lower()
        text = ""
        
        if filename_lower.endswith('.pdf'):
            reader = PdfReader(uploaded_file)
            parts = [page.extract_text() for page in reader.pages if page.extract_text()]
            text = '\n'.join(parts)
        elif filename_lower.endswith('.txt'):
            text = uploaded_file.read().decode('utf-8')
        
        return text.strip() or None
    except Exception as e:
        print(f"Erro na extração: {e}")
        return None

def convert_text_to_latex_file(conteudo_limpo: str, filename) -> str:
    """Salva o conteúdo LIMPO em um arquivo .tex temporário."""
    base_dir = Path(__file__).resolve().parent.parent
    folder_path = base_dir / 'arquivos'
    folder_path.mkdir(parents=True, exist_ok=True)
    
    filename = filename.replace(' ', '_')
    output_path = folder_path / f'{filename}_temp.tex'
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(conteudo_limpo)
        print(f"DEBUG: Arquivo .tex salvo em: {output_path}")
        return str(output_path)
    except Exception as e:
        print(f"Erro ao salvar temp tex: {e}")
        return ""

def convert_tex_file_to_pdf(tex_file_path: str) -> Optional[str]:
    """Usa PyLaTeX para gerar o .tex e subprocess para compilar o PDF (seguro contra erros de encoding)."""
    try:
        # Configurações de Geometria e Documento
        geometry_options = {"tmargin": "2.5cm", "lmargin": "3cm", "rmargin": "2cm", "bmargin": "2.5cm"}
        doc = Document(geometry_options=geometry_options)
        
        # --- ADICIONANDO PACOTES ---
        doc.packages.append(Package('amsmath'))
        doc.packages.append(Package('amssymb'))
        doc.packages.append(Package('amsfonts'))
        doc.packages.append(Package('graphicx'))
        doc.packages.append(Package('float'))
        doc.packages.append(Package('inputenc', options=['utf8']))
        doc.packages.append(Package('fontenc', options=['T1']))
        doc.packages.append(Package('babel', options=['brazil']))
        doc.packages.append(Package('hyperref'))
        
        # Lê o conteúdo gerado pela IA (temp file)
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Adiciona o conteúdo ao documento
        doc.append(NoEscape(content))
        
        # Define nome base (sem extensão) para o arquivo final
        base_filename = tex_file_path.replace('_temp.tex', '')
        
        print(f"Gerando arquivo estruturado: {base_filename}.tex")
        
        # 1. Gera apenas o arquivo .tex final (estrutura + conteúdo)
        # O PyLaTeX adiciona .tex automaticamente, então passamos sem extensão
        doc.generate_tex(base_filename)
        
        # 2. Compilação Manual Robusta
        # Define diretório de trabalho e nome do arquivo
        working_dir = os.path.dirname(os.path.abspath(base_filename))
        tex_filename = os.path.basename(base_filename) + ".tex"
        pdf_filename = os.path.basename(base_filename) + ".pdf"
        full_pdf_path = os.path.join(working_dir, pdf_filename)

        print(f"Iniciando compilação manual do arquivo: {tex_filename}...")

        # Comando do pdflatex
        cmd = ['pdflatex', '-interaction=nonstopmode', tex_filename]
        
        # Executa o processo
        # errors='replace' é o segredo: troca caracteres inválidos do log por  em vez de travar
        process = subprocess.run(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace' 
        )

        if process.returncode == 0:
            if os.path.exists(full_pdf_path):
                print(f"PDF gerado com sucesso: {full_pdf_path}")
                return full_pdf_path
        else:
            print("="*30)
            print("ERRO DE COMPILAÇÃO LATEX (LOG):")
            # Mostra as últimas 20 linhas do erro para debug
            print('\n'.join(process.stdout.splitlines()[-20:]))
            print("="*30)
            return None
            
        return None
        
    except Exception as e:
        print("="*30)
        print(f"ERRO GERAL NO PROCESSO: {e}")
        print("="*30)
        return None
        
    except Exception as e:
        print("="*30)
        print(f"ERRO DE COMPILAÇÃO LATEX: {e}")
        print("DICA: Abra o arquivo .log na pasta 'arquivos' para ver o erro detalhado.")
        print("="*30)
        return None

def validar_balanceamento_latex(texto: str) -> bool:
    """Verifica se o número de begins e ends parece correto."""
    num_begin = texto.count("\\begin{")
    num_end = texto.count("\\end{")
    
    if num_begin != num_end:
        print(f"AVISO: O código gerado parece desbalanceado! \\begin: {num_begin}, \\end: {num_end}")
        # Se quiser ser agressivo, retorne False para nem tentar compilar
        # return False 
    return True

def format_text_with_gemini(input_text, style, filename) -> dict:
    few_shot = decide_fewshot(style)
    
    prompt = f"""
        You are a LaTeX formatting specialist. Your task is to convert the text below into LaTeX.

        STRICT RULES (To avoid breaking the compiler):
        1. The code will be injected into a file that ALREADY HAS \\documentclass and \\begin{{document}}.
        2. IMAGES ARE FORBIDDEN: Do not use `\\includegraphics` or `figure`. If there is any mention of an image, write only "[Image removed]".
        3. COMPLEX TABLES ARE FORBIDDEN: Do not use the `tabular` or `table` environment. Convert all tables into lists (`itemize` or `enumerate`) or descriptive text.
        4. UNICODE MATH IS FORBIDDEN: Do not use symbols like α, β, ∞. You MUST use the commands `$\\alpha$`, `$\\beta$`, `$\\infty$`.
        5. Do NOT include any preamble (no \\documentclass, no \\usepackage).
        6. Do NOT include \\begin{{document}} or \\end{{document}}.
        7. Start directly with \\section{{Title}} or with the content.
        8. For mathematics, use ONLY LaTeX commands ($\\alpha$, $\\beta$), NOT Unicode symbols.
        9. TEXT ALIGNMENT: The body text MUST be fully justified (standard LaTeX behavior). 
        10. PROHIBITED: Do NOT use the commands `\\centering` or `\\begin{{center}}` for the main body text. Only center the Main Title if necessary, then immediately switch back.
        11. NO DEEP NESTING: Do NOT nest lists (`itemize` or `enumerate`) more than 2 levels deep. Deep nesting causes the compiler to crash ("Too deeply nested" error).
        12. CLOSE ALL ENVIRONMENTS: Every `\\begin{{...}}` MUST have a matching `\\end{{...}}`. Double-check that no list is left open.
        13. ESCAPE SPECIAL CHARACTERS: You MUST escape reserved characters in text mode to avoid "Runaway argument":
            - `%` becomes `\\%`
            - `_` becomes `\\_`
            - `&` becomes `\\&`
            - `$` becomes `\\$`
            - `#` becomes `\\#`
        14. Desired style: {few_shot}.
        
        Original Text:
        {input_text[:50000]}

        The API must translate the final response into Portuguese.
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        
        if not response.text: return None
        
        print("IA gerou texto. Limpando e compilando...")
        
        # 1. Limpa a resposta (remove markdown, documentclass duplicado, etc)
        texto_limpo = limpar_resposta_ia(response.text)
        # Validação simples (apenas printa aviso no console por enquanto)
        validar_balanceamento_latex(texto_limpo)

        # 2. Salva o .tex
        caminho_tex = convert_text_to_latex_file(texto_limpo, filename)
        
        # 3. Compila para gerar o PDF
        caminho_pdf = convert_tex_file_to_pdf(caminho_tex)
        
        if caminho_pdf and os.path.exists(caminho_pdf):
            # RETORNA UM DICIONÁRIO
            return {
                "success": True,
                "base_filename": os.path.basename(caminho_pdf).replace('.pdf', '')
            }
        else:
             return {"success": False, "error": "Erro na compilação do PDF"}

    except Exception as e:
        print(f"Erro no fluxo Gemini: {e}")
        return {"success": False, "error": str(e)}