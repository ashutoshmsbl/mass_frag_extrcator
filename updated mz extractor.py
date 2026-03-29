import streamlit as st
import pandas as pd
import io

# Predefined metabolite ranges
predefined_ranges = {
    "Ala": [(317,320),(302,305),(260,263),(232,235),(158,161)],
    "Gly": [(303,306),(288,291),(246,249),(218,221),(144,147),(302,305)],
    "Val": [(345,350),(330,335),(288,293),(260,265),(186,191),(302,307)],
    "Pro": [(343,348),(328,333),(286,291),(258,263),(184,189),(301,306)],
    "Met": [(377,382),(362,367),(320,325),(292,297),(218,223),(302,307)],
    "Phe": [(393,400),(378,385),(336,343),(308,315),(234,241),(302,309)],
    "Ser": [(447,450),(432,435),(390,393),(362,365),(288,291),(302,305)],
    "Thr": [(461,466),(446,451),(404,409),(376,381),(302,307)],
    "Lys": [(488,495),(473,480),(431,438),(403,410),(329,336),(302,309)],
    "His": [(497,504),(482,489),(440,447),(412,419),(338,345),(302,309),(195,202)],
    "Glu": [(489,494),(474,479),(432,437),(404,409),(330,335),(302,307),(187,192)],
    "Asp": [(475,480),(460,465),(418,423),(390,395),(316,321),(302,307),(173,178)],
}

# Function to extract m/z data
def extract_mz_abundance(uploaded_file, compound, selected_sheets, mz_ranges):
    xl = pd.ExcelFile(uploaded_file)
    output_data = {}

    for sheet in selected_sheets:
        df = xl.parse(sheet)

        if 'm/z' not in df.columns or compound not in df.columns:
            st.warning(f"⚠️ Required columns not found in sheet: {sheet}")
            continue

        df_filtered = pd.DataFrame()
        for mz_min, mz_max in mz_ranges:
            df_temp = df[df['m/z'].between(mz_min, mz_max)][['m/z', compound]]
            df_temp = df_temp.rename(columns={compound: f"{sheet}"})
            df_filtered = pd.concat([df_filtered, df_temp], ignore_index=True)

        if not df_filtered.empty:
            output_data[sheet] = df_filtered.set_index('m/z')

    if output_data:
        combined_df = pd.concat(output_data.values(), axis=1)
        combined_df.reset_index(inplace=True)
        return combined_df
    else:
        return None

# UI
st.title("13C Mass Fragment Data Extraction Tool")

if 'mz_ranges' not in st.session_state:
    st.session_state.mz_ranges = []

uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

if uploaded_file:
    xl = pd.ExcelFile(uploaded_file)
    sheets = xl.sheet_names
    df_sample = xl.parse(sheets[0])

    compounds = [col for col in df_sample.columns if not (col.lower().startswith("m/z") or "unnamed" in col.lower())]

    compound = st.selectbox("Select Compound", compounds)

    # Predefined ranges option
    if compound in predefined_ranges:
        if st.button("Load Predefined Ranges"):
            st.session_state.mz_ranges = predefined_ranges[compound]

    st.write("### Select Data files")
    select_all = st.checkbox("Select All Sheets")
    selected_sheets = st.multiselect("Choose Sheets", sheets, default=sheets if select_all else [])

    # Range input (text format)
    st.write("### Add Range (format: 300-345)")
    range_input = st.text_input("Enter range")

    if st.button("Add Range"):
        try:
            parts = range_input.replace("–","-").split("-")
            mz_min, mz_max = int(parts[0]), int(parts[1])
            if mz_min < mz_max:
                st.session_state.mz_ranges.append((mz_min, mz_max))
                st.success(f"Added: {mz_min}-{mz_max}")
            else:
                st.error("Min must be < Max")
        except:
            st.error("Invalid format. Use 300-345")

    # Display ranges
    if st.session_state.mz_ranges:
        st.write("### Selected Ranges")
        for i, r in enumerate(st.session_state.mz_ranges):
            col1, col2 = st.columns([4,1])
            col1.write(f"{r[0]}-{r[1]}")
            if col2.button("❌", key=i):
                st.session_state.mz_ranges.pop(i)
                st.rerun()

    if st.button("Process Data"):
        if not selected_sheets or not st.session_state.mz_ranges:
            st.error("Select sheets and ranges")
        else:
            df_result = extract_mz_abundance(uploaded_file, compound, selected_sheets, st.session_state.mz_ranges)
            if df_result is not None:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df_result.to_excel(writer, index=False)
                output.seek(0)
                st.download_button("Download", output, f"{compound}.xlsx")
            else:
                st.warning("No data found")
