import streamlit as st
import pandas as pd
import io

# Function to extract m/z data
def extract_mz_abundance(uploaded_file, compound, selected_sheets, mz_ranges):
    # Read Excel file directly from uploaded file
    xl = pd.ExcelFile(uploaded_file)
    output_data = {}
    mz_values = set()

    for sheet in selected_sheets:
        df = xl.parse(sheet)

        if 'm/z' not in df.columns or compound not in df.columns:
            st.warning(f"⚠️ Required columns not found in sheet: {sheet}")
            continue

        df_filtered = pd.DataFrame()
        for mz_min, mz_max in mz_ranges:
            df_temp = df[df['m/z'].between(mz_min, mz_max)][['m/z', compound]]
            df_temp = df_temp.rename(columns={compound: f"{compound}_{sheet}"})
            df_filtered = pd.concat([df_filtered, df_temp], ignore_index=True)
            mz_values.update(df_temp['m/z'].tolist())

        if not df_filtered.empty:
            output_data[sheet] = df_filtered.set_index('m/z')

    if output_data:
        combined_df = pd.concat(output_data.values(), axis=1)
        combined_df.reset_index(inplace=True)
        return combined_df
    else:
        return None

# Streamlit UI
st.title("13C Mass Fragment Data Extraction Tool")

# Initialize session state for m/z ranges
if 'mz_ranges' not in st.session_state:
    st.session_state.mz_ranges = []
if 'selected_compound' not in st.session_state:
    st.session_state.selected_compound = None

# File Upload
uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

if uploaded_file:
    try:
        # Read Excel file using Pandas
        xl = pd.ExcelFile(uploaded_file)
        sheets = xl.sheet_names
        df_sample = xl.parse(sheets[0])

        # Remove "m/z:" and "Unnamed:" from compound list
        compounds = [col for col in df_sample.columns if not (col.lower().startswith("m/z") or "unnamed" in col.lower())]

        # Compound Selection
        compound = st.selectbox("Select Compound", compounds, key='compound_selection')
        
        # Reset m/z ranges only if a new compound is selected
        if st.session_state.selected_compound != compound:
            st.session_state.mz_ranges = []
        st.session_state.selected_compound = compound

        # Sheet Selection
        st.write("### Select Data files")
        select_all_sheets = st.checkbox("Select All Sheets")
        selected_sheets = st.multiselect("Choose Sheets", sheets, default=sheets if select_all_sheets else [])

        # m/z Range Input
        st.write("### Add m/z Ranges")
        mz_min = st.number_input("Min m/z", value=100, step=1)
        mz_max = st.number_input("Max m/z", value=200, step=1)

        if st.button("Add Range"):
            if mz_min < mz_max:
                st.session_state.mz_ranges.append((mz_min, mz_max))
                st.success(f"✅ Added Range: {mz_min}-{mz_max}")
            else:
                st.error("⚠️ Min m/z should be less than Max m/z")

        # Display added ranges with remove option
        if st.session_state.mz_ranges:
            st.write("#### Selected m/z Ranges:")
            for i, r in enumerate(st.session_state.mz_ranges):
                col1, col2 = st.columns([4, 1])
                col1.write(f"{r[0]} - {r[1]}")
                if col2.button(f"❌ Remove", key=f"remove_{i}"):
                    st.session_state.mz_ranges.pop(i)
                    st.experimental_rerun()  # Refresh UI to reflect changes

        # Process and Save Data
        if st.button("Process Data"):
            if not selected_sheets or not st.session_state.mz_ranges:
                st.error("⚠️ Please select at least one sheet and add m/z ranges.")
            else:
                df_result = extract_mz_abundance(uploaded_file, compound, selected_sheets, st.session_state.mz_ranges)

                if df_result is not None:
                    st.success("✅ Data processed successfully!")

                    # Save to Excel in-memory
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        df_result.to_excel(writer, index=False, sheet_name="Results")
                        writer.close()

                    output.seek(0)

                    # Download button for Excel file
                    st.download_button("⬇️ Download Processed Data", output, f"{compound}_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.warning("⚠️ No matching data found.")

    except Exception as e:
        st.error(f"⚠️ Error loading file: {e}")
