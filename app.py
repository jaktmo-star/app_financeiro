from datetime import date

import streamlit as st
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import GoogleAuthError

from firebase_service import (
    create_transaction,
    delete_transaction,
    get_firestore_client,
    get_monthly_goal,
    get_transactions,
    set_monthly_goal,
    update_transaction,
)

st.set_page_config(page_title="Finanças Pessoais", page_icon="💰", layout="wide")
st.markdown(
    """
    <style>
    .block-container {max-width: 1200px; padding-top: 1.5rem;}
    @media (max-width: 640px) {
        .block-container {padding: 1rem 1rem 2rem;}
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column;
            align-items: stretch;
            gap: 0.5rem;
        }
        div[data-testid="stHorizontalBlock"] > div {
            width: 100% !important;
            min-width: 100% !important;
        }
        h1 {font-size: 1.8rem !important;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def format_brl(value: float) -> str:
    formatted_value = f"{value:,.2f}".translate(str.maketrans({",": ".", ".": ","}))
    return f"R$ {formatted_value}"

st.title("💰 Finanças Pessoais")
st.caption("Controle simples de receitas e despesas com Firebase Cloud Firestore.")

try:
    db = get_firestore_client()
    transactions = get_transactions(db)
    monthly_goal = get_monthly_goal(db)
except (GoogleAPICallError, GoogleAuthError, ValueError) as error:
    st.error(f"Não foi possível conectar ao Cloud Firestore: {error}")
    st.info(
        "Confira o ID do projeto e configure as credenciais conforme o "
        "README.md. O banco utilizado é o Firestore `(default)`."
    )
    st.stop()

today = date.today()
month_start = today.replace(day=1)
filter_columns = st.columns(2)
with filter_columns[0]:
    start_date = st.date_input(
        "Data inicial",
        value=month_start,
        format="DD/MM/YYYY",
    )
with filter_columns[1]:
    end_date = st.date_input(
        "Data final",
        value=today,
        format="DD/MM/YYYY",
    )
if start_date > end_date:
    st.error("A data inicial não pode ser posterior à data final.")
    st.stop()

dated_transactions = []
invalid_date_count = 0
for item in transactions:
    try:
        transaction_date = date.fromisoformat(item["date"])
    except ValueError:
        invalid_date_count += 1
        continue
    dated_transactions.append((item, transaction_date))
if invalid_date_count:
    st.warning(
        f"{invalid_date_count} lançamento(s) com data inválida foram "
        "ignorados nos totais e no gráfico."
    )

filtered_transactions = [
    item
    for item, transaction_date in dated_transactions
    if start_date <= transaction_date <= end_date
]
income_total = sum(
    item["amount"]
    for item in filtered_transactions
    if item["type"] == "Receita"
)
expense_total = sum(
    item["amount"]
    for item in filtered_transactions
    if item["type"] == "Despesa"
)
balance = income_total - expense_total

income_column, expense_column, balance_column = st.columns(3)
income_column.metric("Receitas", format_brl(income_total))
expense_column.metric("Despesas", format_brl(expense_total))
balance_column.metric("Saldo", format_brl(balance))

st.subheader(f"Meta de despesas — {today.strftime('%m/%Y')}")
current_month_expenses = sum(
    item["amount"]
    for item, transaction_date in dated_transactions
    if item["type"] == "Despesa"
    and transaction_date.year == today.year
    and transaction_date.month == today.month
)
if monthly_goal > 0:
    progress = current_month_expenses / monthly_goal
    st.progress(min(progress, 1.0))
    goal_columns = st.columns(3)
    goal_columns[0].metric("Limite mensal", format_brl(monthly_goal))
    goal_columns[1].metric("Gasto no mês", format_brl(current_month_expenses))
    goal_columns[2].metric(
        "Restante",
        format_brl(monthly_goal - current_month_expenses),
    )
    if progress > 1:
        st.warning("O limite de despesas deste mês foi ultrapassado.")
else:
    st.info("Defina um limite mensal de despesas para acompanhar sua meta.")

with st.form("monthly_goal_form"):
    goal_amount = st.number_input(
        "Limite mensal de despesas (R$)",
        min_value=0.0,
        value=monthly_goal,
        step=100.0,
        format="%.2f",
    )
    goal_submitted = st.form_submit_button("Salvar meta mensal")
if goal_submitted:
    if goal_amount <= 0:
        st.error("Informe um limite mensal maior que zero.")
    else:
        try:
            set_monthly_goal(db, goal_amount)
        except (GoogleAPICallError, GoogleAuthError) as error:
            st.error(f"Não foi possível salvar a meta: {error}")
        else:
            st.success("Meta mensal salva.")
            st.rerun()

st.subheader("Gastos por categoria no período")
category_totals: dict[str, float] = {}
for item in filtered_transactions:
    if item["type"] == "Despesa":
        category = item["category"] or "Sem categoria"
        category_totals[category] = category_totals.get(category, 0) + item["amount"]
if category_totals:
    chart_data = {
        "Categoria": list(category_totals),
        "Gastos (R$)": list(category_totals.values()),
    }
    st.bar_chart(
        chart_data,
        x="Categoria",
        y="Gastos (R$)",
    )
else:
    st.info("Não há despesas no período selecionado para montar o gráfico.")

st.subheader("Lançamentos")
if filtered_transactions:
    st.dataframe(
        [
            {
                "Data": item["date"],
                "Descrição": item["description"],
                "Categoria": item["category"],
                "Tipo": item["type"],
                "Valor (R$)": item["amount"],
            }
            for item in filtered_transactions
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Nenhum lançamento encontrado no período selecionado.")

st.subheader("Adicionar lançamento")
with st.form("create_transaction", clear_on_submit=True):
    description = st.text_input("Descrição")
    category = st.text_input("Categoria", placeholder="Ex.: Moradia, salário")
    transaction_type = st.selectbox("Tipo", ["Despesa", "Receita"])
    amount = st.number_input("Valor (R$)", min_value=0.01, step=1.00, format="%.2f")
    transaction_date = st.date_input("Data", value=date.today())
    submitted = st.form_submit_button("Salvar lançamento", type="primary")

if submitted:
    if not description.strip() or not category.strip():
        st.error("Preencha a descrição e a categoria.")
    else:
        try:
            create_transaction(
                db,
                {
                    "description": description.strip(),
                    "category": category.strip(),
                    "type": transaction_type,
                    "amount": amount,
                    "date": transaction_date.isoformat(),
                },
            )
        except (GoogleAPICallError, GoogleAuthError) as error:
            st.error(f"Não foi possível salvar o lançamento: {error}")
        else:
            st.success("Lançamento salvo.")
            st.rerun()

if transactions:
    st.subheader("Editar ou excluir lançamento")
    transaction_by_id = {item["id"]: item for item in transactions}
    selected_id = st.selectbox(
        "Selecione um lançamento",
        options=list(transaction_by_id),
        format_func=lambda transaction_id: (
            f'{transaction_by_id[transaction_id]["date"]} — '
            f'{transaction_by_id[transaction_id]["description"]} '
            f'({format_brl(transaction_by_id[transaction_id]["amount"])})'
        ),
    )
    selected = transaction_by_id[selected_id]

    with st.form("edit_transaction"):
        edited_description = st.text_input(
            "Descrição", value=selected["description"], key="edit_description"
        )
        edited_category = st.text_input(
            "Categoria", value=selected["category"], key="edit_category"
        )
        edited_type = st.selectbox(
            "Tipo",
            ["Despesa", "Receita"],
            index=["Despesa", "Receita"].index(selected["type"]),
            key="edit_type",
        )
        edited_amount = st.number_input(
            "Valor (R$)",
            min_value=0.01,
            value=max(0.01, selected["amount"]),
            step=1.00,
            format="%.2f",
            key="edit_amount",
        )
        edited_date = st.date_input(
            "Data",
            value=date.fromisoformat(selected["date"]),
            key="edit_date",
        )
        update_submitted = st.form_submit_button("Atualizar lançamento")

    if update_submitted:
        if not edited_description.strip() or not edited_category.strip():
            st.error("Preencha a descrição e a categoria.")
        else:
            try:
                update_transaction(
                    db,
                    selected_id,
                    {
                        "description": edited_description.strip(),
                        "category": edited_category.strip(),
                        "type": edited_type,
                        "amount": edited_amount,
                        "date": edited_date.isoformat(),
                    },
                )
            except (GoogleAPICallError, GoogleAuthError) as error:
                st.error(f"Não foi possível atualizar o lançamento: {error}")
            else:
                st.success("Lançamento atualizado.")
                st.rerun()

    with st.form("delete_transaction"):
        confirm_delete = st.checkbox("Confirmo a exclusão permanente deste lançamento.")
        delete_submitted = st.form_submit_button(
            "Excluir lançamento selecionado", type="secondary"
        )

    if delete_submitted and not confirm_delete:
        st.error("Marque a confirmação antes de excluir.")
    elif delete_submitted:
        try:
            delete_transaction(db, selected_id)
        except (GoogleAPICallError, GoogleAuthError) as error:
            st.error(f"Não foi possível excluir o lançamento: {error}")
        else:
            st.success("Lançamento excluído.")
            st.rerun()
