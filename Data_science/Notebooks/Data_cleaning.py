
import numpy as np
import pandas as pd
import os


'''all this code is trying to prevent the file not found 
error by using the oparating system nodule 
to joins foleders in a correct order'''


current_folder = os.path.dirname(os.path.abspath(__file__))

data_science_folder = current_folder
while os.path.basename(data_science_folder) != "Data_science":
    parent = os.path.dirname(data_science_folder)
    if parent == data_science_folder:
        pass
        # We reached the very top of the drive and never found it
        #raise Exception("Could not find a folder  ")
    data_science_folder = parent

raw_folder = os.path.join(data_science_folder, "Data", "raw")
processed_folder = os.path.join(data_science_folder, "Data", "processed")
docs_folder = os.path.join(data_science_folder, "Docs")

# thIS where the csv files are, os.path.basename(raw_folder))

# ---------------------------------------------------------
# STEP 1: Load the three CSV files
# ---------------------------------------------------------
print("STEP 1: Loading the data")

utilities = pd.read_csv(os.path.join(raw_folder, "utilities.csv"))
substations = pd.read_csv(os.path.join(raw_folder, "substations.csv"))
lines = pd.read_csv(os.path.join(raw_folder, "lines.csv"))

# Let's look at the size of each file
print("Utilities file has", len(utilities), "rows")
print("Substations file has", len(substations), "rows")
print("Lines file has", len(lines), "rows")


# ---------------------------------------------------------
# STEP 2: Check for missing values
# ---------------------------------------------------------
print("STEP 2: Checking for missing values")

# .isnull() checks each cell and returns True if it is empty
# .sum() then counts how many True values are in each column
print("Missing values in utilities:")
print(utilities.isnull().sum())

print("Missing values in substations:")
print(substations.isnull().sum())

print("Missing values in lines:")
print(lines.isnull().sum())

# Now we decide what to do about missing values.
# We do NOT just guess numbers randomly. We use simple, explainable rules:

# Rule 1: If the ID column is missing, we cannot use that row at all,
# because we would not know what record it belongs to.

utilities = utilities.dropna(subset=["Utility ID"])
substations = substations.dropna(subset=["Substation ID"])
lines = lines.dropna(subset=["Line ID"])

# Rule 2: If Latitude or Longitude is missing, we do NOT invent a
# location. We just leave it empty (NaN) so it is not used in mapping,
# but we still keep the row for other analysis.
# (No code needed here, we simply choose not to fill these columns.)

# Rule 3: For number columns like Voltage and Capacity, if a value is
# missing, we fill it with the average (mean) of that column.
# This is a simple and common beginner approach.
if substations["Voltage (kV)"].isnull().sum() > 0:
    average_voltage = substations["Voltage (kV)"].mean()
    substations["Voltage (kV)"] = substations["Voltage (kV)"].fillna(average_voltage)
    print("Filled missing Voltage values with the average:", average_voltage)

if substations["Capacity (MVA)"].isnull().sum() > 0:
    average_capacity = substations["Capacity (MVA)"].mean()
    substations["Capacity (MVA)"] = substations["Capacity (MVA)"].fillna(average_capacity)
    print("Filled missing Capacity values with the average:", average_capacity)

# Rule 4: For text/category columns like Status, we fill missing values
# with the word "Unknown" instead of guessing.
if substations["Status"].isnull().sum() > 0:
    substations["Status"] = substations["Status"].fillna("Unknown")
    print("Filled missing Status values with 'Unknown'")


# ---------------------------------------------------------
# STEP 3: Validate the data
# ---------------------------------------------------------

# Check 3b: Look for duplicate rows (the exact same row appearing twice)
duplicate_substations = substations.duplicated().sum()
duplicate_lines = lines.duplicated().sum()
print("Duplicate rows in substations:", duplicate_substations)
print("Duplicate rows in lines:", duplicate_lines)

# COordinate checks

low_latitude = 4.0
high_latitude = 15.0
low_longitude = -15.0
high_longitude = 5.0

coordinate_problems = 0
for index, row in substations.iterrows():
    lat = row["Latitude"]
    lon = row["Longitude"]
    if lat < low_latitude or lat > high_latitude:
        print("Problem: Substation ID", row["Substation ID"], "has a strange Latitude:", lat)
        coordinate_problems = coordinate_problems + 1
    if lon < low_longitude or lon > high_longitude:
        print("Problem: Substation ID", row["Substation ID"], "has a strange Longitude:", lon)
        coordinate_problems = coordinate_problems + 1

if coordinate_problems == 0:
    print("Coordinates checked")

# Check 3d: Make sure number columns are really stored as numbers
print("Data type of Latitude column:", substations["Latitude"].dtype)
print("Data type of Longitude column:", substations["Longitude"].dtype)
print("Data type of Voltage column:", substations["Voltage (kV)"].dtype)
print("Data type of Capacity column:", substations["Capacity (MVA)"].dtype)


# ---------------------------------------------------------
# STEP 4: Save the cleaned files
# ---------------------------------------------------------
print("\nSTEP 4: Saving cleaned files")

# to_csv() will NOT create folders for you - if "processed" or "Docs"
# don't exist yet on disk, it will crash. So we create them here first,
# if they aren't already there. exist_ok=True means "don't complain if
# the folder is already there, just carry on."
os.makedirs(processed_folder, exist_ok=True)
os.makedirs(docs_folder, exist_ok=True)

utilities.to_csv(os.path.join(processed_folder, "utilities_clean.csv"), index=False)
substations.to_csv(os.path.join(processed_folder, "substations_clean.csv"), index=False)
lines.to_csv(os.path.join(processed_folder, "lines_clean.csv"), index=False)

print("Saved cleaned files into Data/processed/")


# ---------------------------------------------------------
# STEP 5: Basic statistics summary
# ---------------------------------------------------------
print("\nSTEP 5: Basic statistics summary")

# .describe() gives count, mean, min, max, etc. for number columns
print(utilities.describe(include="all"))
print(substations.describe(include="all"))
print(lines.describe(include="all"))

# Save this summary into a text file as a deliverable
summary_file = open(os.path.join(docs_folder, "basic_statistics_summary.txt"), "w")
summary_file.write("UTILITIES SUMMARY\n")
summary_file.write(str(utilities.describe(include="all")))
summary_file.write("\n\nSUBSTATIONS SUMMARY\n")
summary_file.write(str(substations.describe(include="all")))
summary_file.write("\n\nLINES SUMMARY\n")
summary_file.write(str(lines.describe(include="all")))
summary_file.close()

print("Saved basic_statistics_summary.txt into Docs/")

print("\nAll done! Check the Data/processed folder and Docs folder for the results.")