import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Finance Automation Suite",
    layout="wide",
    page_icon="📊"
)
# Custom styling to improve layout and spacing
st.markdown(
    """
    <style>
    /* Hide Streamlit menu and footer for a cleaner app */
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    /* Narrow the sidebar and style headers */
    .css-1d391kg {padding-top: 0rem;} 
    .stMarkdown h1, .stMarkdown h2 {color: #0f172a}
    .app-header {display:flex; align-items:center; justify-content:space-between}
    .card {background: #f8fafc; padding: 12px; border-radius: 8px}
    </style>
    """,
    unsafe_allow_html=True,
)
# =====================================================
# LOGIN SYSTEM (ADDED ONLY THIS PART)
# =====================================================

def check_login(username, password):
    users = {
        "admin": "12345",
        "bco": "finance2026"
    }
    return users.get(username) == password


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


def login_page():
    st.title("🔐 Finance Automation Login")
    st.markdown("### Please login to continue")

    username = st.text_input("User ID")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_login(username, password):
            st.session_state.logged_in = True
            st.success("Login Successful ✅")
            st.rerun()
        else:
            st.error("Invalid ID or Password ❌")


# STOP APP IF NOT LOGGED IN
if not st.session_state.logged_in:
    login_page()
    st.stop()

# OPTIONAL LOGOUT BUTTON
st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False}))

# =====================================================
# COMMON FUNCTIONS
# =====================================================

def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            t = page.extract_text(layout=True)
            if t:
                text += t + "\n"
    return text


def normalize_text(text):
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def clean_amount(value):
    if not value:
        return ""
    value = re.sub(r"[^\d.]", "", value)
    return value.strip()


def get_value(label, text):
    pattern = rf"{re.escape(label)}\s*[:\-]?\s*([^\n]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_last_number_from_row(pattern, text):
    row = re.search(pattern, text, re.IGNORECASE)
    if row:
        numbers = re.findall(r"[\d,]+\.?\d*", row.group(0))
        if numbers:
            return clean_amount(numbers[-1])
    return ""

# ✅ NEW FUNCTION ADDED FOR COMPANY NAME FIX
def extract_establishment_details(text):

    text = re.sub(r"\s+", " ", text)

    pattern = r"Establishment Code\s*&\s*Name\s+([A-Z0-9]+)\s+(.*?)(?=\s+Dues\s+for\s+the\s+wage\s+month|\s+Address)"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        establishment_code = match.group(1).strip()
        company_name = match.group(2).strip()
    else:
        establishment_code = ""
        company_name = ""

    return establishment_code, company_name


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("📊 Finance Suite")

module = st.sidebar.radio(
    "Select Module",
    ["Dashboard", "Professional Tax (PT)", "Provident Fund (PF)", "ESIC","Bank Statement"]
)

# =====================================================
# DASHBOARD
# =====================================================

if module == "Dashboard":

    header = st.container()
    with header:
        left, right = st.columns([3, 1])
        with left:
            st.title("📊 Finance Automation Suite")
            st.markdown("#### PDF to Excel Compliance Automation Platform — quick tools for PT / PF / ESIC / Bank")
        with right:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.rerun()

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("Modules", "PT · PF · ESIC · Bank")
    col2.metric("Processed Files", "—")
    col3.metric("Automation", "PDF → Excel")

    st.info("Use the sidebar to select a module. Tip: you can upload multiple PDFs at once.")


# =====================================================
# PROFESSIONAL TAX (PT)
# =====================================================

