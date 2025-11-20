import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from typing import Optional
from PyPDF2 import PdfReader
import subprocess

# Configuração de logs
logger = logging.getLogger(__name__)

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def decide_fewshot(style: str) -> str:
    """Gera um exemplo de formatação (few-shot) baseado no estilo."""
    prompt = f"""
    Forneça um exemplo curto de código LaTeX para o estilo {style}.
    Inclua apenas: cabeçalho (documentclass), pacote utf8, e um exemplo de equação matemática usando comandos (ex: \\alpha).
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return ""

def extract_text_from_file(uploaded_file):
    """Extrai texto de PDF ou TXT."""
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
        logger.error(f"Erro na extração: {e}")
        return None

def convert_text_to_latex_file(latex_content: str, filename: str) -> str:
    """Salva o texto da IA em um arquivo .tex"""
    folder_path = './arquivos'
    os.makedirs(folder_path, exist_ok=True)
    
    clean_filename = filename.replace(' ', '_')
    output_path = os.path.join(folder_path, f'{clean_filename}_formatado.tex')
    
    # Garante que o cabeçalho essencial exista se a IA esquecer
    if r"\documentclass" not in latex_content:
        header = "\\documentclass{article}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath}\n\\begin{document}\n"
        footer = "\n\\end{document}"
        latex_content = header + latex_content + footer

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex_content)
    return output_path

def convert_tex_file_to_pdf(tex_file_path: str) -> Optional[str]:
    """Compila o .tex para PDF usando pdflatex via subprocess."""
    work_dir = os.path.dirname(tex_file_path)
    tex_filename = os.path.basename(tex_file_path)
    
    # -interaction=nonstopmode impede que o latex trave esperando input em caso de erro
    cmd = ['pdflatex', '-interaction=nonstopmode', tex_filename]
    
    try:
        subprocess.run(cmd, cwd=work_dir, capture_output=True, timeout=30)
        pdf_path = tex_file_path.replace('.tex', '.pdf')
        if os.path.exists(pdf_path):
            return pdf_path
        return None
    except Exception as e:
        logger.error(f"Erro compilação PDF: {e}")
        return None

def format_text_with_gemini(input_text, style, filename) -> Optional[str]:
    few_shot = decide_fewshot(style)
    
    # PROMPT ANTI-ERRO DE UNICODE
    prompt = f"""
    ATUE COMO UM COMPILADOR LATEX. Converta o texto abaixo para LaTeX (Estilo: {style}).
    
    REGRAS OBRIGATÓRIAS:
    1. NÃO use símbolos Unicode (α, β, ∞, −). USE APENAS COMANDOS: $\\alpha$, $\\beta$, $\\infty$, $-$.
    2. Se o texto for longo, resuma o conteúdo para garantir que o código LaTeX esteja completo e feche com \\end{{document}}.
    3. Retorne APENAS o código LaTeX.
    
    Texto:
    {input_text[:20000]} (Texto truncado por segurança se for muito longo)
    """
    
    try:
        # Use o modelo PRO para evitar cortes em textos longos
        model = genai.GenerativeModel("gemini-1.5-pro") 
        response = model.generate_content(prompt)
        
        if not response.text: return None

        caminho_tex = convert_text_to_latex_file(response.text, filename)
        caminho_pdf = convert_tex_file_to_pdf(caminho_tex)
        
        return caminho_pdf
    except Exception as e:
        logger.error(f"Erro Gemini: {e}")
        return None