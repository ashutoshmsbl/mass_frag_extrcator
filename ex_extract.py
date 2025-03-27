import streamlit as st
import pandas as pd

# Title of the App
st.title("13C Mass Fragment Data Extraction Tool")

# File Uploader
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    # Read Excel File
    try:
        xl = pd.ExcelFile(uploaded_file)
        sheets = xl.sheet_names

        # Select Sheets
        selected_sheets = st.multiselect("Select Sheets", sheets, default=sheets)

        # Load column names
        df_sample = xl.parse(sheets[0])
        df_sample.columns = [col.strip() for col in df_sample.columns]  # Remove spaces
        compounds = [col for col in df_sample.columns if "m/z" not in col.lower() and "unnamed" not in col.lower()]

        # Select Compound
        compound = st.selectbox("Select Compound", compounds)

        # m/z Ranges
        mz_ranges = []
        mz_min = st.text_input("Enter m/z Min", key="mz_min")
        mz_max = st.text_input("Enter m/z Max", key="mz_max")

        if st.button("Add Range"):
            try:
                min_val, max_val = int(mz_min), int(mz_max)
                if min_val < max_val:
                    mz_ranges.append((min_val, max_val))
                    st.success(f"Range {min_val} - {max_val} added!")
                else:
                    st.warning("⚠️ m/z Min should be less than m/z Max.")
            except ValueError:
                st.warning("⚠️ Enter valid numerical values.")

        # Show added ranges
        if mz_ranges:
            st.write("### Selected m/z Ranges:")
            for mz in mz_ranges:
                st.write(f"{mz[0]} - {mz[1]}")

        # Remove m/z Range
        if mz_ranges and st.button("Remove Last Range"):
            mz_ranges.pop()
            st.success("Last range removed!")

        # Process Data
        if st.button("Extract Data"):
            if not selected_sheets or not mz_ranges:
                st.warning("⚠️ Please select at least one sheet and add m/z ranges.")
            else:
                extracted_data = extract_mz_abundance(uploaded_file, compound, selected_sheets, mz_ranges)

                if extracted_data is not None:
                    output_file = f"{compound}_extracted_data.xlsx"
                    extracted_data.to_excel(output_file, index=False)

                    with open(output_file, "rb") as f:
                        st.download_button(label="Download Extracted Data", data=f, file_name=output_file, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.warning(f"⚠️ No data found for compound '{compound}' in the selected sheets.")

    except Exception as e:
        st.error(f"⚠️ Error loading file: {e}")
