from playwright.sync_api import sync_playwright
import json
from pathlib import Path
import re
import gspread
from google.oauth2.service_account import Credentials
import time

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
# ID da sua planilha Google atualizado
SPREADSHEET_ID = "ID_DA_PLANILHA_DO_GOOGLE_SHEETS" 
CREDENCIAIS_GOOGLE = "google_credentials.json"

def carregar_credenciais_utfpr():
    diretorio_script = Path(__file__).parent
    arquivo_credenciais = diretorio_script / "credenciais.json"
    
    if not arquivo_credenciais.exists():
        print(f"Erro: Arquivo de credenciais da UTFPR não encontrado em {arquivo_credenciais}")
        return None
    
    try:
        with open(arquivo_credenciais, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler o arquivo JSON da UTFPR: {e}")
        return None

def autenticar_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(CREDENCIAIS_GOOGLE, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SPREADSHEET_ID)
    except Exception as e:
        print(f"Erro ao autenticar no Google Sheets. Verifique o arquivo '{CREDENCIAIS_GOOGLE}' e o ID da planilha.")
        print(f"Detalhe: {e}")
        return None

def limpar_nome_para_aba(nome):
    nome_limpo = re.sub(r'[\\/*?:\[\]]', '', nome)
    return nome_limpo[:31].strip()

def extrair_grade_horarios(frame_real):
    """Extrai os dados da grade horária de forma estruturada"""
    try:
        frame_real.locator("table.horarios").wait_for(state="visible", timeout=10000)
        tabela_html = frame_real.locator("table.horarios").inner_html()
        
        dados = {'manha': {}, 'tarde': {}, 'noite': {}}
        turno_map = {'m': 'manha', 't': 'tarde', 'n': 'noite'}
        
        pattern = r'id="(dv_\d[mtn]\d+)"[^>]*>(.*?)</td>'
        matches = re.findall(pattern, tabela_html, re.DOTALL | re.IGNORECASE)
        
        for cell_id, cell_html in matches:
            match_id = re.match(r'dv_(\d)([mtn])(\d+)', cell_id)
            if match_id:
                dia = int(match_id.group(1))
                turno_letra = match_id.group(2)
                numero = match_id.group(3)
                turno = turno_map.get(turno_letra)
                
                if turno:
                    texto = re.sub(r'<[^>]+>', ' ', cell_html).strip()
                    texto = re.sub(r'\s+', ' ', texto).replace('&nbsp;', '').strip()
                    horario_key = f"{turno_letra}{numero}"
                    
                    if horario_key not in dados[turno]:
                        dados[turno][horario_key] = {}
                    
                    if texto and texto != '':
                        dados[turno][horario_key][dia] = texto
        return dados
    except Exception as e:
        print(f"Erro ao extrair grade: {e}")
        return None

def gerar_linhas_grade(dados_grade):
    """Gera a matriz de dados (lista de listas) para enviar ao Google Sheets"""
    linhas = []
    
    # Linha 1: Cabeçalho
    linhas.append(['', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Aulas', ''])
    
    # Estrutura de horários
    estrutura = [
        ('Manhã', 'titulo', None),
        ('M1\n07:30', 'horario', 'm1'), ('M2\n08:20', 'horario', 'm2'), ('M3\n09:10', 'horario', 'm3'),
        ('Intervalo Manhã [ 20 min. ] - 10:00', 'intervalo', None),
        ('M4\n10:20', 'horario', 'm4'), ('M5\n11:10', 'horario', 'm5'), ('M6\n12:00', 'horario', 'm6'),
        ('Tarde', 'titulo', None),
        ('T1\n13:00', 'horario', 't1'), ('T2\n13:50', 'horario', 't2'), ('T3\n14:40', 'horario', 't3'),
        ('Intervalo Tarde [ 20 min. ] - 15:30', 'intervalo', None),
        ('T4\n15:50', 'horario', 't4'), ('T5\n16:40', 'horario', 't5'), ('T6\n17:50', 'horario', 't6'),
        ('Noite', 'titulo', None),
        ('N1\n18:40', 'horario', 'n1'), ('N2\n19:30', 'horario', 'n2'), ('N3\n20:20', 'horario', 'n3'),
        ('Intervalo Noite [ 10 min. ] - 21:10', 'intervalo', None),
        ('N4\n21:20', 'horario', 'n4'), ('N5\n22:10', 'horario', 'n5'),
        ('', 'vazio', None), # Linha 25
        ('Total de Aulas', 'total', None), # Linha 26
        ('Dias de Aula', 'dias', None) # Linha 27 
    ]
    
    for nome_linha, tipo, chave in estrutura:
        if tipo == 'titulo' or tipo == 'intervalo' or tipo == 'vazio':
            linha = [nome_linha] + [''] * 8
        elif tipo == 'total':
            linha = [''] * 6 + ['Total de Aulas', '=SOMA(H3:H24)', '']
        elif tipo == 'dias':
            formula_dias = '=SE(CONT.SE(B3:B24;"?*")>0;1;0) + SE(CONT.SE(C3:C24;"?*")>0;1;0) + SE(CONT.SE(D3:D24;"?*")>0;1;0) + SE(CONT.SE(E3:E24;"?*")>0;1;0) + SE(CONT.SE(F3:F24;"?*")>0;1;0) + SE(CONT.SE(G3:G24;"?*")>0;1;0)'
            linha = [''] * 6 + ['Dias de Aula', formula_dias, '']
        else:
            turno = chave[0]
            dados_turno = dados_grade.get(f"{turno}anha" if turno == 'm' else f"{turno}arde" if turno == 't' else 'noite', {})
            dados_horario = dados_turno.get(chave, {})
            
            celulas_dias = [str(dados_horario.get(dia, '')) for dia in range(2, 8)]
            num_linha = len(linhas) + 1
            
            formula_contse = f'=CONT.SE(B{num_linha}:G{num_linha}; "*")'
            linha = [nome_linha] + celulas_dias + [formula_contse, '']
            
        linhas.append(linha)
        
    return linhas

def formatar_aba_google(worksheet, spreadsheet):
    """Aplica formatação (mesclagem, cores, negrito) OTIMIZADA em Lote"""
    sheet_id = worksheet.id
    
    # 1. Agrupa TODAS as mesclagens (Merge) em 1 ÚNICA chamada de API
    merge_requests = []
    linhas_merge = [1, 5, 9, 13, 17, 21] # Índices base 0 para as linhas 2, 6, 10, 14, 18, 22
    for l in linhas_merge:
        merge_requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": l,
                    "endRowIndex": l + 1,
                    "startColumnIndex": 0, # Coluna A
                    "endColumnIndex": 7    # Coluna G (inclusiva, pois o final é exclusivo)
                },
                "mergeType": "MERGE_ALL"
            }
        })
    
    if merge_requests:
        spreadsheet.batch_update({"requests": merge_requests})

    # 2. Agrupa TODAS as formatações visuais em 1 ÚNICA chamada de API
    formatos = [
        {"range": "A1:I1", "format": {"textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}, "backgroundColor": {"red": 0.266, "green": 0.447, "blue": 0.764}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}},
        {"range": "G26:H27", "format": {"textFormat": {"bold": True}, "verticalAlignment": "MIDDLE"}},
        {"range": "G26:H26", "format": {"textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 0, "blue": 0}}}},
        {"range": "G26:G27", "format": {"horizontalAlignment": "RIGHT"}},
        {"range": "H26:H27", "format": {"horizontalAlignment": "CENTER"}},
        {"range": "A3:I25", "format": {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP"}}
    ]
    
    for rng in ['A2:G2', 'A6:G6', 'A10:G10', 'A14:G14', 'A18:G18', 'A22:G22']:
        formatos.append({"range": rng, "format": {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}})

    # Aplica todas as formatações de uma vez só
    worksheet.batch_format(formatos)

def gerar_aba_resumo(spreadsheet, lista_professores):
    """Gera a aba de Resumo e move ela para a primeira posição da planilha"""
    print("\nGerando aba de Resumo de Carga Horária...")
    sheet_name = "Resumo"
    worksheet = None
    
    # 1. Busca blindada: ignora maiúsculas, minúsculas e espaços
    for sheet in spreadsheet.worksheets():
        if sheet.title.lower().strip() == sheet_name.lower().strip():
            worksheet = sheet
            break
            
    # 2. Decide se limpa a existente ou tenta criar uma nova
    if worksheet:
        print("  -> Aba 'Resumo' já existe. Limpando dados antigos...")
        worksheet.clear()
    else:
        print("  -> Aba 'Resumo' não encontrada. Criando nova...")
        try:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=max(100, len(lista_professores)+10), cols=15)
        except gspread.exceptions.APIError as e:
            # 3. Trava de segurança máxima: se o Google AINDA disser que existe, nós forçamos a abertura dela.
            if 'already exists' in str(e).lower():
                worksheet = spreadsheet.worksheet(sheet_name)
                worksheet.clear()
            else:
                raise e # Se for outro erro de API, o script para e mostra
        
    # Move a aba para a primeira posição
    try:
        body_move = {
            "requests": [{"updateSheetProperties": {"properties": {"sheetId": worksheet.id, "index": 0}, "fields": "index"}}]
        }
        spreadsheet.batch_update(body_move)
    except Exception as e:
        print(f"Aviso: Não foi possível mover a aba para a primeira posição automaticamente: {e}")

    cabecalho = [
        "Nome", "Tipo", "Métrica", "Total de Aulas", "EaD", "Presencial", 
        "Situação", "Dias", "Quantidade de disciplinas", "Turmas", "Disciplinas EaD"
    ]
    linhas = [cabecalho]

    for i, dados_prof in enumerate(lista_professores):
        row_idx = i + 2
        nome_completo = dados_prof['nome_completo']
        nome_aba = dados_prof['nome_aba'].replace("'", "''") 
        
        form_metrica = f'=SE(B{row_idx}="Substituto"; 16; SE(B{row_idx}="Efetivo Normal"; 12; SE(B{row_idx}="Perm. Programa"; 8; SE(B{row_idx}="Coordenador Prog"; 6; SE(B{row_idx}="Coordenador"; 6; SE(B{row_idx}="Chefe"; 6; SE(B{row_idx}="Diretor"; 0; SE(B{row_idx}="Afastado"; 0; ""))))))))'
        form_total_aulas = f"='{nome_aba}'!H26"
        form_presencial = f"=D{row_idx}"
        form_situacao = f'=SE(C{row_idx}=""; ""; D{row_idx} - C{row_idx})'
        form_dias = f"='{nome_aba}'!H27"
        
        linha = [
            nome_completo,    
            "",               
            form_metrica,     
            form_total_aulas, 
            "",               
            form_presencial,  
            form_situacao,    
            form_dias,        
            "", "", ""        
        ]
        linhas.append(linha)

    worksheet.update(values=linhas, range_name=f'A1:K{len(linhas)}', value_input_option='USER_ENTERED')
    
    worksheet.format('A1:K1', {
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
        "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"
    })
    worksheet.format(f'B2:K{len(linhas)}', {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
    
    try:
        body_validation = {
            "requests": [{
                "setDataValidation": {
                    "range": {"sheetId": worksheet.id, "startRowIndex": 1, "startColumnIndex": 1, "endColumnIndex": 2},
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_LIST",
                            "values": [{"userEnteredValue": v} for v in ["Substituto", "Efetivo Normal", "Perm. Programa", "Coordenador Prog", "Coordenador", "Chefe", "Diretor", "Afastado"]]
                        },
                        "showCustomUi": True, "strict": True
                    }
                }
            }]
        }
        spreadsheet.batch_update(body_validation)
    except Exception as e:
        print(f"Aviso: Não foi possível criar as listas suspensas (dropdown) no Resumo: {e}")
        
    print("-> Aba Resumo concluída com sucesso!")


def main():
    credenciais_utfpr = carregar_credenciais_utfpr()
    if not credenciais_utfpr: return
    
    spreadsheet = autenticar_google_sheets()
    if not spreadsheet: return

    usuario = credenciais_utfpr.get("usuario")
    senha = credenciais_utfpr.get("senha")
    
    if not usuario or not senha:
        print("Erro: As credenciais da UTFPR devem conter 'usuario' e 'senha'")
        return

    professores_extraidos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Acessando o portal de sistemas da UTFPR...")
        page.goto("https://sistemas2.utfpr.edu.br/")
        
        print("Realizando login...")
        page.wait_for_selector("input[formcontrolname='username']")
        page.fill("input[formcontrolname='username']", usuario)
        page.fill("input[formcontrolname='password']", senha)
        page.get_by_role("button", name="Entrar").click()
        
        page.wait_for_url("**/home/sistemas-corporativos**")
        print("Login realizado com sucesso!")
        
        try:
            botao_campus = page.get_by_role("button", name="Cornélio Procópio")
            botao_campus.wait_for(state="visible", timeout=3000)
            botao_campus.click()
            page.wait_for_timeout(1000)
        except:
            pass
        
        print("Navegando: Acadêmico -> Horários -> Consultas -> Mapa De Professor...")
        page.get_by_text("Acadêmico").click()
        page.get_by_text("Horários", exact=True).click()
        page.get_by_text("Consultas").click()
        page.get_by_text("Mapa De Professor").click()
        
        print("Aguardando carregamento do Mapa de Professor...")
        page.wait_for_selector("iframe[name='frameUrl']", timeout=30000)
        page.wait_for_timeout(2000)
        
        frame_real = None
        for f in page.frames:
            if f.name == 'frameUrl' or 'frameUrl' in f.url:
                frame_real = f
                break
        
        if not frame_real:
            print("Erro: Não foi possível localizar o iframe frameUrl")
            input("\nPressione ENTER para fechar o navegador...")
            browser.close()
            return
        
        print("Preenchendo filtros: Período 2026/2 e Depto DACOM...")
        try:
            frame_real.fill("input#pi_periodoanualanonr", "2026")
            frame_real.fill("input#pr_periodoanualseqnr", "2")
            frame_real.select_option("select#pm_deptoacadnr", value="2569")
            frame_real.check("input#p_sitcodnr_1")
            
            print("Aguardando carregamento da lista de professores...")
            frame_real.locator("select#pm_profmnemcodnr option").nth(1).wait_for(state="attached", timeout=15000)
            print("Lista de professores carregada com sucesso!\n")
        except Exception as e:
            print(f"Erro ao preencher filtros: {e}")
            input("\nPressione ENTER para fechar o navegador...")
            browser.close()
            return

        options = frame_real.locator("select#pm_profmnemcodnr option").all()
        total_professores = len(options) - 1
        print(f"Total de professores encontrados: {total_professores}\n")
        
        for i in range(1, len(options)):
            prof_nome = options[i].inner_text().strip()
            prof_valor = options[i].get_attribute("value")
            
            if prof_valor == "-1":
                continue
                
            sheet_name = limpar_nome_para_aba(prof_nome)
            print(f"[{i}/{total_professores}] Processando: {prof_nome}")
            
            try:
                frame_real.select_option("select#pm_profmnemcodnr", value=prof_valor)
                frame_real.click("input#bt_pesquisar")
                
                frame_real.locator("table.horarios").wait_for(state="visible", timeout=10000)
                page.wait_for_timeout(1500)
                
                dados_grade = extrair_grade_horarios(frame_real)
                
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                    worksheet.clear() 
                except gspread.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=30, cols=10)
                
                if not dados_grade:
                    print(f"  -> Aviso: Nenhum horário encontrado. Criando aba em branco.")
                    worksheet.update(values=[['Nenhum horário registrado para este período.']], range_name='A1', value_input_option='USER_ENTERED')
                else:
                    print(f"  -> Formatando e enviando dados para a aba '{sheet_name}'...")
                    linhas = gerar_linhas_grade(dados_grade)
                    
                    # 1 ÚNICA chamada para inserir todos os dados:
                    worksheet.update(values=linhas, range_name='A1:I27', value_input_option='USER_ENTERED')
                    
                    # Apenas 2 chamadas de API (Uma para merge, outra para formato visual):
                    formatar_aba_google(worksheet, spreadsheet)
                    print(f"  -> Sucesso! Dados salvos.")
                    
                professores_extraidos.append({
                    'nome_completo': prof_nome,
                    'nome_aba': sheet_name
                })
                
            except Exception as e:
                print(f"  -> ERRO ao processar {prof_nome}: {e}")
            
            # Delay exato: 4 segundos geram no máx. 15 requisições de professores por minuto (60 requisições totais de API)
            print("  -> Aguardando 4 segundos para evitar limite da API (Quota Exceeded)...\n")
            time.sleep(4)
        
        if professores_extraidos:
            gerar_aba_resumo(spreadsheet, professores_extraidos)

        print("\n" + "="*60)
        print("PROCESSO CONCLUÍDO COM SUCESSO!")
        print(f"Verifique sua planilha: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print("="*60)
        
        input("\nPressione ENTER para fechar o navegador...")
        browser.close()

if __name__ == "__main__":
    main()
