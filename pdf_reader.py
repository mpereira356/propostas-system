"""
Módulo para extração de dados de PDFs de propostas comerciais
"""
import re
import os
import pdfplumber
from datetime import datetime


class PropostaExtractor:
    """Classe para extrair dados de propostas comerciais em PDF"""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.text = ""
        self.lines = []
        
    def extract_text(self):
        """Extrai todo o texto do PDF"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                self.text = ""
                for page in pdf.pages:
                    # Alguns PDFs retornam None; evitar TypeError.
                    page_text = page.extract_text()
                    if not page_text:
                        # Fallback para layouts que não extraem bem no modo padrão.
                        try:
                            page_text = page.extract_text(layout=True)
                        except Exception:
                            page_text = None
                    if page_text:
                        self.text += page_text + "\n"
                
                # Criar lista de linhas para facilitar busca
                self.lines = [line.strip() for line in self.text.split('\n') if line.strip()]
            return True
        except Exception as e:
            print(f"Erro ao extrair texto do PDF: {e}")
            return False
    
    def find_line_with(self, pattern):
        """Encontra linha que contém o padrão"""
        for i, line in enumerate(self.lines):
            if re.search(pattern, line, re.IGNORECASE):
                return i, line
        return None, None
    
    def extract_id_proposta(self):
        """Extrai o ID da proposta"""
        # Primeiro, tentar extrair pelo rótulo "ID da Proposta"
        pattern_label = r'ID\s+da\s+Proposta:\s*([A-Z]{2}\.[A-Z0-9-]{3,6}/\d{2,4})'
        match = re.search(pattern_label, self.text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Variante comum: "ID da <ID>"
        pattern_label_short = r'ID\s+da\s+([A-Z]{2}\.[A-Z0-9-]{3,6}/\d{2,4})'
        match = re.search(pattern_label_short, self.text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback: procurar IDs no formato XX.XXXX/AA(AA) (com letras/números)
        pattern_generic = r'[A-Z]{2}\.[A-Z0-9-]{3,6}/\d{2,4}'
        match = re.search(pattern_generic, self.text, re.IGNORECASE)
        if match:
            return match.group(0)

        # Último fallback: tentar montar a partir do nome do arquivo
        id_from_filename = self.extract_id_from_filename()
        if id_from_filename:
            return id_from_filename
        return None

    def _find_section_by_numbered_heading(self, keyword):
        """Retorna o bloco de texto de uma seção numerada (ex.: '2.13 INSTALAÇÃO')."""
        if not self.lines:
            return None
        heading_pattern = re.compile(r'^\d+(?:\.\d+)?\s+.*$', re.IGNORECASE)
        keyword_pattern = re.compile(r'^\d+(?:\.\d+)?\s+.*' + re.escape(keyword) + r'.*$', re.IGNORECASE)

        start_idx = None
        for i, line in enumerate(self.lines):
            if keyword_pattern.search(line):
                start_idx = i
                break
        if start_idx is None:
            return None

        end_idx = len(self.lines)
        for j in range(start_idx + 1, len(self.lines)):
            if heading_pattern.match(self.lines[j]):
                end_idx = j
                break
        return "\n".join(self.lines[start_idx:end_idx])

    def _extract_incluso_status(self, section_text):
        """Detecta se a seção indica 'incluso' ou 'não incluso'."""
        if not section_text:
            return "Não informado"
        if re.search(r'n[aã]o\s+inclus', section_text, re.IGNORECASE):
            return "Não incluso"
        if re.search(r'inclus', section_text, re.IGNORECASE):
            return "Incluso"
        return "Não informado"

    def extract_servicos(self):
        """Extrai status de serviços: instalação, qualificações e treinamento."""
        instalacao_text = self._find_section_by_numbered_heading('INSTALAÇÃO') or \
            self._find_section_by_numbered_heading('INSTALACAO')
        qualificacoes_text = self._find_section_by_numbered_heading('QUALIFICAÇÕES') or \
            self._find_section_by_numbered_heading('QUALIFICACOES')
        treinamento_text = self._find_section_by_numbered_heading('TREINAMENTO')

        qualificacoes_status = self._extract_incluso_status(qualificacoes_text)
        if qualificacoes_text and qualificacoes_status == "Incluso":
            inclui_qi = re.search(r'\bQI\b', qualificacoes_text, re.IGNORECASE) is not None
            inclui_qo = re.search(r'\bQO\b', qualificacoes_text, re.IGNORECASE) is not None
            inclui_qd = re.search(r'\bQD\b', qualificacoes_text, re.IGNORECASE) is not None
            qualificacoes_partes = []
            if inclui_qi:
                qualificacoes_partes.append('QI')
            if inclui_qo:
                qualificacoes_partes.append('QO')
            if inclui_qd:
                qualificacoes_partes.append('QD')
            if qualificacoes_partes:
                qualificacoes_status = f"{qualificacoes_status} ({'/'.join(qualificacoes_partes)})"

        return {
            'instalacao_status': self._extract_incluso_status(instalacao_text),
            'qualificacoes_status': qualificacoes_status,
            'treinamento_status': self._extract_incluso_status(treinamento_text),
        }

    def extract_garantia(self):
        """Extrai a seção de garantia e um resumo de prazos."""
        if not self.lines:
            return {'garantia_resumo': None, 'garantia_texto': None}

        # Localizar início da garantia
        start_idx = None
        for i, line in enumerate(self.lines):
            if re.search(r'GARANTIA', line, re.IGNORECASE):
                start_idx = i
                break
        if start_idx is None:
            return {'garantia_resumo': None, 'garantia_texto': None}

        heading_pattern = re.compile(r'^\d+(?:\.\d+)?\s+.*$', re.IGNORECASE)
        end_idx = len(self.lines)
        for j in range(start_idx + 1, len(self.lines)):
            if heading_pattern.match(self.lines[j]):
                end_idx = j
                break

        garantia_texto = "\n".join(self.lines[start_idx:end_idx])

        # Resumo de prazos: normalizar quebras para evitar "MESES" em linha separada
        texto_compacto = " ".join(self.lines[start_idx:end_idx])
        texto_compacto = re.sub(r'\s+', ' ', texto_compacto).strip()

        prazos = []
        pattern = re.compile(
            r'Para\s+(.+?)\s+(\d{1,3})\s*(?:\([A-Z\s]+\))?\s*(MESES|MÊS|DIAS|DIA)',
            re.IGNORECASE
        )
        for match in pattern.finditer(texto_compacto):
            descricao = match.group(1).strip().rstrip(':')
            quantidade = match.group(2)
            unidade = match.group(3).upper()
            prazos.append(f"Para {descricao}: {quantidade} {unidade}")

        garantia_resumo = "\n".join(prazos) if prazos else None
        return {'garantia_resumo': garantia_resumo, 'garantia_texto': garantia_texto}

    def extract_id_from_filename(self):
        """Monta um ID baseado no nome do arquivo, se possível."""
        filename = os.path.basename(self.pdf_path)
        # Ex.: "015B - ...", "009-B - ...", "010A - ..."
        match = re.match(r'^\s*([0-9]{3,4}[A-Z]?(-[A-Z])?)', filename)
        if not match:
            return None
        codigo = match.group(1)

        # Tentar inferir ano pela data de emissão já extraída
        data_emissao = self.extract_data_emissao()
        ano = None
        if data_emissao:
            try:
                ano = data_emissao.split('/')[-1][-2:]
            except Exception:
                ano = None

        # Inferir prefixo
        prefixo = "BA"
        if re.search(r'MP-?BIOS', self.text, re.IGNORECASE):
            prefixo = "MP"

        if ano:
            return f"{prefixo}.{codigo}/{ano}"
        return f"{prefixo}.{codigo}"
    
    def extract_data_emissao(self):
        """Extrai a data de emissão"""
        pattern = r'\d{2}/[A-Z]{3}/\d{2,4}'
        match = re.search(pattern, self.text[:500])
        if match:
            date_str = match.group(0)
            # Converter formato 17/JAN/25 para datetime
            try:
                meses = {
                    'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
                    'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
                    'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
                }
                parts = date_str.split('/')
                day = parts[0]
                month = meses.get(parts[1], '01')
                year = parts[2]
                if len(year) == 2:
                    year = '20' + year
                return f"{day}/{month}/{year}"
            except:
                return date_str
        return None
    
    def extract_validade(self):
        """Extrai a validade da proposta"""
        # Ex.: "30 (TRINTA) DIAS"
        pattern = r'(\d+)\s*\([A-Z]+\)\s*DIAS'
        match = re.search(pattern, self.text[:500], re.IGNORECASE)
        if match:
            return f"{match.group(1)} DIAS"

        # Ex.: "Validade: 30 DIAS"
        pattern = r'Validade:\s*(\d+)\s*DIAS'
        match = re.search(pattern, self.text[:500], re.IGNORECASE)
        if match:
            return f"{match.group(1)} DIAS"

        # Ex.: "Validade: Até 30.05.2025" ou "Validade: 30/05/2025"
        pattern = r'Validade:\s*(?:Até\s*)?(\d{2}[./]\d{2}[./]\d{4})'
        match = re.search(pattern, self.text[:500], re.IGNORECASE)
        if match:
            date_str = match.group(1).replace('.', '/')
            return date_str
        return None
    
    def extract_razao_social(self):
        """Extrai a razão social"""
        # Preferir linha após "Razão Social:"
        idx, line = self.find_line_with(r'Raz[aã]o\s+Social:')
        if idx is not None:
            parts = line.split(':')
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
            if idx + 1 < len(self.lines):
                next_line = self.lines[idx + 1]
                if not re.search(r'(Nome Fantasia|CNPJ|Telefone|Contato|Inscri)', next_line, re.IGNORECASE):
                    return next_line

        # Fallback: linha após "Emissão:"
        idx, _ = self.find_line_with(r'Emiss[aã]o:')
        if idx is not None and idx + 1 < len(self.lines):
            razao = self.lines[idx + 1]
            # Verificar se não é um campo conhecido
            if not re.search(r'(Nome Fantasia|CNPJ|Telefone|Contato)', razao, re.IGNORECASE):
                return razao
        return None
    
    def extract_nome_fantasia(self):
        """Extrai o nome fantasia"""
        idx, line = self.find_line_with(r'Nome Fantasia ou Local')
        if idx is not None:
            # Verificar se tem conteúdo na mesma linha
            parts = line.split(':')
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
            # Verificar linha seguinte
            if idx + 1 < len(self.lines):
                next_line = self.lines[idx + 1]
                if not re.search(r'(CNPJ|Telefone|Contato|Inscrição)', next_line):
                    return next_line
        return "Não informado"
    
    def extract_cnpj(self):
        """Extrai o CNPJ"""
        patterns = [
            r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}',
            r'\d{2}[.\-]\d{3}[.\-]\d{3}[/-]\d{4}[/-]\d{2}'
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                return match.group(0)
        return None
    
    def extract_telefone(self):
        """Extrai o telefone"""
        # Procurar telefone na linha "Telefone:"
        idx, line = self.find_line_with(r'Telefone:')
        if idx is not None:
            tel_match = re.search(r'\(\s*\d{2}\s*\)\s*\d{4,5}-?\d{4}', line)
            if tel_match:
                return tel_match.group(0).replace("  ", " ").strip()

        # Fallback: procurar primeiro telefone no texto
        tel_match = re.search(r'\(\s*\d{2}\s*\)\s*\d{4,5}-?\d{4}', self.text)
        if tel_match:
            return tel_match.group(0).replace("  ", " ").strip()
        return "Não informado"
    
    def extract_celular(self):
        """Extrai o celular"""
        pattern = r'Cel:\s*\((\d{2})\)\s*(\d{4,5}-?\d{4})'
        match = re.search(pattern, self.text)
        if match:
            return f"({match.group(1)}) {match.group(2)}"
        return None
    
    def extract_email(self):
        """Extrai o email"""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, self.text[:1500])
        if match:
            return match.group(0)
        return None
    
    def extract_pessoa_contato(self):
        """Extrai a pessoa de contato"""
        idx, line = self.find_line_with(r'Contato:')
        if idx is not None:
            # Verificar se tem conteúdo na mesma linha
            parts = line.split(':')
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
            # Verificar linha seguinte
            if idx + 1 < len(self.lines):
                next_line = self.lines[idx + 1]
                if not re.search(r'(Telefone|Cel:|E-?Mail)', next_line):
                    return next_line
        return None
    
    def extract_itens(self):
        """Extrai os itens da proposta com valores"""
        itens = []

        if not self.lines:
            return itens

        # Encontrar in??cio da se????o de itens (v??rios formatos)
        start_patterns = [
            r'It\.\s+Descricao\s+Qt',
            r'CONFIGUR.*VALORES.*ITENS',
            r'ITENS\s+COTAD',
            r'DESCRICAO\s+DO\s+ITEM'
        ]
        idx_inicio = None
        for pattern in start_patterns:
            idx_inicio, _ = self.find_line_with(pattern)
            if idx_inicio is not None:
                break
        if idx_inicio is None:
            return itens

        # Procurar final da se????o de itens
        end_patterns = [
            r'VALOR\s+TOTAL\s+DA\s+PROPOSTA',
            r'TOTAL\s+DA\s+PROPOSTA',
            r'^TOTAL\s+R\$'
        ]
        idx_fim = None
        for pattern in end_patterns:
            idx_fim, _ = self.find_line_with(pattern)
            if idx_fim is not None:
                break
        if idx_fim is None:
            idx_fim = len(self.lines)

        # Fallback: se encontrar um novo cabe??alho numerado depois do in??cio
        heading_pattern = re.compile(r'^\d+(?:\.\d+)?\s+.*$', re.IGNORECASE)
        for j in range(idx_inicio + 1, len(self.lines)):
            if heading_pattern.match(self.lines[j]):
                idx_fim = min(idx_fim, j)
                break

        price_pattern = re.compile(r'R\$\s*([\d.,]+)\s+R\$\s*([\d.,]+)')
        qty_line_pattern = re.compile(r'^(\d{1,3})\s+(\d{1,3})$')
        item_num_pattern = re.compile(r'ITEM\s*(\d{1,3})', re.IGNORECASE)
        header_ignore = re.compile(r'(It\.\s+Descricao|Qt|Unitario|Sub\s*Total|em\s*R\$|\(em\s*R\$\))', re.IGNORECASE)

        descricao_buffer = []
        i = idx_inicio + 1
        fallback_num = 1
        while i < idx_fim:
            line = self.lines[i]

            # Ignorar linhas de cabe??alho da tabela
            if header_ignore.search(line):
                i += 1
                continue

            price_match = price_pattern.search(line)
            if price_match:
                valor_unitario = price_match.group(1)
                valor_total = price_match.group(2)

                descricao_parts = []
                if descricao_buffer:
                    descricao_parts.extend([d for d in descricao_buffer if not header_ignore.search(d)])
                    descricao_buffer = []

                # Parte antes dos valores na pr??pria linha
                parte_antes = line[:price_match.start()].strip()
                if parte_antes:
                    descricao_parts.append(parte_antes)

                descricao = ' '.join(descricao_parts).strip() or None

                numero = None
                quantidade = None

                if descricao:
                    num_match = item_num_pattern.search(descricao)
                    if num_match:
                        numero = num_match.group(1).zfill(2)

                # Tentar pegar quantidade na linha seguinte
                if i + 1 < idx_fim:
                    qty_line = self.lines[i + 1]
                    qty_match = qty_line_pattern.match(qty_line)
                    if qty_match:
                        numero = numero or qty_match.group(1).zfill(2)
                        quantidade = qty_match.group(2)
                        i += 1

                if numero is None:
                    numero = str(fallback_num).zfill(2)
                if quantidade is None:
                    quantidade = '1'

                itens.append({
                    'numero': numero,
                    'descricao': descricao or '',
                    'quantidade': quantidade,
                    'valor_unitario': valor_unitario,
                    'valor_total': valor_total
                })
                fallback_num += 1
                i += 1
                continue

            # Acumular descri????o at?? achar linha com pre??os
            if line and not re.match(r'^\d+\.\d+', line) and not header_ignore.search(line):
                descricao_buffer.append(line)

            i += 1

        return itens

    def extract_valor_total(self):
        """Extrai o valor total da proposta"""
        patterns = [
            r'TOTAL\s+R\$\s+([\d.,]+)',
            r'VALOR\s+TOTAL\s+DA\s+PROPOSTA[:\s]*R?\$?\s*([\d.,]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def extract_all(self):
        """Extrai todos os dados da proposta"""
        if not self.extract_text():
            return None
        
        dados = {
            'id_proposta': self.extract_id_proposta(),
            'data_emissao': self.extract_data_emissao(),
            'validade': self.extract_validade(),
            'razao_social': self.extract_razao_social(),
            'nome_fantasia': self.extract_nome_fantasia(),
            'cnpj': self.extract_cnpj(),
            'telefone': self.extract_telefone(),
            'celular': self.extract_celular(),
            'email': self.extract_email(),
            'pessoa_contato': self.extract_pessoa_contato(),
            'itens': self.extract_itens(),
            'valor_total': self.extract_valor_total()
        }

        # Serviços inclusos e garantia
        servicos = self.extract_servicos()
        dados.update(servicos)
        garantia = self.extract_garantia()
        dados.update(garantia)
        
        # Para compatibilidade com o schema original, pegar o primeiro item
        if dados['itens'] and len(dados['itens']) > 0:
            primeiro_item = dados['itens'][0]
            dados['descricao_item'] = primeiro_item['descricao']
            dados['quantidade'] = primeiro_item['quantidade']
        else:
            dados['descricao_item'] = None
            dados['quantidade'] = None
        
        return dados


def test_extractor():
    """Função de teste"""
    pdf_path = "/home/ubuntu/upload/0012-CooperativadetrabalhomedidodePousoAlegre(UNIMED)-CME-542P-890P(conf.1)-PHB105P-TWE400P-EA34.03-E0201-042-cod050.pdf"
    
    extractor = PropostaExtractor(pdf_path)
    dados = extractor.extract_all()
    
    if dados:
        print("=== DADOS EXTRAÍDOS ===")
        for key, value in dados.items():
            if key != 'itens':
                print(f"{key}: {value}")
        
        print("\n=== ITENS ===")
        for item in dados.get('itens', []):
            print(f"Item {item['numero']}: {item['descricao'][:80]}...")
            print(f"  Quantidade: {item['quantidade']}")
            print(f"  Valor Unitário: R$ {item['valor_unitario']}")
            print(f"  Valor Total: R$ {item['valor_total']}")
            print()
    else:
        print("Erro ao extrair dados")


if __name__ == "__main__":
    test_extractor()
