import streamlit as st
import pandas as pd
import io

def extract_mz_abundance(file, amino_acid, selected_sheets, mz_ranges):
    xl = pd.ExcelFile(file)
    output_data = {}

    for sheet in selected_sheets:
        df = xl.parse(sheet)

        if 'm/z' not in df.columns or amino_acid not in df.columns:
            st.warning(f"Required columns not found in sheet: {sheet}")
            continue

        df_filtered = pd.DataFrame()
        for mz_min, mz_max in mz_ranges:
            df_temp = df[(df['m/z'].between(mz_min, mz_max))][['m/z', amino_acid]]
            df_temp = df_temp.rename(columns={amino_acid: f"{amino_acid}_{sheet}"})
            df_filtered = pd.concat([df_filtered, df_temp], ignore_index=True)

        if not df_filtered.empty:
            output_data[sheet] = df_filtered

    if output_data:
        combined_df = pd.concat(output_data.values(), axis=1)
        return combined_df
    else:
        return None

# Streamlit UI
st.title("Amino Acid Data Extraction Tool")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    xl = pd.ExcelFile(uploaded_file)
    sheets = xl.sheet_names
    df_sample = xl.parse(sheets[0])
    amino_acids = [col for col in df_sample.columns if col != 'm/z']

    amino_acid = st.selectbox("Select an Amino Acid", amino_acids)
    selected_sheets = st.multiselect("Select Sheets", sheets)

    mz_ranges = []
    st.write("### Add m/z Ranges")
    mz_min = st.number_input("Min m/z", value=100, step=1)
    mz_max = st.number_input("Max m/z", value=200, step=1)
    
    if st.button("Add Range"):
        if mz_min < mz_max:
            mz_ranges.append((mz_min, mz_max))
            st.session_state["mz_ranges"] = mz_ranges
        else:
            st.error("Min m/z should be less than Max m/z.")

    if "mz_ranges" in st.session_state:
        st.write("Selected m/z Ranges:", st.session_state["mz_ranges"])

    if st.button("Process Data"):
        if not selected_sheets or not mz_ranges:
            st.warning("Please select at least one sheet and one m/z range.")
        else:
            with st.spinner("Processing..."):
                result = extract_mz_abundance(uploaded_file, amino_acid, selected_sheets, st.session_state["mz_ranges"])
                if result is not None:
                    st.success("Extraction Completed!")
                    st.dataframe(result)

                    # Save to Excel and provide download link
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        result.to_excel(writer, index=False)
                    output.seek(0)

                    st.download_button("Download Excel File", output, f"{amino_acid}_extracted.xlsx", "application/vnd.ms-excel")
                else:
                    st.error("No valid data found.")
