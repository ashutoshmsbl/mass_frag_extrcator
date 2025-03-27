import streamlit as st
import pandas as pd
import io

# Function to extract m/z data
def extract_mz_abundance(uploaded_file, amino_acid, selected_sheets, mz_ranges):
    # Read Excel file directly from uploaded file
    xl = pd.ExcelFile(uploaded_file)
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
st.title("13C Mass Fragment Data Extraction Tool")

# Initialize session state for mz_ranges
if 'mz_ranges' not in st.session_state:
    st.session_state.mz_ranges = []

# File Upload
uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

if uploaded_file:
    # Read Excel file using Pandas
    xl = pd.ExcelFile(uploaded_file)
    sheets = xl.sheet_names
    df_sample = xl.parse(sheets[0])
    amino_acids = [col for col in df_sample.columns if col != 'm/z']

    # Amino Acid Selection
    amino_acid = st.selectbox("Select an Amino Acid", amino_acids)

    # Sheet Selection
    st.write("### Select Sheets")
    select_all_sheets = st.checkbox("Select All Sheets")
    selected_sheets = st.multiselect("Choose Sheets", sheets, default=sheets if select_all_sheets else [])

    # m/z Range Input
    st.write("### Add m/z Ranges")
    mz_min = st.number_input("Min m/z", value=100, step=1)
    mz_max = st.number_input("Max m/z", value=200, step=1)

    if st.button("Add Range"):
        if mz_min < mz_max:
            st.session_state.mz_ranges.append((mz_min, mz_max))
            st.success(f"Added Range: {mz_min}-{mz_max}")
        else:
            st.error("Min m/z should be less than Max m/z")

    # Display added ranges
    if st.session_state.mz_ranges:
        st.write("#### Selected m/z Ranges:")
        for r in st.session_state.mz_ranges:
            st.write(f"{r[0]} - {r[1]}")

    # Process and Save Data
    if st.button("Process Data"):
        if not selected_sheets or not st.session_state.mz_ranges:
            st.error("Please select at least one sheet and add m/z ranges.")
        else:
            df_result = extract_mz_abundance(uploaded_file, amino_acid, selected_sheets, st.session_state.mz_ranges)

            if df_result is not None:
                st.success("Data processed successfully!")

                # Save to Excel in-memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df_result.to_excel(writer, index=False, sheet_name="Results")
                    writer.close()
                
                output.seek(0)
                
                # Download button for Excel file
                st.download_button("Download Processed Data", output, f"{amino_acid}_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("No matching data found.")