elif module == "Professional Tax (PT)":

    st.title("📁 Professional Tax (PT) Consolidation")

    files = st.file_uploader(
        "Upload PT Treasury PDFs",
        type=["pdf"],
        accept_multiple_files=True
    )

    if files:

        progress = st.progress(0)
        data_list = []

        for i, file in enumerate(files):

            try:
                text = read_pdf(file)

                tin = re.search(r"Registration\s*No\.?\s*(\d{8,15})", text)
                tin = tin.group(1) if tin else ""

                dealer = re.search(r"Depositor/Dealer Name\s*(.*)", text)
                dealer = dealer.group(1).strip() if dealer else ""

                urn = re.search(r"(MPTURN\d+)", text)
                urn = urn.group(1) if urn else ""

                crn = re.search(r"(MPT\d+)", text)
                crn = crn.group(1) if crn else ""

                amount = re.search(r"Total\s*Amount.*?([\d,]+\.\d+)", text)
                amount = clean_amount(amount.group(1)) if amount else ""

                data_list.append({
                    "TIN": tin,
                    "Dealer Name": dealer,
                    "URN": urn,
                    "CRN": crn,
                    "Total Amount": amount,
                    "Source File": file.name
                })

            except Exception as e:
                st.error(f"Error processing {file.name} → {e}")

            progress.progress((i + 1) / len(files))

        df = pd.DataFrame(data_list)

        if not df.empty:

            df["Total Amount"] = pd.to_numeric(df["Total Amount"], errors="coerce")

            total_amount = df["Total Amount"].sum()
            files_processed = df["Source File"].nunique()

            cols_top = st.columns([2, 2, 1])
            cols_top[0].metric("Total PT Amount", f"₹ {total_amount:,.2f}")
            cols_top[1].metric("Files Processed", files_processed)
            cols_top[2].write(" ")

            with st.expander("PT Report Preview (click to expand)", expanded=True):
                st.dataframe(df, use_container_width=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="PT Report")

            st.download_button(
                "Download PT Report",
                output.getvalue(),
                "PT_Consolidated_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# =====================================================
# PROVIDENT FUND (PF)
# =====================================================

elif module == "Provident Fund (PF)":

    st.title("📁 Provident Fund (PF) Automation")

    pf_section = st.sidebar.radio(
        "PF Sections",
        ["Combined Challan", "Payment Receipt"]
    )

    # Combined Challan logic (UNCHANGED)
    if pf_section == "Combined Challan":

        uploaded_files = st.file_uploader(
            "Upload Combined Challan PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            key="combined_pf"
        )

        if uploaded_files:

            progress = st.progress(0)
            records = []

            for i, file in enumerate(uploaded_files):

                try:
                    text = read_pdf(file)

                    trrn = get_value("TRRN", text)

                    est_code, company_name = extract_establishment_details(text)

                    wage_month = re.search(
                        r"Dues for the wage month of\s+([A-Za-z]+\s+\d{4})",
                        text
                    )
                    wage_month = wage_month.group(1) if wage_month else ""

                    admin = extract_last_number_from_row(
                        r"Administration Charges.*",
                        text
                    )

                    employer = extract_last_number_from_row(
                        r"Employer's Share Of.*",
                        text
                    )

                    employee = extract_last_number_from_row(
                        r"Employee's Share Of.*",
                        text
                    )

                    total = re.search(r"Grand Total.*?([\d,]+)", text)
                    total = clean_amount(total.group(1)) if total else ""

                    records.append({
                        "TRRN": trrn,
                        "Establishment Code": est_code,
                        "Company Name": company_name,
                        "Wage Month": wage_month,
                        "Employee Share": employee,
                        "Employer Share": employer,
                        "Admin Charges": admin,
                        "Grand Total (PDF)": total,
                        "Source File": file.name
                    })

                except Exception as e:
                    st.error(f"Error processing {file.name} → {e}")

                progress.progress((i + 1) / len(uploaded_files))

            df = pd.DataFrame(records)

            if not df.empty:

                numeric_cols = [
                    "Employee Share",
                    "Employer Share",
                    "Admin Charges",
                    "Grand Total (PDF)"
                ]

                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

                df["Calculated Total"] = (
                    df["Employee Share"].fillna(0) +
                    df["Employer Share"].fillna(0) +
                    df["Admin Charges"].fillna(0)
                )

                df["Mismatch"] = df["Calculated Total"] != df["Grand Total (PDF)"]

                st.dataframe(df, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="PF Combined")

                st.download_button(
                    "Download Combined PF Report",
                    data=output.getvalue(),
                    file_name="PF_Combined_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    # Payment Receipt logic (UNCHANGED + normalization)
    elif pf_section == "Payment Receipt":

        receipt_files = st.file_uploader(
            "Upload Payment Confirmation Receipt PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            key="receipt_pf"
        )

        if receipt_files:

            progress = st.progress(0)
            receipt_records = []

            for i, file in enumerate(receipt_files):

                try:
                    text = read_pdf(file)
                    text = normalize_text(text)

                    record = {
                        "TRRN No": get_value("TRRN No", text),
                        "Challan Status": get_value("Challan Status", text),
                        "Challan Generated On": get_value("Challan Generated On", text),
                        "Establishment ID": get_value("Establishment ID", text),
                        "Establishment Name": get_value("Establishment Name", text),
                        "Challan Type": get_value("Challan Type", text),
                        "Total Members": get_value("Total Members", text),
                        "Wage Month": get_value("Wage Month", text),
                        "Total Amount (Rs)": clean_amount(get_value("Total Amount (Rs)", text)),
                        "Account-1 Amount": clean_amount(get_value("Account-1 Amount (Rs)", text)),
                        "Account-2 Amount": clean_amount(get_value("Account-2 Amount (Rs)", text)),
                        "Account-10 Amount": clean_amount(get_value("Account-10 Amount (Rs)", text)),
                        "Account-21 Amount": clean_amount(get_value("Account-21 Amount (Rs)", text)),
                        "Account-22 Amount": clean_amount(get_value("Account-22 Amount (Rs)", text)),
                        "Payment Confirmation Bank": get_value("Payment Confirmation Bank", text),
                        "CRN": get_value("CRN", text),
                        "Payment Date": get_value("Payment Date", text),
                        "Payment Confirmation Date": get_value("Payment Confirmation Date", text),
                        "Total PMRPY Benefit": clean_amount(get_value("Total PMRPY Benefit", text)),
                        "Source File": file.name
                    }

                    receipt_records.append(record)

                except Exception as e:
                    st.error(f"Error processing {file.name} → {e}")

                progress.progress((i + 1) / len(receipt_files))

            receipt_df = pd.DataFrame(receipt_records)

            if not receipt_df.empty:

                numeric_cols = [
                    "Total Amount (Rs)",
                    "Account-1 Amount",
                    "Account-2 Amount",
                    "Account-10 Amount",
                    "Account-21 Amount",
                    "Account-22 Amount",
                    "Total PMRPY Benefit"
                ]

                for col in numeric_cols:
                    receipt_df[col] = pd.to_numeric(receipt_df[col], errors="coerce")

                receipt_df["Calculated Total"] = (
                    receipt_df["Account-1 Amount"].fillna(0) +
                    receipt_df["Account-2 Amount"].fillna(0) +
                    receipt_df["Account-10 Amount"].fillna(0) +
                    receipt_df["Account-21 Amount"].fillna(0) +
                    receipt_df["Account-22 Amount"].fillna(0)
                )

                receipt_df["Mismatch"] = (
                    receipt_df["Calculated Total"] != receipt_df["Total Amount (Rs)"]
                )

                st.dataframe(receipt_df, use_container_width=True)

                st.metric(
                    "Total Amount Paid",
                    f"₹ {receipt_df['Total Amount (Rs)'].sum():,.2f}"
                )

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    receipt_df.to_excel(writer, index=False, sheet_name="PF Receipt")

                st.download_button(
                    "Download Payment Receipt Report",
                    data=output.getvalue(),
                    file_name="PF_Payment_Receipt_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


# =====================================================
# ESIC MODULE
# =====================================================

elif module == "ESIC":

    st.title("📁 ESIC Automation")

    esic_files = st.file_uploader(
        "Upload ESIC Challan PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="esic_upload"
    )

    if esic_files:

        progress = st.progress(0)
        esic_records = []

        for i, file in enumerate(esic_files):

            try:
                text = read_pdf(file)
                text = normalize_text(text)

                record = {
                    "Transaction Status": get_value("Transaction status", text),
                    "Employer's Code No": get_value("Employer's Code No", text),
                    "Employer's Name": get_value("Employer's Name", text),
                    "Challan Period": get_value("Challan Period", text),
                    "Challan Number": get_value("Challan Number", text),
                    "Challan Created Date": get_value("Challan Created Date", text),
                    "Challan Submitted Date": get_value("Challan Submitted Date", text),
                    "Amount Paid": clean_amount(get_value("Amount Paid", text)),
                    "Transaction Number": get_value("Transaction Number", text),
                    "Source File": file.name
                }

                esic_records.append(record)

            except Exception as e:
                st.error(f"Error processing {file.name} → {e}")

            progress.progress((i + 1) / len(esic_files))

        esic_df = pd.DataFrame(esic_records)

        if not esic_df.empty:

            esic_df["Amount Paid"] = pd.to_numeric(
                esic_df["Amount Paid"],
                errors="coerce"
            )

            st.dataframe(esic_df, use_container_width=True)

            st.metric(
                "Total ESIC Amount Paid",
                f"₹ {esic_df['Amount Paid'].sum():,.2f}"
            )

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                esic_df.to_excel(writer, index=False, sheet_name="ESIC Report")

            st.download_button(
                "Download ESIC Report",
                data=output.getvalue(),
                file_name="ESIC_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
# =====================================================
# BANK STATEMENT MODULE
# =====================================================

elif module == "Bank Statement":

    st.title("🏦 Universal Bank Statement Engine (All Banks + BOA Fixed)")

    bank_files = st.file_uploader(
        "Upload Bank Statement PDFs",
        type=["pdf"],
        accept_multiple_files=True
    )

    # --------------------------------------------------
    # Helper Functions
    # --------------------------------------------------

    def split_dr_cr(value):
        if not value:
            return "", ""
        value = str(value).replace(",", "").strip()
        if value.upper().endswith("DR"):
            return value[:-2], ""
        elif value.upper().endswith("CR"):
            return "", value[:-2]
        return "", ""

    def detect_bank(text):
        text = text.lower()
        if "bank of america" in text:
            return "BANK OF AMERICA"
        elif "state bank of india" in text:
            return "SBI"
        elif "hdfc bank" in text:
            return "HDFC"
        elif "icici bank" in text:
            return "ICICI"
        elif "axis bank" in text:
            return "AXIS"
        elif "kotak" in text:
            return "KOTAK"
        elif "punjab national bank" in text:
            return "PNB"
        return "UNKNOWN"

    def extract_account_details(text, file_name):

        acc_no = re.search(r"ACCOUNT NUMBER\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
        currency = re.search(r"Currency\s*[:\-]?\s*(\w+)", text, re.IGNORECASE)
        stmt_date = re.search(r"(Statement Date|This Statement Date)\s*[:\-]?\s*(\w+)", text, re.IGNORECASE)
        name = re.search(r"(Account Name|Customer Name)\s*[:\-]?\s*(.*)", text, re.IGNORECASE)

        return {
            "Bank Name": detect_bank(text),
            "Account Holder": name.group(2).strip() if name else "",
            "Account Number": acc_no.group(1) if acc_no else "",
            "Currency": currency.group(1) if currency else "",
            "Statement Date": stmt_date.group(2) if stmt_date else "",
            "Source File": file_name
        }

    # --------------------------------------------------
    # MAIN PROCESSING
    # --------------------------------------------------

    if bank_files:

        all_transactions = []
        account_summary = []
        progress = st.progress(0)

        for i, file in enumerate(bank_files):

            try:
                full_text = read_pdf(file)
                bank_name = detect_bank(full_text)
                account_info = extract_account_details(full_text, file.name)
                account_summary.append(account_info)

                with pdfplumber.open(file) as pdf:

                    for page in pdf.pages:

                        # ----------------------------
                        # TRY TABLE EXTRACTION FIRST
                        # ----------------------------
                        tables = page.extract_tables()

                        if tables:
                            for table in tables:

                                df = pd.DataFrame(table).dropna(how="all")
                                if df.empty:
                                    continue

                                header_row = None
                                for idx in range(min(5, len(df))):
                                    row_text = " ".join(df.iloc[idx].astype(str)).lower()
                                    if "date" in row_text and "balance" in row_text:
                                        header_row = idx
                                        break

                                if header_row is None:
                                    continue

                                df.columns = df.iloc[header_row]
                                df = df[header_row + 1:].reset_index(drop=True)

                                for _, row in df.iterrows():

                                    amount_raw = ""
                                    debit = ""
                                    credit = ""

                                    # Separate Debit/Credit columns
                                    debit_col = next((c for c in df.columns if "debit" in str(c).lower() or "withdraw" in str(c).lower()), None)
                                    credit_col = next((c for c in df.columns if "credit" in str(c).lower() or "deposit" in str(c).lower()), None)
                                    balance_col = next((c for c in df.columns if "balance" in str(c).lower()), None)
                                    date_col = next((c for c in df.columns if "date" in str(c).lower()), None)
                                    desc_col = next((c for c in df.columns if any(x in str(c).lower() for x in ["narration","description","particular","reference"])), None)
                                    amount_col = next((c for c in df.columns if "amount" in str(c).lower()), None)

                                    if debit_col or credit_col:
                                        debit = row.get(debit_col, "")
                                        credit = row.get(credit_col, "")
                                    elif amount_col:
                                        amount_raw = row.get(amount_col, "")
                                        debit, credit = split_dr_cr(amount_raw)

                                    all_transactions.append({
                                        "Date": row.get(date_col, ""),
                                        "Description": row.get(desc_col, ""),
                                        "Debit": debit,
                                        "Credit": credit,
                                        "Balance": row.get(balance_col, ""),
                                        "Account Number": account_info["Account Number"],
                                        "Currency": account_info["Currency"],
                                        "Bank Name": bank_name,
                                        "Source File": file.name
                                    })

                        # ----------------------------
                        # FALLBACK TEXT PARSING (BOA FIX)
                        # ----------------------------
                        else:

                            lines = page.extract_text().split("\n")

                            for line in lines:
                                if re.match(r"\d{2}[A-Z]{3}\d{2}", line.strip()):
                                    parts = re.split(r"\s{2,}", line)
                                    if len(parts) >= 5:

                                        posted_date = parts[0]
                                        description = parts[3]
                                        amount_raw = parts[-2]
                                        balance = parts[-1]

                                        debit, credit = split_dr_cr(amount_raw)

                                        all_transactions.append({
                                            "Date": posted_date,
                                            "Description": description,
                                            "Debit": debit,
                                            "Credit": credit,
                                            "Balance": balance,
                                            "Account Number": account_info["Account Number"],
                                            "Currency": account_info["Currency"],
                                            "Bank Name": bank_name,
                                            "Source File": file.name
                                        })

            except Exception as e:
                st.error(f"Error processing {file.name} → {e}")

            progress.progress((i + 1) / len(bank_files))

        # --------------------------------------------------
        # FINAL DATAFRAME
        # --------------------------------------------------

        if all_transactions:

            df = pd.DataFrame(all_transactions)

            for col in ["Debit", "Credit", "Balance"]:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

            acc_df = pd.DataFrame(account_summary).drop_duplicates()

            st.success("Bank Statements Processed Successfully ✅")

            st.subheader("📄 Account Summary")
            st.dataframe(acc_df, use_container_width=True)

            st.subheader("📊 Transactions")
            st.dataframe(df, use_container_width=True)

            col1, col2 = st.columns(2)
            col1.metric("Total Debit", f"₹ {df['Debit'].sum():,.2f}")
            col2.metric("Total Credit", f"₹ {df['Credit'].sum():,.2f}")

            # EXPORT
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                acc_df.to_excel(writer, index=False, sheet_name="Account Summary")
                df.to_excel(writer, index=False, sheet_name="Transactions")

            st.download_button(
                "⬇ Download Final Bank Report",
                output.getvalue(),
                "Universal_Bank_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )