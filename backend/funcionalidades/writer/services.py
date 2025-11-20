import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from typing import Optional
from PyPDF2 import PdfReader
from pylatex import Document, Command, Package
from pylatex.utils import NoEscape

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
    folder_path = './arquivos'
    os.makedirs(folder_path, exist_ok=True)
    
    filename = filename.replace(' ', '_')
    output_path = os.path.join(folder_path, f'{filename}_temp.tex')
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(conteudo_limpo)
        return output_path
    except Exception as e:
        print(f"Erro ao salvar temp tex: {e}")
        return ""

def convert_tex_file_to_pdf(tex_file_path: str) -> Optional[str]:
    """Usa PyLaTeX para gerar o PDF final."""
    try:
        # Configurações de Geometria e Documento
        geometry_options = {"tmargin": "2.5cm", "lmargin": "3cm", "rmargin": "2cm", "bmargin": "2.5cm"}
        doc = Document(geometry_options=geometry_options)
        
        # --- ADICIONANDO PACOTES CRÍTICOS ---
        # Isso evita erros de "Undefined control sequence" em matemática
        doc.packages.append(Package('amsmath'))
        doc.packages.append(Package('amssymb'))
        doc.packages.append(Package('amsfonts'))
        doc.packages.append(Package('graphicx'))
        doc.packages.append(Package('float'))
        doc.packages.append(Package('inputenc', options=['utf8']))
        doc.packages.append(Package('fontenc', options=['T1']))
        doc.packages.append(Package('babel', options=['brazil'])) # Ajuste conforme idioma
        
        # Lê o conteúdo gerado pela IA
        with open(tex_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Adiciona o conteúdo ao documento
        doc.append(NoEscape(content))
        
        # Define nome de saída
        pdf_file_path = tex_file_path.replace('_temp.tex', '')
        
        print(f"Iniciando compilação do arquivo: {pdf_file_path}...")
        
        # Gera o PDF
        # clean_tex=False permite que você veja o .tex gerado se der erro
        doc.generate_pdf(pdf_file_path, clean_tex=False, compiler='pdflatex')
        
        full_path = pdf_file_path + ".pdf"
        if os.path.exists(full_path):
            print(f"PDF gerado com sucesso: {full_path}")
            return full_path
        return None
        
    except Exception as e:
        print("="*30)
        print(f"ERRO DE COMPILAÇÃO LATEX: {e}")
        print("DICA: Abra o arquivo .log na pasta 'arquivos' para ver o erro detalhado.")
        print("="*30)
        return None

def format_text_with_gemini(input_text, style, filename) -> Optional[str]:
    few_shot = decide_fewshot(style)
    
    prompt = f"""
        Você é um formatador LaTeX especializado. Sua tarefa é converter o texto abaixo para LaTeX.
        
        REGRAS ESTRITAS (Para não quebrar o compilador):
        1. O código será injetado dentro de um arquivo que JÁ POSSUI \\documentclass e \\begin{{document}}.
        2. PROIBIDO USAR IMAGENS: Não use `\\includegraphics` ou `figure`. Se houver menção a imagem, escreva apenas "[Imagem removida]".
        3. PROIBIDO USAR TABELAS COMPLEXAS: Não use o ambiente `tabular` ou `table`. Converta todas as tabelas em listas (`itemize` ou `enumerate`) ou texto descritivo.
        4. PROIBIDO UNICODE MATEMÁTICO: Não use símbolos como α, β, ∞. Use OBRIGATORIAMENTE os comandos `$\\alpha$`, `$\\beta$`, `$\\infty$`.
        5. NÃO inclua preâmbulos (\\documentclass, \\usepackage).
        6. NÃO inclua \\begin{{document}} ou \\end{{document}}.
        7. Comece direto com \\section{{Título}} ou o conteúdo.
        8. Para matemática, use APENAS comandos LaTeX ($\\alpha$, $\\beta$), NÃO use símbolos Unicode.
        9. Estilo desejado: {style}.
        
        Texto Original:
        {input_text[:25000]} 
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt)
        
        if not response.text: return None
        
        print("IA gerou texto. Limpando e compilando...")
        
        # 1. Limpa a resposta (remove markdown, documentclass duplicado, etc)
        texto_limpo = limpar_resposta_ia(response.text)
        
        # 2. Salva temp
        caminho_temp = convert_text_to_latex_file(texto_limpo, filename)
        
        # 3. Compila
        caminho_pdf = convert_tex_file_to_pdf(caminho_temp)
        
        return caminho_pdf

    except Exception as e:
        print(f"Erro no fluxo Gemini: {e}")
        return None