# 🤖 RPA - Horários dos Professores

Este é um script de automação (RPA) desenvolvido em Python para gerenciar, extrair e consolidar dados de horários e frequências de professores diretamente no **Google Sheets**. O script processa os dados e gera automaticamente uma aba de "Resumo" na planilha, organizando a carga horária e a situação de cada professor.

## 🚀 Funcionalidades

- Conecta-se automaticamente ao Google Sheets via API.
- Processa a lista de professores e suas respectivas cargas horárias.
- Cria (ou atualiza) uma aba chamada **Resumo**, posicionando-a como a primeira aba da planilha.
- Trata erros de nomenclatura e evita duplicação de abas usando sistema de busca cega (case-insensitive).

## 📋 Pré-requisitos

Antes de começar, você precisará ter instalado em sua máquina:

* [Python 3.7+](https://www.python.org/downloads/)
* Gerenciador de pacotes `pip`
* Uma conta no Google Cloud Platform (para gerar as credenciais da API)

## ⚙️ Configuração da API do Google

Para que o script consiga ler e editar a sua planilha do Google, você precisa criar credenciais de acesso:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto.
3. Vá em **APIs e Serviços > Biblioteca** e ative duas APIs:
   * **Google Drive API**
   * **Google Sheets API**
4. Vá em **Credenciais > Criar Credenciais > Conta de Serviço** (Service Account).
5. Preencha os dados, conclua a criação e, na tela da conta de serviço criada, vá na aba **Chaves** > **Adicionar Chave** > **Criar nova chave** (formato JSON).
6. Faça o download do arquivo `.json` gerado.
7. Renomeie esse arquivo para `credentials.json` e coloque-o na mesma pasta deste script.
8. **IMPORTANTE:** Abra a sua planilha no Google Sheets, clique em "Compartilhar" e adicione o e-mail da conta de serviço (o e-mail que termina com `iam.gserviceaccount.com`) como **Editor**.

## 🛠️ Instalação

1. Clone este repositório para a sua máquina local:
   ```bash
   git clone [https://github.com/ldsampaio/RPAfrequencias.git](https://github.com/ldsampaio/RPAfrequencias.git)
   cd RPAfrequencias

(Opcional, mas recomendado) Crie um ambiente virtual:

Bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
Instale as dependências necessárias:

Bash
pip install -r requirements.txt
(Se você não tiver um arquivo requirements.txt, instale as bibliotecas manualmente digitando: pip install gspread google-auth)

💻 Como executar
Após ter configurado as credenciais e instalado as dependências, certifique-se de que o arquivo RPAhorariosProfessores.py aponta para o nome ou ID correto da sua planilha.

Para rodar a automação, execute no terminal:

Bash
python RPAhorariosProfessores.py
Você verá no terminal os logs de execução (ex: "Gerando aba de Resumo de Carga Horária...", "Aba 'Resumo' já existe. Limpando dados antigos...").

📁 Estrutura do Projeto

RPAfrequencias/
├── RPAhorariosProfessores.py  # Script principal da automação
├── credentials.json           # Chave de API do Google (NÃO COMITE ESTE ARQUIVO)
├── requirements.txt           # Lista de dependências do Python
└── README.md                  # Este arquivo de documentação
