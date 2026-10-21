# Finanças Pessoais

Aplicação CRUD simples em Python e Streamlit para controlar receitas e despesas
no Cloud Firestore do projeto Firebase. A aplicação usa o banco Firestore
`(default)` e a coleção `transactions`.

## Configurar o Firebase

1. No Console do Firebase, abra o projeto `despesas` e confirme o **ID do
   projeto** em Configurações do projeto. O ID pode não ser igual ao nome
   apresentado no console.
2. Crie ou confirme o banco **Cloud Firestore** com o ID `(default)`.
3. Confirme que a conta de serviço representada em `despesas.json` tem
   permissão de leitura e escrita no Firestore (por exemplo, a função IAM
   `Cloud Datastore User`). Nunca publique ou envie essa chave para o
   repositório.
4. `.streamlit\secrets.toml` já foi preenchido a partir de `despesas.json` no
   formato esperado pelo Streamlit. O arquivo de secrets e o JSON original são
   ignorados pelo Git. Se precisar recriar o arquivo, copie os campos da chave
   JSON para as seções `[firebase]` e `[gcp_service_account]`; nunca publique
   essa chave.

Também é possível autenticar com Application Default Credentials: configure
`GOOGLE_APPLICATION_CREDENTIALS` para apontar para o JSON da conta de serviço e
`FIREBASE_PROJECT_ID` para o ID do projeto. Sem uma configuração explícita, o
app usa o `project_id` das credenciais ou, por último, `despesas`.

## Acesso ao app

O app não implementa login próprio. No Cloud Run, mantenha o serviço privado e
autorize as contas Google desejadas concedendo a elas a função **Cloud Run
Invoker** (`roles/run.invoker`). A identidade de execução do Cloud Run deve ter
permissão mínima de leitura e escrita no Firestore (por exemplo, `Cloud
Datastore User`). Assim, o IAM do Google controla quem abre o serviço e a conta
de execução controla o acesso ao banco; não é necessária uma tabela de usuários
nem uma configuração `[auth]` no `secrets.toml`.

Para abrir o endereço do serviço em um navegador comum, configure uma forma
compatível de acesso interativo, como Identity-Aware Proxy (IAP), ou use um
cliente autenticado que envie um token de identidade. Apenas tornar o serviço
privado por IAM não adiciona automaticamente um formulário de login ao app.
Executar `streamlit run app.py` localmente não passa pelo IAM do Cloud Run; use
somente em uma máquina confiável.

No Cloud Run, prefira Application Default Credentials da identidade de execução
em vez de distribuir uma chave privada. Guarde secrets necessários em um secret
do Google Secret Manager e monte-os no caminho `.streamlit\secrets.toml` relativo
à pasta de execução do app; não inclua credenciais na imagem ou no repositório.

## Melhorias

- Filtros de data inicial e final para lançamentos, totais e gráfico.
- Limite de despesas mensal armazenado no Firestore, com acompanhamento do gasto.
- Gráfico de despesas por categoria no período selecionado.
- Layout que empilha controles e indicadores em telas estreitas.
- Acesso controlado pelo IAM do Cloud Run.

## Executar no Windows

No PowerShell, a partir desta pasta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Funcionalidades

- Cadastrar receitas e despesas com descrição, categoria, valor e data.
- Consultar lançamentos e totais de receitas, despesas e saldo por período.
- Editar ou excluir um lançamento existente.
